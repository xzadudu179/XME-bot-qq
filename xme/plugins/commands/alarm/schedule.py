"""回复消息 + 「记录日程/设置计时器」：用免费模型从被回复的内容里抽日程，确认后登记。

命中后走这个流程：
1. 取被回复消息的文本（msgtools.get_replied_message，靠 CQ:reply / reply 消息段 + get_msg）；
2. 免费模型只负责「摘录与切分」：列出原文里出现的「时间表达 + 事项名称」，不改写、不换算；
3. 时间表达再交给本地解析器（timetools.parse_leading_time）判定能不能解析，不能的就丢掉；
4. 只剩一条直接登记；多条回一份编号列表，用户发序号（空格隔开，如 "1 3"）后把选中的登记。

选择状态按 (group_id, user_id) 隔离、带超时，发别的内容即作废。登记共用 reminders.register_reminder，
所以名字校验/容量/去重/循环等规则与 /alm 完全一致。
"""
import re
import time
from dataclasses import dataclass
from typing import Optional

import aiocqhttp
from nonebot import NoneBot, message_preprocessor
from nonebot.command import has_running_session
from nonebot.log import logger
from nonebot.message import CanceledException
from nonebot.plugin import PluginManager

from character import get_message
from xme.xmetools import cmdtools, timetools
from xme.xmetools.bottools import is_friend, strip_bot_name
from xme.xmetools.msgtools import get_replied_message, get_reply_message_id, send_event_msg
from xme.xmetools.texttools import remove_punctuation, strip_cq, text_combinations
from xme.xmetools.plugintools import record_plugin_call

from . import __plugin_name__
from .constants import DUPLICATE_TOLERANCE_SECS
from .reminders import not_friend_hint, register_reminder, time_display
from .timers import AlarmTimer, is_duplicate_reminder

# 触发语：消息以这些说法开头（允许「记录日程吧」这类尾巴）
TRIGGER_PHRASES = ("记录日程", "记日程", "记一下日程", "记个日程", "加日程", "添加日程", "添加一下日程", "加一下日程",
                   "设置计时器", "设计时器", "设个计时器", "设置一个计时器", "设置一下计时器", "设一下计时器", "设置下计时器", "登记日程", "登记一下日程", "登记一个日程")
TRIGGER_PREFIXS = ("帮我{suf}", "为我{suf}", "给我{suf}", "{suf}")
# 一次最多接受几条候选日程
MAX_SCHEDULE_ITEMS = 10
# 等用户选序号的超时（秒）
SELECT_TIMEOUT = 120
# 模型调用超时（秒）
PARSE_TIMEOUT = 20.0
# 触发语里允许夹的口语指代词（「记录这个日程」=「记录日程」）
_TRIGGER_FILLER_RE = re.compile(r"这个|那个|一个|一下")
# 纯序号输入（用户在选择阶段发的，如 "1 3"）
_INDEXES_RE = re.compile(r"^[\d\s]+$")

# 模型提示词：只摘录、不换算，时间是否成立由本地解析器判定
_SCHEDULE_PROMPT = (
    "你是\"漠月\"机器人的日程解析器。用户回复了一条消息，请从这条消息里找出所有可以设置成提醒的"
    "事项，只输出一个 JSON 对象：{\"items\": [{\"time\": \"时间表达\", \"name\": \"事项名称\"}]}，"
    "不要输出任何其他内容。\n"
    "规则：\n"
    "- time 必须是原文里出现的**时间表达原样摘录**（如\"明天下午三点\"、\"5分钟后\"、\"每天9点\"），"
    "不要换算成具体日期、不要自己编；\n"
    "- name 要让人一眼看懂\"要做什么\"：用**主体/对象 + 动作**的短语（如\"开会\"\"吃药\"\"交房租\"），"
    "2~10 个字，用原文里的词；不要只写一个动词或一个泛词（\"出发\"\"开始\"\"提醒\"这种不合格）；名字一时想不好也要输出这一项，把动词和原文里的主题词拼起来即可；\n"
    "- 一句话里没写清主体时，从上下文（同一段话、上一句）里把主题词补进 name。"
    "例如原文是\"签到失败，4小时20分后才能继续\"，应输出 time=\"4小时20分后\"、name=\"继续签到\"，"
    "不要写成 name=\"继续\"；\n"
    "- name 里不要带时间（时间放在 time 里），多个事项的名字要能互相区分；\n"
    "- 只提取确实带时间的日程，没有写时间的事项不要提取；\n"
    "- time 和 name 都不要带上对方的词，例如原文\"明天九点开会\"应输出 time=\"明天九点\"、name=\"开会\"；\n"
    f"- 最多 {MAX_SCHEDULE_ITEMS} 项；确实没有可提取的日程时输出 {{\"items\": []}}。"
)


@dataclass(frozen=True)
class ScheduleCandidate:
    """一条抽出来、且时间能被本地解析器解析的候选日程。"""
    parsed: timetools.TimeResult
    name: str


class PendingSchedules:
    """按 (group_id, user_id) 隔离的待选日程表，带过期时间（只做记录与失效判断，不碰 IO）。"""

    def __init__(self, timeout: float = SELECT_TIMEOUT):
        self._timeout = timeout
        self._items: dict[tuple, tuple[float, list[ScheduleCandidate]]] = {}

    def set(self, key: tuple, items: list[ScheduleCandidate]) -> None:
        """登记一份待选列表，顺带清掉已过期的记录。"""
        self.prune()
        self._items[key] = (time.time() + self._timeout, items)

    def get(self, key: tuple) -> Optional[list[ScheduleCandidate]]:
        """取出一份仍有效的待选列表（保留在表里），没有则返回 None。"""
        self.prune()
        item = self._items.get(key)
        return item[1] if item else None

    def discard(self, key: tuple) -> None:
        """作废某个聊天的待选列表。"""
        self._items.pop(key, None)

    def prune(self) -> None:
        """清掉已过期的记录。"""
        now = time.time()
        for key in [k for k, (expire_at, _) in self._items.items() if expire_at <= now]:
            del self._items[key]


pending_schedules = PendingSchedules()


# get_pure_text_message 把图片等非文本段写成 &#91;类型&#93; 占位，喂模型前换成普通说明
_TEXT_PLACEHOLDER_RE = re.compile(r"&#91;(?P<kind>[^&]*?)&#93;")


def clean_text_for_model(text: str) -> str:
    """把喂给模型的被回复文本清理一下：占位符换成「[类型]」、压掉多余空行。"""
    cleaned = _TEXT_PLACEHOLDER_RE.sub(lambda m: f"[{m.group('kind')}]", text or "")
    return re.sub(r"\n{2,}", "\n", cleaned).strip()


def pick_candidates(raw_items: list, now: float | None = None) -> list[ScheduleCandidate]:
    """把模型给的 (时间, 名称) 过滤成可解析的候选（纯函数，便于单独测试）。

    时间交给 timetools 解析，解析不了/名字为空的丢掉；模型偶尔的重复项也在这里去掉。
    """
    now_ts = time.time() if now is None else now
    candidates: list[ScheduleCandidate] = []
    dropped: list[str] = []
    for item in raw_items:
        if not isinstance(item, dict) or len(candidates) >= MAX_SCHEDULE_ITEMS:
            continue
        time_text = str(item.get("time") or "").strip()
        name = str(item.get("name") or "").strip()
        if not time_text:
            continue
        parsed = timetools.parse_leading_time(time_text, now_ts)
        if parsed.error is not None or parsed.consumed == 0:
            dropped.append(f"时间解析不了 {time_text!r}（{parsed.error.value if parsed.error else '没识别到'}）")
            continue
        name = name or time_text[parsed.consumed:].strip(" ，,。.、")
        if len(name) < 2:
            # 单字名字没有信息量（模型偶尔给"吃"这种），直接丢弃
            dropped.append(f"名字太短 {name!r}")
            continue
        duplicate = next((c for c in candidates if is_duplicate_reminder(
            AlarmTimer(user_id=0, name=c.name, fire_at=c.parsed.fire_at, created_at=0,
                       repeat=c.parsed.repeat),
            name, parsed.fire_at, parsed.repeat, DUPLICATE_TOLERANCE_SECS)), None)
        if duplicate is not None:
            # 和已接受的候选算同一件事（口径与登记时一致），不再重复列出
            dropped.append(f"与「{duplicate.name}」重复 {name!r}")
            continue
        candidates.append(ScheduleCandidate(parsed=parsed, name=name))
    if dropped:
        logger.info(f"日程解析：丢掉了 {len(dropped)} 项 —— " + "；".join(dropped))
    return candidates


def parse_indexes(text: str, count: int) -> Optional[list[int]]:
    """把「1 3」这类序号文本解析成 0 起的下标列表；有超范围/重复以外的非法项返回 None。"""
    indexes: list[int] = []
    for token in text.split():
        if not token.isdecimal():
            return None
        index = int(token) - 1
        if not 0 <= index < count:
            return None
        if index not in indexes:
            indexes.append(index)
    return indexes or None


async def ask_schedule_items(text: str, now: float | None = None) -> Optional[list[ScheduleCandidate]]:
    """用模型从文本里抽日程，返回可解析的候选列表；模型调用失败返回 None。"""
    from xme.plugins.commands.ai_helper.llm import oneshot   # 懒导入：模型栈很重
    result = await oneshot.ask(
                                                           # 填写 None 调用免费模型
        clean_text_for_model(text), system=_SCHEDULE_PROMPT, model=["dsflash", "minimax", "qwenflash"], temperature=0.0,
        timeout=PARSE_TIMEOUT, json_output=True, silent=True, label="日程解析",
        response_format={"type": "json_object"})
    if result is None:
        logger.warning("日程解析：模型调用失败（所有候选都不可用）")
        return None
    data = result.data
    raw_items = data.get("items") if isinstance(data, dict) else None
    logger.info(f"日程解析：模型返回 {raw_items!r}")
    if not isinstance(raw_items, list):
        return []
    return pick_candidates(raw_items, now)


async def _reply(bot: NoneBot, event: aiocqhttp.Event, message: str) -> None:
    """回一条消息（失败只记日志，不打断流程）。"""
    try:
        await send_event_msg(bot, event, message)
    except Exception:
        logger.warning(f"日程解析回复发送失败：{message}")


async def _register_chosen(bot: NoneBot, event: aiocqhttp.Event,
                           candidates: list[ScheduleCandidate], indexes: list[int]) -> None:
    """把选中的候选登记成计时器，并回执（规则/文案与 /alm 完全共用）。"""
    replies = []
    any_ok = False
    for index in indexes:
        candidate = candidates[index]
        ok, text = await register_reminder(bot, event, event.user_id,
                                           candidate.parsed, candidate.name)
        any_ok = any_ok or ok
        replies.append(text)
    if any_ok:
        replies[-1] += await not_friend_hint(bot, event.user_id)
    await _reply(bot, event, "\n".join(replies))


def _normalize_trigger(text: str) -> str:
    """触发语归一化：去掉标点与口语里夹的指代词（「记录这个日程。」→「记录日程」）。"""
    return _TRIGGER_FILLER_RE.sub("", remove_punctuation(text))


def matches_trigger(text: str) -> bool:
    """消息（已剥称呼）是不是「记录日程/设置计时器」这类请求。

    标点与口语里夹的指代词不影响判定：「记录日程。」「记录这个日程」「帮我记录一下日程」都算。
    """
    normalized = _normalize_trigger(text)
    phrases = tuple(TRIGGER_PHRASES) + tuple(text_combinations(TRIGGER_PREFIXS, suf=TRIGGER_PHRASES))
    return any(normalized.startswith(_normalize_trigger(phrase)) for phrase in phrases)


def _format_candidates(candidates: list[ScheduleCandidate]) -> str:
    """把候选列表拼成「编号. 时间 名称」的回复文案。"""
    now = time.time()
    lines = [
        get_message("plugins", __plugin_name__, "list_item", index=index, name=candidate.name,
                    time=time_display(candidate.parsed.fire_at, candidate.parsed.seconds,
                                      candidate.parsed.repeat),
                    replace_cq_str=True)
        for index, candidate in enumerate(candidates, start=1)
    ]
    return "\n".join([get_message("plugins", __plugin_name__, "schedule_list_header",
                                  count=len(candidates)),
                      *lines,
                      get_message("plugins", __plugin_name__, "schedule_list_suffix")])


@message_preprocessor
async def schedule_from_reply(bot: NoneBot, event: aiocqhttp.Event, plugin_manager: PluginManager):
    """回复消息 + 「记录日程/设置计时器」：解析被回复内容并登记；随后按序号选择要记的日程。"""
    if event.user_id == event.self_id:
        return
    # 回复别人的消息时消息以 reply 段开头：框架不会自动剥昵称、也不会置 to_me，
    # 而且 str(event.message) 里带着 [CQ:reply,id=…] 前缀——这里统一自己处理
    raw_text = strip_cq(str(event.message)).strip()
    if not raw_text or cmdtools.is_command(raw_text):
        return
    text = strip_bot_name(raw_text)
    called = text != raw_text          # 剥掉过称呼 = 叫了 bot
    key = (event.get("group_id"), event.user_id)

    pending = pending_schedules.get(key)
    if pending is not None:
        if _INDEXES_RE.match(text):
            pending_schedules.discard(key)
            indexes = parse_indexes(text, len(pending))
            if indexes is None:
                # 序号不合法：列表留着，让用户重发
                pending_schedules.set(key, pending)
                await _reply(bot, event, get_message("plugins", __plugin_name__,
                                                     "schedule_select_invalid"))
                record_plugin_call(__plugin_name__, from_user_id=event.user_id,
                                   call_group=event.get("group_id"), success=True, args=text)
                raise CanceledException("日程序号不合法")
            await _register_chosen(bot, event, pending, indexes)
            record_plugin_call(__plugin_name__, from_user_id=event.user_id,
                               call_group=event.get("group_id"), success=True, args=text)
            raise CanceledException("已按序号登记日程")
        # 不是序号：放弃这次选择，继续按"新请求"处理
        pending_schedules.discard(key)

    if not matches_trigger(text):
        return
    if event.get("group_id") is not None and not (event.get("to_me") or called):
        # 群聊里没叫我：像在和群友说话，不接管
        return
    if has_running_session(event):
        return
    from xme.plugins.commands.ai_helper import aistop
    if aistop.has_running_turn(event.get("group_id"), event.user_id):
        return
    if event.get("group_id") is None and not await is_friend(bot, event.user_id):
        return

    replied = await get_replied_message(bot, event)
    if replied is None:
        if get_reply_message_id(event) is None:
            await _reply(bot, event, get_message("plugins", __plugin_name__, "schedule_not_reply"))
            raise CanceledException("不是回复消息")
        # 有回复段、但取不到那条消息（被撤回 / 协议端不支持）
        await _reply(bot, event, get_message("plugins", __plugin_name__, "schedule_reply_missing"))
        raise CanceledException("取不到被回复的消息")
    if not replied.text:
        await _reply(bot, event, get_message("plugins", __plugin_name__, "schedule_no_items"))
        raise CanceledException("回复内容为空")
    candidates = await ask_schedule_items(replied.text)
    if candidates is None:
        await _reply(bot, event, get_message("plugins", __plugin_name__, "schedule_parse_failed"))
        raise CanceledException("日程解析失败")
    if not candidates:
        await _reply(bot, event, get_message("plugins", __plugin_name__, "schedule_no_items"))
        raise CanceledException("回复里没有可解析的日程")
    if len(candidates) == 1:
        await _register_chosen(bot, event, candidates, [0])
        record_plugin_call(__plugin_name__, from_user_id=event.user_id,
                           call_group=event.get("group_id"), success=True, args=text)
        raise CanceledException("已登记日程")
    pending_schedules.set(key, candidates)
    await _reply(bot, event, _format_candidates(candidates))
    record_plugin_call(__plugin_name__, from_user_id=event.user_id,
                       call_group=event.get("group_id"), success=True, args=text)
    raise CanceledException("已列出候选日程")
