# some are made by Deepseek-v4-flash-vison-exp at Deepseek Harness
from character import get_message
from xme.xmetools.msgtools import CMD_END, aget_arg

from . import history
from .constants import __plugin_name__, MAX_SESSIONS
from .session import AISession

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
    """创建并切换到新会话：new [会话名]（不填名则自动命名：会话1、会话2...）"""
    ai_session = (args[0].strip() if args and args[0] else "")
    lock = bool(ai_session)  # 用户指定名字 → AI 不可修改
    if not ai_session:
        ai_session = AISession.next_auto_name(user.id)
    ai_session = ai_session.replace(" ", "_")
    if not AISession.is_valid_name(ai_session):
        return get_message("plugins", __plugin_name__, "session_name_invalid")
    if AISession(user.id, ai_session).exists():
        return get_message("plugins", __plugin_name__, "session_exists", ai_session=ai_session)
    if len(AISession.all(user.id)) >= MAX_SESSIONS:
        return get_message("plugins", __plugin_name__, "session_limit", max_sessions=MAX_SESSIONS)
    try:
        s = AISession.create(user.id, ai_session, lock=lock)
    except ValueError:
        return get_message("plugins", __plugin_name__, "session_limit", max_sessions=MAX_SESSIONS)
    s.set_current()
    return get_message("plugins", __plugin_name__, "session_new", ai_session=ai_session)


def list_sessions(session, user, args=None):
    """显示所有 AI 会话列表（含序号、记录条数、默认/当前/AI 不可修改标记）。"""
    sessions = AISession.all(user.id)
    current = AISession.current(user.id)
    lines = [get_message("plugins", __plugin_name__, "session_list_header")]
    for index, s in enumerate(sessions, 1):
        marks = ""
        if s.is_default:
            marks += get_message("plugins", __plugin_name__, "session_mark_default")
        if s.is_locked():
            marks += get_message("plugins", __plugin_name__, "session_mark_locked")
        if s.ai_session == current.ai_session:
            marks += get_message("plugins", __plugin_name__, "session_mark_current")
        lines.append(get_message(
            "plugins", __plugin_name__, "session_list_item",
            index=index, name=s.ai_session, marks=marks, count=s.count,
        ))
    lines.append(get_message(
        "plugins", __plugin_name__, "session_list_footer",
        count=len(sessions), max_sessions=MAX_SESSIONS,
    ))
    return "\n".join(lines)


def name_session(session, user, args=None):
    """命名/重命名会话：name <新名字>（当前会话）或 name <会话序号> <新名字>。

    用户命名后该会话标记为 AI 不可修改；命名默认会话（序号 1）等同把它提升为新会话。
    """
    args = [a.strip() for a in (args or []) if a.strip()]
    if not args or (len(args) == 1 and args[0].isdigit()):
        return get_message("plugins", __plugin_name__, "session_name_need_new")
    if len(args) == 1:
        target = AISession.current(user.id)
        new_name = args[0]
    else:
        target, err = _session_by_index(user.id, args[0])
        if err:
            return err
        new_name = args[1]
    new_name = new_name.replace(" ", "_")
    if not AISession.is_valid_name(new_name):
        return get_message("plugins", __plugin_name__, "session_name_invalid")
    if new_name == target.ai_session:
        return get_message("plugins", __plugin_name__, "session_same_name", ai_session=new_name)
    locked_hint = get_message("plugins", __plugin_name__, "session_mark_locked")
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


def clear_history(session, user, args=None):
    """无参清空当前会话；带 <序号> 删除指定会话（默认会话不可删除）。"""
    current = AISession.current(user.id)
    num = _parse_index(args)
    if num is not None:
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
    # 无参：清空当前会话（历史文件 + 转存文件夹）
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


def switch_session(session, user, args=None):
    """切换到指定序号的会话：swi <序号>"""
    num = _parse_index(args)
    if num is None:
        return get_message("plugins", __plugin_name__, "session_switch_need_arg")
    target, err = _session_by_index(user.id, num)
    if err:
        return err
    target.set_current()
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
        rules=lambda r: r.strip().lower() in ("y", "yes", "是", "确认"),
        can_use_cmd=True,
        max_times=3,
    )
    if reply == CMD_END or reply is None:
        return get_message("plugins", __plugin_name__, "session_clear_all_canceled")
    if reply.strip().lower() not in ("y", "yes", "是", "确认"):
        return get_message("plugins", __plugin_name__, "session_clear_all_canceled")
    cleared = history.clear_all_history(user.id)
    return get_message("plugins", __plugin_name__, "session_clear_all_done", count=cleared)
