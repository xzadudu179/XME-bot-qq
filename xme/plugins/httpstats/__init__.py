from nonebot import on_command, CommandSession
from . import httpstats as h

@on_command('httpstats', aliases=('http', 'http状态码', 'httpstatus'), only_to_me=False, permission=lambda sender: sender.is_groupchat)
async def _(session: CommandSession):
    message = "你没输入状态码诶"
    # doc = httpstats
    params = session.current_arg_text.strip()
    if not params:
        params = (await session.aget(prompt="请发送状态码哦")).strip()

    if params:
        search = params.strip()
        stat = h.httpstats(search)
        if not stat:
            message = f"查询不到 {search} 状态码代表什么意思诶"
        else:
            message = f"状态码 {search} 的意思是: {stat}\n[CQ:image,file=https://http.cat/{search}]"

    await session.send(message)