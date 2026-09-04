# some are made by Deepseek-v4-flash-vison-exp at Deepseek Harness
import re

from character import get_message
from xme.xmetools.msgtools import CMD_END, aget_arg, send_to_user

from . import history, share
from .constants import (
    MAX_JOINED_SHARED,
    MAX_SESSIONS,
    MAX_SHARED_MEMBERS,
    SESSION_NAME_MAX_LEN,
    __plugin_name__,
)
from .session import AISession
from .share import SharedSession
from xme.xmetools.videotools import extract_video_links, extract_and_download

# 注意：命令函数统一签名 (session, user, args=None)；
# "ai_session" 一律指 AI 会话名，"session" 一律指 bot 的 CommandSession；
# 会话对象统一用 AISession（见 session.py）。


def _parse_index(args) -> str | None:
    """解析命令行里的会话序号参数；没有序号返回 None。"""
    if not args or not args[0].strip():
        return None
    return args[0].strip()


def _session_by_index(user_id, num: str) -> tuple[AISession | None, str | None]:
    """按会话序号取会话对象，返回 (会话, 错误提示)；出错时会话为 None。"""
    if not num.isdigit():
        return None, get_message("plugins", __plugin_name__, "session_index_not_int", index=num)
    index = int(num)
    sessions = AISession.all(user_id)
    if index < 1 or index > len(sessions):
        return None, get_message("plugins", __plugin_name__, "session_index_not_found", index=index)
    return sessions[index - 1], None


def new_session(session, user, args=None):
    """创建并切换到新会话：new （自动命名：会话1、会话2...）"""
    # ai_session = (args[0].strip() if args and args[0] else "")
    # lock = bool(ai_session)  # 用户指定名字 → AI 不可修改

    # if not ai_session:
    ai_session = AISession.next_auto_name(user.id)
    # ai_session = ai_session.replace(" ", "_")

    if not AISession.is_valid_name(ai_session):
        raise ValueError(f"会话名无效：{ai_session}")
        # return get_message("plugins", __plugin_name__, "session_name_invalid")
    if AISession(user.id, ai_session).exists():
        return get_message("plugins", __plugin_name__, "session_exists", ai_session=ai_session)
    if len(AISession.all(user.id)) >= MAX_SESSIONS:
        return get_message("plugins", __plugin_name__, "session_limit", max_sessions=MAX_SESSIONS)
    try:
        s = AISession.create(user.id, ai_session, lock=False)
    except ValueError:
        return get_message("plugins", __plugin_name__, "session_limit", max_sessions=MAX_SESSIONS)
    s.set_current()
    return get_message("plugins", __plugin_name__, "session_new", ai_session=ai_session)


def list_sessions(session, user, args=None):
    """显示所有 AI 会话列表（含序号、记录条数、默认/当前/AI 不可修改标记）。"""
    sessions = AISession.all(user.id)
    current = AISession.current(user.id)
    lines = [get_message("plugins", __plugin_name__, "session_list_header", count=len(sessions), max_sessions=MAX_SESSIONS,)]
    for index, s in enumerate(sessions, 1):
        marks = ""
        # if s.is_default:
            # marks += get_message("plugins", __plugin_name__, "session_mark_default")
        # if s.is_locked():
            # marks += get_message("plugins", __plugin_name__, "session_mark_locked")
        if s.ai_session == current.ai_session:
            marks += get_message("plugins", __plugin_name__, "session_mark_current")
        name = s.ai_session if s.ai_session != "default" else "[默认会话]"
        lines.append(get_message(
            "plugins", __plugin_name__, "session_list_item",
            index=index, name=name, marks=marks, count=s.count,
        ))
    # lines.append(get_message(
        # "plugins", __plugin_name__, "session_list_footer",
    # ))
    # 共享会话列表与普通会话分开（a 序号，a1=最早加入的）
    codes = share.joined_codes(user.id)
    if codes:
        current_shared = share.current_shared(user.id)
        lines.append(get_message("plugins", __plugin_name__, "shared_list_header",
                                 count=len(codes), joined_max=MAX_JOINED_SHARED))
        for index, code in enumerate(codes, 1):
            s = SharedSession(code)
            if not s.exists():
                marks = get_message("plugins", __plugin_name__, "shared_mark_dead")
            else:
                marks = ""
                if current_shared is not None and s.code == current_shared.code:
                    marks += get_message("plugins", __plugin_name__, "session_mark_current")
                if s.is_owner(user.id):
                    marks += get_message("plugins", __plugin_name__, "shared_mark_owner")
            lines.append(get_message(
                "plugins", __plugin_name__, "shared_list_item",
                index=f"a{index}", code=code, title=s.title if s.exists() else "-",
                marks=marks, member_count=len(s.members) if s.exists() else 0,
                member_max=MAX_SHARED_MEMBERS,
            ))
    lines.append(get_message("plugins", __plugin_name__, "list_footer"))
    return "\n".join(lines)


def _rename_shared(user, shared: SharedSession, new_name: str) -> str:
    """重命名共享会话（仅群主可改）：只更新 meta 的 title 展示字段。

    与普通会话不同：共享会话目录以群号码命名，改名不涉及文件移动。
    """
    if not shared.is_owner(user.id):
        return get_message("plugins", __plugin_name__, "shared_rename_need_owner")
    if not shared.rename(new_name):
        return get_message("plugins", __plugin_name__, "session_name_invalid")
    return get_message("plugins", __plugin_name__, "shared_renamed",
                       code=shared.code, new_name=shared.title)


def name_session(session, user, args=None):
    """命名/重命名会话：name <新名字>（当前会话）或 name <会话序号> <新名字>。

    用户命名后该会话标记为 AI 不可修改；命名默认会话（序号 1）等同把它提升为新会话。
    共享会话：当前处于共享模式时 name <新名字> 改共享标题，或 name <a 序号> <新名字>
    （如 name a2 名字）；仅群主可改，只改展示标题不改目录名。
    """
    args = [a.strip() for a in (args or []) if a.strip()]

    if not args or (len(args) == 1 and (args[0].isdigit() or re.fullmatch(r"a\d+", args[0]))):
        return get_message("plugins", __plugin_name__, "session_name_need_new")

    if len(args) == 1:
        shared = share.current_shared(user.id)
        if shared is not None:
            return _rename_shared(user, shared, args[0])
        target = AISession.current(user.id)
        new_name = args[0]
    elif re.fullmatch(r"a\d+", args[0]):
        shared = share.shared_by_a_index(user.id, int(args[0][1:]))
        if shared is None:
            return get_message("plugins", __plugin_name__, "shared_index_not_found", index=args[0])
        return _rename_shared(user, shared, args[1])
    else:
        target, err = _session_by_index(user.id, args[0])
        if err:
            return err
        new_name = args[1]

    new_name = new_name.replace(" ", "_")
    if len(new_name) > SESSION_NAME_MAX_LEN:
        return get_message("plugins", __plugin_name__, "session_name_too_long", max_length=SESSION_NAME_MAX_LEN)
    if not AISession.is_valid_name(new_name):
        return get_message("plugins", __plugin_name__, "session_name_invalid")
    if new_name == target.ai_session:
        return get_message("plugins", __plugin_name__, "session_same_name", ai_session=new_name)
    locked_hint = get_message("plugins", __plugin_name__, "session_mark_locked")

    ######################

    if target.is_default:
        promoted = AISession.promote_default(user.id, new_name, lock=True)
        if promoted is None:
            return get_message("plugins", __plugin_name__, "session_exists", ai_session=new_name)
        return get_message("plugins", __plugin_name__, "session_promoted", new_name=new_name, locked_hint=locked_hint)
    old_name = target.ai_session

    if not target.rename(new_name, lock=True):
        if AISession(user.id, new_name).exists():
            return get_message("plugins", __plugin_name__, "session_exists", ai_session=new_name)
        return get_message("plugins", __plugin_name__, "session_name_invalid")
    return get_message("plugins", __plugin_name__, "session_renamed", old_name=old_name, new_name=new_name, locked_hint=locked_hint)


async def clear_history(session, user, args=None):
    """清空/删除会话：无参清空当前会话；<数字序号> 删除普通会话；
    <a序号> 删除共享会话（仅群主，其他成员与申请者收到私聊通知）。

    当前处于共享会话时，无参 clear 作用于共享会话（仅群主可清），
    不再误清各自的普通会话。
    """
    num = _parse_index(args)
    # ---- a 序号：删除整个共享会话（仅群主）----
    if num is not None and re.fullmatch(r"a\d+", num):
        shared = share.shared_by_a_index(user.id, int(num[1:]))
        if shared is None:
            return get_message("plugins", __plugin_name__, "shared_index_not_found", index=num)
        if not shared.is_owner(user.id):
            return get_message("plugins", __plugin_name__, "shared_delete_need_owner")
        # 名单要在删除前取出（meta 随目录一起消失，requests 一并移除）
        code, title = shared.code, shared.title
        targets = [uid for uid in
                   [*shared.member_ids, *[r.get("user_id") for r in shared.requests]]
                   if uid is not None]
        file_count = shared.delete()
        share.detach_users(code, targets)  # 清各用户的 .joined 与共享指针（含自己）
        notified = 0
        for uid in targets:
            if uid == user.id:
                continue
            await send_to_user(session.bot, uid, get_message(
                "plugins", __plugin_name__, "shared_deleted_notify", code=code, title=title))
            notified += 1
        return get_message("plugins", __plugin_name__, "shared_deleted",
                           code=code, title=title, file_count=file_count, notify_count=notified)
    # ---- 无参：共享模式下清空共享会话（仅群主），否则清空普通当前会话 ----
    if num is None:
        shared = share.current_shared(user.id)
        if shared is not None:
            if not shared.is_owner(user.id):
                return get_message("plugins", __plugin_name__, "shared_clear_need_owner")
            cleared_hist, cleared_files = shared.clear()
            if cleared_hist == 0 and cleared_files == 0:
                return get_message("plugins", __plugin_name__, "session_clear_no_content")
            return get_message(
                "plugins", __plugin_name__, "session_cleared",
                hist_count=cleared_hist, file_count=cleared_files,
            )
        current = AISession.current(user.id)
        cleared_hist, cleared_files = current.clear()
        if cleared_hist == 0 and cleared_files == 0:
            return get_message("plugins", __plugin_name__, "session_clear_no_content")
        # 非默认会话被清空后重新建立一个空会话，避免当前指针指向不存在的会话（命名锁保持）
        if not current.is_default and not current.exists():
            AISession.create(user.id, current.ai_session)
        return get_message(
            "plugins", __plugin_name__, "session_cleared",
            hist_count=cleared_hist, file_count=cleared_files,
        )
    # ---- 数字序号：删除指定普通会话（默认会话不可删除）----
    target, err = _session_by_index(user.id, num)
    if err:
        return err
    if target.is_default:
        # 默认会话不可删除：clear <默认序号> = 清空默认会话内容（当前在默认会话时等价于无参 clear）
        cleared_hist, cleared_files = target.clear()
        if cleared_hist == 0 and cleared_files == 0:
            return get_message("plugins", __plugin_name__, "session_clear_no_content")
        return get_message(
            "plugins", __plugin_name__, "session_cleared",
            hist_count=cleared_hist, file_count=cleared_files,
        )
    cleared = target.delete()
    if cleared == 0:
        return get_message("plugins", __plugin_name__, "session_delete_failed", ai_session=target.ai_session)
    return get_message("plugins", __plugin_name__, "session_deleted", ai_session=target.ai_session, count=cleared)


def switch_session(session, user, args=None):
    """切换到指定序号的会话：swi <序号>（数字=普通会话，a 开头=共享会话，如 a1）。"""
    num = _parse_index(args)
    if num is None:
        return get_message("plugins", __plugin_name__, "session_switch_need_arg")
    if re.fullmatch(r"a\d+", num):
        shared = share.shared_by_a_index(user.id, int(num[1:]))
        if shared is None:
            return get_message("plugins", __plugin_name__, "shared_index_not_found", index=num)
        share.set_current_shared(user.id, shared.code)
        return get_message("plugins", __plugin_name__, "shared_switched",
                           code=shared.code, title=shared.title)
    target, err = _session_by_index(user.id, num)
    if err:
        return err
    target.set_current()
    share.set_current_shared(user.id, None)  # 切回普通会话时退出共享模式
    return get_message("plugins", __plugin_name__, "session_switched", ai_session=target.ai_session)


async def clear_all_sessions(session, user, args=None):
    """删除所有会话（删除前发送警告，回复 y 确认才会执行）。"""
    sessions = AISession.all(user.id)
    total = sum(s.count for s in sessions)
    reply = await aget_arg(
        session,
        prompt=get_message(
            "plugins", __plugin_name__, "session_clear_all_confirm",
            count=len(sessions), total=total,
        ),
        rules=lambda r: r.strip().lower() in ("y", "Y"),
        can_use_cmd=True,
        max_times=1,
    )
    if reply is CMD_END:
        return CMD_END
    if reply is None:
        return get_message("plugins", __plugin_name__, "session_clear_all_canceled")
    if reply.strip().lower() not in ("y", "Y"):
        return get_message("plugins", __plugin_name__, "session_clear_all_canceled")
    # 先把用户从所有共享会话移除（读 .joined 后再清空用户目录，共享侧名单同步清理）
    share.leave_all(user.id)
    cleared = history.clear_all_history(user.id)
    return get_message("plugins", __plugin_name__, "session_clear_all_done", count=cleared)
