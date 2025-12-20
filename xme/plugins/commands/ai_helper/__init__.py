from nonebot import on_command, CommandSession
from xme.xmetools.cmdtools import use_args
from xme.xmetools.doctools import CommandDoc, shell_like_usage
# from nonebot.argparse import ArgumentParser
from xme.xmetools.bottools import XmeArgumentParser
from .commands import clear_history
import cn2an
from traceback import format_exc
import httpx
# from xme.xmetools.texttools import dec_to_chinese
from xme.xmetools.jsontools import read_from_path, save_to_path
from xme.xmetools.msgtools import send_session_msg
from character import get_message
from xme.xmetools.timetools import TimeUnit
from keys import GLM_API_KEY
import asyncio
from xme.plugins.commands.xme_user.classes import user as u
from zhipuai import ZhipuAI



cmds = {
        "clear": {
            "content": clear_history,
            "args": "",
            "desc": "清除你的所有对话历史"
        }
    }

def get_command_list():
    cmd_list_str = "当前指令参数列表：\n"
    for k, v in cmds.items():
        cmd_list_str += f"{k} {v['args']}: {v['desc']}\n"
    return cmd_list_str

def parse_control(session: CommandSession, text: str, user: u.User) -> str:
    text, args = text.split(" ")[0], text.split(" ")[1:]
    parse_func = lambda text, **_: f"没有这个指令 \"{text}\" 哦"
    cmd = cmds.get(text, None)
    if cmd is not None:
        parse_func = cmd["content"]
    return parse_func(session=session, user=user, text=text, args=args)

arg_usage = shell_like_usage("OPTION", [
    {
        "name": "help",
        "abbr": "h",
        "desc": "查看帮助"
    },
    {
        "name": "raw",
        "abbr": "r",
        "desc": "会把之后的文本全都解析为单纯的文本（注：这个参数优先级最大）"
    },
    {
        "name": "ctrl",
        "abbr": "c",
        "desc": f"只需要在任意地方输入 -c 即可将原本输入给 AI 的内容变为指令\n{get_command_list()}"
    }

])

alias = ['ai', 'aih']
__plugin_name__ = 'ai_helper'
__plugin_usage__ = CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    usage=f'(对话内容) [OPTION]\n{arg_usage}',
    permissions=[],
    alias=alias
)

# history = read_from_path("./ai_configs.json")[__plugin_name__]["history"]

TIMES_LIMIT = 15
@on_command(__plugin_name__, aliases=alias, only_to_me=False, shell_like=True, permission=lambda _: True)
@u.using_user(save_data=True)
@u.limit(__plugin_name__, 1, get_message("plugins", __plugin_name__, 'limited'), unit=TimeUnit.HOUR, count_limit=TIMES_LIMIT, fails=lambda x: x == 2 or x == False)
async def _(session: CommandSession, user: u.User):
    times_left_now = TIMES_LIMIT - u.get_limit_info(user, __plugin_name__)[1] - 1
    intext = ""
    if "-r " in session.current_arg_text:
        intext = "-r"
    elif "--raw " in session.current_arg_text:
        intext = '--raw'
    if intext:
        text = intext.join(session.current_arg_text.split(intext)[1:])
    else:
        parser = XmeArgumentParser(session=session, usage=arg_usage)
        parser.exit_mssage = get_message("config", "shell_error", command_name=__plugin_name__)
        parser.add_argument('-c', '--ctrl', action='store_true', default=False)
        parser.add_argument('text', nargs='*')
        args = parser.parse_args(session.argv)
        # print(session.argv)
        text =  ' '.join(args.text).strip()
        MAX_LENGTH = 1000
        if args.ctrl and text and len(text) <= MAX_LENGTH:
            await send_session_msg(session, parse_control(session, text, user))
            return 2
    if not text:
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'no_arg'))
        return False
    if len(text) > MAX_LENGTH:
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'too_long', count=MAX_LENGTH))
        return False
    await send_session_msg(session, get_message("plugins", __plugin_name__, 'talking_to_ai'))
    try:
        print("正常")
        await send_session_msg(session,
                               get_message("plugins", __plugin_name__, 'talk_result', talk=(await talk(session, text, user)), times_left_now=cn2an.an2cn(times_left_now)), tips=True)
    except Exception as ex:
        print("错误：", ex)
        await send_session_msg(session, get_message("config", "unknown_error", ex=format_exc()))
        return False
    return True

def get_history(user: u.User):
    user_history = user.ai_history
    if not user_history:
        return ""
    build_str = "历史记录：\n"
    for i, item in enumerate(user_history):
        build_str += f"{i + 1}. [用户{user.id}]: {item['ask']};\n\t你回答：{item['ans']}\n----------\n"
    build_str += "=" * 15
    build_str += "\n当前对话："
    return build_str

def build_history(user: u.User, ask, ans):
    user_history = user.ai_history
    # if user_history is None:
    #     user.ai_history = []
    user.ai_history.append({
        "ask": ask,
        "ans": ans
    })
    if len(user.ai_history) > 20:
        del user.ai_history[-1]
#     save_history()

# def save_history():
#     ai_conf = read_from_path("./ai_configs.json")
#     ai_conf[__plugin_name__]["history"] = history
#     save_to_path("./ai_configs.json", ai_conf, indent=4)

async def talk(session: CommandSession, text, user: u.User):
    httpx_client = httpx.Client(
        proxy=None,
        trust_env=False,
        timeout=60.0
    )
    client = ZhipuAI(api_key=GLM_API_KEY, http_client=httpx_client)
    with open("./static/glossary.md") as gl:
        glossary = gl.read()
    with open("./docs.md") as do:
        docs = do.read()
    role = read_from_path("./ai_configs.json")[__plugin_name__]["system"].format(docs=docs, glossary=glossary)
    # print(role)
    # print(f"{get_history(session.event.user_id)}\n{text}")
    response = client.chat.asyncCompletions.create(
    # model="glm-4-flashx",
    model="glm-4.6",
    messages=[
            {"role": "system","content": role},
            {"role": "user","content": f"{get_history(user)}\n{text}"}
        ], temperature=0.3)
    task_id = response.id
    task_status = ''
    get_cnt = 0
    while task_status != 'SUCCESS' and task_status != 'FAILED' and get_cnt <= 100:
        result_response = client.chat.asyncCompletions.retrieve_completion_result(id=task_id)
        # print(result_response)
        task_status = result_response.task_status
        await asyncio.sleep(0.5)
        get_cnt += 1
    ans = result_response.choices[0].message.content
    build_history(user=user, ask=text, ans=ans)
    print("处理结果")
    return result_response.choices[0].message.content