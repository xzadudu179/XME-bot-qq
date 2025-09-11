from xme.xmetools.reqtools import fetch_data
from character import get_message
from keys import WEATHER_API_KEY
import config
from xme.xmetools.jsontools import read_from_path, save_to_path

async def search_location(loc: str, headers: dict = {"X-QW-Api-Key": WEATHER_API_KEY}, dict_output=True) -> dict | str:
    """搜索地点

    Args:
        loc (str): 地点关键字
        headers (dict, optional): 请求用 Headers. Defaults to {"X-QW-Api-Key": WEATHER_API_KEY}.
        dict_output (bool, optional): 始终输出字典格式. Defaults to True.

    Returns:
        dict | str: 搜索结果
    """
    city = f"https://mb3h2ky7r9.re.qweatherapi.com/geo/v2/city/lookup?location={loc}"
    city_info = await fetch_data(city, headers=headers)
    if city_info.get("code", "") != "200":
        print(city_info)
        print("无法搜索")
        if dict_output:
            return city_info
        return get_message("apis", "search_location_error", code=city_info.get('code', '未知'), msg=city_info.get('detail', '未知'))
    return city_info


async def get_user_location(user_id, location_text="") -> tuple[list[dict], dict | None]:
    """获取用户搜索的位置

    Args:
        user_id (int | str): 用户 id
        location_text (str): 用户搜索的位置. Defaults to "".

    Returns:
        tuple[list[dict], dict]: 搜索到的位置，用户位置
    """
    data = read_from_path(config.BOT_SETTINGS_PATH)
    user_location_info = data["locations"].get(str(user_id), None)
    locations = []
    if location_text:
        print("搜索城市中...")
        search = await search_location(location_text, dict_output=True)
        locations = search.get("location", [])
    else:
        locations = [user_location_info]
    return locations, user_location_info