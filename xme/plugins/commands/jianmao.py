from nonebot import CommandSession
from xme.xmetools.debugtools import debug_msg
from nonebot.log import logger
from xme.xmetools.plugintools import on_command
from xme.xmetools.doctools import CommandDoc
from keys import JIANMAO_TOKEN, JIANMAO_QQ, generate_jwt
import httpx
from character import get_message
from xme.xmetools.msgtools import send_session_msg
from xme.xmetools.imgtools import image_msg

alias = ['鉴毛', 'jianmao', 'jrjm']
__plugin_name__ = '今日鉴毛'
__plugin_usage__ = CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    usage=f'',
    permissions=["无"],
    alias=alias
)

async def get_random_jianmao_data(token: str, qq: str):
    url = "http://furgon.yjwmidc.com:8000/furry_will/random/"
    '''
    随机为 "http://furgon.yjwmidc.com:8000/furry_will/random/"
    期数搜索为 "http://furgon.yjwmidc.com:8000/furry_will/qishu/" + 期数id
    名称搜索为 "http://furgon.yjwmidc.com:8000/furry_will/name/" + 关键字
    '''
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
            return {"error": f"HTTP error: {e}"}
        except httpx.RequestError as e:
            logger.error(f"Request error occurred: {e}")
            return {"error": f"Request error: {e}"}
        except ValueError as e:
            logger.error(f"JSON decode error occurred: {e}")
            return {"error": f"Invalid JSON response: {e}"}

@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda _: True)
async def _(session: CommandSession):
    data = (await get_random_jianmao_data(generate_jwt(JIANMAO_QQ, JIANMAO_TOKEN), JIANMAO_QQ)).get('data', None)[0]
    if data is None:
        return await send_session_msg(session, get_message("plugins", __plugin_name__, 'error'), tips=True)
    return await send_session_msg(session, await image_msg(data['url']) + get_message("plugins", __plugin_name__, 'result', city=data['city'], type=data['zhongzu'], name=data['name']), tips=True)