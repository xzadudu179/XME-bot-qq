"""私聊指令提示：免费模型猜普通消息想用哪个指令，命中就提示一句并吞掉消息。

预处理器只接管私聊里的非指令消息（群聊、bot 自身消息、本身就是指令的一律放行）：
把消息、最近对话（最近两分钟，不足三条取最近三条，含 bot 回复）和全部可见指令的
「指令名： 简介」清单一起交给免费模型。模型返回可能的指令（可带参数：消息里说清的
参数原样带上，没说清的用简短中文占位描述）则回复「可以试试 "/xxx 参数" 指令哦」，
仅群聊可用的指令改说"在群里"，随后吞掉这条消息——意图已被识别，不该再触发别的回复。

同一「指令名 + 参数」的建议提示过一次后，接下来 `SUGGEST_DEDUP_COUNT` 条用户消息
内不再重复提示：已提示过的建议会注入提示词；模型仍原样重复时（免费模型常见），
带「必须给使用例子」的强化要求重试一次，让它输出通用参数的例子（如 "/game guess"），
重试仍重复才放行给 AI 接话。用户正常使用指令不受影响。记录（含 bot 回复与提示
标记）落盘到 RECENT_STORE_PATH，重启不丢。模型走 ai_helper 的 oneshot 免费候选链，
超时/限流/解析不出一律按「不匹配」放行，绝不影响原流程。

QQ 默认系统消息（好友申请/添加成功提示）与加好友之前的陌生人消息一律不记录、
不处理——它们不是用户输入，进上下文只会污染匹配。
"""
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import NamedTuple, Optional

import aiocqhttp
import config
from character import get_message
from nonebot import NoneBot, message_preprocessor
from nonebot.command import has_running_session
from nonebot.log import logger
from nonebot.message import CanceledException
from nonebot.plugin import PluginManager
from xme.xmetools import cmdtools

from xme.xmetools.doctools import is_group_only_cmd, iter_visible_cmd_docs
from xme.xmetools.msgtools import send_event_msg
from xme.xmetools.texttools import pinyin_sort_key, remove_punctuation, strip_cq

from . import fuzzy_command

# 同一指令提示过一次后，接下来这么多条用户消息内不再重复提示
SUGGEST_DEDUP_COUNT = 5
# 每人最多保留的记录条数（含 bot 回复，需容纳静默窗口 + 对话上下文）
RECENT_KEEP_PER_USER = 15
# 记录持久化位置（重启后静默状态与上下文不丢）
RECENT_STORE_PATH = Path("./data/recent_private_msgs.json")
# 单条记录文本的存储截断上限（AI 回复可能很长，没必要整段保存）
STORE_TEXT_MAX_CHARS = 500
# 带入模型上下文的范围：最近这么多秒内的消息，不足 CONTEXT_MIN_COUNT 条则取最近同样条数
CONTEXT_WINDOW_SECONDS = 120
CONTEXT_MIN_COUNT = 3
# 上下文单行的展示截断上限（要放得下 /xxx -h 帮助全文的 OPTIONS 段，约 200 字符）
CONTEXT_LINE_MAX_CHARS = 300
# 推荐参数与用户消息的截断上限
HINT_ARGS_MAX_CHARS = 50
HINT_MAX_CHARS = 300
# 单次模型调用超时（秒），候选链内超时自动换下一个候选
HINT_TIMEOUT = 8.0
# QQ 客户端自动附加的默认系统消息（好友申请/添加成功提示），不是用户输入
QQ_DEFAULT_TEXTS = ("请求添加你为好友", "我们已成功添加为好友，现在可以开始聊天啦~")
# 好友列表缓存时长（秒）：避免每条私聊都拉一次好友列表 API
FRIEND_CACHE_TTL = 300


@dataclass
class RecentMessage:
    """一条私聊消息记录：role 为 "user"/"bot"，用户消息带 is_cmd 与提示标记。"""
    role: str
    text: str
    is_cmd: bool = False
    time: float = 0.0    # 记录时间戳（time.time()）
    suggested_cmd: str = ""   # 这条消息之后 bot 提示过的建议（"指令名 参数"，查重键）

    def __post_init__(self):
        if not self.time:
            self.time = time.time()

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "RecentMessage":
        return cls(
            role=str(data.get("role") or "user"),
            text=str(data.get("text") or ""),
            is_cmd=bool(data.get("is_cmd") or False),
            time=float(data.get("time") or 0),
            suggested_cmd=str(data.get("suggested_cmd") or ""),
        )


class CmdEntry(NamedTuple):
    """一条可提示的指令：主名、简介、作用、是否仅群聊、展示用最短别名。"""
    name: str
    desc: str
    introduction: str
    group_only: bool
    display: str = ""


@dataclass
class CmdMatch:
    """一次命中：指令条目 + 模型从消息里提取的参数（可能为空）。"""
    entry: CmdEntry
    args: str = ""


class RecentMessages:
    """按 user_id 隔离的最近私聊消息表（新的在前），落盘持久化，重启不丢。

    只做记录、静默判断与上下文拼装，不碰网络，可脱离 bot 单独测试。
    """

    def __init__(self, keep: int = RECENT_KEEP_PER_USER, path: Path = RECENT_STORE_PATH):
        self._keep = keep
        self._path = path
        self._msgs: dict[int, list[RecentMessage]] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        """首次访问时从磁盘恢复（文件不存在或损坏时从空开始，不影响主流程）。"""
        if self._loaded:
            return
        self._loaded = True
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            for user_id, items in data.items():
                self._msgs[int(user_id)] = [RecentMessage.from_dict(d) for d in items]
                del self._msgs[int(user_id)][self._keep:]
        except FileNotFoundError:
            pass
        except Exception:
            logger.exception(f"读取私聊消息记录失败: {self._path}")

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps({str(u): [m.to_dict() for m in msgs]
                            for u, msgs in self._msgs.items()}, ensure_ascii=False),
                encoding="utf-8")
        except Exception:
            logger.exception(f"写入私聊消息记录失败: {self._path}")

    def append(self, user_id: int, message: RecentMessage) -> None:
        """记录一条消息（每人只保留最近 keep 条）并落盘。"""
        self._ensure_loaded()
        msgs = self._msgs.setdefault(user_id, [])
        msgs.insert(0, message)
        del msgs[self._keep:]
        self._save()

    def was_suggested(self, user_id: int, cmd: str,
                      window: int = SUGGEST_DEDUP_COUNT) -> bool:
        """该用户最近 window 条自己的消息里是否提示过同一建议（键为「指令名 参数」）。"""
        self._ensure_loaded()
        counted = 0
        for msg in self._msgs.get(user_id, []):
            if msg.role != "user":
                continue
            if cmd and msg.suggested_cmd == cmd:
                return True
            counted += 1
            if counted >= window:
                break
        return False

    def mark_suggested(self, user_id: int, message: RecentMessage, cmd: str) -> None:
        """给已记录的一条用户消息打上「已提示过 cmd」（键为「指令名 参数」）标记并落盘。"""
        if not any(m is message for m in self._msgs.get(user_id, [])):
            return
        message.suggested_cmd = cmd
        self._save()

    def suggested_keys(self, user_id: int, window: int = SUGGEST_DEDUP_COUNT) -> list[str]:
        """该用户最近 window 条自己的消息里提示过的建议键（新的在前，去重）。"""
        self._ensure_loaded()
        keys: list[str] = []
        counted = 0
        for msg in self._msgs.get(user_id, []):
            if msg.role != "user":
                continue
            if msg.suggested_cmd and msg.suggested_cmd not in keys:
                keys.append(msg.suggested_cmd)
            counted += 1
            if counted >= window:
                break
        return keys

    def recent_context(self, user_id: int, bot_label: str = "bot",
                       within_seconds: float = CONTEXT_WINDOW_SECONDS,
                       min_count: int = CONTEXT_MIN_COUNT) -> str:
        """拼装带入模型的最近对话（旧的在上）：最近 within_seconds 秒内的消息，
        不足 min_count 条时取最近 min_count 条；每行截断到 CONTEXT_LINE_MAX_CHARS。"""
        self._ensure_loaded()
        entries = self._msgs.get(user_id, [])
        if not entries:
            return ""
        now = time.time()
        window = [e for e in entries if e.time and now - e.time <= within_seconds]
        chosen = window if len(window) >= min_count else entries[:min_count]
        return "\n".join(
            f"{'用户' if e.role == 'user' else bot_label}：{e.text[:CONTEXT_LINE_MAX_CHARS]}"
            for e in reversed(chosen))


recent_msgs = RecentMessages()


def _pick_display_cmd(doc) -> str:
    """展示用指令名：主名与别名里按拼音长度取最短的（中文按拼音算，平局取先出现的）。"""
    aliases = doc.alias or ()
    candidates = [doc.name, *(str(a).strip() for a in aliases if str(a).strip())]
    return min(candidates, key=lambda c: len(pinyin_sort_key(c)))


def visible_cmd_entries() -> list[CmdEntry]:
    """收集全部普通用户可见指令的（主名, 简介, 介绍, 是否仅群聊, 展示别名），供模型清单与结果校验。"""
    entries = []
    for doc in iter_visible_cmd_docs():
        entries.append(CmdEntry(
            name=doc.name,
            desc=doc.desc,
            introduction=doc.introduction,
            group_only=is_group_only_cmd(doc.permissions),
            display=_pick_display_cmd(doc),
        ))
    return entries


def _bot_name_prefixes() -> list[str]:
    """bot 名字/昵称前缀清单（config.NICKNAME 是指令分发实际剥离的口径）。"""
    names = {get_message("bot_info", "name")}
    nickname = getattr(config, "NICKNAME", [])
    if not isinstance(nickname, list):
        nickname = [nickname]
    names.update(str(n) for n in nickname if n)
    return [n for n in names if n]


def strip_bot_name(text: str) -> str:
    """去掉正文开头连续出现的 bot 名字/昵称（如「漠月 /s」→「/s」），供指令判定。"""
    for name in _bot_name_prefixes():
        while text.startswith(name):
            text = text[len(name):].strip()
    return text


_friend_cache: dict[int, tuple[float, set[int]]] = {}   # self_id → (过期时间, 好友 id 集)


def is_qq_system_text(text: str) -> bool:
    """是否为 QQ 客户端自动附加的默认消息（好友申请/添加成功提示；系统消息以该短语开头）。"""
    return any(text.startswith(default) for default in QQ_DEFAULT_TEXTS)


async def is_friend(bot: NoneBot, user_id: int) -> bool:
    """用户是否为 bot 好友（带 TTL 缓存；SUPERUSERS 视为好友；列表拉取失败按好友处理）。

    口径与 private_messages 的好友校验一致：加好友之前的陌生人消息不该进上下文。
    """
    if user_id in config.SUPERUSERS:
        return True
    now = time.time()
    cached = _friend_cache.get(bot.self_id)
    if cached is None or cached[0] <= now:
        try:
            friends = await bot.get_friend_list()
        except Exception:
            logger.warning(f"拉取好友列表失败，本次按好友处理 user_id={user_id}")
            return True
        cached = (now + FRIEND_CACHE_TTL, {int(f.get("user_id") or 0) for f in friends})
        _friend_cache[bot.self_id] = cached
    return user_id in cached[1]


def build_prompt(text: str, entries: list[CmdEntry], context: str = "",
                 suggested: list[str] | None = None,
                 force_example: str = "") -> tuple[str, str]:
    """构造匹配提示词，返回 (system, user)：带最近对话、已提示建议与指令清单。

    force_example：非空时在末尾追加「该建议已提示过、必须改给使用例子」的强化要求
    （查重命中后的重试用），放最后以获得最高权重。
    """
    cmd_lines = "\n".join(
        f"- {e.name}：{e.desc}\n``` Text\n{e.introduction}\n```" if e.desc else f"- {e.name}" for e in entries)
    system = (
        "你是\"漠月\"机器人的指令匹配器。综合「最近对话」与「本次输入」，"
        "判断用户最想使用下面哪条指令，只输出一个 JSON 对象："
        '匹配到就输出 {"command": "指令名", "args": "参数"}，'
        '确实没有合适的指令才输出 {"command": null, "args": ""}，'
        "不要输出任何其他内容。\n"
        "判定规则：\n"
        "- 用户想使用某个功能（如「怎么查天气」「能不能查XX」），直接推荐那条指令本身，"
        '如「怎么查天气」输出 {"command": "wea", "args": ""}，不要推荐 help；\n'
        "- 用户问某种东西怎么获得/获取/拿到（如「星币怎么获取」），优先推荐能**产出**它的指令"
        "（介绍里写了签到得到、领取、抽奖这类获取途径的），"
        "排行榜、查询、统计、转账类指令只用于查看或转移数据，不是获取途径；"
        "清单里没有合适的获取途径时，推荐 ai_helper 且 args 留空，让用户问 AI；\n"
        "- 用户让你推荐或找点事情玩（如「推荐一个功能」「还有什么能玩的」「除了这个呢」），"
        "从指令清单里挑一条**没在「最近已提示过的建议」里出现过**的合适指令直接推荐，"
        "args 按消息里的线索填，没有就留空，"
        "不要推荐 help，也不要把用户的问题原文或最近对话里出现过的参数抄进 args；\n"
        "- 只有用户已经用过某条指令但出了问题或还是不会用（最近对话里能看到），"
        '或明确在问那条指令的用法时，才推荐 help：输出 {"command": "help", "args": "那条指令名"}；'
        "但最近对话里 bot 已经发过这条指令的帮助（[指令] xxx 开头的帮助内容）时不要再推荐 help，"
        "直接给使用例子；\n"
        "- 宽泛的指令问题用 help 说不清（如「XX是什么意思」「为什么不行」），"
        "或已经提示过 /help 用户还是不明白、又不好举例子时，"
        '推荐 AI 助手：输出 {"command": "ai_helper", "args": ""}，让用户直接向 AI 提问，'
        "不要把用户的话或上下文内容塞进 args；\n"
        '- 拿不准、用户只是在闲聊，或消息只是游戏/指令会话中的应答（如单独一个数字、单个词 quit、选项内容）或无关内容 (如 game 后出现了和 game 无关的文字例如 think) 时，'
        '输出 {"command": null, "args": ""}——单独的「1」「好」这类短应答绝不是指令意图；'
        '「最近对话」里的指令活动不代表当前消息与它有关，'
        "以本次输入本身为准，不要为了给例子而编造匹配。\n"
        "args 规则：\n"
        "- args 只放这条指令的参数本身，绝不能放用户整句话、问题原文或从最近对话里"
        "抄来的内容，用户没给出的内容不要编造；\n"
        "- 消息里明确给出的参数（地点、名字、数字等）原样带上，"
        '如「扬州天气怎么样」输出 {"command": "wea", "args": "扬州"}；\n'
        "- 需要参数但用户没说清时，args 用简短的中文描述占位（如「你想绑定的位置」）；\n"
        "- 但当用户想看使用例子，或对「最近已提示过的建议」里的指令还有疑问时，"
        "不要再原样输出那些建议，直接输出使用例子——args 填通用参数"
        "（如「1 2」「guess」这类数字或子指令名，不要编造食物名等具体内容）；"
        "例子必须构成一次**能成功执行**的调用：参数数量与格式要满足指令本身的要求"
        "（如 choice 至少要两个选项，「1 2」可以而单独「1」会报错）；"
        "例子要贴合用户想做的操作：用户问的是某个选项/子指令（如 -i、-a、guess）"
        "就把它带进例子（如用户问查看游戏信息，输出 {\"command\": \"game\", \"args\": \"-i guess\"} "
        "而不是不带 -i 的游玩例子）；\n"
        "- 没有参数需求就输出空字符串，对于“有可能是参数需求但概率不算大”的情况默认**无需求**。\n"
        f"可用指令：\n{cmd_lines}"
    )
    body = ""
    if context.strip():
        body += f"[最近对话]\n{context}\n\n"
    if suggested:
        body += ("[最近已提示过的建议]\n" + "\n".join(f"- {s}" for s in suggested)
                 + "\n（不要原样重复这些；用户还想了解时直接给使用例子）\n\n")
    body += f"[本次输入]\n{text[:HINT_MAX_CHARS]}"
    if force_example:
        body += ("\n\n[补充要求]\n"
                 f"「{force_example}」已经提示过用户了，绝对不要再输出这条建议"
                 "（换逗号、换分隔符写参数的变体也算重复）。请二选一：\n"
                 "a) 用户是对这条指令本身还有疑问：给出它的使用例子——command 用该指令本身"
                 "（不要推荐 help，若原建议是 help 就换成它所帮助的那条指令），"
                 "args 填通用参数（子指令名、数字范围、1 2 这类，可参考可用指令与最近对话），"
                 "且必须构成能成功执行的调用（如 choice 给「1 2」而不要单独「1」），"
                 "例子要贴合用户问的选项/子指令（用户问 -i 这类查看信息就带上 -i）；\n"
                 "b) 用户是想再要一条别的推荐（如「推荐一个功能」「除了这个呢」）："
                 "从可用指令里换一条**未提示过的**合适指令，args 按消息线索填或留空；\n"
                 '若用户的消息其实与指令无关（会话应答、闲聊），输出 {"command": null, "args": ""}。')
    return system, body


def _clean_args(raw: object) -> str:
    """清洗模型给出的推荐参数：压平空白成单行短文本，剥掉花括号（防污染文案占位符）。"""
    if not isinstance(raw, str):
        return ""
    args = " ".join(raw.replace("{", "").replace("}", "").split())
    return args[:HINT_ARGS_MAX_CHARS]


def parse_match(data: object, entries: list[CmdEntry]) -> Optional[CmdMatch]:
    """把模型输出的 JSON 归一到可见指令；没匹配到或指令无效时返回 None。

    接受主名或别名（别名经 cmdtools.get_cmd_by_alias 归一到主名）；只有 entries
    收录的指令才算命中，SUPERUSER 专用等不可提示的指令一律算没匹配。
    """
    if not isinstance(data, dict) or not isinstance(data.get("command"), str):
        return None
    name = data["command"].strip()
    if not name:
        return None
    if name[0] in config.COMMAND_START:
        name = name[1:].strip()
    if not name:
        return None
    by_name = {e.name: e for e in entries}
    entry = next((by_name[c] for c in (name, name.split(" ")[0]) if c in by_name), None)
    if entry is None:
        cmd = cmdtools.get_cmd_by_alias(name, need_cmd_start=False)
        entry = by_name.get(cmd.name[0]) if cmd else None
    if entry is None:
        return None
    return CmdMatch(entry, _clean_args(data.get("args")))


def hint_text(match: CmdMatch) -> str:
    """按「私聊可用 / 仅群聊可用」取角色文案；指令名用最短别名展示，没有简介时省略简介段。"""
    cmd = match.entry.display or match.entry.name
    name = f"{cmd} {match.args}".strip() if match.args else cmd
    desc_line = get_message("config", "cmd_suggest_desc", desc=match.entry.desc) if match.entry.desc else ""
    prefix = "在群里" if match.entry.group_only else ""
    return get_message("config", "cmd_suggest", name=name, desc_line=desc_line, prefix=prefix)


def suggest_key(match: CmdMatch) -> str:
    """建议查重键：指令名 + 归一化参数。

    参数归一时把逗号（全半角）视同空白——模型常用「1,2,3」这类换分隔符的变体
    绕过「1 2 3」的查重，归一后视为同一条建议；只影响查重比对，不影响展示。
    """
    args = " ".join(match.args.replace(",", " ").replace("，", " ").split())
    return f"{match.entry.name} {args}".strip()


async def match_command(text: str, context: str = "",
                        suggested: list[str] | None = None,
                        force_example: str = "") -> Optional[CmdMatch]:
    """把一条普通消息交给免费模型匹配可见指令；不匹配/失败返回 None，不抛异常。"""
    # 懒导入：ai_helper 包体很重，加载顺序上也晚于本插件
    from xme.plugins.commands.ai_helper.llm import oneshot

    entries = visible_cmd_entries()
    if not entries:
        return None
    system, prompt = build_prompt(text, entries, context, suggested, force_example)
    result = await oneshot.ask(
        prompt, system=system, model=None, temperature=0.0,
        timeout=HINT_TIMEOUT, json_output=True, silent=False, label="私聊指令提示",
        response_format={"type": "json_object"})
    if result is None:
        return None
    return parse_match(result.data, entries)


@message_preprocessor
async def cmd_suggest(bot: NoneBot, event: aiocqhttp.Event, plugin_manager: PluginManager):
    """私聊普通消息可能想用某指令时提示一句并吞掉消息，其余一律放行。"""
    if event.get("group_id") is not None:
        # 仅私聊生效
        return
    if cmdtools.is_command(event.raw_message):
        return
    text = strip_cq((event.raw_message or "")).strip()
    if event.user_id == event.self_id:
        # bot 自己发出的私聊消息：记为对 target_id 用户的回复，供上下文使用
        # （对陌生人发不出消息，理论到不了这里；好友判定兜底保持口径一致）
        target = int(event.get("target_id") or 0)
        if target > 0 and text and await is_friend(bot, target):
            recent_msgs.append(target, RecentMessage(
                role="bot", text=text[:STORE_TEXT_MAX_CHARS]))
        return
    if not text:
        return
    if is_qq_system_text(text):
        return
    if has_running_session(event):
        # 指令会话接管输入中（handler 执行或 aget 等待参数，如游戏数字、恢复对话的
        # 选项回复）：消息属于会话参数，不记录也不提示，交回 handle_command 喂给会话
        return
    from xme.plugins.commands.ai_helper import aistop
    if aistop.has_running_turn(event.get("group_id"), event.user_id):
        # AI 会话运行中（含等待回复/插入模式）：消息由 aistop 全权接管（插入入队或
        # 提示），本模块让路，避免抢跑打断 AI 对话与恢复确认流程
        return
    if remove_punctuation(text).lower() in ["y"]:
        # fuzzy_cmd 的确认词，不参与提示
        return
    if not await is_friend(bot, event.user_id):
        # 加好友之前的陌生人消息：不入上下文、不提示，直接不处理
        return
    is_cmd = cmdtools.is_command(strip_bot_name(text))
    context = recent_msgs.recent_context(
        event.user_id, bot_label=get_message("bot_info", "name"))
    suggested = recent_msgs.suggested_keys(event.user_id)
    user_record = RecentMessage(role="user", text=text[:STORE_TEXT_MAX_CHARS], is_cmd=is_cmd)
    recent_msgs.append(event.user_id, user_record)
    if is_cmd:
        # 本身是指令（含纠错重分发）：照常执行，不做提示
        return
    if fuzzy_command.correction_target(text) is not None:
        # 漏前缀/打错名的消息由 fuzzy_cmd 接管，避免同一句话双重提示
        return
    match = await match_command(text, context, suggested)
    if match is None:
        return
    suggestion = suggest_key(match)
    if recent_msgs.was_suggested(event.user_id, suggestion):
        # 模型原样重复已提示过的建议（免费模型常见）：带强制换建议/给例子的要求重试一次
        match = await match_command(text, context, suggested, force_example=suggestion)
        if match is None:
            return
        suggestion = suggest_key(match)
        if recent_msgs.was_suggested(event.user_id, suggestion):
            # 重试仍重复：放弃提示，消息照常走原流程
            return
    try:
        await send_event_msg(bot, event, hint_text(match))
    except Exception:
        # 发送失败（如非好友）就放行，不吞消息
        return
    recent_msgs.mark_suggested(event.user_id, user_record, suggestion)
    raise CanceledException(f"已提示指令 {suggestion}")
