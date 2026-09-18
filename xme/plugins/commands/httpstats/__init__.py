from nonebot import CommandSession
from xme.xmetools.plugintools import on_command
from . import httpstats as h
from xme.xmetools.msgtools import send_session_msg, aget_session_msg
from character import get_message
from xme.xmetools.doctools import CommandDoc
from xme.xmetools.reqtools import fetch_data

alias = ['http', 'http状态码']
__plugin_name__ = 'httpcode'
__plugin_usage__ = CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    # desc='查询状态码',
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    # introduction='查看指定 http 状态码和它的猫猫图',
    usage='<状态码>',
    permissions=[],
    alias=alias
)


@on_command(__plugin_name__, aliases=alias, only_to_me=False)
async def _(session: CommandSession):
    message = get_message("plugins", __plugin_name__, 'default')
    # message = "你没输入状态码诶"
    # doc = httpstats
    params = session.current_arg_text.strip()
    if not params:
        params: str = (await aget_session_msg(session, prompt=get_message("plugins", __plugin_name__, 'code_prompt'))).strip()
    # 输入校验必须早返回：不合法的输入只回提示，绝不再进入后续文案与链接拼接
    # （用户文本直接进 [CQ:image,...] 模板或消息文案会造成 CQ 注入）
    if not params.isdecimal():
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'content_not_decimal'), tips=True, tips_percent=20)
        return
    if len(params) > 5:
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'content_too_long'), tips=True, tips_percent=20)
        return
    search = params.strip()
    stat = ": " + x if (x:=h.httpstats(search)) else ""
    cat_image = await fetch_data(f"https://http.cat/{search}", "byte")
    image_404 = await fetch_data("https://http.cat/404", "byte")
    image_is_404 = cat_image == image_404
    if not stat and image_is_404 and search != "404":
        message = get_message("plugins", __plugin_name__, 'code_not_found', search=search)
        # message = f"查询不到 {search} 状态码代表什么意思诶"
    else:
        message = get_message("plugins", __plugin_name__, 'code_found', search=search, stat=stat, image=f"[CQ:image,file=https://http.cat/{search}]")
        # message = f"状态码 {search} 的意思是: {stat}\n[CQ:image,file=https://http.cat/{search}]"

    await send_session_msg(session, message, tips=True, tips_percent=20)