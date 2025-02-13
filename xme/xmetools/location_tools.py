from xme.xmetools.request_tools import fetch_data
from keys import WEATHER_API_KEY

async def search_location(loc: str, headers: dict = {"X-QW-Api-Key": WEATHER_API_KEY}):
    city = f"https://geoapi.qweather.com/v2/city/lookup?location={loc}"
    city_info = await fetch_data(city, headers=headers)
    if city_info["code"] != "200":
        print(city_info)
        print("ERROR")
        return False
    return city_info