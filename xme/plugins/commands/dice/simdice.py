# 简单骰子
from nonebot import CommandSession
from xme.xmetools.plugintools import on_command
from xme.plugins.commands.dice import __plugin_name__
import config
from xme.xmetools.msgtools import send_session_msg
from character import get_message
import random
random.seed()

dicealias = ["d", "rd", "骰子"]
command_name = 'dice'
@on_command('dice', aliases=dicealias, only_to_me=False, permission=lambda _: True)
async def _(session: CommandSession):
    MAX_FACES = 100_000_000
    MAX_COUNT = 50
    counts = 1
    arg = session.current_arg_text.strip()
    message = get_message("plugins", __plugin_name__, "dice_error")
    args = arg.split(" ")
    if arg == "":
        faces = 6
    else:
        try:
            faces = int(args[0])
            if len(args) > 1:
                counts = int(args[1])
        except:
            await send_session_msg(session, message=message)
            return
    points_list = []
    try:
        if len(args) > 1:
            counts = int(args[1])
        if counts > 50:
            message = get_message("plugins", __plugin_name__, "count_too_many", max_count=format(MAX_COUNT, ","))
            return await send_session_msg(session, message=message, tips=True)
        if faces * counts > MAX_FACES:
            message = get_message("plugins", __plugin_name__, "faces_too_many", max_faces=format(MAX_FACES, ","))
            return await send_session_msg(session, message=message, tips=True)
        if counts < 1:
            return await send_session_msg(session, get_message("plugins", __plugin_name__, "count_too_low"), tips=True)
        if faces < 1:
            return await send_session_msg(session, get_message("plugins", __plugin_name__, "faces_too_low"), tips=True)
        for _ in range(counts):
            points_list.append(random.randint(1, faces))
        count_morethan_1_prefix = get_message("plugins", __plugin_name__, "count_morethan_1_prefix")
        await send_session_msg(session, message=
                           get_message("plugins", __plugin_name__, "dice_result",
                               counts=format(counts, ','),
                               faces=format(faces, ','),
                               faces_result_prefix=count_morethan_1_prefix if len(args) > 1 else '',
                               faces_formula=('+'.join([format(points, ',') for points in points_list]) + '=' + format(sum(points_list), ',')) if len(args) > 1 else format(points_list[0], ',')), tips=True, tips_percent=20)
    except Exception as ex:
        await send_session_msg(session, message=message)