import aiohttp
import json


async def get_weather(city: str) -> dict:
    response = await fetch_data(
        f"https://restapi.amap.com/v3/weather/weatherInfo?key=4689bd09a31f3d65937db430bdae8327&city={city}"
        f"&extensions=all")
    json_dict = json.loads(response)
    return json_dict


async def fetch_data_post(url, **params):
    try:
        async with aiohttp.ClientSession() as aiosession:
            async with aiosession.post(url, json=params) as response:
                data = await response.json()
                return data
    except Exception as e:
        print(e)
        return None


async def fetch_data(url):
    try:
        async with aiohttp.ClientSession() as aiosession:
            async with aiosession.get(url) as response:
                data = await response.text()
                return data
    except Exception as e:
        print(e)
        return None
