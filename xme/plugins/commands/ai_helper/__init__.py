from nonebot import on_command, CommandSession
from xme.xmetools.cmdtools import use_args
from xme.xmetools.doctools import CommandDoc, shell_like_usage
from nonebot.argparse import ArgumentParser
from .commands import clear_history
from xme.xmetools.jsontools import read_from_path, save_to_path
from xme.xmetools.msgtools import send_session_msg
from character import get_message
from xme.xmetools.timetools import TimeUnit
from keys import GLM_API_KEY
import asyncio
from xme.plugins.commands.xme_user.classes import user as u
from zhipuai import ZhipuAI

cmds = {
        "hisclear": {
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

def parse_control(session: CommandSession, text) -> str:
    parse_func = lambda text, **kwargs: f"没有这个指令 \"{text}\" 哦"
    cmd = cmds.get(text, None)
    if cmd is not None:
        parse_func = cmd["content"]
    return parse_func(user_id=session.event.user_id, history=history, text=text)

arg_usage = shell_like_usage("OPTION", [
    {
        "name": "help",
        "abbr": "h",
        "desc": "查看帮助"
    },
    {
        "name": "ctrl",
        "abbr": "c",
        "desc": f"只需要在任意地方输入 -c 即可将原本输入给 AI 的内容变为指令\n{get_command_list()}"
    }
])

alias = ['ai', 'aih']
__plugin_name__ = 'ai_helper'
__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    usage=f'(对话内容) [OPTION]',
    permissions=[],
    alias=alias
))

history = read_from_path("./ai_configs.json")[__plugin_name__]["history"]

@on_command(__plugin_name__, aliases=alias, only_to_me=False, shell_like=True)
@u.using_user(save_data=False)
@u.limit(__plugin_name__, 1, get_message("plugins", __plugin_name__, 'limited'), unit=TimeUnit.HOUR, count_limit=15)
async def _(session: CommandSession, user: u.User):
    parser = ArgumentParser(session=session, usage=arg_usage)
    parser.add_argument('-c', '--ctrl', action='store_true', default=False)
    parser.add_argument('text', nargs='*')
    # print(session.argv)
    args = parser.parse_args(session.argv)
    text =  ' '.join(args.text).strip()
    if not text:
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'no_arg'))
        return False
    if len(text) > 300:
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'too_long'))
        return False
    if args.ctrl:
        await send_session_msg(session, parse_control(session, text))
        return False
    await send_session_msg(session, get_message("plugins", __plugin_name__, 'talk_result', talk=(await talk(session, text))))
    return True

def get_history(user_id):
    user_id = str(user_id)
    user_history = history.get(user_id, [])
    if not user_history:
        return ""
    build_str = "历史记录：\n"
    for i, item in enumerate(user_history):
        build_str += f"{i + 1}. [用户{user_id}]: {item['ask']};\n\t你回答：{item['ans']}\n----------\n"
    build_str += "=" * 15
    build_str += "\n当前对话："
    return build_str

def build_history(user_id, ask, ans):
    user_id = str(user_id)
    user_history = history.get(user_id, None)
    if user_history is None:
        history[user_id] = []
    history[user_id].append({
        "ask": ask,
        "ans": ans
    })
    if len(history[user_id]) > 100:
        del history[user_id][-1]
    save_history()

def save_history():
    ai_conf = read_from_path("./ai_configs.json")
    ai_conf[__plugin_name__]["history"] = history
    save_to_path("./ai_configs.json", ai_conf, indent=4)

async def talk(session: CommandSession, text):
    client = ZhipuAI(api_key=GLM_API_KEY)
    with open("./static/glossary.md") as gl:
        glossary = gl.read()
    with open("./docs.md") as do:
        docs = do.read()
    role = read_from_path("./ai_configs.json")[__plugin_name__]["system"].format(docs=docs, glossary=glossary)
    # print(role)
    # print(f"{get_history(session.event.user_id)}\n{text}")
    response = client.chat.asyncCompletions.create(
    # model="glm-4-flashx",
    model="glm-4-plus",
    messages=[
            {"role": "system","content": role},
            {"role": "user","content": f"{get_history(session.event.user_id)}\n{text}"}
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
    build_history(user_id=session.event.user_id, ask=text, ans=ans)
    return result_response.choices[0].message.content