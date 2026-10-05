from aiohttp import ClientResponseError

from xme.xmetools.reqtools import fetch_data
from character import get_message
from keys import WEATHER_API_KEY
# import config
from xme.plugins.commands.xme_user.classes.user import try_load, User
from xme.xmetools.debugtools import debug_msg
# from nonebot.log import logger
# from xme.xmetools.jsontools import read_from_path, save_to_path

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
    cannot_search = False
    try:
        city_info = await fetch_data(city, headers=headers)
    except ClientResponseError:
        cannot_search = True
    if city_info.get("code", "") != "200" or cannot_search:
        debug_msg(city_info)
        debug_msg("无法搜索")
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
    # data = read_from_path(config.BOT_SETTINGS_PATH)
    user_location_info = None
    user = try_load(user_id)
    if isinstance(user, User):
        user_location_info = user.plugin_datas.get("location", None)
    # user_location_info = data["locations"].get(str(user_id), None)
    locations = []
    if location_text:
        debug_msg("搜索城市中...")
        search = await search_location(location_text, dict_output=True)
        locations = search.get("location", [])
    else:
        locations = [user_location_info]
    return locations, user_location_info


# 直辖市/港澳的省份即自身简称；键名与外部数据源的城市写法保持一致
CITY_PROVINCE: dict[str, str] = {
    # 直辖市 / 港澳台
    "北京": "北京", "天津": "天津", "上海": "上海", "重庆": "重庆",
    "香港特别行政区": "香港", "澳门": "澳门",
    "台北": "台湾", "新北": "台湾", "板桥": "台湾", "南港": "台湾", "桃園": "台湾",
    "台中": "台湾", "台南": "台湾", "高雄": "台湾", "新竹": "台湾", "苗栗": "台湾",
    "南投": "台湾", "彰化": "台湾", "嘉义": "台湾", "屏东": "台湾", "宜兰": "台湾",
    "花莲": "台湾", "台东": "台湾", "基隆": "台湾",
    # 河北
    "石家庄": "河北", "唐山": "河北", "保定": "河北", "秦皇岛": "河北", "邯郸": "河北",
    "邢台": "河北", "张家口": "河北", "承德": "河北", "沧州": "河北", "廊坊": "河北",
    "衡水": "河北",
    # 山西
    "太原": "山西", "大同": "山西", "晋中": "山西", "临汾": "山西", "运城": "山西",
    "长治": "山西",
    # 内蒙古
    "呼和浩特": "内蒙古", "鄂尔多斯": "内蒙古", "包头": "内蒙古", "赤峰": "内蒙古",
    "通辽": "内蒙古",
    # 辽宁
    "沈阳": "辽宁", "大连": "辽宁", "鞍山": "辽宁", "抚顺": "辽宁", "锦州": "辽宁",
    "营口": "辽宁", "盘锦": "辽宁",
    # 吉林
    "长春": "吉林", "延边": "吉林", "白山市": "吉林", "吉林": "吉林", "四平": "吉林",
    "通化": "吉林", "松原": "吉林",
    # 黑龙江
    "哈尔滨": "黑龙江", "大庆": "黑龙江", "齐齐哈尔": "黑龙江", "牡丹江": "黑龙江",
    # 江苏
    "南京": "江苏", "苏州": "江苏", "无锡": "江苏", "淮安": "江苏", "徐州": "江苏",
    "常州": "江苏", "扬州": "江苏", "南通": "江苏", "镇江": "江苏", "盐城": "江苏",
    "泰州": "江苏", "连云港": "江苏", "宿迁": "江苏",
    # 浙江
    "杭州": "浙江", "宁波": "浙江", "温州": "浙江", "嘉兴": "浙江", "台州": "浙江",
    "绍兴": "浙江", "金华": "浙江", "湖州": "浙江", "丽水": "浙江", "衢州": "浙江",
    "舟山": "浙江", "义乌": "浙江",
    # 安徽
    "合肥": "安徽", "芜湖": "安徽", "蚌埠": "安徽", "马鞍山": "安徽", "安庆": "安徽",
    "黄山": "安徽", "阜阳": "安徽",
    # 福建
    "福州": "福建", "厦门": "福建", "泉州": "福建", "漳州": "福建", "宁德": "福建",
    "莆田": "福建",
    # 江西
    "南昌": "江西", "宜春": "江西", "赣州": "江西", "九江": "江西", "上饶": "江西",
    "吉安": "江西",
    # 山东
    "济南": "山东", "青岛": "山东", "淄博": "山东", "济宁": "山东", "滨州": "山东",
    "枣庄": "山东", "东营": "山东", "烟台": "山东", "威海": "山东", "潍坊": "山东",
    "临沂": "山东", "泰安": "山东", "日照": "山东", "菏泽": "山东", "德州": "山东",
    "聊城": "山东",
    # 河南
    "郑州": "河南", "洛阳": "河南", "开封": "河南", "新乡": "河南", "焦作": "河南",
    "南阳": "河南", "许昌": "河南", "安阳": "河南", "商丘": "河南", "信阳": "河南",
    "周口": "河南",
    # 湖北
    "武汉": "湖北", "鄂州": "湖北", "宜昌": "湖北", "襄阳": "湖北", "荆州": "湖北",
    "黄石": "湖北", "十堰": "湖北", "孝感": "湖北", "黄冈": "湖北",
    # 湖南
    "长沙": "湖南", "株洲": "湖南", "湘潭": "湖南", "岳阳": "湖南", "衡阳": "湖南",
    "常德": "湖南", "郴州": "湖南", "张家界": "湖南",
    # 广东
    "广州": "广东", "佛山": "广东", "深圳": "广东", "东莞": "广东", "惠州": "广东",
    "揭阳": "广东", "珠海": "广东", "中山": "广东", "汕头": "广东", "江门": "广东",
    "湛江": "广东", "肇庆": "广东", "韶关": "广东", "清远": "广东", "潮州": "广东",
    # 广西
    "南宁": "广西", "北海": "广西", "桂林": "广西", "柳州": "广西", "玉林": "广西",
    # 海南
    "海口": "海南", "三亚": "海南",
    # 四川
    "成都": "四川", "绵阳": "四川", "泸州": "四川", "自贡": "四川", "宜宾": "四川",
    "德阳": "四川", "南充": "四川", "乐山": "四川", "达州": "四川",
    # 贵州
    "贵阳": "贵州", "黔东南苗族侗族自治州": "贵州", "凯里": "贵州", "遵义": "贵州",
    "安顺": "贵州",
    # 云南
    "昆明": "云南", "丽江": "云南", "大理": "云南", "曲靖": "云南", "西双版纳": "云南",
    # 西藏
    "拉萨": "西藏",
    # 陕西
    "西安": "陕西", "汉中": "陕西", "咸阳": "陕西", "宝鸡": "陕西", "渭南": "陕西",
    "延安": "陕西",
    # 甘肃
    "兰州": "甘肃", "天水": "甘肃", "酒泉": "甘肃",
    # 青海
    "西宁": "青海",
    # 宁夏
    "银川": "宁夏",
    # 新疆
    "乌鲁木齐": "新疆", "喀什": "新疆", "伊犁": "新疆",
}

# 行政区划后缀，长后缀在前避免截半
_SUFFIXES = ("维吾尔自治区", "壮族自治区", "回族自治区", "特别行政区", "自治区",
             "朝鲜族自治州", "苗族侗族自治州", "自治州", "省", "市")


def short_region(name: str) -> str:
    """行政区划名转常用简称（江苏省→江苏、内蒙古自治区→内蒙古、北京市→北京）。"""
    for suffix in _SUFFIXES:
        if name.endswith(suffix) and len(name) > len(suffix):
            return name[:-len(suffix)]
    return name


def derive_province(region: str) -> str:
    """由城市级地区名推导省份简称（如 南京→江苏、香港特别行政区→香港）。

    直辖市/港澳返回自身简称；未知城市返回空串，调用方需容忍缺失。
    """
    if not region:
        return ""
    if region in CITY_PROVINCE:
        return CITY_PROVINCE[region]
    if region.endswith("市"):
        return CITY_PROVINCE.get(region[:-1], "")
    return ""