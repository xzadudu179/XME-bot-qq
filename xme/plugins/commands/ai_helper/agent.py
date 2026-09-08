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
from xme.xmetools.texttools import get_images_from_message, hash_text
from xme.xmetools.debugtools import debug_msg
from xme.xmetools.msgtools import is_text_can_send, send_session_msg, setup_logger
from xme.xmetools.bottools import get_user_name
from xme.xmetools.timetools import get_time_now, Timer
from xme.xmetools import jsontools
from xme.xmetools.jsontools import read_from_path
from character import get_message
from xme.plugins.commands.xme_user.classes import user as u
from zai import ZhipuAiClient
from zai.core._errors import APIRequestFailedError
from xme.xmetools.videotools.core import VideoExtractResult
from .constants import (
    __plugin_name__,
    MAX_CHECK_TIMES,
    MAX_TOOL_CALL_TIMES,
    MAX_HISTORY_COUNT,
    COMPRESS_TRIGGER,
    CONTEXT_KEEP_RECENT,
    COMPRESS_MAX_LENGTH,
    THINKING_PARAMS,
    CONTEXT_LIMIT_DEFAULT,
    FOLD_HARD_RATIO,
    FOLD_KEEP_RECENT_ASSISTANTS,
    FOLD_KEEP_RECENT_TOOLS,
    FOLD_HARD_RATIO,
    FOLD_KEEP_RECENT_ASSISTANTS,
    FOLD_KEEP_RECENT_TOOLS,
    FOLD_TRIGGER_RATIO,
    CONTEXT_LIMIT_DEFAULT,
    MODEL_CONTEXT_LIMITS,
    FLASH_MODEL,
    MAX_HISTORY_FILE_COUNTS,
    MAX_HISTORY_FILES_SIZE,
)
from . import history
from . import credits
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


def _context_limit(model: str) -> int:
    """按模型名查输入上下文上限（tokens）；未知模型用兜底值。"""
    return MODEL_CONTEXT_LIMITS.get(model, CONTEXT_LIMIT_DEFAULT)


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


def _fold_early_context(messages: list, *, fold_tools: bool = False) -> int:
    """轮内上下文折叠：删除最早若干轮 assistant 的 reasoning_content（保留 content/tool_calls，
    协议结构不变；等价于 GLM-4.5 之前的标准消息形态，API 仍接受，代价仅是那几轮的推理连贯性
    与缓存命中）；fold_tools=True 时再把早期 tool 消息的 content 替换为可重取的占位符
    （tool_call_id 必须保留——协议要求 tool 消息与 tool_call 一一对应）。

    就地修改传入的 messages，返回折叠释放的估算字符量。幂等：无可折叠内容时返回 0。
    """
    freed = 0
    assistant_idx = [i for i, m in enumerate(messages)
                     if isinstance(m, dict) and m.get("role") == "assistant"]
    for i in assistant_idx[:-FOLD_KEEP_RECENT_ASSISTANTS] if FOLD_KEEP_RECENT_ASSISTANTS else assistant_idx:
        reasoning = messages[i].get("reasoning_content")
        if reasoning:
            messages[i].pop("reasoning_content", None)
            freed += len(str(reasoning))
    if fold_tools:
        tool_idx = [i for i, m in enumerate(messages)
                    if isinstance(m, dict) and m.get("role") == "tool"]
        for i in tool_idx[:-FOLD_KEEP_RECENT_TOOLS] if FOLD_KEEP_RECENT_TOOLS else tool_idx:
            content = messages[i].get("content")
            if isinstance(content, str) and len(content) > 200 and not content.startswith("[早期工具结果已折叠"):
                messages[i]["content"] = (f"[早期工具结果已折叠（原 {len(content)} 字）；"
                                          f"如需数据请重新调用该工具]")
                freed += len(content)
    return freed


def build_user_content(text: str, image_urls: list[str] | None = None,
                       extra_parts: list | None = None) -> list:
    """组装 GLM 多模态 user content：文本段 + 图片段 + 额外段（如视频文件）。

    发起者的原始输入与共享会话的插入消息共用此封装，保证两种输入形态一致。
    """
    parts: list = [{"type": "text", "text": text}]
    parts += [{"type": "image_url", "image_url": {"url": url}} for url in (image_urls or [])]
    parts += list(extra_parts or [])
    return parts


def _strip_unloadable_images(messages: list) -> int:
    """静默移除上下文里所有图片/视频/文件段（就地修改），返回移除数量。

    用于 GLM 1210（媒体输入解析失败）兜底：剥离只为保住会话，属内部机制，
    不应让模型感知——因此不做"链接失效"类提示（媒体本就是一次性输入，模型
    无需再次加载）；仅当消息因此变空时补一个中性占位维持结构完整。
    非 text 段一律移除（含未知类型），避免漏网段导致重试再次 1210。
    """
    removed = 0
    for m in messages:
        if not isinstance(m, dict):
            continue
        content = m.get("content")
        if not isinstance(content, list):
            continue
        new_parts = [p for p in content
                     if not (isinstance(p, dict) and p.get("type") not in (None, "text"))]
        dropped = len(content) - len(new_parts)
        if dropped:
            if not new_parts:
                new_parts = [{"type": "text", "text": "（媒体）"}]
            m["content"] = new_parts
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

    def __init__(self, ai_client: ZhipuAiClient, user_id: int, session, model="flash", ai_session=history.DEFAULT_SESSION, shared_session=None, resume_data=None):
        # ai_session：用户当前使用的 AI 会话名；session：bot 的 CommandSession
        # shared_session：共享会话对象（share.SharedSession）；不为 None 时历史读写走共享会话
        self.shared = shared_session
        self.ai_session = (shared_session.code if shared_session is not None else ai_session) or history.DEFAULT_SESSION
        MODEL_MAP = {
            "pro": "glm-5.3",
        }
        self.ref_map = {}
        # 文件内容指纹（路径 → sha256）：AI 经工具读到/写出文件时更新，
        # edit_file 写入前比对，拦截"读取后文件被外部改动"的静默错改
        self.file_hashes: dict[str, str] = {}
        self.tokens = 0
        self.other_credits = 0
        self.model_arg = model
        m = MODEL_MAP.get(model, None)
        self.model = m if m is not None else FLASH_MODEL
        # 当前轮真实使用的模型（带图轮会强制切视觉模型）：工具执行时据此决定
        # 是否走图片直注入（ImageToolResult）；每轮由 run_agent 刷新
        self.current_model = self.model
        self.cached_tokens = 0
        self.client = ai_client
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
        self.asks: list[dict] = []
        if resume_data:
            self.resume_messages = resume_data.get("messages") or []
            self.resume_model = resume_data.get("model")
            self.asks = list(resume_data.get("asks") or [])
            self.used_tools = list(resume_data.get("used_tools") or [])
            self.participants = list(resume_data.get("participants") or [user_id])
            self.tool_call_times = int(resume_data.get("tool_call_times") or 0)
            # 计费累加器：断点前的消耗一并恢复，最终结算不漏记
            self.tokens = float(resume_data.get("tokens") or 0)
            self.cached_tokens = float(resume_data.get("cached_tokens") or 0)
            self.other_credits = float(resume_data.get("other_credits") or 0)
            self.activate_skills = list(resume_data.get("activate_skills") or [])
        # 插入队列键与开关：共享会话按群号码，普通会话按 用户+会话名（所有会话均可开启）
        if self.shared is not None:
            self.insert_key = share.shared_insert_key(self.shared.code)
            self.insert_enabled = self.shared.insert_enabled
        else:
            self.insert_key = share.user_insert_key(user_id, self.ai_session)
            self.insert_enabled = normal_insert_enabled(user_id, self.ai_session)
        tools_path = Path(__file__).parent / "tools.json"
        with open(tools_path, "r", encoding="utf-8") as f:
            self.tools = json.load(f)
        _validate_tools(self.tools)

    async def run_agent(self, session, messages, model):
        # 本轮真实模型：工具（view_item/screenshot_page 等）据此决定图片直注入与否
        self.current_model = model
        MAX_RETRY_TIMES = 5
        retry_times = 0
        while True:
            try:
                result = await self.create_and_wait(session, messages, model)
            except APIRequestFailedError as ex:
                # 1210=媒体输入解析失败（过期链接 / video_url 不被支持等）。
                # 剥离全部媒体段后重建任务重试：剥离是破坏性的（媒体段只减不增），
                # 因此无需次数限制也可保证收敛；无媒体可剥时照抛，避免掩盖其他错误
                removed = _strip_unloadable_images(messages)
                if "1210" not in str(ex) or not removed:
                    raise
                ai_logger.warning(
                    f"媒体输入解析失败（1210），已静默移除 {removed} 个媒体段后重建任务重试")
                continue
            except RuntimeError:
                if retry_times >= MAX_RETRY_TIMES:
                    raise
                retry_times += 1
                # 紧急折叠后再重试：若失败源于输入超长，重试才有机会成功
                freed = _fold_early_context(messages, fold_tools=True)
                if freed:
                    ai_logger.warning(
                        f"模型调用失败，紧急折叠上下文后重试（第 {retry_times} 次，释放约 {freed:,} 字符）")
                continue
            message = result.choices[0].message
            self.tokens += result.usage.total_tokens
            self.cached_tokens += result.usage.prompt_tokens_details.cached_tokens
            # 轮内上下文折叠：用本次请求的真实输入量判断，在下一轮请求前瘦身
            self.last_prompt_tokens = result.usage.prompt_tokens
            limit = _context_limit(model)
            if self.last_prompt_tokens > limit * FOLD_TRIGGER_RATIO:
                fold_tools = self.last_prompt_tokens > limit * FOLD_HARD_RATIO
                freed = _fold_early_context(messages, fold_tools=fold_tools)
                if freed:
                    ai_logger.info(
                        f"上下文折叠：输入 {self.last_prompt_tokens:,}/{limit:,} tokens，"
                        f"{'含工具结果' if fold_tools else '仅思考'}，释放约 {freed:,} 字符")
            if message.reasoning_content:
                ai_logger.info(
                    f"\n===== GLM Reasoning {session.event.user_id} =====\n"
                    f"{message.reasoning_content}\n"
                    f"========================="
                )

            # 没有工具调用
            if not message.tool_calls:
                return result, self.tool_call_times
            # 有工具调用
            self.tool_call_times += 1
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    ai_logger.info(
                        f"[GLM Tool Call] "
                        f"{tool_call.function.name}"
                        f"({tool_call.function.arguments})"
                    )

            # 把 assistant 的原始消息加入上下文（含 reasoning_content）。
            # 交错式思考的硬性要求（GLM 文档）：工具结果必须与未修改的
            # reasoning_content 一并回传，model_dump 原样保留该字段
            assistant_message = message.model_dump(exclude_none=True)

            messages.append(assistant_message)

            # 执行所有工具
            injected_parts: list = []
            for tool_call in message.tool_calls:
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
            # 图片直注入（ImageToolResult）：工具拿到的图片/视频/文件不再经独立视觉
            # 调用转述，而是合并为一条 user 消息附给本轮模型，让模型亲自查看
            if injected_parts and self.current_model == FLASH_MODEL:
                messages.append({"role": "user", "content": build_user_content(
                    "[以上工具返回的图片/附件已附在本消息中，请结合上方工具结果处理]",
                    [], injected_parts)})

            # 插入模式：工具执行完毕后先打断以并入插入消息，再发起下一次模型调用
            if self.insert_enabled and share.has_pending_inserts(self.insert_key):
                raise InsertInterrupted()

    # session 留着以后有用
    async def execute_tool(self, session, tool_call, curr_tool_call_times):
        prefix = ""
        if curr_tool_call_times >= MAX_TOOL_CALL_TIMES:
            return f"[工具执行失败：次数已达到上限，请在下一个会话继续]"
        if curr_tool_call_times >= MAX_TOOL_CALL_TIMES - 7:
            prefix = f"[警告：剩余 {MAX_TOOL_CALL_TIMES - curr_tool_call_times} 次 tools 调用次数]\n"
        name = tool_call.function.name
        if name not in self.used_tools:
            self.used_tools.append(name)
        try:
            arguments = json.loads(tool_call.function.arguments)
            ai_logger.info(get_message("plugins", __plugin_name__, "call_tool", tool_name=name, arguments=tool_call.function.arguments))

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

    def _save_snapshot(self, messages: list, model: str) -> None:
        """把进行中的完整上下文落盘为快照（best-effort）。

        每次模型调用前覆盖写；进程异常死亡时文件残留，
        供 /ai --continue 恢复（用户输入/思考/工具结果/插入消息全在 messages 里）。
        """
        try:
            data = {
                "user_id": self.user_id,
                "ai_session": None if self.shared is not None else self.ai_session,
                "shared_code": self.shared.code if self.shared is not None else None,
                "model": model,
                "messages": messages,
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

    async def create_and_wait(self, session, messages, model):
        self._save_snapshot(messages, model)
        response = self.client.chat.asyncCompletions.create(
            model=model,
            messages=messages,
            tools=self.tools,
            thinking=dict(THINKING_PARAMS),
            tool_choice="auto",
            temperature=0.5,
        )
        task_id = response.id
        check_times = 0
        while check_times <= MAX_CHECK_TIMES:
            result = self.client.chat.asyncCompletions.retrieve_completion_result(
                id=task_id
            )

            if result.task_status == "SUCCESS":
                return result

            if result.task_status == "FAIL":
                raise RuntimeError(result)
            check_times += 1
            # 旧 arg 轮询（aget_arg_with_timeout）已退役：aistop 与同聊插入均由
            # 消息预处理器接管（工具执行中同样即时生效），这里只做固定间隔轮询 +
            # 插入打断检查，打断后由 user_talk 并入上下文重启
            logger.info(f"{session.event.user_id} 获取 AI 状态")
            if self.insert_enabled and share.has_pending_inserts(self.insert_key):
                raise InsertInterrupted()
            await asyncio.sleep(1)
        raise TimeoutError(f"AI 调用超时 (>{MAX_CHECK_TIMES}次)")

    async def _glm_chat(self, messages, model=FLASH_MODEL):
        """通用的一次性 chat 完成调用（用于历史压缩等），返回模型文本。"""
        response = self.client.chat.asyncCompletions.create(
            model=model,
            messages=messages,
        )
        task_id = response.id
        while True:
            result = self.client.chat.asyncCompletions.retrieve_completion_result(
                id=task_id
            )
            if result.task_status == "SUCCESS":
                self.other_credits += result.usage.total_tokens - (result.usage.prompt_tokens_details.cached_tokens * 0.75)
                return result.choices[0].message.content
            if result.task_status == "FAIL":
                raise RuntimeError("AI 压缩调用失败")
            await asyncio.sleep(0.5)

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
        if len(normals) <= COMPRESS_TRIGGER:
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
                await send_session_msg(session, get_message("plugins", __plugin_name__, 'talking_to_ai', model=self.model_arg, ai_session=self.ai_session))
                return len(summary)
        except Exception as ex:
            ai_logger.exception(f"上下文压缩失败: {ex}")
            return 0
        return 0

    async def get_video_url_dicts(self, text):
        """把文本里的视频链接转为 video_url 输入段。

        - 平台链接（B站/YouTube 等）：yt-dlp 下载到本地后以限时直链附入（文本替换为
          "[视频:平台] …"，只展示平台链接，不暴露本地直链）；
        - 媒体直链（.mp4 等）：LLM 已持有可用直链，直接原样附入，不下载。
        """
        links = extract_video_links(text)
        video_dicts: list = []
        pths: list = []
        new_text = text
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
                        video_dicts.append({"type": "video_url", "video_url": {"url": get_local_file_url(str(f))}})
            except Exception as ex:
                return f"[解析视频出现异常: {ex}]" + new_text, [], []
        # 媒体直链：LLM 已持有可用直链，直接原样附入（不下载、不暴露额外链接）
        def _direct_repl(m):
            url = m.group(0)
            video_dicts.append({"type": "video_url", "video_url": {"url": url}})
            return f"[视频:直链] {url}"
        new_text = _DIRECT_VIDEO_RE.sub(_direct_repl, new_text)
        return new_text, video_dicts, pths

    def compute_credits(self) -> dict:
        """按已累计 tokens 计算本轮 credits 消耗与参与者均摊（正常结束与中断结算共用）。

        返回 {"credits_use", "credits_split", "cached", "total"}；模型倍率取
        self.current_model（每轮 run_agent 刷新，中断时即最近一轮的真实模型）。
        """
        # 缓存 tokens 占 1/4
        credits_use = (
            self.tokens
            - self.cached_tokens * 0.75
        )
        multis = 1
        match self.current_model:
            case "glm-5.3":
                multis = 10
            case m if m == FLASH_MODEL:  # 裸名是捕获模式，必须用 guard 做值比较
                multis = 0.5
        credits_use *= multis
        credits_use += self.other_credits
        # 共享会话插入模式：全部用量在参与者间均摊（发起者 + 插入者）
        per_share = credits_use / len(self.participants) if self.participants else credits_use
        credits_split = {str(uid): round(per_share, 2) for uid in self.participants}
        return {"credits_use": credits_use, "credits_split": credits_split,
                "cached": self.cached_tokens, "total": self.tokens}

    async def user_talk(self, session: CommandSession, role, user, text):
        self.spent_secs.start()
        self.pending_messages.clear()
        prefix = ""
        if self.resume_messages is not None:
            # /ai --continue：以上次快照的完整上下文（用户输入/思考/工具结果/插入）重入循环
            compressed = 0
            ai_params = self.resume_messages
            asks = self.asks
            real_model = self.resume_model or self.model
            text = asks[-1].get("text", "") if asks else text
            prefix = get_message("plugins", __plugin_name__, "resume_prefix", count=len(ai_params))
        else:
            compressed = await self._compress_context(session)
            history, curr_text = await get_history(user, self.storage)

            # 提取 text 里的图片
            image_objects, matches = await get_images_from_message(session.bot, text)
            # pattern = r"\[CQ:image,(?![^\]]*emoji_id=)[^\]]*file=[^\]]*?\]"
            # matches = re.findall(pattern, text)
            for image_cq in matches:
                text = text.replace(image_cq, f"[图片{hash_text(image_cq)} 已附在输入里]")
            image_urls = [x["file"] for x in image_objects]

            text, video_dicts, pths = await self.get_video_url_dicts(text)
            self.temp_file_paths += pths
            self.user_input_urls["images"] = image_urls
            url_dicts = [{"type": "image_url", "image_url": {"url": v}} for v in image_urls]
            url_dicts += video_dicts
            ai_logger.info(f"用户 {user.id} 说：{text}")
            ai_logger.info(f"用户附带了以下图片url {url_dicts}")

            ai_params = [
                {"role": "system","content": role},
                *history,
                {"role": "user","content": build_user_content(f"{curr_text}\n{text}", image_urls, url_dicts)},
            ]
            real_model = FLASH_MODEL if len(url_dicts) > 0 else self.model
            if real_model != self.model:
                prefix = get_message("plugins", __plugin_name__, "model_change_prefix", model=self.model, vision_model=real_model)
            # 多提问记录：发起者的原始输入 + 每一条被并入的插入消息（共享会话插入模式）
            asks = [{"user_id": user.id, "text": text, "image_urls": list(image_urls)}]
            self.asks = asks
        # 插入队列键：共享会话按群号码，普通会话按 用户+会话名（与 AIHelper.insert_key 一致）
        while True:
            try:
                result, tool_call_times = await self.run_agent(session, ai_params, model=real_model)
                break
            except InsertInterrupted:
                # 打断点：把全部待插入消息并入上下文后重入 agent 循环（messages 数组原样延续）
                inserts = share.consume_inserts(self.insert_key)
                has_image_insert = False
                for ins in inserts:
                    if self.shared is not None:
                        ins_name = await get_user_name(ins.user_id, default=str(ins.user_id))
                        ins_label = f"[共享会话成员 {ins_name}(qq{ins.user_id}) 插入] "
                    else:
                        ins_label = "[用户插入] "  # 普通会话：插入者即用户本人
                    ai_params.append({"role": "user", "content": build_user_content(
                        f"{ins_label}{ins.text}",
                        list(ins.image_urls))})
                    asks.append({"user_id": ins.user_id, "text": ins.text,
                                 "image_urls": list(ins.image_urls)})
                    has_image_insert = has_image_insert or bool(ins.image_urls)
                    if ins.user_id not in self.participants:
                        self.participants.append(ins.user_id)
                    ai_logger.info(f"插入消息已并入上下文: {ins.user_id} {ins.text[:150]!r}" + "..." if len(ins.text) > 150 else "")
                if has_image_insert and real_model != FLASH_MODEL:
                    # 插入消息带图片：切换到视觉模型
                    real_model = FLASH_MODEL
                    prefix += get_message("plugins", __plugin_name__, "model_change_prefix",
                                          model=self.model, vision_model=real_model)
        self.spent_secs.stop()
        if result == False or result is AISTOP:
            # 主动中断（ask_user 的 aistop）：已消耗的 tokens 照常结算并提示
            tokens_use_dict = self.compute_credits()
            lefts = credits.settle_split(tokens_use_dict["credits_split"])
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
            ans = result.choices[0].message.content

            ai_logger.info(
                f"AI 返回了以下 response：{result}"
            )
            tokens_use_dict = self.compute_credits()
            credits_use = tokens_use_dict["credits_use"]
            credits_split = tokens_use_dict["credits_split"]
            debug_msg("处理结果")
            logger.info(
                f"缓存tokens "
                f"{self.cached_tokens}, "
                f"减少 {credits_use} 个 tokens"
            )
            if not (await is_text_can_send(session, ans, 4)):
                return "这个话题好像不是很合适呢...我们换个话题聊吧。", tokens_use_dict, {"messages": self.pending_messages, "prefix": prefix, "history_compressed": compressed, "talk_secs": self.spent_secs.get_timer_value()}, 0
            build_history(
                user=user,
                ask=asks[-1].get("text", text) if asks else text,
                ans=ans,
                agent=self,
                asks=asks,
            )
            return ans, tokens_use_dict, {"messages": self.pending_messages, "prefix": prefix, "history_compressed": compressed, "talk_secs": self.spent_secs.get_timer_value()}, tool_call_times
        except AttributeError as ex:
            ai_logger.error(f"attribute 错误: {ex}")

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
            marker = tools_marker if ask_index == 0 else ""
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


def build_history(user: u.User, ask, ans, agent, asks: list | None = None):
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
    # 共享会话插入模式：一次回答对应多个提问者时，额外记录结构化的 asks 列表
    if asks and len(asks) > 1:
        entry["asks"] = asks
    # 本次对话实际用过的工具（注入上下文时以 [使用工具:…] 标记置于该条目开头）
    if agent.used_tools:
        entry["used_tools"] = list(dict.fromkeys(agent.used_tools))
    normals.append(entry)
    if len(normals) > MAX_HISTORY_COUNT:
        normals = normals[-MAX_HISTORY_COUNT:]
    session_obj.save_history(history.merge(summary, normals, skills=summary_skills))
