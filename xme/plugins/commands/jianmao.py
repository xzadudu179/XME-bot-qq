from nonebot import CommandSession
# from xme.xmetools.debugtools import debug_msg
from nonebot.log import logger
from xme.xmetools.plugintools import on_command
from xme.xmetools.doctools import CommandDoc
from keys import JIANMAO_TOKEN, JIANMAO_QQ, generate_jwt
# import httpx
from character import get_message
from xme.xmetools.msgtools import send_session_msg
from xme.xmetools.reqtools import fetch_data_post, fetch_data
from xme.xmetools.msgtools import image_msg

API_URL="https://mrjm.fur-bot.com"
# API_URL="http://furgon.yjwmidc.com:8000"

alias = ['鉴毛', 'jianmao', 'jrjm']
__plugin_name__ = '今日鉴毛'
__plugin_usage__ = CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    usage='<期数或关键字>',
    permissions=["无"],
    alias=alias
)
async def get_jianmao_data_from_id(id: str):
    url = f"{API_URL}/furry_will/qishu"
    '''
    期数搜索为 "http://furgon.yjwmidc.com:8000/furry_will/qishu/"
    '''
    return await apost(url, params={"all": "1", "qishu": id})

async def check_health() -> bool:
    data = await aget(f"{API_URL}/health")
    logger.info(data)
    status = data['status']
    return status == "ok", data

async def apost(url, params={}):
    jwt = generate_jwt(JIANMAO_QQ, JIANMAO_TOKEN)
    logger.info(f"正在发送请求至 {url}, 请求体为 {params}")
    res =  await fetch_data_post(url, json={"token": jwt, "qq": JIANMAO_QQ}, params=params)
    logger.info(f"请求结果：{res}")
    return res

async def aget(url):
    jwt = generate_jwt(JIANMAO_QQ, JIANMAO_TOKEN)
    logger.info(f"正在从 {url} 获取请求")
    res = await fetch_data(url=url, json={"token": jwt, "qq": JIANMAO_QQ})
    logger.info(f"请求结果：{res}")
    return res

async def get_jianmao_data_from_name(name: str):
    url = f"{API_URL}/furry_will/search"
    '''
    名称搜索为 "http://furgon.yjwmidc.com:8000/furry_will/search/" + name
    '''
    return await apost(url, params={"all": "1", "name": name})

async def get_random_jianmao_data():
    url = f"{API_URL}/furry_will/random"
    '''
    随机为 "http://furgon.yjwmidc.com:8000/furry_will/random/"
    期数搜索为 "http://furgon.yjwmidc.com:8000/furry_will/qishu/"
    名称搜索为 "http://furgon.yjwmidc.com:8000/furry_will/search/"
    '''
    return await apost(url)

async def get_jianmao_data(session, jianmao_func, **jianmao_kwargs) -> bool:
    datas = (await jianmao_func(**jianmao_kwargs))
    logger.info(datas)
    data = datas.get('data', [])
    if datas.get('status', "") == "error" or len(data) < 1:
        error = datas.get("message", datas.get("error", "未知问题"))
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'error', error=error), tips=True)
        return False
    data = data[0]
    await send_session_msg(session, await image_msg(data['url']) +  get_message("plugins", __plugin_name__, 'result', city=data['city'], type=data['race'], name=data['name']), tips=True)
    return True

@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda _: True)
async def _(session: CommandSession):
    arg = session.current_arg_text.strip()
    health, health_data = await check_health()
    if not health:
        return await send_session_msg(session, get_message("plugins", __plugin_name__, 'server_error', data=health_data))
    if arg and arg.isdigit():
        return await get_jianmao_data(session, get_jianmao_data_from_id, id=arg)
    elif arg:
        return await get_jianmao_data(session, get_jianmao_data_from_name, name=arg)
    return await get_jianmao_data(session, get_random_jianmao_data)
