import requests

def get_weather(city: str) -> dict:
    response = requests.get(f"https://restapi.amap.com/v3/weather/weatherInfo?key=4689bd09a31f3d65937db430bdae8327&city={city}&extensions=all")
    json_dict = response.json()
    return json_dict