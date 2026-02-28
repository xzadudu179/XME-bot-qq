from nonebot import CommandSession
# from xme.xmetools.debugtools import debug_msg
from nonebot.log import logger
from xme.xmetools.plugintools import on_command
from xme.xmetools.doctools import CommandDoc
from keys import JIANMAO_TOKEN, JIANMAO_QQ, generate_jwt
import httpx
from character import get_message
from xme.xmetools.msgtools import send_session_msg
from xme.xmetools.msgtools import image_msg

API_URL="http://8.141.27.115:8000"
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
async def get_jianmao_data_from_id(token: str, qq: str, id: str):
    url = f"{API_URL}/furry_will/qishu/{id}"
    '''
    期数搜索为 "http://furgon.yjwmidc.com:8000/furry_will/qishu/" + 期数id
    '''
    return await aget(token, qq, url)


async def aget(token: str, qq: str, url):
    payload = {
        "token": token,
        "qq": qq
    }
    async with httpx.AsyncClient(trust_env=False) as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()  # 检查 HTTP 状态码
            return response.json()  # 解析 JSON 响应
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e}")
            return {"error": f"HTTP 错误: {e}"}
        except httpx.RequestError as e:
            try:
                code = response.status_code
            except Exception:
                code = "未知"
            logger.error(f"Request error occurred: {e}")
            return {"error": f"请求出现错误: {e}\ncode:{code}"}
        except ValueError as e:
            logger.error(f"JSON decode error occurred: {e}")
            return {"error": f"无效的 JSON response: {e}"}

async def get_jianmao_data_from_name(token: str, qq: str, name: str):
    url = f"{API_URL}/furry_will/name/{name}"
    '''
    名称搜索为 "http://furgon.yjwmidc.com:8000/furry_will/name/" + name
    '''
    return await aget(token, qq, url)

async def get_random_jianmao_data(token: str, qq: str):
    url = f"{API_URL}/furry_will/random/"
    '''
    随机为 "http://furgon.yjwmidc.com:8000/furry_will/random/"
    期数搜索为 "http://furgon.yjwmidc.com:8000/furry_will/qishu/" + 期数id
    名称搜索为 "http://furgon.yjwmidc.com:8000/furry_will/name/" + 关键字
    '''
    return await aget(token, qq, url)

async def get_jianmao_data(session, jianmao_func, **jianmao_kwargs) -> bool:
    jwt = generate_jwt(JIANMAO_QQ, JIANMAO_TOKEN)
    datas = (await jianmao_func(jwt, JIANMAO_QQ, **jianmao_kwargs))
    logger.info(datas)
    data = datas.get('data', [])
    if datas.get('status', "") == "error" or len(data) < 1:
        error = datas.get("message", datas.get("error", "未知问题"))
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'error', error=error), tips=True)
        return False
    data = data[0]
    await send_session_msg(session, await image_msg(data['url']) +  get_message("plugins", __plugin_name__, 'result', city=data['city'], type=data['zhongzu'], name=data['name']), tips=True)
    return True

@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda _: True)
async def _(session: CommandSession):
    arg = session.current_arg_text.strip()
    if arg and arg.isdigit():
        return await get_jianmao_data(session, get_jianmao_data_from_id, id=arg)
    elif arg:
        return await get_jianmao_data(session, get_jianmao_data_from_name, name=arg)
    return await get_jianmao_data(session, get_random_jianmao_data)
