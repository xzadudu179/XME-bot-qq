from xme.xmetools.request_tools import fetch_data
from character import get_message
from keys import WEATHER_API_KEY

async def search_location(loc: str, headers: dict = {"X-QW-Api-Key": WEATHER_API_KEY}, dict_output=True):
    city = f"https://geoapi.qweather.com/v2/city/lookup?location={loc}"
    city_info = await fetch_data(city, headers=headers)
    if city_info.get("code", "") != "200":
        print(city_info)
        print("ERROR")
        if dict_output:
            return city_info
        return get_message("apis", "search_location_error", code=city_info.get('status', '未知'), msg=city_info.get('detail', '未知'))
    return city_info