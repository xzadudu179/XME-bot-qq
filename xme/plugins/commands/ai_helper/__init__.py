import argparse
import inspect
import httpx

import config
from nonebot import CommandSession

from traceback import format_exc
from xme.plugins.commands.ai_helper import history
from xme.xmetools.plugintools import on_command
from xme.xmetools.doctools import CommandDoc, shell_like_usage
from xme.xmetools.bottools import XmeArgumentParser
from xme.xmetools.msgtools import is_text_can_send, send_session_msg
from xme.xmetools.jsontools import read_from_path
from xme.xmetools.timetools import TimeUnit, get_time_now, secs_to_ymdh
from character import get_message, get_character_item, character_format
from keys import GLM_API_KEY
from xme.plugins.commands.xme_user.classes import user as u
from zai import ZhipuAiClient

from .agent import AIHelper, ai_logger
from .session import AISession
from . import constants
from .constants import __plugin_name__, TOKENS_LIMIT, MAX_TOOL_CALL_TIMES, MAX_HISTORY_COUNT
from .commands import clear_history, clear_all_sessions, list_sessions, name_session, new_session, switch_session


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
        "desc": "切换到指定序号的会话",
    },
}


def get_command_list():
    cmd_list_str = "当前指令参数列表：\n"
    for k, v in cmds.items():
        cmd_list_str += f"{k} {v['args']}: {v['desc']}\n"
    return cmd_list_str


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
    return result


arg_usage = shell_like_usage("OPTION", [
    {
        "name": "help",
        "abbr": "h",
        "desc": "查看帮助"
    },
    {
        "name": "raw",
        "abbr": "r",
        "desc": "会把之后的文本全都解析为单纯的文本，如果你在发东西给 ai 的时候出现了 \"指令执行的参数有问题哦\" 的问题，可以试试在发送的内容前加上 -r 哦"
    },
    {
        "name": "model",
        "abbr": "m",
        "desc": "切换模型，可使用 \"pro\" 或 \"flash\" 两种，默认 \"flash\"。"
    },
    {
        "name": "ctrl",
        "abbr": "c",
        "desc": f"只需要在任意地方输入 -c 即可将原本输入给 AI 的内容变为指令\n{get_command_list()}"
    }
])

alias = ['ai']
__plugin_usage__ = CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    usage=f'(对话内容) [OPTION]\n{arg_usage}',
    permissions=[],
    alias=alias
)


@on_command(__plugin_name__, aliases=alias, only_to_me=False, shell_like=True, permission=lambda _: True)
@u.using_user(save_data=True)
@u.custom_limit(__plugin_name__, 1, unit=TimeUnit.DAY, count_limit=TOKENS_LIMIT)
async def _(session: CommandSession, user: u.User, validate, count_tick):
    global curr_sessions
    superuser_mode = False
    if validate() and user.id not in config.SUPERUSERS:
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'limited'))
        return False
    # 如果有 session 在运行
    if curr_sessions.get(user.id):
        await send_session_msg(session, get_message("plugins", __plugin_name__, "ai_session_on"))
        return False
    MAX_LENGTH = 3000
    parser = XmeArgumentParser(session=session, usage=arg_usage)
    parser.exit_mssage = get_message("config", "shell_error", command_name=__plugin_name__)
    parser.add_argument('-c', '--ctrl', action='store_true', default=False)
    parser.add_argument('-m', '--model', type=str)
    parser.add_argument("-r", nargs=argparse.REMAINDER)
    parser.add_argument('text', nargs='*')
    args = parser.parse_args(session.argv)
    text = ' '.join(args.r or args.text).strip()
    # 输入风控
    moderation_result = await is_text_can_send(session, text)
    can_send = moderation_result["result"]
    reason = moderation_result["reason"]
    if not can_send:
        await send_session_msg(session, get_message("config", "moderation_danger_input", reason=reason))
        return False
    # ---------
    if args.ctrl and text and len(text) <= MAX_LENGTH:
        await send_session_msg(session, await parse_control(session, text, user))
        return 2
    if not text:
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'no_arg'))
        return False
    if len(text) > MAX_LENGTH:
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'too_long', count=MAX_LENGTH))
        return False

    available_models = ["flash", "pro"]
    model = args.model if args.model else "flash"
    if model not in available_models:
        return await send_session_msg(session, get_message("plugins", __plugin_name__, 'error_model', model=model, models="、".join([f'"{i}"' for i in available_models])))
    ai_session = AISession.current(session.event.user_id).ai_session
    if len(history.load_history(session.event.user_id, ai_session)) <= constants.COMPRESS_TRIGGER:
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'talking_to_ai', model=model))
    try:
        t, tokens_use_dict, messages_dict, tool_call_times = await talk(session, text, user, model, ai_session)
        if not t:
            return False
        pending_messages = messages_dict["messages"]
        prefix = messages_dict["prefix"]
        history_compressed = messages_dict['history_compressed']
        secs = messages_dict['talk_secs']
        if history_compressed > 0:
            prefix = prefix + f"上下文已压缩，使用 {history_compressed} 字"
        credits_use = tokens_use_dict["credits_use"]
        cached = tokens_use_dict["cached"]
        total = tokens_use_dict["total"]

        credits_left_now = TOKENS_LIMIT - u.get_limit_info(user, __plugin_name__)[1] - credits_use
        message = "\n".join([str(s) for s in pending_messages])
        ai_logger.info(f"msg {t}")
        t = t.replace("[", "&#91;").replace("]", "&#93;")
        message += t
        user_history = history.load_history(session.event.user_id, AISession.current(session.event.user_id).ai_session)
        *_, normals = history.split(user_history)
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
        # 输出风控
        # if len(send_msg) <= 2000:
        moderation_result = await is_text_can_send(session, send_msg)
        can_send = moderation_result["result"]
        reason = moderation_result["reason"]
        if not can_send:
            await send_session_msg(session, get_message("config", "moderation_danger_send", reason=reason))
            return False
        # ---------

        await send_session_msg(
            session,
            send_msg, tips=True
        )
        if not superuser_mode:
            count_tick(credits_use)
        return True
    except Exception:
        ai_logger.error("AI 调用错误：", format_exc())
        await send_session_msg(session, get_message("config", "unknown_error", ex=format_exc()))
        return False
    finally:
        curr_sessions[user.id] = False


async def talk(session, text, user: u.User, model: str, ai_session=history.DEFAULT_SESSION):
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
        "worldview_settings": "漠月、漠星和九九/九镹所在世界观相关的设定合集，在有世界观相关的问题可以调用。"
    }
    skills_text = "\n".join([f"{i + 1}. {k}: {v}" for i, (k, v) in enumerate(skills.items())])
    role = read_from_path("./ai_configs.json")[__plugin_name__]["system"].format(docs=docs, glossary=glossary, tips=tips_str, time=get_time_now(), telia=telia, skills=skills_text, max_tool_call_times=MAX_TOOL_CALL_TIMES, max_history_len=constants.MAX_HISTORY_COUNT)
    ai_helper = AIHelper(client, user.id, session=session, model=model, ai_session=ai_session)
    # 开始前先清空放置上轮会话强制结束之类的问题
    ai_helper.delete_temp()
    result = await ai_helper.user_talk(session, role, user, text)
    ai_helper.delete_temp()
    return result
