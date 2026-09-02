import functools

import aiohttp
# import asyncio
import json
# from xme.xmetools.debugtools import debug_msg
from keys import GLM_API_KEY
from nonebot.log import logger


async def get_weather(city: str) -> dict:
    response = await fetch_data(f"https://restapi.amap.com/v3/weather/weatherInfo?key=***&city={city}&extensions=all")
    # print(response)
    json_dict = json.loads(response)
    return json_dict

async def fetch_data_post(url, json, *args, **kwargs):
    try:
        async with aiohttp.ClientSession() as aiosession:
            async with aiosession.post(url, *args, **kwargs, json=json) as response:
                data = await response.json()
                return data
    except Exception as e:
        logger.exception(e)
        raise

@functools.lru_cache(maxsize=1)
def glm_headers() -> dict:
    """GLM 开放平台请求头（Bearer 认证）。缓存避免每次重复构造。"""
    return {
        "Authorization": f"Bearer {GLM_API_KEY}",
        "Content-Type": "application/json",
    }


async def glm_api_request(path: str, method: str = "POST", **payload) -> dict:
    """调用智谱(GLM) 开放平台接口，统一处理 base url、认证头与 request_id。

    之后新增 GLM 工具接口（网页搜索、文件、知识库等）只需调用本函数并传入 path 与参数：
        result = await glm_api_request("/paas/v4/reader", url="https://...")
    失败时会抛出异常。
    """
    from xme.plugins.commands.ai_helper.functions import GLM_API_BASE
    import uuid
    url = GLM_API_BASE + path
    headers = glm_headers()
    if method.upper() == "GET":
        return await fetch_data(url, response_type="json", headers=headers, params=payload)
    body = dict(payload)
    body["request_id"] = body.get("request_id", str(uuid.uuid4()))
    return await fetch_data_post(url, json=body, headers=headers)

async def fetch_data(url, response_type="json", **args):
    async with aiohttp.ClientSession() as aiosession:
        async with aiosession.get(url, **args) as response:
            response.raise_for_status()
            match response_type:
                case "json":
                    data = await response.json()

                case "text":
                    data = await response.text()

                case "byte":
                    data = await response.read()
                case _:
                    raise ValueError(
                        "返回类型只能是 json, byte 或 text"
                    )
            return data