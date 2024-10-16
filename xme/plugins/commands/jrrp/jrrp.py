from anyio import sleep
from itsdangerous import base64_encode

from nonebot import on_command, CommandSession

from xme.plugins.commands.jrrp.luck_algorithm import get_luck
from xme.xmetools.doc_gen import CommandDoc

alias = ["今日人品" , "jrrp"]
__plugin_name__ = 'jrrp'

__plugin_usage__= str(CommandDoc(
    name=__plugin_name__,
    desc='今日人品',
    introduction='今日人品',
    usage=f'jrrp',
    permissions=[],
    alias=alias
))

@on_command(__plugin_name__, aliases=alias)
async def jrrp(session: CommandSession):
    qq = session.event.user_id
    key = base64_encode("嘿嘿嘿...179....嘿嘿嘿")
    result = get_luck(qq, key)
    if result == 0:
        await session.send("""
        请悉知:本插件绝对不会有任何对于任何用户有负面性的针对的影响。
        本插件jrrp算法采用加密算法，且没有任何的set()方法。
        在使用本插件时，请确保您有足够的心态，倘若因为该结果的原因导致您做出包括但不限于以下行为时:
        如：砸坏您的电子设备、对于其他人造成不可逆的影响等一切行为时，
        本插件一律不付任何的责任
        本插件开发者绝对不会做出任何的干预行为
        """.strip())
        await sleep(100)
        await session.send(f"很抱歉，您的今日人品为:{result}")
    elif result == 100:
        await session.send("您的今日人品为100!100!100!")
    else:
        await session.send(f"您的今日人品为:{result}")
