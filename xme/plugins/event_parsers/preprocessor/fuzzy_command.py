"""指令纠错：漏了指令开头字符、或把指令名打错时，提示用户确认后替他执行。

预处理器在 nonebot 命令分发之前运行，只接管两类消息（其余一律放行给原有流程）：

- 漏了开头字符（如「天气 南京」）或指令名打错（如「/weathr 南京」）：
  发一条确认提示，并把纠正后的指令记入待确认表；
- 该用户紧接着在本聊天回复 `y`：按纠正后的指令替他执行，并吞掉这条 `y`。

待确认表按 `(group_id, user_id)` 隔离（私聊 `group_id` 为 `None`，与 aistop
的运行中会话同形状），带 `CONFIRM_TIMEOUT` 秒过期时间，用户回复别的内容即作废。
"""
import time
from typing import Optional, Tuple

import aiocqhttp
import config
from character import get_message
from nonebot import NoneBot, message_preprocessor
from nonebot.message import CanceledException
from nonebot.plugin import PluginManager

from xme.xmetools import cmdtools
from xme.xmetools.msgtools import send_event_msg
from xme.xmetools.texttools import fuzzy_search, strip_cq

# 等待用户回 `y` 的有效期（秒），超时即作废
CONFIRM_TIMEOUT = 60
# 指令名相似度下限，低于这个比例不算「打错」
FUZZY_RATIO = 0.7

ConfirmsKey_T = Tuple[Optional[int], int]


class PendingConfirms:
    """按 `(group_id, user_id)` 隔离的待确认指令表，带过期时间。

    私聊的 `group_id` 为 `None`，因此同一个人在群聊与私聊里互不串味——这正是
    旧实现（按 user_id 索引的全局变量）会把 A 群的纠错状态泄露到 B 群的原因。
    只做记录与失效判断，不碰 IO，可脱离 bot 单独测试。
    """

    def __init__(self, timeout: float = CONFIRM_TIMEOUT):
        self._timeout = timeout
        self._confirms: dict[ConfirmsKey_T, Tuple[float, str]] = {}

    def set(self, key: ConfirmsKey_T, command: str) -> None:
        """登记一条待确认指令，顺带清掉已过期的记录。"""
        self.prune()
        self._confirms[key] = (time.time() + self._timeout, command)

    def pop(self, key: ConfirmsKey_T) -> Optional[str]:
        """取出一条仍有效的待确认指令（取出即作废），没有则返回 None。"""
        self.prune()
        item = self._confirms.pop(key, None)
        return item[1] if item else None

    def discard(self, key: ConfirmsKey_T) -> None:
        """作废某个聊天的待确认指令。"""
        self._confirms.pop(key, None)

    def prune(self) -> None:
        """清掉已过期的记录。"""
        now = time.time()
        expired = [k for k, (expire_at, _) in self._confirms.items() if expire_at <= now]
        for key in expired:
            del self._confirms[key]


confirms = PendingConfirms()


def strip_self_at(text: str, self_id: int) -> str:
    """去掉正文开头 @ 本 bot 的那段 CQ 码，返回剩余内容。"""
    if not text.startswith(f"[CQ:at,qq={self_id}"):
        return text
    return text.partition("]")[2].strip()


def correction_target(text: str) -> Optional[str]:
    """算出这条消息该被纠正成哪条指令（含开头字符与原参数），无需纠正返回 None。

    两种情况：指令名打错（有开头字符但名字不在指令表里），或漏了开头字符
    （首词本身就是某个指令名/别名）。
    """
    if not text:
        return None
    if text[0] in config.COMMAND_START:
        body = text[1:]
        name = body.split(" ")[0]
        args = body[len(name):].strip()
        matched = fuzzy_search(name, cmdtools.get_cmds_alias_strings(), FUZZY_RATIO)
        if matched is None:
            return None
        return f"{config.COMMAND_START[0]}{matched}" + (f" {args}" if args else "")
    first = text.split(" ")[0]
    # 首词命中指令名/别名就够了：能走到这里说明它不是合法指令
    if len(first) < 2 or not cmdtools.get_cmd_by_alias(first, need_cmd_start=False):
        return None
    return f"{config.COMMAND_START[0]}{text}"


@message_preprocessor
async def fuzzy_cmd(bot: NoneBot, event: aiocqhttp.Event, plugin_manager: PluginManager):
    """漏前缀/打错指令名时提示确认，用户回 `y` 时代他执行。"""
    if event.user_id == event.self_id:
        # bot 自己的输出不参与纠错
        return
    text = (event.raw_message or "").strip()
    if not text:
        return
    text = strip_self_at(text, event.self_id)
    key = (event.get("group_id"), event.user_id)

    if strip_cq(text).strip().lower() == "y":
        command = confirms.pop(key)
        if command is not None:
            await cmdtools.event_send_cmd(command, bot, event)
            raise CanceledException(f"已按指令纠错执行 {command}")

    # 没回 y（或回的不是 y）：本次纠错作废，只认紧接着的那一句话
    confirms.discard(key)

    if cmdtools.is_command(text):
        return
    target = correction_target(text)
    if target is None:
        return
    await send_event_msg(bot, event, get_message("config", "fuzzy_cmd", new_cmd=target))
    confirms.set(key, target)
