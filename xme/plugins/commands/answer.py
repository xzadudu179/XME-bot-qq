from nonebot import on_command, CommandSession
from xme.xmetools.doc_tools import CommandDoc
from xme.xmetools import request_tools
from xme.xmetools import random_tools
from xme.xmetools import text_tools
from xme.xmetools.time_tools import curr_days
import random
from xme.xmetools.command_tools import send_session_msg
from character import get_message
import json

alias = ['答案之书', 'ans']
__plugin_name__ = 'answer'
__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    # desc='查看答案之书',
    desc=get_message("plugins", __plugin_name__, "desc"),
    # introduction='随机翻开答案之书的一页，并且返回内容\n"心中默念你的问题，将会得到你的答案。"',
    introduction=get_message("plugins", __plugin_name__, "introduction"),
    usage=f'',
    permissions=["无"],
    alias=alias
))

REPLACE_STR_ZH = {
    "办何自己不肯妥协，先问一下自已的能力。": "为何自己不肯妥协，先问一下自己的能力。",
    "有。": "是的。"
}

@random_tools.change_seed(curr_days())
def get_current_days_550w_percent():
    percent = (random.random() * 17.4) + 0.5
    return percent

@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda _: True)
async def _(session: CommandSession):
    message = get_message("plugins", __plugin_name__, "default_error")
    # message = "呜呜，书突然找不到了"
    args = session.current_arg_text.strip()
    print(args.upper())

    if args and '550W' in args.upper():
        print("有人在询问 550W")
        # random.seed(curr_days())
        percent = get_current_days_550w_percent()
        # random.seed(time.time())
        print(f"今天是 550w 的概率是 {percent}%")
        if random_tools.random_percent(percent):
            print("没错，我是 550W")
            await send_session_msg(session, f"\n" + get_message("plugins", __plugin_name__, "550w"))
            return
        else:
            print("550W 还没来")
    try:
        ans_json = json.loads(await request_tools.fetch_data('https://api.andeer.top/API/answer.php'))
        if ans_json['code'] != 200:
            message = get_message("plugins", __plugin_name__, "cannot_fetch")
            # message = "呜呜，书翻不开了..."
        else:
            data = REPLACE_STR_ZH.get(ans_json['data']['zh'], ans_json['data']['zh'])
            message = f"\n{get_message('plugins', __plugin_name__, 'answer')}\n\"{data}\"\n\"{ans_json['data']['en']}\""
    except Exception as ex:
        print(ex)
    finally:
        await send_session_msg(session, message)
