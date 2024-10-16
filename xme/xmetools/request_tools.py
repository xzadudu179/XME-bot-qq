import aiohttp
import json

async def get_weather(city: str) -> dict:
    response = fetch_data(f"https://restapi.amap.com/v3/weather/weatherInfo?key=4689bd09a31f3d65937db430bdae8327&city={city}&extensions=all")
    json_dict = json.loads(response)
    return json_dict

async def fetch_data(url):
    try:
        async with aiohttp.ClientSession() as aiosession:
            async with aiosession.get(url) as response:
                if response.status == 200:
                    data = await response.text()
                    return data
                else:
                    return None
    except Exception as e:
        print(e)
        return None
