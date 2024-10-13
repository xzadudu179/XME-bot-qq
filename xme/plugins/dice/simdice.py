# 简单骰子
from nonebot import on_command, CommandSession
import random

__plugin_name__ = 'dice'
__plugin_usage__ = r"""
简单骰子

dice  [面数]
""".strip()

@on_command('dice', aliases=('d'), only_to_me=False)
async def _(session: CommandSession):
    if session.current_arg_text.strip() == "":
        return await session.send("/dice [骰子面数]")
    message = "投骰子出现错误 xwx，请确定骰子面数是不小于 1 的整数哦"
    try:
        faces = int(session.current_arg_text.strip())
        if faces > 100_000_000:
            message = "骰子面数过大啦ovo (>100000000)"
            return await session.send(message=message)
        if faces < 1:
            return await session.send(message="骰子面数不可以小于 1 哦")
        point = random.randint(1, faces)
        await session.send(message=f"[CQ:at,qq={session.event.user_id}] 你投出了一个 {faces} 面的骰子，投到了 {point}！")
    except:
        await session.send(message=message)