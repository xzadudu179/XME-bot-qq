# 简单骰子
from nonebot import on_command, CommandSession
import random

dicealias = ["d"]
@on_command('dice', aliases=dicealias, only_to_me=False)
async def _(session: CommandSession):
    arg = session.current_arg_text.strip()
    if arg == "":
        return await session.send("/dice [骰子面数] <骰子数量>")
    message = "投骰子出现错误 xwx，请确定骰子面数是不小于 1 的整数哦"
    points_list = []
    args = arg.split(" ")
    try:
        counts = 1
        faces = int(args[0])
        if len(args) > 1:
            counts = int(args[1])
        if counts > 50:
            message = "最多投 50 个骰子哦"
            return await session.send(message=message)
        if faces * counts > 100_000_000:
            message = "骰子总面数过大啦ovo (>100000000)"
            return await session.send(message=message)
        if faces < 1:
            return await session.send(message="骰子面数不可以小于 1 哦")
        for _ in range(counts):
            points_list.append(random.randint(1, faces))
        await session.send(message=f"[CQ:at,qq={session.event.user_id}] 你投出了 {counts} 个 {faces} 面的骰子，{'总共' if len(args) > 1 else ''}投到了 {('+'.join([str(points) for points in points_list]) + '=' + str(sum(points_list))) if len(args) > 1 else points_list[0]}！")
    except Exception as ex:
        # print(f"{ex.with_traceback()}")
        await session.send(message=message)