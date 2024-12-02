from nonebot import on_command, CommandSession
from . import httpstats as h
from xme.xmetools.command_tools import send_msg
from character import get_message
from xme.xmetools.doc_gen import CommandDoc

alias = ['http', 'http状态码']
__plugin_name__ = 'httpcode'
__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    desc=get_message(__plugin_name__, 'desc'),
    # desc='查询状态码',
    introduction=get_message(__plugin_name__, 'introduction'),
    # introduction='查看指定 http 状态码和它的猫猫图',
    usage=f'<状态码>',
    permissions=[],
    alias=alias
))


@on_command(__plugin_name__, aliases=alias, only_to_me=False)
async def _(session: CommandSession):
    message = get_message(__plugin_name__, 'default')
    # message = "你没输入状态码诶"
    # doc = httpstats
    params = session.current_arg_text.strip()
    if not params:
        params: str = (await session.aget(prompt=get_message(__plugin_name__, 'code_prompt'))).strip()
        # params: str = (await session.aget(prompt="请发送你想要查询的状态码")).strip()

    if params:
        search = params.strip()
        stat = h.httpstats(search)
        if not stat:
            message = get_message(__plugin_name__, 'code_not_found').format(search=search)
            # message = f"查询不到 {search} 状态码代表什么意思诶"
        else:
            message = get_message(__plugin_name__, 'code_found').format(search=search, stat=stat, image=f"[CQ:image,file=https://http.cat/{search}]")
            # message = f"状态码 {search} 的意思是: {stat}\n[CQ:image,file=https://http.cat/{search}]"

    await send_msg(session, message)