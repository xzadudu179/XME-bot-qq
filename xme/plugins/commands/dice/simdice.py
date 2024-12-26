# 简单骰子
from nonebot import on_command, CommandSession
from xme.plugins.commands.dice import __plugin_name__
import config
from xme.xmetools.command_tools import send_cmd_msg
from character import get_message
import random

dicealias = ["d"]
command_name = 'dice'
@on_command('dice', aliases=dicealias, only_to_me=False)
async def _(session: CommandSession):
    MAX_FACES = 100_000_000
    MAX_COUNT = 50
    counts = 1
    arg = session.current_arg_text.strip()
    message = get_message(__plugin_name__, "dice_error")
    args = arg.split(" ")
    if arg == "":
        faces = 6
        # return await send_msg(session, get_message(__plugin_name__, "no_args_message", command_name=config.COMMAND_START[0] + command_name))
        # return await send_msg(session, "使用方法：/dice [骰子面数] <骰子数量>")
    else:
        try:
            faces = int(args[0])
            if len(args) > 1:
                counts = int(args[1])
        except:
            await send_cmd_msg(session, message=message)
            return
    # message = "投骰子出现错误 xwx，请确定骰子面数及数量是不小于 1 的整数哦"
    points_list = []
    try:
        if len(args) > 1:
            counts = int(args[1])
        if counts > 50:
            message = get_message(__plugin_name__, "count_too_many", max_count=format(MAX_COUNT, ","))
            # message = "最多投 50 个骰子哦"
            return await send_cmd_msg(session, message=message)
        if faces * counts > MAX_FACES:
            message = get_message(__plugin_name__, "faces_too_many", max_faces=format(MAX_FACES, ","))
            # message = "骰子总面数过大啦ovo (>100,000,000)"
            return await send_cmd_msg(session, message=message)
        if counts < 1:
            return await send_cmd_msg(session, get_message(__plugin_name__, "count_too_low"))
            # return await send_msg(session, "骰子数量不可以小于 1 哦")
        if faces < 1:
            return await send_cmd_msg(session, get_message(__plugin_name__, "faces_too_low"))
            # return await send_msg(session, message="骰子面数不可以小于 1 哦")
        for _ in range(counts):
            points_list.append(random.randint(1, faces))
        count_morethan_1_prefix = get_message(__plugin_name__, "count_morethan_1_prefix")
        await send_cmd_msg(session, message=
                           get_message(__plugin_name__, "dice_result",
                               counts=format(counts, ','),
                               faces=format(faces, ','),
                               faces_result_prefix=count_morethan_1_prefix if len(args) > 1 else '',
                               faces_formula=('+'.join([format(points, ',') for points in points_list]) + '=' + format(sum(points_list), ',')) if len(args) > 1 else format(points_list[0], ',')))
    except Exception as ex:
        await send_cmd_msg(session, message=message)