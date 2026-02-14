from nonebot import CommandSession
from xme.xmetools.debugtools import debug_msg
from nonebot.log import logger
from xme.xmetools.plugintools import on_command
from xme.xmetools.doctools import CommandDoc
from xme.xmetools import texttools
from xme.xmetools import randtools
from xme.xmetools import jsontools
from xme.plugins.commands.xme_user.classes.user import User, using_user
from xme.xmetools.timetools import curr_days
import random
from xme.xmetools.msgtools import send_session_msg
from character import get_message
random.seed()

alias = ['答案之书', 'ans']
__plugin_name__ = 'answer'
__plugin_usage__ = CommandDoc(
    name=__plugin_name__,
    # desc='查看答案之书',
    desc=get_message("plugins", __plugin_name__, "desc"),
    # introduction='随机翻开答案之书的一页，并且返回内容\n"心中默念你的问题，将会得到你的答案。"',
    introduction=get_message("plugins", __plugin_name__, "introduction"),
    usage='<问题>',
    permissions=["无"],
    alias=alias
)


@randtools.change_seed(curr_days())
def get_current_days_550w_percent():
    percent = (random.random() * 17.4) + 0.5
    return percent

@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda _: True)
@using_user(False)
async def _(session: CommandSession, u: User):
    message = get_message("plugins", __plugin_name__, "default_error")
    # message = "呜呜，书突然找不到了"
    args = session.current_arg_text.strip()
    debug_msg(args.upper())

    if args and '550W' in args.upper():
        debug_msg("有人在询问 550W")
        # random.seed(curr_days())
        percent = get_current_days_550w_percent()
        random.seed()
        # random.seed(time.time())
        debug_msg(f"今天是 550w 的概率是 {percent}%")
        if randtools.random_percent(percent):
            debug_msg("没错，我是 550W")
            await send_session_msg(session, "\n" + get_message("plugins", __plugin_name__, "550w"))
            await u.achieve_achievement(session, "550W")
            return
        else:
            debug_msg("550W 还没来")
    elif args and texttools.remove_punctuation(args) in ['人类能活下来吗', '人类能活下来嘛']:
        if randtools.random_percent(25):
            debug_msg("触发 550W 彩蛋 01")
            await send_session_msg(session, randtools.messy_string("\n" + get_message("plugins", __plugin_name__, "550w_1"), 35))
            await u.achieve_achievement(session, "550W")
            return
    try:
        ans_json = jsontools.read_from_path("./static/answers.json")
        random.seed()
        data = random.choice(ans_json)
        # data = REPLACE_STR_ZH.get(ans_json['data']['zh'], ans_json['data']['zh'])
        message = f"{get_message('plugins', __plugin_name__, 'answer')}\n\"{data['zh']}\"\n\"{data['en']}\""
    except Exception as ex:
        logger.exception(ex)
    finally:
        await send_session_msg(session, message, tips=True, tips_percent=20)
