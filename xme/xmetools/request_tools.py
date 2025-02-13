import aiohttp
import json

async def get_weather(city: str) -> dict:
    response = await fetch_data(f"https://restapi.amap.com/v3/weather/weatherInfo?key=4689bd09a31f3d65937db430bdae8327&city={city}&extensions=all")
    json_dict = json.loads(response)
    return json_dict

async def fetch_data_post(url, params, *args, **kwargs):
    try:
        async with aiohttp.ClientSession() as aiosession:
            async with aiosession.post(url, *args, **kwargs, json=params) as response:
                data = await response.json()
                return data
    except Exception as e:
        print(e)
        return None

async def fetch_data(url, response_type="json", *args, **kwargs):
    async with aiohttp.ClientSession() as aiosession:
        async with aiosession.get(url, *args, **kwargs) as response:
            match response_type:
                case "json":
                    data = await response.json()
                case "text":
                    data = await response.text()
                case _:
                    raise ValueError("返回类型只能是 json 或 text")
            return data