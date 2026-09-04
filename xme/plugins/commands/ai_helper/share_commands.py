"""/ai -c 的共享会话子命令实现（share / join / rev / info / kick / leave / history）。

统一签名 (session, user, args=None)，薄层：清洗参数 → 调 share.py 的存储/业务 →
get_message 拼回复文案；涉及他人通知的统一走 msgtools.send_to_user（私聊，失败不打断主流程）。
当前会话由 session.current_storage 统一解析（统一指针，isinstance 区分普通/共享）。
"""
from character import get_message
from nonebot import CommandSession
from nonebot.log import logger

from xme.xmetools.bottools import get_user_name
from xme.xmetools.msgtools import (
    CMD_END,
    change_group_message_content,
    send_forward_msg,
    send_to_user,
)
from xme.xmetools.timetools import get_time_difference, get_time_now

from . import history, share
from .commands import _session_by_index
from .constants import (
    DEFAULT_SHARED_TITLE,
    JOIN_REQUEST_COOLDOWN,
    MAX_HISTORY_VIEW,
    MAX_JOINED_SHARED,
    MAX_SHARED_MEMBERS,
    SHARED_REQUEST_OPS,
    __plugin_name__,
)
from .session import current_storage, set_current_session
from .share import SharedSession


def _msg(key: str, **kwargs) -> str:
    """取 ai_helper 插件文案的快捷方式。"""
    return get_message("plugins", __plugin_name__, key, **kwargs)


def _clean_args(args) -> list[str]:
    """统一清洗子命令参数：去首尾空白、丢弃空串。"""
    return [a.strip() for a in (args or []) if a and a.strip()]


async def _sender_dict(session: CommandSession, user_id) -> dict:
    """构造 change_group_message_content 需要的 {"sender": ...} 字典。

    群内取群成员信息（含群名片），私聊取陌生人信息。
    """
    if session.event.group_id:
        info = await session.bot.api.get_group_member_info(group_id=session.event.group_id, user_id=user_id)
    else:
        info = await session.bot.api.get_stranger_info(user_id=user_id)
    return {"sender": info}


def share_session(session, user, args=None):
    """创建共享会话：share [普通会话序号]（带序号则复制该会话历史为初始记录）。

    创建后自动把调用者切换到新共享会话。
    """
    args = _clean_args(args)
    if len(share.joined_codes(user.id)) >= MAX_JOINED_SHARED:
        return _msg("shared_join_limit", joined_max=MAX_JOINED_SHARED)
    items, title = [], DEFAULT_SHARED_TITLE
    if args:
        source, err = _session_by_index(user.id, args[0])
        if err:
            return err
        items = source.load_history()
        title = source.ai_session
    s = SharedSession.create(user.id, title=title, history_items=items)
    if s is None:
        return _msg("shared_code_exhausted")
    share.add_joined(user.id, s.code)
    set_current_session(user.id, s.code)
    return _msg("shared_created", code=s.code, title=s.title,
                member_max=MAX_SHARED_MEMBERS, joined=len(share.joined_codes(user.id)),
                joined_max=MAX_JOINED_SHARED)


async def join_session(session, user, args=None):
    """请求加入共享会话：join <群号码>（写入待审请求并私聊通知群主）。"""
    args = _clean_args(args)
    if not args:
        return _msg("join_need_arg")
    code = share.normalize_code(args[0])
    s = SharedSession(code)
    if not s.exists():
        return _msg("shared_code_not_found", code=code)
    if s.is_member(user.id):
        return _msg("join_already_member")
    if s.is_blocked(user.id):
        # 被屏蔽：静默忽略——不回复请求者、不通知群主、不进入请求列表
        return CMD_END
    if s.is_full():
        return _msg("join_members_full", member_max=MAX_SHARED_MEMBERS)
    if len(share.joined_codes(user.id)) >= MAX_JOINED_SHARED:
        return _msg("shared_join_limit", joined_max=MAX_JOINED_SHARED)
    last_time = s.latest_request_time(user.id)
    if last_time is not None:
        gap = get_time_difference(last_time)
        if 0 <= gap < JOIN_REQUEST_COOLDOWN:
            remaining = JOIN_REQUEST_COOLDOWN - gap
            mins = max(1, -(-int(remaining) // 60))  # 剩余秒数向上取整为分钟
            return _msg("join_cooldown", mins=max(1, mins))
    s.add_request(user.id, get_time_now())
    name = await get_user_name(user.id, group_id=session.event.group_id, default=str(user.id))
    await send_to_user(session.bot, s.owner, _msg(
        "join_notify", name=name, user_id=str(user.id), code=s.code, title=s.title))
    return _msg("join_sent", code=code)


async def rev_requests(session, user, args=None):
    """处理共享会话的加入请求（群主专用，当前会话须为共享会话）。

    rev 查看请求列表；rev <用户序号> apr|rej|block 处理指定请求。
    """
    args = _clean_args(args)
    current = current_storage(user.id)
    if not isinstance(current, SharedSession):
        return _msg("shared_need_current")
    s = current
    if not s.is_owner(user.id):
        return _msg("shared_need_owner")
    if not args:
        requests = s.requests
        if not requests:
            return _msg("rev_list_empty")
        lines = [_msg("rev_list_header", count=len(requests), code=s.code)]
        for index, r in enumerate(requests, 1):
            name = await get_user_name(r.get("user_id"), default=str(r.get("user_id")))
            lines.append(_msg("rev_list_item", index=index, name=name,
                              user_id=str(r.get("user_id")), time=r.get("time", "未知时间")))
        return "\n".join(lines)
    if len(args) == 1:
        return _msg("rev_need_op", ops="/".join(SHARED_REQUEST_OPS))
    index_text, op = args[0], args[1].lower()
    if not index_text.isdigit():
        return _msg("rev_bad_index")
    if op not in SHARED_REQUEST_OPS:
        return _msg("rev_bad_op", ops="/".join(SHARED_REQUEST_OPS))
    index = int(index_text)
    if op == "apr":
        if s.is_full():
            return _msg("rev_members_full", member_max=MAX_SHARED_MEMBERS)
        request = s.approve_request(index)
        if request is None:
            return _msg("rev_bad_index")
        target_id = request.get("user_id")
        target_name = await get_user_name(target_id, default=str(target_id))
        if not share.add_joined(target_id, s.code):
            # 对方的共享会话列表在等待期间被占满：回滚本次通过，请求保留
            s.remove_member(target_id)
            s.add_request(target_id, request.get("time", get_time_now()))
            return _msg("rev_target_limit", name=target_name, user_id=str(target_id))
        await send_to_user(session.bot, target_id, _msg("join_apr", code=s.code, title=s.title))
        return _msg("rev_apr_done", name=target_name, user_id=str(target_id), code=s.code)
    request = s.pop_request(index)
    if request is None:
        return _msg("rev_bad_index")
    target_id = request.get("user_id")
    target_name = await get_user_name(target_id, default=str(target_id))
    if op == "rej":
        await send_to_user(session.bot, target_id, _msg("join_rej", code=s.code, title=s.title))
        return _msg("rev_rej_done", name=target_name, user_id=str(target_id))
    # block：只屏蔽不通知（需求确认）
    s.add_blocked(target_id)
    return _msg("rev_block_done", name=target_name, user_id=str(target_id))


async def session_info(session, user, args=None):
    """查看当前会话信息：info（普通=名称+条数；共享=群号码/标题/成员列表等）。"""
    s = current_storage(user.id)
    if not isinstance(s, SharedSession):
        name = "[默认会话]" if s.is_default else s.ai_session
        return _msg("info_normal", name=name, count=s.count)
    owner_name = await get_user_name(s.owner, default=str(s.owner))
    lines = [_msg("info_shared_header", code=s.code, title=s.title,
                  owner_name=owner_name, owner_id=str(s.owner),
                  member_count=len(s.members), member_max=MAX_SHARED_MEMBERS,
                  request_count=len(s.requests), count=s.count)]
    for index, m in enumerate(s.members, 1):
        user_id = m.get("user_id")
        mark = _msg("shared_mark_owner") if user_id == s.owner else ""
        name = await get_user_name(user_id, default=str(user_id))
        lines.append(_msg("info_member_item", index=index, name=name,
                          user_id=str(user_id), mark=mark))
    return "\n".join(lines)


async def kick_member(session, user, args=None):
    """把成员踢出当前共享会话：kick <成员序号>（序号见 info 的成员列表，群主专用）。"""
    args = _clean_args(args)
    current = current_storage(user.id)
    if not isinstance(current, SharedSession):
        return _msg("shared_need_current")
    s = current
    if not s.is_owner(user.id):
        return _msg("shared_need_owner")
    if not args:
        return _msg("kick_need_arg")
    if not args[0].isdigit():
        return _msg("kick_bad_index")
    index = int(args[0])
    members = s.members
    if not 1 <= index <= len(members):
        return _msg("kick_bad_index")
    target_id = members[index - 1].get("user_id")
    if target_id == s.owner:
        return _msg("kick_owner_unkickable")
    share.leave_shared(s, target_id)
    name = await get_user_name(target_id, default=str(target_id))
    await send_to_user(session.bot, target_id, _msg("kick_notify", code=s.code, title=s.title))
    return _msg("kick_done", name=name, user_id=str(target_id), code=s.code)


async def leave_shared_session(session, user, args=None):
    """退出当前共享会话：leave（群主不可退出）。"""
    current = current_storage(user.id)
    if not isinstance(current, SharedSession):
        return _msg("shared_need_current")
    s = current
    if s.is_owner(user.id):
        return _msg("leave_owner_denied")
    share.leave_shared(s, user.id)
    return _msg("leave_done", code=s.code, title=s.title)


async def session_history(session, user, args=None):
    """查看当前会话历史：history（伪造聊天记录转发，提问=调用者、回答=bot 自己）。

    群内用合并转发；私聊或转发失败时降级为纯文本；只展示最近 MAX_HISTORY_VIEW 条。
    """
    storage = current_storage(user.id)
    entries = [it for it in storage.load_history() if not history.is_summary(it)][-MAX_HISTORY_VIEW:]
    if not entries:
        return _msg("history_empty")
    event = session.event
    if event.group_id:
        try:
            nodes = []
            for it in entries:
                asker_id = it.get("user_id", user.id)  # 提问者身份（旧记录无 user_id 时回落调用者）
                ask_text = f"[{it.get('time', '未知时间')}]\n{it.get('ask', '')}"
                nodes.append(change_group_message_content(
                    await _sender_dict(session, asker_id), ask_text, user_id=asker_id))
                nodes.append(change_group_message_content(
                    await _sender_dict(session, session.self_id), it.get("ans", ""),
                    user_id=session.self_id))
            await send_forward_msg(session.bot, event, nodes)
            return CMD_END
        except Exception as e:
            logger.warning(f"共享会话历史转发发送失败，降级为文本: {e}")
    return "\n\n".join(
        _msg("history_private_item", time=it.get("time", "未知时间"),
             ask=it.get("ask", ""), ans=it.get("ans", ""))
        for it in entries
    )
