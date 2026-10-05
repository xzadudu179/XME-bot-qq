# some are made by Deepseek-v4-flash-vison-exp at Deepseek Harness
"""会话交互与杂项工具：追问用户、骰子、会话改名、中途汇报等。"""
import random
import re
import time
from pathlib import Path

from nonebot.log import logger
from xme.xmetools.msgtools import aget_arg_with_timeout, image_msg, send_session_msg, is_text_can_send
from xme.xmetools.texttools import image_placeholder
from character import get_message
from ..session import AISession
from ._common import ImageToolResult

async def _judge_reply_relevance(question: str, reply: str, image_count: int = 0) -> int | None:
    """用 oneshot.ask（免费模型候选链）判定用户回复是否在回答 AI 的问题。

    返回置信度 0-100；判定失败（免费模型全不可用/输出无法解析）返回 None：
    跳过判定直接采纳回复，判定器故障不应该卡住正常的提问流程。
    image_count 为回复附带的图片数：判定器看不到图片内容，而 ai_ask 明确允许
    携带图片回答——附带图片默认视为在回答（system 约束置信度下限），避免纯图
    回复被判 0 分触发无意义的确认流程。
    """
    from ..llm.oneshot import ask
    image_note = (f"\n（用户回复中还附带了 {image_count} 张图片）" if image_count > 0 else "")
    result = await ask(
        f"[AI 的问题]\n{question}\n\n[用户的回复]\n{reply}{image_note}\n\n"
        "请判定这条回复是否在回答该问题。",
        system=("你是判定器。判断用户的回复是否是在回答 AI 提出的问题，只输出 JSON："
                '{"confidence": 整数}。confidence 为 0-100 的置信度：'
                "明确回应了问题内容给 80-100；部分相关或模糊回答给 40-79；"
                "答非所问、闲聊、单纯语气词/表情描述给 0-39。"
                "回复中的 [图片...] 占位代表用户发了图片，判定器看不到图片内容——"
                "附带图片默认视为在回答（置信度不低于 80，除非问题与图片明显无关）。"),
        json_output=True, timeout=15, label="ask_user 相关性判定")
    if result is None:
        return None
    data = result.data if isinstance(result.data, dict) else None
    value = data.get("confidence") if data else None
    if value is None:
        # JSON 解析失败：从原文里兜底提取整数
        match = re.search(r"\d{1,3}", result.text or "")
        value = match.group() if match else None
    if value is None:
        return None
    return min(100, max(0, int(value)))


async def ask_user(prompt: str, session, timeout: int = 120, agent=None):
    from ..agent import AISTOP
    from .. import __plugin_name__, aistop, safe_get_images
    from ..constants import ASK_RELEVANCE_CONFIDENCE
    send_time = time.time()
    if timeout > 400:
        timeout = 400
    interval = 0
    islegal = False
    reply = None
    attempts = 0
    # 提问期间标记"AI 在等用户回复"：消息预处理器据此放行，让回复能进 arg 通道
    aistop.set_awaiting_reply(session.event.group_id, session.event.user_id, True)
    try:
        # 注意：条件只应看"是否拿到合法回复"；原先写成 `interval < 3 and not islegal`，
        # 而 interval 在正常回复时必然 ≥3 → 短路导致"违规重问"逻辑形同虚设
        img = await image_msg("./static/img/attention.png")
        while not islegal and attempts < 5:
            attempts += 1
            # 问题（含提示图）只在第一次发送；重问等待不再重复，避免刷屏
            ask_prompt = (img + get_message("plugins", __plugin_name__, "ai_ask",
                                            prompt=prompt, timeout=timeout)) if attempts == 1 else None
            reply = await aget_arg_with_timeout(session, timeout_secs=timeout, prompt=ask_prompt)
            if reply is None:
                break   # 超时：不再反复提问
            # 提取回复中的图片（reply 是含 CQ 码的字符串），文本部分换成占位符：
            # 图片经 ImageToolResult 直注入视觉输入，风控只审剥图后的文本
            image_objects, cq_matches = await safe_get_images(session.bot, reply)
            reply_text = reply
            for image_cq in cq_matches:
                reply_text = reply_text.replace(image_cq, image_placeholder(image_cq))
            reply_time = time.time()
            interval = reply_time - send_time
            if interval < 3 and not image_objects:
                # 秒回防护只针对纯文本（发图节奏快是正常行为）
                await send_session_msg(session, get_message("plugins", __plugin_name__, "reply_too_fast"))
                continue
            # 风控只审真实文本：剥掉全部 CQ 码（图片/at 等段不该按字面送审）；纯图回复跳过
            audited_text = re.sub(r"\[CQ:[^\]]*\]", "", reply).strip()
            if audited_text:
                # is_text_can_send 返回 dict，必须取 result 判断（原先当 bool 用导致风控与提示失效）
                islegal = bool((await is_text_can_send(session, audited_text, 4)).get("result", False))
            else:
                islegal = True
            if not islegal:
                await send_session_msg(session, get_message("plugins", __plugin_name__, "reply_is_illegal"))
                continue
            # 相关性判定 + 低置信确认子循环：回复不像是在回答问题时要求用户确认。
            # 1=确认刚才那条是回答；2=拒绝并结束提问；其他消息作为新回复重新判定
            while True:
                confidence = await _judge_reply_relevance(
                    prompt, reply_text or reply, image_count=len(image_objects))
                logger.info(f"回复符合置信度 {confidence}%")
                if confidence is None or confidence >= ASK_RELEVANCE_CONFIDENCE:
                    break
                await send_session_msg(session, get_message(
                    "plugins", __plugin_name__, "ask_low_confidence"))
                confirm = await aget_arg_with_timeout(session, timeout_secs=timeout)
                if confirm is None:
                    reply = None   # 确认阶段超时：与主流程超时同样处理
                    break
                choice = confirm.strip().translate(str.maketrans("１２", "12"))
                if choice == "1":
                    break   # 用户确认原回复有效
                if choice == "2":
                    return "[用户表示刚才的消息不是要回答这个问题，已取消本次提问]"
                # 其他消息：当作新的回复，重走图片提取与相关性判定
                image_objects, cq_matches = await safe_get_images(session.bot, confirm)
                reply = confirm
                reply_text = confirm
                for image_cq in cq_matches:
                    reply_text = reply_text.replace(image_cq, image_placeholder(image_cq))
    finally:
        aistop.set_awaiting_reply(session.event.group_id, session.event.user_id, False)
    if not reply:
        return "[用户未在时限内回复任何内容]"
    if reply == "aistop":
        return AISTOP
    await send_session_msg(session, get_message("plugins", __plugin_name__, "user_content_reply"))
    if image_objects:
        parts = [{"type": "image_url", "image_url": {"url": x["file"]}} for x in image_objects]
        return ImageToolResult(f"[用户回复] {reply_text}", parts)
    return f"[用户回复] {reply_text}"

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

