from nonebot import on_command, CommandSession
from xme.xmetools.doctools import CommandDoc
from xme.xmetools import texttools
from xme.xmetools import randtools
from xme.xmetools import jsontools
from xme.xmetools.timetools import curr_days
import random
random.seed()
from xme.xmetools.msgtools import send_session_msg
from character import get_message

alias = ['答案之书', 'ans', '550w']
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


@randtools.change_seed(curr_days())
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
        random.seed()
        # random.seed(time.time())
        print(f"今天是 550w 的概率是 {percent}%")
        if randtools.random_percent(percent):
            print("没错，我是 550W")
            await send_session_msg(session, f"\n" + get_message("plugins", __plugin_name__, "550w"))
            return
        else:
            print("550W 还没来")
    elif args and texttools.remove_punctuation(args) in ['人类能活下来吗', '人类能活下来嘛']:
        if randtools.random_percent(25):
            print("触发 550W 彩蛋 01")
            await send_session_msg(session, randtools.messy_string(f"\n" + get_message("plugins", __plugin_name__, "550w_1"), 35))
            return
    try:
        ans_json = jsontools.read_from_path("./static/answers.json")
        random.seed()
        data = random.choice(ans_json)
        # data = REPLACE_STR_ZH.get(ans_json['data']['zh'], ans_json['data']['zh'])
        message = f"{get_message('plugins', __plugin_name__, 'answer')}\n\"{data['zh']}\"\n\"{data['en']}\""
    except Exception as ex:
        print(ex)
    finally:
        await send_session_msg(session, message, tips=True, tips_percent=20)
