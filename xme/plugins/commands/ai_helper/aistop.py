# some are made by Deepseek-v4-flash-vison-exp at Deepseek Harness
"""aistop 与同聊消息接管：消息预处理器统一处理运行中会话的输入。

预处理器在 nonebot 命令分发（含暂停会话的 arg 通道）之前运行，因此无论 AI 正在
等模型、执行长工具还是等待用户插入，发起者在本聊天的消息都能即时处理：
- `aistop`：取消会话任务并吞掉消息（长工具执行中同样即时生效）；
- `/ai xxx`：插入消息入队（开启插入模式时），`/ai stop` 直接中断；
- 其他指令：回复"正在与 AI 聊天中"提示；
- 普通文本：私聊下作为插入消息入队（开启插入模式时，未开则提示如何开启）；
  群聊下静默吞掉（避免群内闲聊被误吞/误插）。
以上均吞掉消息（CanceledException），不再进入任何命令/会话流；发送者在该聊天
没有运行中的会话时，本预处理器不干预，消息照常流转。
取消的收尾统一在 talk() 的 CancelledError 分支：清快照、清 temp、发送中断文案。
"""
import asyncio

import config
from nonebot.log import logger
from nonebot.message import message_preprocessor, CanceledException

from character import get_message
from xme.xmetools.cmdtools import is_command
from xme.xmetools.msgtools import send_event_msg
from xme.xmetools.texttools import get_images_from_message, hash_text
from xme.xmetools.timetools import get_time_now

from .constants import __plugin_name__, MAX_PENDING_INSERTS, COMMAND_ALIAS
from . import share

# 运行中的 AI 会话登记：key = (group_id, user_id)，value = {task, insert_key,
# insert_enabled}。私聊 group_id 为 None；key 里查不到时本预处理器一律放行。
_running_turns: dict[tuple, dict] = {}


def register_turn(group_id, user_id, task: asyncio.Task, insert_key: str = None, insert_enabled: bool = False) -> None:
    """会话开始时登记任务与插入信息（talk() 调用）。"""
    _running_turns[(group_id, user_id)] = {
        "task": task, "insert_key": insert_key, "insert_enabled": insert_enabled,
        "awaiting_reply": False,
    }


def set_awaiting_reply(group_id, user_id, flag: bool) -> None:
    """标记"AI 正在等用户回复"（ask_user 提问期间）。

    此时预处理器不再接管消息（直接放行），让用户回复经 nonebot 的 arg 通道
    送给 ask_user；否则回复会被当作"普通文本"静默吞掉，ask_user 只能等到超时。
    """
    turn = _running_turns.get((group_id, user_id))
    if turn is not None:
        turn["awaiting_reply"] = bool(flag)


def unregister_turn(group_id, user_id) -> None:
    """会话结束时注销（talk() 的 finally 调用）。"""
    _running_turns.pop((group_id, user_id), None)


def request_stop(group_id, user_id) -> bool:
    """取消该 (聊天, 用户) 正在运行的会话任务；找到并取消返回 True。

    /ai stop 与预处理器共用此入口；取消的收尾统一在 talk() 的
    CancelledError 分支处理（清快照/temp + 中断文案）。
    """
    turn = _running_turns.get((group_id, user_id))
    if turn is None:
        return False
    turn["task"].cancel()
    return True


def _insert_enabled_now(turn: dict) -> bool:
    """按插入键实时查询插入模式是否开启（对话进行中切换可立即生效）。

    构造期登记的快照值可能过期（群主在对话中打开插入），故以实时配置为准。
    """
    key = turn.get("insert_key") or ""
    try:
        if key.startswith("shared:"):
            return bool(share.SharedSession(key[len("shared:"):]).insert_enabled)
        if key.startswith("user:"):
            _, uid, name = key.split(":", 2)
            from . import session as session_module
            return session_module.normal_insert_enabled(int(uid), name)
    except Exception:
        pass
    return bool(turn.get("insert_enabled"))


@message_preprocessor
async def handle_running_turn_input(bot, event, plugin_manager):
    """接管运行中会话发起者在本聊天的消息：aistop / 插入 / 指令提示 / 静默。"""
    text = str(event.message).strip()
    if not text:
        return
    turn = _running_turns.get((event.get("group_id"), event.user_id))
    if turn is None:
        return
    # AI 正在等用户回复（ask_user 提问期间）：放行消息，交给 nonebot 的 arg 通道，
    # 让 ask_user 拿到回复（顺带 aistop 也能经此送达并触发中断）
    if turn.get("awaiting_reply"):
        return

    async def swallow(reason: str, reply: str = ""):
        """吞掉本消息（可选先回复一条），后续命令分发不再进行。"""
        if reply:
            try:
                await send_event_msg(bot, event, reply)
            except Exception:
                logger.warning(f"aistop 预处理器回复失败（消息仍被吞掉）：{reason}")
        raise CanceledException(reason)

    async def enqueue_and_ack(ins_text: str):
        """提取图片后把文本入插入队列，并按结果回执（/ai 分支与私聊普通文本共用）。"""
        image_objects, cq_matches = await get_images_from_message(bot, ins_text)
        for image_cq in cq_matches:
            ins_text = ins_text.replace(image_cq, f"[图片{hash_text(image_cq)}]")
        enqueued = share.enqueue_insert(turn["insert_key"], share.Insert(
            user_id=event.user_id, text=ins_text,
            image_urls=tuple(x["file"] for x in image_objects),
            time=get_time_now()))
        if enqueued:
            await swallow("insert", reply=get_message(
                "plugins", __plugin_name__, "shared_insert_accepted"))
            return
        await swallow("insert-full", reply=get_message(
            "plugins", __plugin_name__, "shared_insert_queue_full",
            max_pending=MAX_PENDING_INSERTS))

    # aistop：任意时刻（含长工具执行中）即时取消
    if text == "aistop":
        turn["task"].cancel()
        logger.info(f"{event.user_id} 发送 aistop：已中断其运行中的 AI 会话")
        raise CanceledException("aistop")

    if turn.get("insert_key") is None:
        return  # 会话尚未完成登记（AIHelper 未建好），放行给原有流程

    # /ai xxx：插入入队；/ai stop：直接中断
    if text[0] in config.COMMAND_START and text.split(" ")[0][1:] in (__plugin_name__, *COMMAND_ALIAS):
        ins_text = " ".join(text.split(" ")[1:]).strip()
        if ins_text in ("stop", "aistop"):
            turn["task"].cancel()
            logger.info(f"{event.user_id} 发送 /ai stop：已中断其运行中的 AI 会话")
            raise CanceledException("/ai stop")
        if not ins_text:
            await swallow("insert", reply=get_message(
                "plugins", __plugin_name__, "no_shared_insert"))
            return
        if not _insert_enabled_now(turn):
            # 未开插入模式：给提示（原指令路径的 ai_session_on 提示因预处理器先接管而永不触发）
            from character import get_message as _gm
            await swallow("ai-cmd-no-insert",
                          reply=_gm("plugins", __plugin_name__, "ai_session_on"))
            return
        await enqueue_and_ack(ins_text)
        return

    # 其他指令：提示正在与 AI 聊天中
    if is_command(text):
        await swallow("other-cmd", reply=get_message("plugins", __plugin_name__, "ai_sending"))
        return
    # 私聊普通文本：开了插入模式 → 作为插入消息入队并回执（私聊下最自然的插入方式）；
    # 未开 → 提示如何开启。群聊维持静默（避免群内闲聊被误吞/误插）。
    if event.get("group_id") is None and (turn.get("insert_key") or "").startswith("user:"):
        if not _insert_enabled_now(turn):
            await swallow("plain-text-no-insert", reply=get_message(
                "plugins", __plugin_name__, "normal_insert_off"))
            return
        await enqueue_and_ack(text)
        return
    await swallow("plain-text")
