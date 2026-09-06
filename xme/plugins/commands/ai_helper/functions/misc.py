# some are made by Deepseek-v4-flash-vison-exp at Deepseek Harness
"""会话交互与杂项工具：追问用户、骰子、会话改名、中途汇报等。"""
import random
import time
from pathlib import Path

from nonebot.log import logger
from xme.xmetools.msgtools import aget_arg_with_timeout, send_session_msg, is_text_can_send
from character import get_message
from ..session import AISession

async def ask_user(prompt: str, session, timeout: int = 120):
    from ..agent import AISTOP
    from .. import __plugin_name__
    send_time = time.time()
    if timeout > 400:
        timeout = 400
    interval = 0
    islegal = False
    while interval < 3 and not islegal:
        reply = await aget_arg_with_timeout(session, timeout_secs=timeout, prompt=get_message("plugins", __plugin_name__, "ai_ask", prompt=prompt, timeout=timeout))
        reply_time = time.time()
        interval = reply_time - send_time
        if interval < 3:
            await send_session_msg(session, get_message("plugins", __plugin_name__, "reply_too_fast"))
            continue
        islegal = await is_text_can_send(session, reply, 4)
        if not islegal:
            await send_session_msg(session, get_message("plugins", __plugin_name__, "reply_is_illegal"))
            continue
    if not reply:
        return "[用户未在时限内回复任何内容]"
    if reply == "aistop":
        return AISTOP
    await send_session_msg(session, get_message("plugins", __plugin_name__, "user_content_reply"))
    return f"[用户回复] {reply}"

def get_user_input_urls(agent):
    return agent.user_input_urls

def dice(faces: int, count: int = 1):
    if count > 100:
        return "[骰子数量不能大于 100 个]"
    if faces > 1000000:
        return "[骰子面数不能大于 1000000]"
    rs = [random.randint(1, faces) for _ in range(count)]
    rs_str = ', '.join(map(str, rs))
    return f"{count}d{faces} → (总计{sum(rs)}) {rs_str}"

def name_session(name: str, agent=None):
    """为当前 AI 会话命名/重命名（会话名会显示在用户的会话列表中）。

    适合在对话主题明确时调用，例如讨论写小说的对话可命名为 "小说写作"。
    当前是共享会话时只改显示标题（群号码/目录不变，普通/群主同名规则见 share.py）；
    当前是默认会话时会把默认会话的内容整体提升为命名会话，默认会话复位为空；
    当前已有名字时直接重命名（历史与转存文件会一并移动）。
    用户手动命名过的会话不可修改（会返回错误）。
    """
    if agent is None:
        return "[错误：无法获取当前会话上下文]"
    name = (name or "").strip()
    # 共享会话：目录以群号码命名，改名只更新 meta 的 title 展示字段
    shared = getattr(agent, "shared", None)
    if shared is not None:
        if shared.rename(name):
            return f"[已将共享会话 {shared.code} 改名为 \"{shared.title}\"（只改显示标题，不影响群号码）]"
        return "[重命名失败：标题需为 1-20 字符且不含特殊符号，请换一个名字]"
    old_name = agent.ai_session
    name = name.replace(" ", "_")
    if not AISession.is_valid_name(name):
        return "[错误：会话名不合法。请控制在 20 字符以内，使用中英文/数字/_-（不以点开头、不含特殊符号），且不能叫 default 或以 history_ 开头]"
    session_obj = AISession(agent.user_id, old_name)
    if session_obj.is_locked():
        return "[错误：当前会话的名字由用户手动指定，AI 不可修改。请不要再重命名该会话]"
    # 旧目录要在 rename 之前捕获（rename 会就地改变 session_obj.ai_session）
    old_dir = session_obj.dir_path
    if session_obj.is_default:
        new_session = AISession.promote_default(agent.user_id, name)
    else:
        new_session = session_obj if session_obj.rename(name) else None
    if new_session is None:
        return f"[重命名失败：目标名 \"{name}\" 可能已被使用，请换一个名字]"
    # 会话目录可能整体移动，ref_map 里指向旧目录的路径同步更新
    new_dir = new_session.dir_path
    for ref, path in list(agent.ref_map.items()):
        p = Path(path)
        if old_dir in p.parents:
            agent.ref_map[ref] = str(new_dir / p.relative_to(old_dir))
    agent.ai_session = new_session.ai_session
    return f"[已为当前会话命名 \"{new_session.ai_session}\"（原 \"{old_name}\"）]"

async def inprocess_report(message: str, agent):
    from ..constants import __plugin_name__
    # 最小间隔s
    MIN_INTERVAL = 30
    try:
        last_response_time = agent.last_response
        curr_response_time = time.time()
        interval = curr_response_time - last_response_time
        if interval < 30:
            return f"[调用回复失败：最小间隔为 {MIN_INTERVAL}s，当前距离上次调用间隔为 {interval}s。]"
        # 中途汇报内容给用户
        await send_session_msg(agent.session, get_message("plugins", __plugin_name__, "inprocess_report", msg=message))
        agent.last_response = time.time()
        return f"成功向用户发送消息"
    except Exception as ex:
        return f"[发送消息失败：{ex}]"

