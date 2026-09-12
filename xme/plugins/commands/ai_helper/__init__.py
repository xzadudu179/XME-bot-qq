import argparse
import asyncio
import inspect
import re
import httpx

import config
from nonebot import CommandSession

from traceback import format_exc
from xme.plugins.commands.ai_helper import history
from xme.xmetools.plugintools import on_command
from xme.xmetools.doctools import CommandDoc, shell_like_usage
from xme.xmetools.bottools import XmeArgumentParser
from xme.xmetools.msgtools import CMD_END, aget_arg, is_text_can_send, send_session_msg, send_to_user
from xme.xmetools.texttools import get_images_from_message, hash_text
from xme.xmetools.jsontools import read_from_path
from xme.xmetools.timetools import get_time_now, secs_to_ymdh
from character import get_message, get_character_item, character_format
from keys import GLM_API_KEY
from xme.plugins.commands.xme_user.classes import user as u
from zai import ZhipuAiClient

from .agent import AIHelper, ai_logger, load_snapshot, clear_snapshot, build_user_content
from .session import (AISession, allows_auto_model, current_storage, enable_normal_insert,
                      set_user_model, user_model, user_model_setting)
from . import constants, share, aistop, credits
from .credits import ai_credits_left
from .constants import LLM_MODELS, __plugin_name__, MAX_TOOL_CALL_TIMES, MAX_HISTORY_COUNT
from .commands import adjust_credits, clear_history, clear_all_sessions, list_sessions, name_session, new_session, switch_session
from .share_commands import (
    join_session,
    kick_member,
    leave_shared_session,
    rev_requests,
    session_history,
    session_info,
    share_session,
    toggle_insert,
)


# 用户: stats
curr_sessions = {}

# 用户可用指令（通过 /ai -c <指令> 使用）
cmds = {
    "new": {
        "content": new_session,
        "args": "",
        "desc": "创建并切换到新会话",
    },
    "list": {
        "content": list_sessions,
        "args": "",
        "desc": "查看所有 AI 会话列表（含序号）",
    },
    "name": {
        "content": name_session,
        "args": "<会话序号> (名称)",
        "desc": "重命名会话，不填写会话序号则命名当前会话",
    },
    "clear": {
        "content": clear_history,
        "args": "<会话序号>",
        "desc": "清空当前会话；指定序号删除指定会话（默认会话不可删除）",
    },
    "clear-all": {
        "content": clear_all_sessions,
        "args": "",
        "desc": "删除所有会话（需回复 y 确认）",
    },
    "swi": {
        "content": switch_session,
        "args": "(会话序号)",
        "desc": "切换到指定序号的会话（a 开头为共享会话，如 a1）",
    },
    "share": {
        "content": share_session,
        "args": "<普通会话序号>",
        "desc": "创建共享会话（带序号则复制该会话内容，否则新建空白会话），创建后自动切换",
    },
    "join": {
        "content": join_session,
        "args": "(共享会话码)",
        "desc": "请求加入共享会话，等待群主审批",
    },
    "rev": {
        "content": rev_requests,
        "args": "<用户序号> <apr/rej/block>",
        "desc": "查看/处理共享会话的加入请求（群主专用，不填任何参数为查看请求列表）",
    },
    "info": {
        "content": session_info,
        "args": "",
        "desc": "查看当前会话信息（共享会话含带序号的成员列表）",
    },
    "kick": {
        "content": kick_member,
        "args": "(成员序号)",
        "desc": "把成员踢出当前共享会话（群主专用）",
    },
    "leave": {
        "content": leave_shared_session,
        "args": "",
        "desc": "退出当前共享会话（群主不可退出）",
    },
    "ins": {
        "content": toggle_insert,
        "args": "",
        "desc": "开关共享会话的插入模式（群主专用，开启后成员可在对话进行中插入消息）",
    },
    "credits": {
        "content": adjust_credits,
        "args": "(qq) (±数值)",
        "desc": "查看/调整用户自存 credits（超管专用；无 qq 查看自己，无数值仅查看）",
    },
    "history": {
        "content": session_history,
        "args": "",
        "desc": "查看当前会话的聊天记录（合并转发，仅最近 30 条）",
    },
}


def get_command_list():
    cmd_list_str = "当前指令参数列表：\n"
    for k, v in cmds.items():
        cmd_list_str += f"\t{k} {v['args']}: {v['desc']}\n"
    cmd_list_str += "指令示例：\n\"/ai -c join AI0000\" 代表申请加入群号为 AI0000 的共享会话\n\"/ai -c clear\" 代表清除当前会话历史记录"
    return cmd_list_str

def auto_model_list() -> str:
    """auto（按话题自动选择）的类别 → 模型映射文案，供切换回执展示。"""
    return "、".join(f"{cat}→{alias}" for cat, alias in
                     (constants.LLM_TOPIC_ROUTING or {}).items())


def get_model_list():
    """模型列表文案（别名 / 简介 / 计费倍率），供帮助与报错提示展示。"""
    return "auto:\t(默认)自动选择合适的模型（flash）\n" + "\n".join(
        f"{n}:\t{m.get('description', '')}（计费 x{m.get('credit_multiplier', 1)} 缓存 x{m.get('cache_credit_ratio', 0.25)}）"
        for n, m in LLM_MODELS.items()
    )

async def parse_control(session: CommandSession, text: str, user: u.User) -> str:
    cmd_name, args = text.split(" ")[0], text.split(" ")[1:]
    async def parse_func(*_, **__):
        return f"没有这个指令 \"{cmd_name}\" 哦"
    cmd = cmds.get(cmd_name, None)
    if cmd is not None:
        parse_func = cmd["content"]
    # 命令函数统一签名 (session, user, args=None)；可能是异步的（如 clear-all 需要 aget_arg 等待用户确认）
    result = parse_func(session=session, user=user, args=args)
    if inspect.iscoroutine(result):
        result = await result
    if result is CMD_END:
        return CMD_END
    return result


arg_usage = shell_like_usage("OPTION", [
    {
        "name": "help",
        "abbr": "h",
        "desc": "查看帮助"
    },
    {
        "name": "continue",
        "abbr": "C",
        "desc": "恢复上次异常中断的会话，保留之前的全部用户输入/思考/工具结果并继续未完成的对话"
    },
    {
        "name": "raw",
        "abbr": "r",
        "desc": "会把之后的文本全都解析为单纯的文本，如果你在发东西给 ai 的时候出现了 \"指令执行的参数有问题哦\" 的问题，可以试试在发送的内容前加上 -r 哦"
    },
    {
        "name": "model",
        "abbr": "m",
        "desc": (f"指定模型：只发 \"/ai -m 模型\" 会把该模型设为你之后默认使用的模型；"
                 f"\"/ai -m 模型 对话内容\" 则只在这次对话临时用它。"
                 f"也可以填 auto（按话题自动选择模型）。模型列表：\n{get_model_list()}")
    },
    {
        "name": "ctrl",
        "abbr": "c",
        "desc": f"只需要在任意地方输入 -c 即可将原本输入给 AI 的内容变为指令\n{get_command_list()}"
    }
])

alias = constants.COMMAND_ALIAS
__plugin_usage__ = CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    usage=f'(对话内容) [OPTION]\n{arg_usage}',
    permissions=[],
    alias=alias
)

def extract_text(raw: str) -> str:
    # -r 后面的全部内容直接作为原始文本
    match = re.search(r"(?:^|\s)-r(?:\s|$)", raw)
    if match:
        return raw[match.end():].strip()
    # 没有 -r，剥离开头的普通选项（容忍前导空白：命令参数常带一个空格）
    raw = raw.lstrip()
    raw = re.sub(r"^(?:-c|--ctrl)\s*", "", raw)
    raw = re.sub(r"^(?:-m|--model)\s+\S+\s*", "", raw)
    return raw.strip()

@on_command(__plugin_name__, aliases=alias, only_to_me=False, shell_like=True, permission=lambda _: True)
@u.using_user(save_data=False)
async def _(session: CommandSession, user: u.User):
    global curr_sessions
    superuser_mode = False

    # 每周免费额度 + 自存 credits 双余额：总余额 ≤0 且非超管才拒绝
    if ai_credits_left(user) <= 0 and user.id not in config.SUPERUSERS:
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'limited'))
        return False
    # 如果有 session 在运行
    running_turn = curr_sessions.get(user.id)
    if running_turn:
        if session.current_arg_text.strip() in ("stop", "aistop"):
            aistop.request_stop(session.event.group_id, user.id)
            return False
        if not isinstance(running_turn, dict):
            # 该对话未开启插入模式：维持原有拒绝
            await send_session_msg(session, get_message("plugins", __plugin_name__, "ai_session_on"))
            return False
        # 进行中的对话开启了插入模式：本条消息将并入其上下文（moderation 之后入队）
        pending_insert = running_turn
    else:
        pending_insert = None
    MAX_LENGTH = 3000
    from . import llm
    available_models = llm.registry.list_model_aliases()
    # current_arg 带 CQ 码（图片等）；current_arg_text 会把 CQ 整个剥掉导致图片丢失
    raw = str(session.current_arg)
    # /ai -m（只给了选项、没给模型名）→ 列出可用模型与当前默认（在 argparse 报错前拦截）
    if re.fullmatch(r"(?:-m|--model)", raw.strip()):
        setting = user_model_setting(user)
        current = "auto（按话题自动选择）" if setting == constants.LLM_AUTO_MODEL_ALIAS else user_model(user)
        return await send_session_msg(session, get_message(
            "plugins", __plugin_name__, "model_list",
            models=get_model_list(), current=current))
    parser = XmeArgumentParser(session=session, usage=arg_usage)
    parser.exit_mssage = get_message("plugins", __plugin_name__, "shell_error")
    parser.add_argument('-c', '--ctrl', action='store_true', default=False)
    parser.add_argument('-C','--continue', dest='resume', action='store_true', default=False)
    parser.add_argument('-m', '--model', type=str)
    parser.add_argument("-r", nargs=argparse.REMAINDER)
    parser.add_argument('text', nargs='*')
    args = parser.parse_args(session.argv)
    # text = ' '.join(args.r or args.text).strip()
    text = extract_text(raw)
    # 输入风控
    moderation_result = await is_text_can_send(session, text, 4)
    can_send = moderation_result["result"]
    reason = moderation_result["reason"]
    if not can_send:
        await send_session_msg(session, get_message("config", "moderation_danger_input", reason=reason))
        return False
    # ---------
    if args.ctrl and text and len(text) <= MAX_LENGTH:
        control = await parse_control(session, text, user)
        if control is CMD_END:
            return False
        await send_session_msg(session, control)
        return False
    # /ai -m <模型> 且没有对话内容：把该模型设为用户的默认模型（持久化，之后 /ai 都用它）
    if args.model and not text:
        if args.model != constants.LLM_AUTO_MODEL_ALIAS and not llm.registry.is_valid_model(args.model):
            return await send_session_msg(session, get_message(
                "plugins", __plugin_name__, 'error_model', model=args.model,
                models="、".join([f'"{i}"' for i in available_models])))
        set_user_model(user, args.model)
        # auto：存的是"按话题自动选择"这一策略，回执文案单独给
        key = 'model_saved_auto' if args.model == constants.LLM_AUTO_MODEL_ALIAS else 'model_saved'
        return await send_session_msg(session, get_message(
            "plugins", __plugin_name__, key, model=args.model,
            models=auto_model_list()))
    if not text:
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'no_arg'))
        return False
    if len(text) > MAX_LENGTH:
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'too_long', count=MAX_LENGTH))
        return False

    # 自己进行中的对话开启了插入模式：本条消息入队，打断并并入其上下文
    if pending_insert is not None:
        if session.event.group_id == pending_insert.get("group_id"):
            # 与首次调用同源：nonebot1 会把该消息经会话 arg 通道交给运行中的 agent 插入，
            # 指令路径不再入队，避免同一句话被插入两次（nonebot1 双投递规避）
            return False
        image_objects, cq_matches = await get_images_from_message(session.bot, text)
        image_urls = [x["file"] for x in image_objects]
        ins_text = text
        for image_cq in cq_matches:
            ins_text = ins_text.replace(image_cq, f"[图片{hash_text(image_cq)}]")
        if not share.enqueue_insert(pending_insert["key"], share.Insert(
                user_id=session.event.user_id, text=ins_text,
                image_urls=tuple(image_urls), time=get_time_now())):
            await send_session_msg(session, get_message("plugins", __plugin_name__, 'shared_insert_queue_full', max_pending=constants.MAX_PENDING_INSERTS))
            return False
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'shared_insert_accepted', code=pending_insert["display"]))
        return False

    # 指定 -m 为临时使用（不落库）；未指定则用该用户的默认模型
    # 模型：-m <模型> 临时指定；-m auto 或用户默认设为 auto → 走话题路由（基线用默认别名）
    auto_requested = args.model == constants.LLM_AUTO_MODEL_ALIAS
    model = args.model or user_model(user)
    if auto_requested:
        model = llm.registry.default_alias()
    elif not llm.registry.is_valid_model(model):
        return await send_session_msg(session, get_message("plugins", __plugin_name__, 'error_model', model=model, models="、".join([f'"{i}"' for i in available_models])))
    # 检测上次异常中断的会话快照：三选项（1 原样继续 / 2 继续并带入当前消息 / 3 取消）
    resume_data = None
    if not args.resume and text:
        snap = load_snapshot(session.event.user_id)
        if snap:
            confirm = await aget_arg(
                session,
                prompt=get_message("plugins", __plugin_name__, "resume_ask",
                                   count=len(snap.get("messages") or []), time=snap.get("time", "")),
                rules=lambda r: True,
                max_times=1,
            )
            if confirm is CMD_END:
                return CMD_END
            choice = (confirm or "").strip().translate(str.maketrans("１２３", "123"))
            if choice.startswith("2"):
                # 继续并把本条新消息（含图片）并入恢复的上下文
                image_objects, cq_matches = await get_images_from_message(session.bot, text)
                image_urls = [x["file"] for x in image_objects]
                new_text = text
                for image_cq in cq_matches:
                    new_text = new_text.replace(image_cq, f"[图片{hash_text(image_cq)}]")
                snap["messages"].append({"role": "user", "content": build_user_content(new_text, image_urls)})
                snap["asks"] = (snap.get("asks") or []) + [
                    {"user_id": user.id, "text": new_text, "image_urls": image_urls}]
                resume_data = snap
            elif choice.startswith("1"):
                resume_data = snap  # 原样恢复，当前消息不带入
            else:
                clear_snapshot(user.id)  # 3 或无效输入：丢弃快照，按新对话处理
    # /ai --continue：显式恢复上次异常中断的会话（快照含全部用户输入/思考/工具结果/插入）
    if args.resume:
        resume_data = load_snapshot(session.event.user_id)
        if not resume_data:
            await send_session_msg(session, get_message("plugins", __plugin_name__, 'no_resume'))
            return False
    if resume_data:
        shared_session = share.SharedSession(resume_data["shared_code"]) if resume_data.get("shared_code") else None
        ai_session = resume_data.get("ai_session") or history.DEFAULT_SESSION
        storage = shared_session if shared_session is not None else AISession(session.event.user_id, ai_session)
    else:
        # 统一指针解析当前会话（普通/共享同等对待，isinstance 区分类型）
        storage = current_storage(session.event.user_id)
        shared_session = storage if isinstance(storage, share.SharedSession) else None
    if shared_session is not None and not share.acquire_busy(
            shared_session.code, group_id=session.event.group_id, user_id=session.event.user_id):
        # 对话进行中：开启插入模式时成员消息入队（打断并插入），否则提示开启方式
        if not shared_session.insert_enabled:
            await send_session_msg(session, get_message("plugins", __plugin_name__, 'shared_busy', title=f"{shared_session.title}({shared_session.code})") + get_message("plugins", __plugin_name__, 'shared_insert_hint'))
            return False
        # 插入消息必须与首次调用者同源（同群，或同一人的私聊），否则看不到 AI 的回答
        if not share.insert_context_allowed(shared_session.code, group_id=session.event.group_id, user_id=session.event.user_id):
            await send_session_msg(session, get_message("plugins", __plugin_name__, 'shared_busy', title=f"{shared_session.title}({shared_session.code})"))
            return False
        image_objects, cq_matches = await get_images_from_message(session.bot, text)
        image_urls = [x["file"] for x in image_objects]
        ins_text = text
        for image_cq in cq_matches:
            ins_text = ins_text.replace(image_cq, f"[图片{hash_text(image_cq)}]")
        ins = share.Insert(user_id=session.event.user_id, text=ins_text,
                           image_urls=tuple(image_urls), time=get_time_now())
        if not share.enqueue_insert(share.shared_insert_key(shared_session.code), ins):
            await send_session_msg(session, get_message("plugins", __plugin_name__, 'shared_insert_queue_full',
            max_pending=constants.MAX_PENDING_INSERTS))
            return False
        if share.acquire_busy(shared_session.code, group_id=session.event.group_id, user_id=session.event.user_id):
            # 对话恰好在入队后结束：撤回自己的插入，按普通对话继续（锁已由本请求持有）
            share.remove_insert(share.shared_insert_key(shared_session.code), ins)
        else:
            await send_session_msg(session, get_message("plugins", __plugin_name__, 'shared_insert_accepted',
            code=shared_session.code,
            max_pending=constants.MAX_PENDING_INSERTS))
            return False
    try:
        ai_session = storage.ai_session
        # 注意："正在使用 X 模型" 提示改为在 talk 内、模型确定（话题路由/媒体切换）之后发送，
        # 这样显示的是本轮真正使用的模型
        # 默认模型动态分配（集中判断）
        # 动态分配介入条件：
        #   开关开启，且（本次显式要求 auto，或 本次没指定模型且用户默认没指定具体模型）
        routing_allowed = (bool(constants.LLM_TOPIC_ROUTING_ENABLED)
                           and (auto_requested
                                or (args.model is None and allows_auto_model(user))))
        t, tokens_use_dict, messages_dict, tool_call_times = await talk(
            session, text, user, model, ai_session, shared=shared_session,
            resume_data=resume_data, routing_allowed=routing_allowed)
        if not t:
            return False
        pending_messages = messages_dict["messages"]
        prefix = messages_dict["prefix"]
        history_compressed = messages_dict['history_compressed']
        secs = messages_dict['talk_secs']
        if history_compressed > 0:
            prefix = prefix + f"上下文已压缩，使用 {history_compressed} 字\n"
        credits_use = tokens_use_dict["credits_use"]
        cached = tokens_use_dict["cached"]
        total = tokens_use_dict["total"]

        message = "\n".join([str(s) for s in pending_messages])
        ai_logger.info(f"msg {t}")
        t = t.replace("[", "&#91;").replace("]", "&#93;")
        message += t
        user_history = storage.load_history()
        *_, normals = history.split(user_history)
        # 插入模式下全部用量在参与者间均摊，逐人结算（本周额度封顶 + 自存 credits 扣透支；超管跳过）
        credits_split = tokens_use_dict.get("credits_split") or {str(user.id): credits_use}
        lefts = credits.settle_split(credits_split)
        credits_left_now = lefts.get(str(user.id), credits.ai_credits_left(user))
        send_msg = get_message(
            "plugins",
            __plugin_name__,
            'talk_result',
            talk=message,
            tokens_left_now=f"{credits_left_now:,.2f}".rstrip('0').rstrip('.')
            if not superuser_mode
            else "∞",
            talk_time=secs_to_ymdh(secs),
            tool_call_times=tool_call_times,
            cached=f"{cached:,.2f}".rstrip('0').rstrip('.'),
            tokens=f"{total:,.2f}".rstrip('0').rstrip('.'),
            credits=f"{credits_use:,.2f}".rstrip('0').rstrip('.'),
            history_used=f"{len(normals):,} / {MAX_HISTORY_COUNT}",
            prefix=prefix
        )
        # ai_logger.info(f"send msg {send_msg}")
        moderation_result = await is_text_can_send(session, send_msg, 4)
        can_send = moderation_result["result"]
        reason = moderation_result["reason"]
        # if not can_send:
            # await send_session_msg(session, get_message("config", "moderation_danger_send", reason=reason))
            # return False
        # ---------

        await send_session_msg(
            session,
            send_msg, tips=True
        )
        # user.update()
        return True
    except Exception:
        # 注意：logging 的格式串必须带 %s 占位符，否则整条记录会被丢弃（静默无日志）
        ai_logger.error(f"AI 调用错误：{format_exc()}")
        await send_session_msg(session, get_message("config", "unknown_error", ex=format_exc()))
        return False
    finally:
        turn = curr_sessions[user.id]
        curr_sessions[user.id] = False
        # 对话结束时残留的插入消息已无法并入，向插入者致歉（共享/普通通用）
        if isinstance(turn, dict) and turn.get("key"):
            for lost in share.consume_inserts(turn["key"]):
                await send_to_user(
                    session.bot,
                    lost.user_id,get_message("plugins",
                            __plugin_name__,
                            'shared_insert_lost', code=turn["display"]
                        )
                    )


async def talk(session, text, user: u.User, model: str, ai_session=history.DEFAULT_SESSION, shared=None, resume_data=None, routing_allowed: bool = False):
    httpx_client = httpx.Client(
        proxy=None,
        trust_env=False,
        timeout=60.0
    )
    global curr_sessions
    curr_sessions[user.id] = True
    client = ZhipuAiClient(api_key=GLM_API_KEY, http_client=httpx_client)
    with open("./static/glossary.md") as gl:
        glossary = gl.read()
    with open("./static/telia.txt") as tel:
        telia = tel.read()
    with open("./docs.md") as do:
        docs = do.read()
    tips = get_character_item("bot_info", "tips", default="无提示")
    if isinstance(tips, list):
        tips = [character_format(t) for t in tips]
    else:
        tips = [tips]
    tips_str = [f"- {t}\n" for t in tips]
    skills = {
        "worldview_settings": "漠月、漠星和九九/九镹所在世界观相关的设定合集，在有世界观相关的问题可以调用。",
        "visual_design_artifact": "Generate art & visual-design artifacts as self-contained deliverables — SVG illustrations, icons, logos, cartoon scenes, SMIL loop animations, HTML/CSS visual pages, generative patterns — each verified by rendering. Use whenever the user asks to 画/设计/生成 anything visual, e.g. \"画一个……的 SVG 小动画\", \"设计一个 logo/图标/头像/海报/封面/banner\", \"来个循环动画/生成艺术/粒子效果\", or asks to fix or beautify an existing visual artifact (形状断开、云朵颠倒、配色乱、构图歪、比例怪 etc.). Even a bare \"帮我画个…\" counts. Document deliverables (docx/pptx/pdf) have their own skills, but the visual principles here still apply to their embedded graphics."
    }
    skills_text = "\n".join([f"{i + 1}. {k}: {v}" for i, (k, v) in enumerate(skills.items())])
    role = read_from_path("./ai_configs.json")[__plugin_name__]["system"].format(docs=docs, glossary=glossary, tips=tips_str, time=get_time_now(), telia=telia, skills=skills_text, max_tool_call_times=MAX_TOOL_CALL_TIMES, max_history_len=constants.MAX_HISTORY_COUNT)
    ai_helper = AIHelper(client, user.id, session=session, model=model, ai_session=ai_session, shared_session=shared, resume_data=resume_data, routing_allowed=routing_allowed)
    # 新会话默认开启插入模式：只在会话尚未存在（= 此刻创建）时登记，
    # 用户事后 -c ins 关闭的不会被这里加回
    if shared is None:
        new_st = AISession(user.id, ai_session)
        if not new_st.exists():
            enable_normal_insert(user.id, ai_session)
    # 进行中的对话登记：开启插入模式时记录插入队列键与展示名（供入口并入与结束清理）
    if ai_helper.insert_enabled:
        display = ai_helper.shared.code if ai_helper.shared is not None else ai_helper.ai_session
        curr_sessions[user.id] = {"key": ai_helper.insert_key, "display": display,
                                  "group_id": session.event.group_id}
    # 开始前先清空放置上轮会话强制结束之类的问题
    ai_helper.delete_temp()
    # aistop 登记：预处理器 / /ai stop 可随时取消本任务（长工具执行中也即时生效）
    aistop.register_turn(session.event.group_id, user.id, asyncio.current_task(),
                         insert_key=ai_helper.insert_key, insert_enabled=ai_helper.insert_enabled)
    try:
        result = await ai_helper.user_talk(session, role, user, text)
    except asyncio.CancelledError:
        # 被 aistop / /ai stop 取消：不发 talk_result、不写历史，
        # 但已消耗的 tokens 照常结算（逐参与者），中断文案附带消耗
        clear_snapshot(user.id)
        ai_helper.delete_temp()
        try:
            tokens_use_dict = ai_helper.compute_credits()
            lefts = credits.settle_split(tokens_use_dict["credits_split"])
            share_used = tokens_use_dict["credits_split"].get(str(user.id))
            left = lefts.get(str(user.id))
            fmt = lambda x: f"{x:,.2f}".rstrip('0').rstrip('.') if x is not None else "未知"
            await send_session_msg(
                session,
                get_message("plugins", __plugin_name__, "ai_send_interrupted",
                            credits=fmt(share_used), left=fmt(left))
            )
        except Exception:
            ai_logger.error(f"aistop 中断结算失败：{format_exc()}")
            await send_session_msg(session, get_message("plugins", __plugin_name__, "ai_send_interrupted", credits="未知", left="未知"))
        return False, {}, {}, 0
    finally:
        aistop.unregister_turn(session.event.group_id, user.id)
    # 对话正常结束（含主动中断）→ 快照已完成使命；异常死亡时快照残留供 --continue 恢复
    clear_snapshot(user.id)
    ai_helper.delete_temp()
    return result
