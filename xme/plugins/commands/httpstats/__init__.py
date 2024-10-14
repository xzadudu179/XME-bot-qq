from nonebot import on_command, CommandSession
from . import httpstats as h
import config
from xme.xmetools.doc_gen import CommandDoc

alias = ['http', 'http状态码']
__plugin_name__ = 'httpcode'
# __plugin_usage__ = rf"""
# 指令 {__plugin_name__}
# 简介：查询状态码
# 作用：查看指定 http 状态码和它的猫猫图
# 用法：
# - {config.COMMAND_START[0]}{__plugin_name__} <状态码>
# 权限/可用范围：无
# 别名：{', '.join(alias)}
# """.strip()
__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    desc='查询状态码',
    introduction='查看指定 http 状态码和它的猫猫图',
    usage=f'<状态码>',
    permissions=[],
    alias=alias
))


@on_command(__plugin_name__, aliases=alias, only_to_me=False)
async def _(session: CommandSession):
    message = "你没输入状态码诶"
    # doc = httpstats
    params = session.current_arg_text.strip()
    if not params:
        params: str = (await session.aget(prompt="请发送你想要查询的状态码")).strip()

    if params:
        search = params.strip()
        stat = h.httpstats(search)
        if not stat:
            message = f"查询不到 {search} 状态码代表什么意思诶"
        else:
            message = f"状态码 {search} 的意思是: {stat}\n[CQ:image,file=https://http.cat/{search}]"

    await session.send(message)