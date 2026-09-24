# some are made by Deepseek-v4-flash-vison-exp at Deepseek Harness
from pathlib import Path
import hashlib
import re
import shutil
import json
import inspect
import asyncio
from traceback import format_exc
from uuid import uuid4
from xme.xmetools.videotools import extract_video_links, extract_and_download, parse_video
from nonebot import CommandSession, MessageSegment

from nonebot.log import logger
from xme.xmetools.filetools import dict_to_file, get_local_file_url, text_to_file, history_file_name, is_safe_custom_name, safe_join, TooManyFilesError, DirectoryTooLargeError
from xme.xmetools.texttools import (IMAGE_PLACEHOLDER_RE, get_images_from_message,
                                        image_placeholder)
from xme.xmetools.debugtools import debug_msg
from xme.xmetools.msgtools import is_text_can_send, send_session_msg, setup_logger
from xme.xmetools.bottools import get_user_name
from xme.xmetools.timetools import get_time_now, Timer
from xme.xmetools import jsontools
from xme.xmetools.jsontools import read_from_path
from character import get_message
from xme.plugins.commands.xme_user.classes import user as u
from xme.xmetools.videotools.core import VideoExtractResult
from .constants import (
    __plugin_name__,
    MAX_TOOL_CALL_TIMES,
    COMPRESS_TRIGGER_RATIO,
    CONTEXT_TOKEN_CHARS,
    CONTEXT_KEEP_RECENT,
    COMPRESS_MAX_LENGTH,
    THINKING_NOTE_MAX_LENGTH,
    THINKING_NOTE_INPUT_CHARS,
    CONTEXT_LIMIT_DEFAULT,
    FOLD_HARD_RATIO,
    FOLD_KEEP_RECENT_ASSISTANTS,
    FOLD_KEEP_RECENT_TOOLS,
    FOLD_TRIGGER_RATIO,
    FLASH_MODEL,
    MAX_HISTORY_FILE_COUNTS,
    MAX_HISTORY_FILES_SIZE,
)
from . import history
from . import constants
from . import credits
from .llm import (
    ChatResult, LLMError, LLMErrorKind, message_to_dict,
)
from .llm import registry
from . import share
from .session import AISession, current_storage, normal_insert_enabled
from .functions._common import ImageToolResult

ai_logger = setup_logger("aihelper", "ai_helper_log")


# 文本中的媒体直链（.mp4 等结尾，允许带查询参数）：用户消息里出现时直接作为
# video_url 附入（LLM 已持有可用直链，无需下载）
_DIRECT_VIDEO_RE = re.compile(
    r"https?://[^\s（）()【】\[\]<>\"']+?\.(?:mp4|webm|mov|m4v|avi|mkv|flv)(?:\?[^\s（）()【】\[\]<>\"']*)?",
    re.IGNORECASE)

class InsertInterrupted(Exception):
    """共享会话有成员插入消息：当前生成被主动打断，已积累的上下文保留待重启。"""


def _snapshot_path(user_id) -> Path:
    """进行中会话的快照文件：data/ai_historys/<用户id>/.unfinished.json。"""
    return history.HISTORY_ROOT / str(user_id) / ".unfinished.json"


def load_snapshot(user_id) -> dict | None:
    """读取会话快照（异常中断的对话）；不存在/损坏返回 None。"""
    data = jsontools.read_from_path(_snapshot_path(user_id))
    return data if isinstance(data, dict) and data.get("messages") else None


def clear_snapshot(user_id) -> None:
    """删除会话快照（对话正常结束后调用）。"""
    _snapshot_path(user_id).unlink(missing_ok=True)


def estimate_context_tokens(summary, normals: list[dict]) -> int:
    """按字符长度估算会话历史的上下文 token 占用（压缩触发与占用展示共用的单点）。

    只累计正文文本（摘要 + 每条问答），技能内容与工具标记不计——偏小估算由
    轮内按真实 prompt_tokens 的折叠兜底。
    """
    total = len(summary or "")
    for it in normals:
        asks = it.get("asks") or []
        ask_text = "".join(str(a.get("text", "")) for a in asks) if asks else str(it.get("ask", ""))
        total += len(ask_text) + len(str(it.get("ans", "")))
        total += len(str(it.get("thinking", "")))   # 思路笔记会注入上下文，一并计入
    return int(total / CONTEXT_TOKEN_CHARS)


def _fold_early_context(messages: list, *, fold_tools: bool = False) -> tuple[int, list[str]]:
    """轮内上下文折叠：删除最早若干轮 assistant 的 reasoning_content（保留 content/tool_calls，
    协议结构不变；等价于 GLM-4.5 之前的标准消息形态，API 仍接受，代价仅是那几轮的推理连贯性
    与缓存命中）；fold_tools=True 时再把早期 tool 消息的 content 替换为可重取的占位符
    （tool_call_id 必须保留——协议要求 tool 消息与 tool_call 一一对应）。

    就地修改传入的 messages，返回 (折叠释放的估算字符量, 被丢弃的 reasoning 列表)，
    调用方负责把丢弃内容归档。幂等：无可折叠内容时返回 (0, [])。
    """
    freed = 0
    dropped: list[str] = []
    assistant_idx = [i for i, m in enumerate(messages)
                     if isinstance(m, dict) and m.get("role") == "assistant"]
    for i in assistant_idx[:-FOLD_KEEP_RECENT_ASSISTANTS] if FOLD_KEEP_RECENT_ASSISTANTS else assistant_idx:
        reasoning = messages[i].get("reasoning_content")
        if reasoning:
            messages[i].pop("reasoning_content", None)
            freed += len(str(reasoning))
            dropped.append(str(reasoning))
    if fold_tools:
        tool_idx = [i for i, m in enumerate(messages)
                    if isinstance(m, dict) and m.get("role") == "tool"]
        for i in tool_idx[:-FOLD_KEEP_RECENT_TOOLS] if FOLD_KEEP_RECENT_TOOLS else tool_idx:
            content = messages[i].get("content")
            if isinstance(content, str) and len(content) > 200 and not content.startswith("[早期工具结果已折叠"):
                messages[i]["content"] = (f"[早期工具结果已折叠（原 {len(content)} 字）；"
                                          f"如需数据请重新调用该工具]")
                freed += len(content)
    return freed, dropped


def build_user_content(text: str, image_urls: list[str] | None = None,
                       extra_parts: list | None = None) -> list:
    """组装 GLM 多模态 user content：文本段 + 图片段 + 额外段（如视频文件）。

    发起者的原始输入与共享会话的插入消息共用此封装，保证两种输入形态一致。
    """
    parts: list = [{"type": "text", "text": text}]
    parts += [{"type": "image_url", "image_url": {"url": url}} for url in (image_urls or [])]
    parts += list(extra_parts or [])
    return parts


# 工具注入媒体的标记文本（注入的 user 消息首段；剥离时据此识别"本轮注入的媒体块"）
_INJECT_MEDIA_NOTE = "[以上工具返回的图片/附件已附在本消息中，请结合上方工具结果处理]"
# 媒体加载失败时给模型看的显式说明（避免其误以为看到了内容）
_MEDIA_LOAD_FAILED_NOTE = ("[注意：本次工具附带的媒体无法被模型加载，已从输入中移除，"
                           "请勿据此作答或声称已看到内容]")


def replace_media_markers(text: str, markers: list[str], urls: list[str]) -> str:
    """把文本里的媒体标记（CQ 码或占位符）按顺序替换成对应直链。

    给"看不了媒体的模型"保留原文用：模型可以拿这些直链去调 view_image / view_video。
    标记数与链接数不一致说明对应关系不可靠，此时原样返回（宁可保留标记也不错配链接）。
    """
    if len(markers) != len(urls):
        ai_logger.warning(f"媒体标记数({len(markers)})与直链数({len(urls)})不一致，跳过替换")
        return text
    for marker, url in zip(markers, urls):
        text = text.replace(marker, url)
    return text


def build_insert_content(ins_label: str, ins, can_see_image: bool) -> list:
    """组装一条插入消息的 user content。

    模型能看图 → 图片仍作为段附入（文本保留占位符）；看不了 → 占位符按顺序换成
    已解析的直链、不附段，并附一条工具提示（模型可自己调 view_image 查看）。
    """
    ins_text = f"{ins_label}{ins.text}"
    if can_see_image or not ins.image_urls:
        return build_user_content(ins_text, list(ins.image_urls))
    ins_text = replace_media_markers(
        ins_text, IMAGE_PLACEHOLDER_RE.findall(ins_text), list(ins.image_urls))
    return build_user_content(f"{ins_text}\n{media_hint(['view_image'])}", [])


def media_hint(tools: list[str]) -> str:
    """模型看不了媒体时给它的操作提示（告知可用哪些工具查看直链）。"""
    return get_message("plugins", __plugin_name__, "media_cannot_view_hint",
                       tools="、".join(tools))


def _find_injected_media_blocks(messages: list) -> set[int]:
    """找出"本轮工具注入的媒体块"的消息索引：注入的 user 消息 + 其前紧邻的 tool 消息。

    注入块是本次重试才第一次进入模型视野的消息，媒体加载失败时必须显式告知；
    其余（历史消息里的旧媒体）模型早已见过，静默移除即可。
    """
    idxs: set[int] = set()
    for i, m in enumerate(messages):
        if not isinstance(m, dict) or m.get("role") != "user":
            continue
        content = m.get("content")
        if not isinstance(content, list) or not content:
            continue
        first = content[0]
        if not (isinstance(first, dict) and first.get("text") == _INJECT_MEDIA_NOTE):
            continue
        idxs.add(i)
        j = i - 1
        while j >= 0 and isinstance(messages[j], dict) and messages[j].get("role") == "tool":
            idxs.add(j)
            j -= 1
    return idxs


_SNAPSHOT_MEDIA_PLACEHOLDER = "（历史媒体未保留）"


def _strip_media_for_snapshot(messages: list) -> list:
    """生成"用于写快照"的副本：把媒体段换成中性占位文本。

    快照里的媒体链接注定失效（本地限时链接 TTL 只有 30 秒、QQ CDN 直链也会过期），
    恢复时必然报"图片无法解析"并终止对话，所以快照不保留媒体；原 messages 深拷贝后
    再改，当前轮对话里的图片照常可用。
    """
    try:
        copy = json.loads(json.dumps(messages, ensure_ascii=False))
    except (TypeError, ValueError):
        return messages   # 理论上不会发生（能写盘就能序列化），兜底不阻断保存
    for m in copy:
        if not isinstance(m, dict):
            continue
        content = m.get("content")
        if not isinstance(content, list):
            continue
        m["content"] = [
            {"type": "text", "text": _SNAPSHOT_MEDIA_PLACEHOLDER}
            if (isinstance(p, dict) and p.get("type") not in (None, "text")) else p
            for p in content
        ]
    return copy


def _strip_unloadable_images(messages: list) -> int:
    """移除上下文里加载失败的媒体段（就地修改），返回移除数量。

    用于 GLM 1210（媒体输入解析失败）兜底。两种情形区别对待：
    - 本轮工具新注入的媒体块：模型在这次重试才第一次看到它们，必须在工具结果上显式
      注明"媒体无法加载"——否则模型会误以为看到了内容（静默剥离的误判来源）；
    - 历史消息里的旧媒体（用户早期发的图等）：模型已经见过，静默移除即可，不加失效措辞。
    非 text 段一律移除（含未知类型），避免漏网段导致重试再次 1210。
    """
    injected = _find_injected_media_blocks(messages)
    removed = 0
    for i, m in enumerate(messages):
        if not isinstance(m, dict):
            continue
        content = m.get("content")
        if isinstance(content, str):
            # 注入块里的 tool 结果（纯字符串）：追加显式说明，保留工具原有文本
            if i in injected and m.get("role") == "tool" and _MEDIA_LOAD_FAILED_NOTE not in content:
                m["content"] = content + "\n" + _MEDIA_LOAD_FAILED_NOTE
            continue
        if not isinstance(content, list):
            continue
        new_parts = [p for p in content
                     if not (isinstance(p, dict) and p.get("type") not in (None, "text"))]
        dropped = len(content) - len(new_parts)
        if not dropped:
            continue
        if i in injected:
            # 注入的 user 消息：标记文本本身陈述了"已附在输入中"，必须替换而非保留
            m["content"] = [{"type": "text", "text": _MEDIA_LOAD_FAILED_NOTE}]
        else:
            # 历史媒体：静默（仅当消息因此变空时补中性占位维持结构）
            m["content"] = new_parts or [{"type": "text", "text": "（媒体）"}]
        removed += dropped
    return removed

class _AISTOP:
    def __repr__(self):
        return "AISTOP"
AISTOP = _AISTOP()

def _validate_tools(tools: list) -> None:
    """校验工具 schema 的基本合法性。
    """
    for tool in tools:
        fn = tool.get("function", {})
        name = fn.get("name", "?")
        if not isinstance(fn.get("description"), str):
            raise ValueError(f"tools.json 工具 {name} 的 description 必须是字符串，"
                             f"实际为 {type(fn.get('description')).__name__}（list/tuple 会导致 API 1210）")
        params = fn.get("parameters") or {}
        if params.get("type") != "object":
            raise ValueError(f"tools.json 工具 {name} 的 parameters.type 必须是 object")
        properties = params.get("properties") or {}
        for pname, prop in properties.items():
            if not isinstance(prop.get("description"), str):
                raise ValueError(f"tools.json 工具 {name} 的参数 {pname} 缺少字符串 description")
        for req in params.get("required") or []:
            if req not in properties:
                raise ValueError(f"tools.json 工具 {name} 的 required 引用了不存在的参数 {req}")


class AIHelper:
    """AIHelper Agent 实例，生命周期仅存在于单个用户会话中
    """

    def is_history_files_too_many(self):
        path = self.get_history_path()
        files = [p for p in path.iterdir() if p.is_file()]
        return len(files) > MAX_HISTORY_FILE_COUNTS

    def is_history_too_big(self):
        path = self.get_history_path()
        total_size = sum(
            p.stat().st_size
            for p in path.rglob("*")
            if p.is_file()
        )
        if total_size is None:
            ai_logger.warning("无法获取 history 的 totalsize")
            return
        return total_size > MAX_HISTORY_FILES_SIZE

    def get_temp_path(self, string=False):
        self._check_user_path()
        if string:
            return f"./data/temp/{self.user_id}"
        return Path(f"./data/temp/{self.user_id}")

    def note_file_state(self, path) -> None:
        """记录文件当前内容指纹：AI 经工具读到/写出该文件时调用，供 edit_file 校验过期。"""
        try:
            resolved = Path(path).resolve()
            data = resolved.read_bytes()
        except OSError:
            return
        self.file_hashes[str(resolved)] = hashlib.sha256(data).hexdigest()

    def file_changed_since_read(self, path) -> bool:
        """该文件在 AI 最近一次读取后是否被外部改动。

        无指纹记录（从未读过/--continue 后）视为未改动（fail-open）；有记录但内容
        不符或文件已消失视为已改动。
        """
        resolved = Path(path).resolve()
        recorded = self.file_hashes.get(str(resolved))
        if recorded is None:
            return False
        try:
            data = resolved.read_bytes()
        except OSError:
            return True
        return hashlib.sha256(data).hexdigest() != recorded

    def forget_file_state(self, path) -> None:
        """清除文件指纹（文件被删除/改名后调用，防脏键）。"""
        self.file_hashes.pop(str(Path(path).resolve()), None)

    def save_file(self, path, data: str | bytes = "", mode: str = "w", binary: bool = False) -> None:
        """写入文件并登记指纹（AI 产出文件的统一写入口，写完自动同步指纹）。

        binary=True 按字节覆盖写；文本模式 mode 与 open() 一致（"w" 覆盖 / "a" 追加）。
        新工具写文件一律走这里，不要手写 write 后再补 note_file_state。
        """
        p = Path(path)
        if p.is_relative_to(self.get_history_path()) and self.is_history_too_big():
            raise DirectoryTooLargeError(f"history 文件夹过大 (>{MAX_HISTORY_FILES_SIZE // 1024 // 1024}MiB)，请删除部分文件再试")
        if p.is_relative_to(self.get_history_path()) and self.is_history_files_too_many():
            raise TooManyFilesError(f"history 文件夹文件过多 (>{MAX_HISTORY_FILE_COUNTS})，请删除部分文件再试")
        if binary:
            with open(p, "wb") as f:
                f.write(data)
        else:
            with open(p, mode, encoding="utf-8") as f:
                f.write(data)
        self.note_file_state(p)

    def rename_file(self, old, new) -> None:
        """改名/移动文件并同步指纹（旧路径清除、新路径登记）。"""
        Path(old).rename(new)
        self.forget_file_state(old)
        self.note_file_state(new)

    def delete_file(self, path) -> None:
        """删除文件并清除指纹；文件不存在时抛 FileNotFoundError（与 unlink 一致）。"""
        Path(path).unlink()
        self.forget_file_state(path)

    def delete_temp(self):
        # 清空临时目录，但保留 history 目录（history 仅在 /ai -c clear 时清空）
        for item in self.get_temp_path().iterdir():
            if item.name == "history":
                continue
            if item.is_file() or item.is_symlink():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
        for path in self.temp_file_paths:
            Path(path).unlink(missing_ok=True)

    def _check_user_path(self):
        Path(f"./data/temp/{self.user_id}").mkdir(parents=True, exist_ok=True)

    @property
    def storage(self):
        """当前会话的存储对象：共享会话返回 SharedSession，否则返回 AISession。

        两者提供 ai_session/load_history/save_history/count/dir_path 同名接口
        （鸭子类型），历史读写、压缩、AI 转存文件路径都经由这里，不感知具体类型。
        """
        if self.shared is not None:
            return self.shared
        return AISession(self.user_id, self.ai_session)

    def get_history_path(self):
        # AI 转存文件默认放到当前 AI 会话的历史文件夹、以会话命名的子文件夹
        # 普通会话：data/ai_historys/<用户id>/<ai_session>/；共享会话：shared/<群号码>/
        path = self.storage.dir_path
        path.mkdir(parents=True, exist_ok=True)
        return path

    def resolve_ref(self, ref: str, use_history=True):
        """解析 ref 对应的文件路径。

        - temp 文件引用：ref_map 里存的是纯文件名，拼上 temp 目录路径；
        - history 引用：ref_map 里存的是完整路径，或按 history_N 推导出会话文件夹内的路径，
          因此即使当前会话 ref_map 未注册，也能直接解析。
        """
        file_name = self.ref_map.get(ref, None)
        if file_name is not None:
            if "/" in file_name or chr(92) in file_name or file_name.startswith("."):
                # 内部生成的完整路径（如会话文件夹下的历史文件），可信
                return Path(file_name)
            # 纯文件名 → 安全拼接到 temp 目录
            return safe_join(self.get_temp_path(), file_name)
        if not use_history:
            raise KeyError(f"无法找到引用 {ref}")
        # 单段引用：history_N 或安全自定义名 → 根目录下推导（文件或文件夹均可）
        derived = history_file_name(ref)
        if derived is not None:
            candidate = safe_join(self.get_history_path(), derived)
            if candidate.exists():
                self.ref_map[ref] = str(candidate)
                return candidate
        # history 嵌套文件夹内的文件/文件夹："文件夹/.../名称"（各段过 is_safe_custom_name 防穿越）
        parts = ref.split("/")
        if 1 < len(parts) and all(is_safe_custom_name(p) for p in parts):
            candidate = self.get_history_path()
            for part in parts:
                candidate = safe_join(candidate, part)
            if candidate.exists():
                self.ref_map[ref] = str(candidate)
                return candidate
        raise KeyError(f"无法找到引用 {ref}")

    def __init__(self, user_id: int, session, model="flash", ai_session=history.DEFAULT_SESSION, shared_session=None, resume_data=None, routing_allowed: bool = False):
        # ai_session：用户当前使用的 AI 会话名；session：bot 的 CommandSession
        # shared_session：共享会话对象（share.SharedSession）；不为 None 时历史读写走共享会话
        self.shared = shared_session
        self.ai_session = (shared_session.code if shared_session is not None else ai_session) or history.DEFAULT_SESSION
        self.ref_map = {}
        # 文件内容指纹（路径 → sha256）：AI 经工具读到/写出文件时更新，
        # edit_file 写入前比对，拦截"读取后文件被外部改动"的静默错改
        self.file_hashes: dict[str, str] = {}
        self.tokens = 0
        self.other_credits = 0
        # 模型：model 为用户给的规格（别名如 flash/pro，或 "provider/model"），
        # 经模型目录解析出目录项（provider/真实模型名/视觉能力/倍率/上下文上限）
        self.model_arg = model
        self.model_entry = registry.resolve_model(model)
        # provider 未配置（配置被改名/删除等）→ 直接回退默认模型，避免对话一开口就报错
        self.model_fallback_note = ""
        if not registry.provider_configured(self.model_entry.get("provider", "")):
            fallback = registry.default_alias()
            fallback_entry = registry.resolve_model(fallback)
            if registry.provider_configured(fallback_entry.get("provider", "")):
                self.model_fallback_note = get_message(
                    "plugins", __plugin_name__, "model_fallback_prefix",
                    model=self.model_entry["model"], fallback=fallback_entry["model"])
                self.model_entry = fallback_entry
        self.model_alias = self.model_entry.get("alias", model)
        self.model = self.model_entry["model"]
        # 运行期是否已回退过（每次对话最多回退一次，避免反复重试）
        self.model_fallback_used = False
        # 动态模型分配：是否按话题自动挑模型（由入口集中判断：全局开关 + 本次没带 -m
        # + 用户自己没设置过默认模型 三者都满足才开启）
        self.routing_allowed = bool(routing_allowed)
        # 当前轮真实使用的模型（带图轮会强制切视觉模型）：工具执行时据此决定
        # 是否走图片直注入（ImageToolResult）；每轮由 run_agent 刷新
        self.current_model = self.model
        self.current_vision = bool(self.model_entry.get("vision"))
        # 视频段（video_url）是否受支持与图片分开判定：DeepSeek 等端点只吃图片
        self.current_video = bool(self.model_entry.get("video"))
        self.cached_tokens = 0
        self.session = session
        self.user_id = user_id
        self.temp_file_paths = []
        self.user_input_urls = {}
        self.activate_skills = []

        self.spent_secs = Timer()
        # 上次回应时间
        self.last_response = 0
        from . import functions
        # 工具使用依赖注入：所有 tool 都是独立函数，需要 agent 的函数声明 agent 形参，
        # 由 execute_tool 在执行时注入，避免工具内部再实例化 agent 造成连环调用。
        self.tool_functions = {
            name: getattr(functions, name)
            for name in functions.__tools__
        }
        self.pending_messages = []
        self.round_reasonings: list[str] = []   # 本轮各步思考原文（供轮末提炼思路笔记）
        # 插入模式：跨重启轮次的工具调用预算 + 本次对话的参与者（额度均摊）
        self.tool_call_times = 0
        self.participants = [user_id]
        # 本次对话实际调用过的工具名（去重保序），随历史条目存入 used_tools 字段
        self.used_tools: list[str] = []
        # 最近一次请求的真实输入 token 数（上下文折叠的触发判据）
        self.last_prompt_tokens = 0
        # 会话快照恢复：/ai --continue 时由快照还原全部进行中状态
        self.resume_messages: list | None = None
        self.resume_model: str | None = None
        self.resume_entry: dict | None = None
        self.asks: list[dict] = []
        if resume_data:
            self.resume_messages = resume_data.get("messages") or []
            self.resume_model = resume_data.get("model")
            # 快照恢复模型目录项：新快照含 provider/别名，旧快照只有真实模型名（反查）
            self.resume_entry = (
                registry.resolve_model(resume_data["model_alias"])
                if resume_data.get("model_alias") and resume_data["model_alias"] in registry.list_model_aliases()
                else registry.model_by_name(resume_data.get("model") or "")
            )
            self.asks = list(resume_data.get("asks") or [])
            self.used_tools = list(resume_data.get("used_tools") or [])
            self.participants = list(resume_data.get("participants") or [user_id])
            self.tool_call_times = int(resume_data.get("tool_call_times") or 0)
            # 计费累加器：断点前的消耗一并恢复，最终结算不漏记
            self.tokens = float(resume_data.get("tokens") or 0)
            self.cached_tokens = float(resume_data.get("cached_tokens") or 0)
            self.other_credits = float(resume_data.get("other_credits") or 0)
            self.activate_skills = list(resume_data.get("activate_skills") or [])
        # 插入模式的队列键与开关都是实时查询（见 insert_key / insert_enabled_now），
        # 不存构造期快照——会话名会被 AI 改名，快照会立刻过期
        tools_path = Path(__file__).parent / "tools.json"
        with open(tools_path, "r", encoding="utf-8") as f:
            self.tools = json.load(f)
        _validate_tools(self.tools)

    def _archive_reasonings(self, dropped: list[str], phase: str) -> None:
        """把被折叠丢弃的 reasoning 归档到会话旁路文件（长期保留，不回注上下文）。"""
        for item in dropped:
            history.append_reasoning(self.user_id, self.ai_session, phase=phase,
                                     model=self.current_model, reasoning=item)

    async def _distill_thinking(self) -> str:
        """把本轮的思考过程提炼成短思路笔记（随条目存入历史，下轮随正文注入上下文）。

        无思考内容 / 未配置提炼提示词 / 提炼失败时返回空串，绝不阻断对话。
        """
        if not self.round_reasonings:
            return ""
        try:
            prompt = read_from_path("./ai_configs.json")[__plugin_name__].get("thinking") or ""
            if not prompt:
                return ""
            prompt = prompt.format(max_length=THINKING_NOTE_MAX_LENGTH)
            joined = "\n---\n".join(self.round_reasonings)
            content = await self._glm_chat([
                {"role": "system", "content": prompt},
                {"role": "user", "content": joined[-THINKING_NOTE_INPUT_CHARS:]},
            ])
            return (content or "").strip()[: THINKING_NOTE_MAX_LENGTH * 2]
        except Exception as ex:
            ai_logger.warning(f"思路笔记提炼失败（跳过）：{type(ex).__name__}: {ex}")
            return ""

    async def run_agent(self, session, messages, model_entry):
        """单轮 agent 循环：反复调用模型并执行工具，直到模型不再请求工具。

        model_entry 为模型目录项（provider/真实模型名/视觉能力等），由 user_talk 解析。
        """
        # 本轮真实模型与媒体能力：工具（view_item/screenshot_page 等）据此决定
        # 是否走媒体直注入（ImageToolResult）；视频单独一位（端点未必支持 video_url）
        self.current_model = model_entry["model"]
        self.current_vision = bool(model_entry.get("vision"))
        self.current_video = bool(model_entry.get("video"))
        MAX_RETRY_TIMES = 5
        retry_times = 0
        while True:
            try:
                result = await self.create_and_wait(session, messages, model_entry)
            except LLMError as ex:
                # 媒体相关失败（含 provider 措辞任意、未被关键词识别的 400）：剥离媒体段重试。
                # 剥离是破坏性的（媒体段只减不增），无需次数限制也可收敛；无媒体可剥时照抛。
                if ex.kind == LLMErrorKind.MEDIA_INVALID or ex.kind in (
                        LLMErrorKind.BAD_REQUEST, LLMErrorKind.UNKNOWN):
                    removed = _strip_unloadable_images(messages)
                    if not removed:
                        raise   # 没有媒体段可剥：不是媒体问题，按原错误抛出
                    ai_logger.warning(
                        f"模型调用失败（{ex.kind} {ex.code or ''}），已移除 {removed} 个媒体段后重试")
                    continue
                if ex.kind not in LLMErrorKind.RETRYABLE or retry_times >= MAX_RETRY_TIMES:
                    raise
                retry_times += 1
                # 紧急折叠后再重试：若失败源于输入超长，重试才有机会成功
                freed, dropped = _fold_early_context(messages, fold_tools=True)
                if freed:
                    self._archive_reasonings(dropped, phase="fold")
                    ai_logger.warning(
                        f"模型调用失败（{ex.kind}），紧急折叠上下文后重试"
                        f"（第 {retry_times} 次，释放约 {freed:,} 字符）")
                continue
            self.tokens += result.usage.total_tokens
            self.cached_tokens += result.usage.cached_tokens
            # 轮内上下文折叠：用本次请求的真实输入量判断，在下一轮请求前瘦身
            self.last_prompt_tokens = result.usage.prompt_tokens
            limit = model_entry.get("context_limit") or CONTEXT_LIMIT_DEFAULT
            if self.last_prompt_tokens > limit * FOLD_TRIGGER_RATIO:
                fold_tools = self.last_prompt_tokens > limit * FOLD_HARD_RATIO
                freed, dropped = _fold_early_context(messages, fold_tools=fold_tools)
                if freed:
                    self._archive_reasonings(dropped, phase="fold")
                    ai_logger.info(
                        f"上下文折叠：输入 {self.last_prompt_tokens:,}/{limit:,} tokens，"
                        f"{'含工具结果' if fold_tools else '仅思考'}，释放约 {freed:,} 字符")
            if result.reasoning:
                self.round_reasonings.append(result.reasoning)
                history.append_reasoning(self.user_id, self.ai_session, phase="round",
                                         model=result.model or self.current_model,
                                         reasoning=result.reasoning)
                ai_logger.info(
                    f"\n===== AI Reasoning {session.event.user_id} =====\n"
                    f"{result.reasoning}\n"
                    f"========================="
                )

            # 插入检查点（任何模式都生效）：非流式/流式回退路径没有 on_tick，
            # 只在工具轮之后检查会让"本轮无工具调用"的插入消息丢失
            if self.insert_enabled_now() and share.has_pending_inserts(self.insert_key):
                raise InsertInterrupted()
            # 没有工具调用
            if not result.tool_calls:
                return result, self.tool_call_times
            # 有工具调用
            self.tool_call_times += 1
            for tool_call in result.tool_calls:
                ai_logger.info(
                    f"[AI Tool Call] {tool_call.name}({tool_call.arguments})"
                )

            # 把 assistant 的原始消息加入上下文（含 reasoning_content）。
            # 交错式思考的硬性要求：工具结果必须与未修改的 reasoning_content
            # 一并回传（message_to_dict 原样保留该字段）
            messages.append(message_to_dict(result))

            # 执行所有工具
            injected_parts: list = []
            for tool_call in result.tool_calls:
                result_content = await self.execute_tool(session, tool_call, self.tool_call_times)
                if result_content is AISTOP:
                    # 中断文案与结算统一在 user_talk 的 AISTOP 分支处理，此处只中断
                    return False, 0
                result_text = str(result_content)
                if isinstance(result_content, ImageToolResult):
                    injected_parts.extend(result_content.image_parts)
                ai_logger.info(
                    f"加入 tool message: {str(result_text)[:500]!r}..."
                )
                messages.append({
                    "role": "tool",
                    "content": result_text,
                    "tool_call_id": tool_call.id
                })
            # 图片/视频直注入（ImageToolResult）：工具拿到的媒体不再经独立视觉调用转述，
            # 而是合并为一条 user 消息附给本轮模型，让模型亲自查看
            has_video = any(isinstance(p, dict) and p.get("type") == "video_url"
                            for p in injected_parts)
            if injected_parts and not self.supports_media("video_url" if has_video else "image_url"):
                # 当前模型收不了这些媒体（如带图轮用了无多模态模型、或视频遇上只支持图片的
                # 端点）：切到对应能力模型；切换失败（无可用配置）则放弃注入，不谎称已附上
                try:
                    model_entry = (registry.video_entry() if has_video
                                   else registry.vision_entry())
                except LLMError as ex:
                    ai_logger.warning(f"工具返回了媒体但切换模型失败，放弃注入：{ex}")
                    injected_parts = []
                else:
                    self.current_model = model_entry["model"]
                    self.current_vision = bool(model_entry.get("vision"))
                    self.current_video = bool(model_entry.get("video"))
                    ai_logger.info(
                        f"工具返回{'视频' if has_video else '图片'}，本轮切换模型: {self.current_model}")
            if injected_parts and self.supports_media(
                    "video_url" if has_video else "image_url"):
                messages.append({"role": "user", "content": build_user_content(
                    _INJECT_MEDIA_NOTE, [], injected_parts)})

            # 插入模式：工具执行完毕后先打断以并入插入消息，再发起下一次模型调用
            if self.insert_enabled_now() and share.has_pending_inserts(self.insert_key):
                raise InsertInterrupted()

    # session 留着以后有用
    async def execute_tool(self, session, tool_call, curr_tool_call_times):
        prefix = ""
        if curr_tool_call_times >= MAX_TOOL_CALL_TIMES:
            return f"[工具执行失败：次数已达到上限，请在下一个会话继续]"
        if curr_tool_call_times >= MAX_TOOL_CALL_TIMES - 7:
            prefix = f"[警告：剩余 {MAX_TOOL_CALL_TIMES - curr_tool_call_times} 次 tools 调用次数]\n"
        name = tool_call.name
        if name not in self.used_tools:
            self.used_tools.append(name)
        try:
            arguments = json.loads(tool_call.arguments)
            ai_logger.info(get_message("plugins", __plugin_name__, "call_tool", tool_name=name, arguments=tool_call.arguments))

            func = self.tool_functions.get(name)

            if func is None:
                return f"工具 {name} 不存在"
            no_compress = False
            # 依赖注入：工具声明了 agent 形参则注入当前 agent
            if "agent" in inspect.signature(func).parameters:
                arguments["agent"] = self
            if "session" in inspect.signature(func).parameters:
                arguments["session"] = session

            if inspect.iscoroutinefunction(func):
                result = await func(**arguments)
            else:
                result = func(**arguments)
            if result is AISTOP:
                return AISTOP
            spent = self.spent_secs.get_timer_value()
            spent_msg = f"本轮对话总计消耗 {spent:,.2f}s"
            ai_logger.info(
                f"[{spent_msg}]工具调用完毕，名称 {name} 结果类型={type(result)}, str={str(result)[:100]!r}...{str(result)[-100:]!r}"
            )

            if isinstance(result, dict):
                no_compress = result.get("no_compress", False)
                result = result.get("result", result)

            if isinstance(result, MessageSegment) or str(result).startswith("[CQ:"):
                self.pending_messages.append(result)
                return prefix + f"[[{spent_msg}] \"{name}\" 工具调用完毕，Segment 消息已经准备好，会在本轮最终回复时发送给用户。]"

            ####### 压缩 ########
            RESULT_MAX_LEN = 10000
            if (isinstance(result, list) and len(str(result)) > RESULT_MAX_LEN) or (isinstance(result, dict) and result.get("result", None) is None) and len(str(result)) > RESULT_MAX_LEN:
                res = dict_to_file(result, self.user_id, name + "_", agent=self)
                result = prefix + f'[{spent_msg}][工具调用完毕，返回列表/字典过长已转为 json，可使用其他 tools 查看 数据如下]：{res}'

            if isinstance(result, str) and len(result) > RESULT_MAX_LEN and not no_compress:
                res = text_to_file(result, self.user_id, self)
                self.ref_map[res["ref"]] = res["file_name"]
                return prefix + f"[{spent_msg}][工具调用完毕，返回文本过长已传为文件，可使用 \"check_file\" 工具传入 `file_ref` 预览。数据如下]：\n{res}"

            if len(str(result)) > 100000:
                return f"[{spent_msg}][错误：无法返回过大内容 (>100000)]"

            if isinstance(result, ImageToolResult):
                # str 拼接会把子类退化成普通 str、丢失 image_parts（注入就此失效），
                # 必须先于通用拼接分支保住身份，前缀并入文本部分
                return ImageToolResult(prefix + str(result), result.image_parts)
            return prefix + result if isinstance(result, str) else result
        except Exception as e:
            ai_logger.exception(f"执行工具 {name} 失败")
            return f"[工具执行失败：{type(e).__name__}: {e}]"

    def _save_snapshot(self, messages: list, model_entry: dict) -> None:
        """把进行中的完整上下文落盘为快照（best-effort）。

        每次模型调用前覆盖写；进程异常死亡时文件残留，
        供 /ai --continue 恢复（用户输入/思考/工具结果/插入消息全在 messages 里）。
        """
        try:
            data = {
                "user_id": self.user_id,
                "ai_session": None if self.shared is not None else self.ai_session,
                "shared_code": self.shared.code if self.shared is not None else None,
                "model": model_entry.get("model"),
                "provider": model_entry.get("provider"),
                "model_alias": model_entry.get("alias"),
                "messages": _strip_media_for_snapshot(messages),
                "asks": self.asks,
                "used_tools": self.used_tools,
                "participants": self.participants,
                "tool_call_times": self.tool_call_times,
                "tokens": self.tokens,
                "cached_tokens": self.cached_tokens,
                "other_credits": self.other_credits,
                "activate_skills": self.activate_skills,
                "time": get_time_now(),
            }
            path = _snapshot_path(self.user_id)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        except Exception as ex:
            ai_logger.warning(f"保存会话快照失败（不影响对话）: {ex}")

    async def create_and_wait(self, session, messages, model_entry):
        """通过统一 provider 发起一次对话调用（流式读块期间可被插入消息打断）。"""
        self._save_snapshot(messages, model_entry)
        # 流式产出统计：中断时用它估算"在途调用"的用量（正常返回后清空）
        stats: dict = {}
        self._stream_stats = stats
        provider = registry.get_provider(model_entry["provider"])
        if provider is None:
            raise LLMError(LLMErrorKind.BAD_REQUEST,
                           f"provider {model_entry['provider']} 未配置（见 keys.py 的 LLM_PROVIDERS）",
                           provider=model_entry["provider"])

        def on_tick():
            # 流式读块期间周期性检查：有插入消息则打断，交由 user_talk 并入上下文后重启。
            # （aistop 走 asyncio 任务取消，无需在此处理）
            if self.insert_enabled_now() and share.has_pending_inserts(self.insert_key):
                raise InsertInterrupted()

        result = await provider.chat(
            messages,
            model=model_entry["model"],
            tools=self.tools,
            temperature=0.5,
            thinking=True,
            on_tick=on_tick,
            stats=stats,
        )
        # 调用已返回：用量由 usage 计入，清掉统计避免被当成"在途调用"重复估算
        self._stream_stats = None
        return result

    async def _chat_once(self, messages, model_entry=None, temperature=None) -> ChatResult:
        """一次性对话调用（历史压缩等带外用途），返回统一结果并计入 other_credits。"""
        entry = model_entry or self.model_entry
        provider = registry.get_provider(entry["provider"])
        if provider is None:
            raise LLMError(LLMErrorKind.BAD_REQUEST,
                           f"provider {entry['provider']} 未配置", provider=entry["provider"])
        result = await provider.chat(messages, model=entry["model"], temperature=temperature)
        self.other_credits += result.usage.billable_tokens(registry.cache_credit_ratio(entry))
        return result

    async def _glm_chat(self, messages, model=FLASH_MODEL):
        """兼容旧调用名：一次性对话，返回文本（历史压缩用）。"""
        result = await self._chat_once(messages)
        return result.text

    @staticmethod
    def _build_compress_input(summary, to_compress, skills=()) -> str:
        """构造压缩输入：[旧摘要] + [涉及技能] + [待压缩的对话历史]。"""
        history_text = "\n".join([
            f"[{it.get('time', '未知时间')}] 用户: {it.get('ask', '')}\nAI: {it.get('ans', '')}"
            for it in to_compress
        ])
        skills_text = "、".join(skills) if skills else "（无）"
        return (
            f"[旧摘要]\n{summary or '（无）'}\n\n"
            f"[涉及技能]\n{skills_text}\n\n"
            f"[待压缩的对话历史]\n{history_text}"
        )

    async def _compress_context(self, session: CommandSession):
        """历史超过阈值时，把最旧的一部分压缩成摘要，存回 history 文件。

        摘要作为第一条特殊 history（携带 summary 键）存放；
        后续 get_history 会在上下文最前面注入这条摘要，让 AI 知道这是总结。
        """
        session_obj = self.storage
        user_history = session_obj.load_history()
        summary, summary_skills, normals = history.split(user_history)
        # 条数不设上限（长期保留）：历史估算占用达模型上下文预算的比例才触发压缩
        limit = self.model_entry.get("context_limit") or CONTEXT_LIMIT_DEFAULT
        if estimate_context_tokens(summary, normals) <= limit * COMPRESS_TRIGGER_RATIO:
            return 0
        await send_session_msg(session, get_message("plugins", __plugin_name__, "compress_context"))
        to_compress = normals[:len(normals) - CONTEXT_KEEP_RECENT]
        keep = normals[len(normals) - CONTEXT_KEEP_RECENT:]
        # 合并旧摘要携带的skills与被压缩记录里用过的skills，压缩后依旧保留
        compressed_skills = sorted(set(summary_skills) | {
            s for it in to_compress for s in (it.get("activate_skills", []) or [])
        })
        try:
            memory_prompt = read_from_path("./ai_configs.json")[__plugin_name__]["memory"]
            if memory_prompt:
                memory_prompt = memory_prompt.format(max_length=COMPRESS_MAX_LENGTH)
            content = await self._glm_chat([
                {"role": "system", "content": memory_prompt},
                {"role": "user", "content": self._build_compress_input(summary, to_compress, compressed_skills)},
            ])
            new_summary = (content or "").strip()
            if new_summary:
                summary = new_summary
                new_history = history.merge(summary, keep, get_time_now(), skills=compressed_skills)
                session_obj.save_history(new_history)
                ai_logger.info(
                    f"上下文已压缩：把 {len(to_compress)} 条历史压成摘要（{len(summary)} 字），保留最近 {len(keep)} 条。"
                )
                # await send_session_msg(session, get_message("plugins", __plugin_name__, 'talking_to_ai', model=self.current_model, ai_session=self.ai_session))
                return len(summary)
        except Exception as ex:
            ai_logger.exception(f"上下文压缩失败: {ex}")
            return 0
        return 0

    async def get_video_url_dicts(self, text, download: bool = True):
        """把文本里的视频链接转为 video_url 输入段。

        - 平台链接（B站/YouTube 等）：yt-dlp 下载到本地后以限时直链附入（文本替换为
          "[视频:平台] …"，只展示平台链接，不暴露本地直链）；
        - 媒体直链（.mp4 等）：LLM 已持有可用直链，直接原样附入，不下载。

        download=False（本轮模型看不了视频）：不下载、不产出 video_url 段，
        文本保留原始链接交给模型自己用 view_video 查看——避免白下载一个看不了的视频。
        """
        links = extract_video_links(text)
        video_dicts: list = []
        pths: list = []
        new_text = text
        if not download:
            return new_text, video_dicts, pths
        if links:
            try:
                result: VideoExtractResult = await extract_and_download(
                    text, output_dir="./data/videos/temp/")
                for link, r in sorted(zip(result.links, result.downloads),
                                    key=lambda p: p[0].start, reverse=True):
                    if not r.ok:
                        raise ValueError(f"下载视频出现错误：{r.error}")
                    video_info = await parse_video(r.url)
                    desc = video_info.description if video_info and video_info.description else "无"
                    desc = desc[:200] + "..." if len(desc) > 200 else desc
                    desc = desc.replace("\r\n", "\n").replace("\r", "\n")
                    title = video_info.title if video_info else (r.title or "未知标题")
                    platform = f"{video_info.platform_name}-{video_info.video_id}" if video_info else "未知平台信息"
                    desc = f"``` Text\n{desc}\n```" if desc.count("\n") > 1 else '"' + desc.strip("\n") + '"'
                    info_text = f"[【视频(已附在输入):{platform}】 标题：{title} | url:{link.url} | 介绍:{desc}]"
                    new_text = new_text[:link.start] + info_text + new_text[link.end:]
                    for f in r.file_paths:
                        pths.append(f)
                        # 视频链接给模型服务端留足拉取时间（默认 30s 太短，抓取超时会变成
                        # 1210「媒体加载失败」即模型看不到视频）
                        video_dicts.append({"type": "video_url", "video_url": {
                            "url": get_local_file_url(str(f), ttl=constants.VIDEO_URL_TTL)}})
            except Exception as ex:
                return f"[解析视频出现异常: {ex}]" + new_text, [], []
        # 媒体直链：LLM 已持有可用直链，直接原样附入（不下载、不暴露额外链接）
        def _direct_repl(m):
            url = m.group(0)
            video_dicts.append({"type": "video_url", "video_url": {"url": url}})
            return f"[视频:直链] {url}"
        new_text = _DIRECT_VIDEO_RE.sub(_direct_repl, new_text)
        return new_text, video_dicts, pths

    def supports_media(self, item_type: str) -> bool:
        """本轮模型能否直接收下这类媒体段（图/文件看 vision，视频看 video）。"""
        if item_type == "video_url":
            return bool(getattr(self, "current_video", False))
        return bool(getattr(self, "current_vision", False))

    async def prepare_user_media(self, session, text) -> tuple[str, list, list[str], list[str]]:
        """整理用户输入里的媒体，返回 (文本, 媒体段, 图片直链, 需提示的查看工具名)。

        模型能看某类媒体 → 仍作为段附入（图片位置保留占位符）；看不了 → 不附段，
        图片 CQ 换成已提取的直链、视频保留原链接且不下载，并把对应的查看工具名
        返回给调用方拼提示（模型据此自己调 view_image / view_video）。
        """
        image_objects, matches = [], []
        try:
            image_objects, matches = await get_images_from_message(session.bot, text)
        except Exception as ex:
            ai_logger.warning(f"提取消息中的图片失败（按无图继续）：{type(ex).__name__}: {ex}")
        image_urls = [x["file"] for x in image_objects]
        can_see_image = bool(self.model_entry.get("vision"))
        can_see_video = bool(self.model_entry.get("video"))
        if can_see_image:
            for image_cq in matches:
                text = text.replace(image_cq, image_placeholder(image_cq) + " 已附在输入里")
        else:
            text = replace_media_markers(text, matches, image_urls)

        has_video_link = bool(extract_video_links(text))
        text, video_dicts, pths = await self.get_video_url_dicts(text, download=can_see_video)
        self.temp_file_paths += pths
        self.user_input_urls["images"] = image_urls
        parts = ([{"type": "image_url", "image_url": {"url": v}} for v in image_urls]
                 if can_see_image else [])
        parts += video_dicts
        hint_tools: list[str] = []
        if image_urls and not can_see_image:
            hint_tools.append("view_image")
        if has_video_link and not can_see_video:
            hint_tools.append("view_video")
        return text, parts, image_urls, hint_tools

    @staticmethod
    def recent_context_text(history: list) -> str:
        """提取话题分类用的上下文：**对话开头的第一次用户输入 + 最近若干轮**。

        人设/角色扮演等设定几乎都写在开场第一句（"你是漠月，用她的语气说话"），
        只取最近几轮会把它丢掉、导致后续"嗯嗯"这类短输入判错，所以开场输入必带；
        其余取最近 N 轮（LLM_TOPIC_CONTEXT_ITEMS），每轮截断并受总长度上限约束。
        """
        items = int(getattr(constants, "LLM_TOPIC_CONTEXT_ITEMS", 3))
        total_chars = int(getattr(constants, "LLM_TOPIC_CONTEXT_CHARS", 600))
        per_item = max(60, total_chars // max(1, (items + 1) * 2))

        def text_of(m) -> str:
            content = m.get("content")
            if isinstance(content, list):
                content = " ".join(p.get("text", "") for p in content
                                   if isinstance(p, dict) and p.get("type") == "text")
            return str(content or "").strip()

        dialog = [(m.get("role"), text_of(m)) for m in (history or [])
                  if isinstance(m, dict) and m.get("role") in ("user", "assistant")]
        dialog = [(r, t) for r, t in dialog if t]
        if not dialog:
            return ""

        picked: list[tuple[str, str]] = []
        first_user = next((t for r, t in dialog if r == "user"), "")
        if first_user:
            picked.append(("user", first_user))          # 开场设定（人设/角色扮演常在此）
        picked.extend(dialog[-items:])                    # 最近的对话
        lines, seen = [], set()
        for role, text in picked:
            who = "用户" if role == "user" else "AI"
            line = f"{who}: {text[:per_item]}"
            if line in seen:                              # 开场与最近轮重叠时去重
                continue
            seen.add(line)
            lines.append(line)
        return "\n".join(lines)[:total_chars]

    async def route_model_entry(self, text: str, context: str = "") -> dict | None:
        """按话题给本轮挑模型（动态分配）；不适用时返回 None（用会话默认模型）。

        context 为最近对话文本（识别"角色扮演在开头定义"这类情况）。
        仅在动态分配开启、用户没有自己设置默认模型时生效；分类失败或路由目标
        的 provider 未配置时返回 None，由调用方回落到会话默认模型。
        """
        from .llm import topic as topic_module
        if not self.routing_allowed:
            return None
        try:
            category = await topic_module.classify_topic(text, context=context, agent=self)
        except Exception as ex:   # 分类器自身已兜底，这里只是最后一道保险
            ai_logger.warning(f"话题分类异常（{type(ex).__name__}: {ex}），使用默认模型")
            return None
        routing = getattr(constants, "LLM_TOPIC_ROUTING", {}) or {}
        alias = routing.get(category)
        if not alias:
            ai_logger.info(f"话题分类：{category}（无对应模型，使用默认模型）")
            return None
        try:
            entry = registry.resolve_model(alias)
        except Exception:
            ai_logger.warning(f"话题分类：{category} → 模型 {alias} 无效，使用默认模型")
            return None
        if not registry.provider_configured(entry.get("provider", "")):
            ai_logger.warning(
                f"话题分类：{category} → {alias}（provider {entry.get('provider')} 未配置，使用默认模型）")
            return None
        ai_logger.info(f"话题分类：{category} → {alias}（{entry['model']}）")
        return entry

    @property
    def insert_key(self) -> str:
        """插入队列键（实时计算）：共享会话按群号码，普通会话按用户。

        普通会话的键**不含会话名**——名字会被 AI（name_session）改，
        键里带名字会导致改名前后的入队/消费用不同键，插入消息收不到。
        """
        if self.shared is not None:
            return share.shared_insert_key(self.shared.code)
        return share.user_insert_key(self.user_id)

    def insert_enabled_now(self) -> bool:
        """实时查询插入模式开关（对话进行中切换、会话改名都能立即生效）。"""
        if self.shared is not None:
            return bool(getattr(self.shared, "insert_enabled", False))
        return normal_insert_enabled(self.user_id, self.ai_session)

    def billing_entry(self) -> dict:
        """计费口径用的模型目录项：**按当轮真实模型反查**。

        倍率与缓存倍率必须来自同一项——否则动态路由/带图切换后会出现
        "倍率按 flash、缓存按 dsflash"的错配（实测少计约 58%）。
        模型不在目录里（如临时用 provider/model 形式）时回落构造期目录项或空。
        """
        return (registry.model_by_name(self.current_model)
                or getattr(self, "model_entry", None) or {})

    def in_flight_tokens(self) -> float:
        """在途调用的 tokens 估算（中断时那一次调用拿不到 usage）。

        流式过程中累计已产出字符数，按约 1.5 字符/token 估算；
        调用正常返回后 `_stream_stats` 会被清空，所以这里非零只意味着"有一次调用没跑完"。
        """
        stats = getattr(self, "_stream_stats", None)
        if not stats:
            return 0.0
        chars = int(stats.get("produced_chars", 0) or 0)
        return chars / 1.5 if chars > 0 else 0.0

    def compute_credits(self) -> dict:
        """按已累计 tokens 计算本轮 credits 消耗与参与者均摊（正常结束与中断结算共用）。

        - 倍率与缓存倍率都取自当轮真实模型的目录项（billing_entry）；
        - 中断时补上"在途调用"的估算用量，避免输出一大段却计 0；
        - participants 为空时兜底按发起者单人分摊（否则不扣费且文案显示"未知"）。
        """
        entry = self.billing_entry()
        cache_ratio = registry.cache_credit_ratio(entry)
        multis = entry.get("credit_multiplier", 1) if entry else 1
        in_flight = self.in_flight_tokens()
        # 缓存 tokens 按该模型的缓存倍率折算（各 provider 折扣不同，见 LLM_MODELS.cache_credit_ratio）
        credits_use = self.tokens - self.cached_tokens * (1 - cache_ratio)
        credits_use *= multis
        credits_use += self.other_credits
        credits_use += in_flight * multis
        # 共享会话插入模式：全部用量在参与者间均摊（发起者 + 插入者）
        per_share = credits_use / len(self.participants) if self.participants else credits_use
        credits_split = {str(uid): round(per_share, 2) for uid in self.participants}
        credits_split = credits_split or {str(self.user_id): round(credits_use, 2)}
        return {"credits_use": credits_use, "credits_split": credits_split,
                "cached": self.cached_tokens, "total": self.tokens,
                "in_flight": in_flight}

    def settle_once(self) -> dict:
        """本轮结算（幂等）：算账 → 落账 → 清零累加器 → 清快照。

        幂等是为了防两类重复扣费：
        1. 结算后到发送之间还有 await，此刻被 aistop 取消会再次走到结算分支；
        2. 结算后若进程异常退出，残留快照会在 --continue 时把同一批用量再算一遍
           （清零累加器 + 立刻清快照双重保证）。
        """
        cached_result = getattr(self, "credits_settled", None)
        if cached_result is not None:
            return cached_result
        data = self.compute_credits()
        data["lefts"] = credits.settle_split(data["credits_split"])
        self.credits_settled = data
        self.tokens = 0.0
        self.cached_tokens = 0.0
        self.other_credits = 0.0
        self._stream_stats = None
        clear_snapshot(self.user_id)   # 已结算即视为本轮结束：避免恢复后再扣一次
        return data

    async def user_talk(self, session: CommandSession, role, user, text):
        self.spent_secs.start()
        self.pending_messages.clear()
        self.round_reasonings.clear()
        prefix = ""
        if self.resume_messages is not None:
            # /ai --continue：以上次快照的完整上下文（用户输入/思考/工具结果/插入）重入循环
            compressed = 0
            ai_params = self.resume_messages
            asks = self.asks
            real_entry = self.resume_entry or self.model_entry
            text = asks[-1].get("text", "") if asks else text
            prefix = get_message("plugins", __plugin_name__, "resume_prefix", count=len(ai_params))
        else:
            compressed = await self._compress_context(session)
            history, curr_text = await get_history(user, self.storage)

            text, url_dicts, image_urls, hint_tools = await self.prepare_user_media(session, text)
            ai_logger.info(f"用户 {user.id} 说：{text}")
            ai_logger.info(f"用户附带了以下图片url {image_urls}，媒体段 {url_dicts}")

            # 看不了的媒体给一条操作提示（不进 asks：避免提示随历史重复注入）
            user_text = f"{curr_text}\n{text}"
            if hint_tools:
                user_text += f"\n{media_hint(hint_tools)}"
            ai_params = [
                {"role": "system","content": role},
                *history,
                # 注意：url_dicts 已包含全部图片段（image_url）与视频段，位置参数再传
                # image_urls 会让同一张图出现两次（浪费 tokens，也更容易触发媒体错误）
                {"role": "user","content": build_user_content(user_text, [], url_dicts)},
            ]
            # 媒体输入不参与话题路由（保持原行为）；也**不再**自动切换视觉模型
            has_media = bool(image_urls or url_dicts or hint_tools)
            real_entry = (self.model_entry if has_media
                          else await self.route_model_entry(
                              text, self.recent_context_text(history)) or self.model_entry)
            # 多提问记录：发起者的原始输入 + 每一条被并入的插入消息（共享会话插入模式）
            asks = [{"user_id": user.id, "text": text, "image_urls": list(image_urls)}]
            self.asks = asks
        # 模型已确定（话题路由 / 媒体切换 / 快照恢复）→ 这时才提示用户在用哪个模型，
        # 与压缩后补发的提示（_compress_context 内）保持一致；本轮刚压缩过则不再补发
        if self.resume_messages is None and not compressed:
            await send_session_msg(session, get_message(
                "plugins", __plugin_name__, "talking_to_ai",
                model=real_entry["model"], ai_session=self.ai_session))
        # 插入队列键：共享会话按群号码，普通会话按 用户+会话名（与 AIHelper.insert_key 一致）
        while True:
            try:
                result, tool_call_times = await self.run_agent(session, ai_params, real_entry)
                break
            except LLMError as ex:
                # 仅"模型名失效/请求被拒"回退默认模型重试一次；
                # 连接不上（超时）、服务端错误、鉴权失败一律照抛报错——这些是配置/网络问题，
                # 回退只会掩盖原因（限流/超时类由 run_agent 自身重试）
                fallback_alias = registry.default_alias()
                if (ex.kind in (LLMErrorKind.BAD_REQUEST, LLMErrorKind.UNKNOWN)
                        and not self.model_fallback_used
                        and real_entry.get("alias", "") != fallback_alias):
                    self.model_fallback_used = True
                    old_model = real_entry["model"]
                    real_entry = registry.resolve_model(fallback_alias)
                    self.model_entry = real_entry      # 本会话后续轮次也用它
                    prefix += get_message("plugins", __plugin_name__, "model_fallback_prefix",
                                          model=old_model, fallback=real_entry["model"])
                    ai_logger.warning(
                        f"模型不可用（{ex.kind}）：{old_model} → 回退到 {real_entry['model']} 重试")
                    continue
                raise
            except InsertInterrupted:
                # 打断点：把全部待插入消息并入上下文后重入 agent 循环（messages 数组原样延续）
                inserts = share.consume_inserts(self.insert_key)
                # 本轮模型能否直接看插入消息里的图片：看不了就不切模型，改为保留直链 + 提示
                can_see_insert_image = bool(real_entry.get("vision"))
                for ins in inserts:
                    if self.shared is not None:
                        ins_name = await get_user_name(ins.user_id, default=str(ins.user_id))
                        ins_label = f"[共享会话成员 {ins_name}(qq{ins.user_id}) 插入] "
                    else:
                        ins_label = "[用户插入] "  # 普通会话：插入者即用户本人
                    ai_params.append({"role": "user", "content": build_insert_content(
                        ins_label, ins, can_see_insert_image)})
                    asks.append({"user_id": ins.user_id, "text": ins.text,
                                 "image_urls": list(ins.image_urls)})
                    if ins.user_id not in self.participants:
                        self.participants.append(ins.user_id)
                    ai_logger.info(
                        f"插入消息已并入上下文: {ins.user_id} {ins.text[:150]!r}"
                        + ("..." if len(ins.text) > 150 else ""))
        self.spent_secs.stop()
        # 构造期若发生过 provider 预检回退，提示一并带出（原来只记录未展示）
        if self.model_fallback_note:
            prefix = self.model_fallback_note + prefix
        if result == False or result is AISTOP:
            # 主动中断（ask_user 的 aistop）：已消耗的 tokens 照常结算并提示（幂等）
            tokens_use_dict = self.settle_once()
            lefts = tokens_use_dict.get("lefts", {})
            share_used = tokens_use_dict["credits_split"].get(str(self.user_id))
            left = lefts.get(str(self.user_id))
            fmt = lambda x: f"{x:,.2f}".rstrip('0').rstrip('.') if x is not None else "未知"
            await send_session_msg(
                session,
                get_message("plugins", __plugin_name__, "ai_send_interrupted",
                            credits=fmt(share_used), left=fmt(left))
            )
            return False, {}, {}, 0
        try:
            ans = result.text or ""
            # 空回复兜底：模型可能被安全策略拦截（finish_reason=sensitive）或未产出文本，
            # 直接送空内容会导致用户端"什么都没收到"，这里显式告知原因与建议
            if not ans.strip():
                reason = result.finish_reason or "未知"
                ai_logger.warning(
                    f"模型未返回文本内容：finish_reason={reason}，"
                    f"usage={result.usage}，tool_calls={len(result.tool_calls)}")
                ans = get_message("plugins", __plugin_name__, "empty_reply", reason=reason)

            ai_logger.info(
                f"AI 返回了以下 response：{result}"
            )
            # 正常结束：直接结算（幂等），入口不再二次落账
            tokens_use_dict = self.settle_once()
            credits_use = tokens_use_dict["credits_use"]
            credits_split = tokens_use_dict["credits_split"]
            debug_msg("处理结果")
            logger.info(
                f"缓存tokens "
                f"{self.cached_tokens}, "
                f"减少 {credits_use} 个 tokens"
            )
            messages_dict = {
                "messages": self.pending_messages, "prefix": prefix,
                "history_compressed": compressed, "talk_secs": self.spent_secs.get_timer_value(),
                "context_limit": self.model_entry.get("context_limit") or CONTEXT_LIMIT_DEFAULT,
            }
            # 回复风控（strictness=4：只有 REJECT/HIGH 级别会被拦下；返回 dict，取 result 判断）
            if not (await is_text_can_send(session, ans, 4))["result"]:
                return "这个话题好像不是很合适呢...我们换个话题聊吧。（本次对话不记录历史）", tokens_use_dict, messages_dict, 0
            build_history(
                user=user,
                ask=asks[-1].get("text", text) if asks else text,
                ans=ans,
                agent=self,
                asks=asks,
                thinking_note=await self._distill_thinking(),
            )
            return ans, tokens_use_dict, messages_dict, tool_call_times
        except AttributeError as ex:
            ai_logger.error(f"attribute 错误: {ex}")
            self.settle_once()   # 已发生的用量照常结算，避免漏记

            await send_session_msg(
                session,
                get_message(
                    "plugins",
                    __plugin_name__,
                    "attribute_error",
                    content=result,
                    replace_cq_str=True
                )
            )
            return False, {}, {}, 0
        except Exception as ex:
            ai_logger.error(f"AI 出现错误: {ex}")
            self.settle_once()   # 已发生的用量照常结算，避免漏记
            await send_session_msg(
                session,
                get_message(
                    "plugins",
                    __plugin_name__,
                    "ai_error",
                    code="未知",
                    msg=str(ex) + "\n" + format_exc()
                )
            )
            return False, {}, {}, 0


async def get_history(user: u.User, session_obj):
    """把某会话的历史构建为上下文消息列表。

    session_obj 为 AISession 或 SharedSession（两者历史接口同名，鸭子类型），
    返回 (messages 列表, 当前对话前缀字符串)。
    """
    user_history = session_obj.load_history()
    ai_session = session_obj.ai_session
    if not user_history:
        return "", ""
    build_list = [{
        "role": "user",
        "content": f"[历史记录-会话 \"{ai_session}\"]",
    }]
    summary = None
    summary_skills: list[str] = []
    uname = await get_user_name(user.id, default=str(user.id))
    # 共享会话的提示：SharedSession 才有 title 属性（普通会话名即文件名，无此字段）
    shared_title = getattr(session_obj, "title", None)
    shared_hint = (
        f"（共享会话「{shared_title}」，多名成员共用此会话，注意区分每位发言者的身份）"
        if shared_title else ""
    )
    # 提问者名字缓存：共享会话中多条记录可能来自同一成员，避免逐条查询
    name_cache: dict = {}
    for _, item in enumerate(user_history):
        if history.is_summary(item):
            summary = item.get("summary")
            summary_skills = list(item.get("skills", []) or [])
            continue
        url_dicts = item.get('urls', {})
        url_str = "|".join([f"{k}: " + "、".join(v) for k, v in url_dicts.items()])
        url_str = f"[附带URLs:{url_str}]" if len(url_str) > 0 else ""
        skills = item.get('activate_skills', [])
        # 提问者列表：共享会话插入模式的条目带 asks（多个提问者），旧条目回落单提问者
        askers = item.get("asks") or [{"user_id": item.get("user_id", user.id), "text": item.get("ask", "")}]
        # 该轮实际用过的工具：以 [使用工具:…] 标记置于条目注入内容的开头
        used_tools = item.get("used_tools") or []
        tools_marker = f"[使用工具:{'、'.join(used_tools)}]" if used_tools else ""
        # 思路笔记与工具标记同置 user 消息头（内部元信息，不进 assistant 正文，
        # 防止模型把它当成自己说过的话而向用户复述）
        thinking = str(item.get("thinking") or "")
        thinking_marker = f"[思路笔记(你当时的内部思考，未展示给用户，勿提及)：{thinking}]" if thinking else ""
        build_dicts = []
        for ask_index, asker in enumerate(askers):
            asker_id = asker.get("user_id", user.id)
            if asker_id not in name_cache:
                name_cache[asker_id] = await get_user_name(asker_id, default=str(asker_id))
            asker_name = name_cache[asker_id]
            # 条目级附带URLs 只标在第一个提问上，避免重复；ask 自身的图片标在各自行
            asker_url_str = url_str if ask_index == 0 else ""
            ask_images = "、".join(asker.get("image_urls") or [])
            if ask_images:
                asker_url_str += f"[附带图片:{ask_images}]"
            marker = (tools_marker + thinking_marker) if ask_index == 0 else ""
            build_dicts.append({
                "role": "user",
                "content": f"{marker}[历史记录-{item.get('time', '未知时间')}][{asker_name}(qq{asker_id})]{asker_url_str} {asker.get('text', '')}",
            })
        tool_calls = []
        tool_messages = []
        if skills:
            for s in skills:
                try:
                    with open(f"./static/skills/{s}.md", 'r', encoding="utf-8") as file:
                        skill = file.read()
                except FileNotFoundError:
                    logger.warning(f"无法找到 skill 文件: {s}.md")
                    continue
                except Exception:
                    logger.exception(f"读取 skill 文件 {s}.md 出错")
                    continue
                tool_id = uuid4().hex
                tool_calls.append({
                    "id": tool_id,
                    "type": "function",
                    "function": {
                        "name": "get_skill_md",
                        "arguments": json.dumps({
                            "name": s
                        })
                    }
                })
                tool_messages.append({
                    "role": "tool",
                    "content": skill,
                    "tool_call_id": tool_id
                })
        if tool_calls:
            build_dicts.append({
                "role": "assistant",
                "tool_calls": tool_calls,
            })

            build_dicts.extend(tool_messages)

        build_dicts.append({
            "role": "assistant",
            "content": item["ans"],
        })
        build_list += build_dicts
    if summary:
        # 在上下文最前面注入长期记忆摘要，让 AI 知道这是此前对话的总结（含用过的技能）
        skill_hint = f"；涉及技能：{'、'.join(summary_skills)}" if summary_skills else ""
        build_list.insert(0, {"role": "user", "content": f"[长期记忆摘要（此前对话总结，供你参考{skill_hint}）：\n{summary}\n]"})
    build_str = f"\n当前对话（现在时间为 {get_time_now()}）发送者为{uname} (qq{user.id}){shared_hint}："
    return build_list, build_str


def build_history(user: u.User, ask, ans, agent, asks: list | None = None, thinking_note: str = ""):
    session_obj = agent.storage
    user_history = session_obj.load_history()
    summary, summary_skills, normals = history.split(user_history)
    entry = {
        "ask": ask,
        "ans": ans,
        "time": get_time_now(),
        "user_id": agent.user_id,  # 提问者（共享会话按此区分成员，历史回放/伪造记录用）
        "urls": agent.user_input_urls,
        "activate_skills":  agent.activate_skills,
    }
    # 本轮思路笔记（轮末由 reasoning 提炼）：下轮随正文重建进上下文
    if thinking_note:
        entry["thinking"] = thinking_note
    # 共享会话插入模式：一次回答对应多个提问者时，额外记录结构化的 asks 列表
    if asks and len(asks) > 1:
        entry["asks"] = asks
    # 本次对话实际用过的工具（注入上下文时以 [使用工具:…] 标记置于该条目开头）
    if agent.used_tools:
        entry["used_tools"] = list(dict.fromkeys(agent.used_tools))
    normals.append(entry)
    session_obj.save_history(history.merge(summary, normals, skills=summary_skills))
