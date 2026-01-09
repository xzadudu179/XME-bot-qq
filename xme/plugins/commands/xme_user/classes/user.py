from character import get_message
coin_name = get_message("user", "coin_name")
coin_pronoun = get_message("user", "coin_pronoun")

import time
from xme.xmetools import timetools
from xme.xmetools import dicttools
from .achievements import get_achievements, has_achievement
from nonebot.session import BaseSession
from functools import wraps
from aiocqhttp import ActionFailed
import json
from xme.xmetools.msgtools import send_to_superusers
from xme.xmetools.bottools import bot_call_action
from nonebot import get_bot
from ..tools.map_tools import *
import inspect
from xme.xmetools.imgtools import hash_image
import math
from xme.xmetools.msgtools import send_session_msg
from .inventory import Inventory
from .celestial.star import Star
from .celestial.planet import Planet, PlanetType
from .xme_map import get_starfield_map, get_celestial_from_uid, get_galaxymap
from ..tools import galaxy_date_tools
from xme.xmetools.dbtools import DATABASE


def is_galaxy_loaded():
    if get_galaxymap():
        return True
    return False

# def is_galaxy_initing():
#     return galaxy_initing

class User:
    def form_dict(data: dict):
        return load_from_dict(data, id=data["user_id"])

    def get_table_name():
        return User.__name__

    async def try_spend(self, session: BaseSession, count, out_of_range_zero=False, message="", spent_message=""):
        if count < 0:
            raise ValueError(f"花费的{coin_name}不能小于 0")
        if self.coins < count:
            await send_session_msg(session, (get_message("user", "no_coin", count=count) if not message else message))
            return False
        r, spend = self.spend_coins(count, out_of_range_zero)
        if r:
            await send_session_msg(session, (get_message("user", "spent_coin", count=spend) if not spent_message else spent_message))
            return True
        return False

    async def get_coins(self, session: BaseSession, count, _get_message=""):
        count = int(count)
        if count < 0:
            raise ValueError(f"获得的{coin_name}不能小于 0")
        # if self.coins < count:
        #     await send_session_msg(session, (get_message("user", "no_coin", count=count) if not message else message))
        #     return False
        r = self.add_coins(count)
        if r:
            await send_session_msg(session, (get_message("user", "get_coin", count=count) if not _get_message else _get_message))
            return True
        return False

    def __init__(
            self,
            user_id: int,
            id: int = -1,
            coins: int = 0,
            inventory: Inventory = Inventory(),
            talked_to_bot: list = [],
            desc: str = "",
            celestial_uid=None,
            xme_favorability=0,
            counters: dict = {},
            # timers: dict = {},
            plugin_datas = {}, # 插件数据，比如 weather 保存用户位置之类的
            achievements: list = [],
            ai_history: list[dict] = [],
            gen_starfield = True,
        ):
        self.db_id = id
        self.id = user_id
        self.desc = desc
        self.inventory = inventory
        self.coins = coins
        self.xme_favorability = xme_favorability
        self.talked_to_bot = talked_to_bot
        self.counters = counters
        self.plugin_datas: dict = plugin_datas
        # self.timers = timers
        # 注册时间
        datas = self.plugin_datas.get("datas", {})
        reg_time = datas.get("register_time", -1)
        if reg_time == -1:
            self.plugin_datas["datas"]["register_time"] = time.time()
        self.achievements = achievements
        self.ai_history = ai_history
        # print(self.ai_history)
        # 用户所在天体
        # print("dbid", self.db_id)
        self.celestial_uid = celestial_uid
        self.celestial = None
        if not gen_starfield:
            return
        # if celestial_uid is not None:

        # if self.celestial is None:
        #     self.gen_celestial()
        # if self.celestial is not None:
        #     starfield = self.get_starfield()
        #     if starfield is None:
        #         print("用户星域坐标无效")
        #         self.celestial = None
        #         self.gen_celestial()

    def get_celestial(self):
        # print("uid:", self.celestial_uid)
        if self.celestial_uid is not None:
            self.celestial = get_celestial_from_uid(self.celestial_uid)
        # print("uid:", self.celestial_uid)
        if self.celestial is None:
            self.gen_celestial()
        return self.celestial

    def get_starfield(self):
        return get_starfield_map(self.get_celestial().galaxy_location)

    def get_achievement(self, achievement_name) -> dict | bool:
        # print("achievement_name:", achievement_name)
        achi = get_achievements().get(achievement_name, False)
        if not achi:
            raise ValueError(f"无该成就名 \"{achievement_name}\"")
        for a in self.achievements:
            if achievement_name in a["name"]:
                return a
        return None

    async def achieve_achievement(self, session: BaseSession, achievement_name: str, achievement_message: str | None = None):
        """达成成就

        Args:
            user (User): 用户
            achievement_name (str): 成就名
        """
        achi = get_achievements().get(achievement_name, False)
        if not achi:
            raise ValueError(f"无该成就名 \"{achievement_name}\"")
        if achievement_name in [a["name"] for a in self.achievements]:
            # 已经有成就就不管了
            print("已达成成就，不执行")
            return
        self.achievements.append({
            "name": achievement_name,
            "achieve_time": timetools.get_time_now(),
            "from": str(session.event.group_id) if session.event.group_id is not None else "私聊"
        })
        self.add_coins(achi["award"])
        if achievement_message is None:
            if not achi["hidden"]:
                achievement_message = get_message("config", "achievement_message", achievement=achievement_name, award=achi["award"])
            else:
                achievement_message = get_message("config", "hidden_achievement_message", achievement=achievement_name, award=achi["award"])
        try:
            await send_to_superusers(session.bot, f"用户 {(await session.bot.api.get_stranger_info(user_id=self.id))['nickname']} ({self.id}) 在 {(await get_bot().api.get_group_info(group_id=session.event.group_id))['group_name']} 得到了一个成就 \"{achievement_name}\"")
        except ActionFailed:
            pass
        if self.id != -1:
            print("更新database")
            rows = DATABASE.update_db(obj=self, id=self.db_id, coins=self.coins, achievements=json.dumps(self.achievements, ensure_ascii=False))
            print("受影响的行数:", rows)
        sent = False
        while not sent:
            try:
                await send_session_msg(session, achievement_message)
                sent = True
            except ActionFailed:
                continue

    def gen_celestial(self):
        """随机获取出生星体
        """
        map = get_galaxymap()
        if not map:
            print("地图未生成")
            return
        choice_celestials = []
        print("随机生成出生星体中")
        # print("USERRRRRRRRRRRRRRR", map.starfields)
        for starfield in map.starfields.values():
            if starfield.calc_faction().id != 1:
                continue
            for c in starfield.celestials.values():
                if isinstance(c, Star):
                    continue
                if isinstance(c, Planet):
                    if c.planet_type not in [
                        PlanetType.CITY,
                        PlanetType.DESOLATE,
                        PlanetType.DRY,
                        PlanetType.SEA,
                        PlanetType.TERRESTRIAL,
                    ]:
                        continue
                choice_celestials.append(c)
        if choice_celestials:
            self.celestial = random.choice(choice_celestials)
            # self.save()
        else:
            print("无法获取到合适的行星")

    def __str__(self):
        try:
            # last_sign_time = time_tools.int_to_days(int(self.counters['sign']["time"]))
            last_sign_time = galaxy_date_tools.get_galaxy_date(int(timetools.get_valuetime(self.counters['sign']["time"], timetools.TimeUnit.DAY)))
            sign_message = get_message("user", "sign_message", last_sign_time="星历" + last_sign_time)
        except:
            sign_message = get_message("user", "no_sign")
        _, rank_ratio, _ = get_user_rank(self.id)
        return get_message("user", "user_info_str",
            id=str(self.id),
            coins_count=self.coins,
            achievements_count=len([a for a in self.achievements if has_achievement(a.get("name", ""))]),
            get_achievements_total=len(get_achievements().items()),
            sign_message=sign_message,
            rank_ratio=f"{rank_ratio:.2f}",
            space=self.inventory.get_space_left(),
            desc=self.desc + "\n----------\n" if self.desc else ""
        )

    def add_favorability(self, count):
        """增加好感度

        Args:
            count (int): 好感度值，可为负数
        """
        if self.xme_favorability + count > 100:
            self.xme_favorability = 100
        elif self.xme_favorability + count < -100:
            self.xme_favorability = -100
        else:
            self.xme_favorability += count

    def get_custom_setting(self, *keys, default="default"):
        return dicttools.get_value("custom", *keys, search_dict=self.plugin_datas, default=default)

    def spend_coins(self, amount: int, out_of_range_zero: bool= False) -> tuple[bool, int]:
        """尝试花费星币

        Args:
            amount (int): 花费数量
            out_of_range_zero (bool, optional): 是否如果付不起，就归零. Defaults to False.

        Returns:
            tuple[bool, int]: 是否花费成功, 当前剩余星币
        """
        # out of range zero 如果付不起就算扣到 0
        amount = int(amount)
        if amount > self.coins and not out_of_range_zero:
            return (False, 0)
        coins_now = self.coins
        self.coins -= amount
        if self.coins < 0:
            self.coins = 0
        return (True, coins_now - self.coins)

    def to_dict(self) -> dict:
        return {
            "id": self.db_id,
            "user_id": self.id,
            "coins": self.coins,
            "counters": self.counters,
            # "timers": self.timers,
            "xme_favorability": self.xme_favorability,
            "desc": self.desc,
            "plugin_datas": self.plugin_datas,
            "inventory": self.inventory.__list__(),
            "talked_to_bot": self.talked_to_bot,
            "achievements": self.achievements,
            "celestial": self.celestial.uid if self.celestial else "",
            "ai_history": self.ai_history,
        }

    def __dict__(self):
        return self.to_dict()

    def add_coins(self, amount: int) -> bool:
        amount = int(amount)
        print("amount", amount)
        if amount < 0:
            return False
        self.coins += amount
        return True

    def exec_query(query, params=(), dict_data=True):
        # DATABASE.create_class_table(User(0))
        return DATABASE.exec_query(query=query, params=params, dict_data=dict_data)

    @staticmethod
    def get_users() -> list[dict]:
        # return jsontools.read_from_path(config.USER_PATH)['users']
        return [load_dict_user(u) for u in User.exec_query(f"SELECT * FROM {User.get_table_name()}")]

    @staticmethod
    def load(id: int, create_default_user=True):
        c = DATABASE.load_class(select_keys=(id,), query='SELECT * FROM {table_name} WHERE user_id = ?', cl=User)
        if c is None and create_default_user:
            print("创建一个新用户")
            return User(user_id=id)
        return c

    def save(self):
        self.db_id = DATABASE.save_to_db(obj=self)

    async def draw_user_galaxy_map(self, img_zoom=2, zoom_fac=1, padding=100, background_color="black", ui_zoom_fac=2, line_width=1, grid_color='#102735'):
        celestial = self.get_celestial()
        # if not self.celestial:
        #     center = (0, 0)
        center = celestial.galaxy_location
        # center = (0, 0)
        if not get_galaxymap():
            return None
        map_size = get_galaxymap().max_size
        map_img = get_galaxymap().draw_galaxy_map(img_zoom=img_zoom, center=center, zoom_fac=zoom_fac, padding=padding, background_color=background_color, line_width=line_width, grid_color=grid_color)
        return await self.draw_user_map(map_size=map_size, img_zoom=img_zoom, map_img=map_img, center=center, location=center, zoom_fac=zoom_fac, ui_zoom_fac=ui_zoom_fac, padding=padding, line_width=line_width)


    async def draw_user_map(self, map_size, img_zoom, map_img, location, center=(0, 0), zoom_fac=1, ui_zoom_fac=2, padding=100, line_width=1, font_size=12) -> str:
        # map_img = galaxy_map.draw_galaxy_map(center, zoom_fac, ui_zoom_fac, padding, background_color, line_width, grid_color)
        # font_size = 12
        width, height = map_img.size
        map_width, map_height = map_size
        text_draw = ImageDraw.Draw(map_img)
        user_name = (await get_bot().api.get_stranger_info(user_id=self.id))['nickname']
        text = f'[HIUN 星图终端]\n[用户] {user_name}\n你在: {center}  缩放倍率: {zoom_fac}x | {ui_zoom_fac}x'
        draw_text_on_image(text_draw, text, (int(15 * ui_zoom_fac), int(height - 40 * ui_zoom_fac - font_size * (text.count('\n') + 1) * ui_zoom_fac)), int(font_size * ui_zoom_fac), 'white', spacing=10)
        # draw_text_on_image(draw, 'Test File HIUN\nYesyt', (15, 1080 - font_size), font_size, 'white')
        # 绘制圆加十字
        zoom_width, zoom_height = map_width // zoom_fac // 2, map_height // zoom_fac // 2
        append_ = (((-center[0] + zoom_width) * zoom_fac), (-center[1] + zoom_height) * zoom_fac)
        point_to_draw = (int(location[0] * zoom_fac + padding + append_[0]) * img_zoom, int(location[1] * zoom_fac + padding + append_[1]) * img_zoom)
        # print("user", point_to_draw, zoom_fac, img_zoom, padding, append_)
        mark_point(text_draw, point_to_draw, location, 0, 'cyan', int(line_width * ui_zoom_fac), int(10 * ui_zoom_fac),f'{user_name} (你)', int(font_size * ui_zoom_fac), text_offset=(0, 24))
        # 保存图片
        path = f'data/images/temp/{hash_image(map_img)}.png'
        map_img.save(path)
        return path

        # 显示图片
        # map_img.show()

DATABASE.create_class_table(User(0))

def try_load(id):
    u = User.load(id)
    if u is None:
        print("USER IS NONE")
        u = User(id)
    return u

def verify_counters(user: User, name: str):
    if not name in user.counters or type(user.counters[name]) != dict:
        user.counters[name] = {}
        user.save()
    user.counters[name].setdefault("time", 0)
    user.counters[name].setdefault("count", 0)


def reset_limit(user: User, name: str, floor_float: bool = True,
                count_add=False):
    """重置限制时间和数量

    Args:
        user (User): 用户
        name (str): 时间限制名
        unit (time_tools.TimeUnit, optional): 时间单位. Defaults to time_tools.TimeUnit.DAY.
        floor_float (bool, optional): 是否向下取整. Defaults to True.
    """
    time_now = timetools.timenow()
    time_now = time_now if not floor_float else math.floor(time_now)
    user.counters[name]["time"] = time_now
    if user.counters[name]["count"] != 0:
        user.counters[name]["count"] = 0
    if count_add:
        user.counters[name]["count"] += 1
    # user.save()


def limit_count_tick(user: User, name: str, count=1):
    """增加默认1次计数器计数

    Args:
        user (User): 用户
        name (str): 时间限制名
        count (int): 次数. Defaults to 1.
    """
    user.counters[name]["count"] += count
    # user.save()

def get_user_rank(user):
    """获取指定用户 id 的金币排名百分比以及数量和位置

    Args:
        user (int): 用户 id

    Returns:
        tuple: 金币数量, 排名比例
    """
    rank_items = get_rank('coins', excluding_zero=True)
    sender_coins_count = None
    sender_index = None
    for index, item in enumerate(rank_items):
        if int(item[0]) != user: continue
        print("匹配到了")
        sender_coins_count = item[1]
        sender_index = index
    rank_ratio = 0
    if sender_coins_count is not None:
        rank_ratio = (len(rank_items[sender_index:]) - 1)/ (len(rank_items) - 1) * 100 if len(rank_items[sender_index:]) > 1 else 100
    return sender_coins_count, rank_ratio, sender_index


def validate_limit(user: User, name: str, limit: float | int, count_limit: int = 1,
                   unit: timetools.TimeUnit = timetools.TimeUnit.DAY, floor_float: bool = True) -> tuple[bool, bool]:
    """是否在时间 / 数量限制内，如果找不到时间限制名则创建

    Args:
        user (User): 用户
        name (str): 时间限制名
        limit (float | int): 限制时间
        count_limit: 限制时间内限制次数 Defaults to 1.
        unit (date_tools.TimeUnit, optional): 时间单位. Defaults to date_tools.TimeUnit.DAY.
        floor_float (bool, optional): 是否向下取整. Defaults to True.

    Returns:
        bool: 是否在限制内
    """
    verify_counters(user, name)

    time_now = timetools.get_valuetime(timetools.timenow(), unit)
    time_now = time_now if not floor_float else math.floor(time_now)
    # True 禁止继续使用指令 因为已受到限制
    time_limit, c_limit = False, False
    # print(time_now)
    # print(user.counters[name]["time"])
    # print(timetools.get_valuetime(user.counters[name]["time"], unit))
    # print(limit)
    if time_now - timetools.get_valuetime(user.counters[name]["time"], unit) < limit:
        print("时间受限制")
        time_limit = True
    else:
        print("时间过了 刷新")
        reset_limit(user, name, floor_float)
        return False
        # return (True, True)
    if user.counters[name]["count"] >= count_limit:
        print("次数受限制")
        c_limit = True
    if time_limit and c_limit:
        # reset_limit(user, name, unit, floor_float)
        return True

    else:
        return False
    #     reset_limit(user, name, unit, floor_float)


def get_limit_info(user, name):
    """返回限制情况

    Args:
        user (User): 用户
        name (str): 时间限制名

    Returns:
        tuple(int | float, int): (当前记录时间, 当前记录次数)
    """
    return (user.counters[name]["time"], user.counters[name]["count"])


def get_rank(*rank_item_key, key=None, excluding_zero=False):
    """获取用户某项内容排名

    Args:
        key (Callable[_T, SupportsRichComparison], optional): 排名方法. Defaults to None.

    Returns:
        list[tuple]: 用户: 键对应值
    """
    rank = {}
    # users: dict = jsontools.read_from_path(config.USER_PATH)['users']
    users = User.get_users()
    for v in users:
        # print(f"item: {v}")
        value = dicttools.get_value(*rank_item_key, search_dict=v)
        if value == None: continue
        rank[v["user_id"]] = value
    if excluding_zero:
        rank_values = [r for r in rank.items() if r[1] > 0]
    else:
        rank_values = [r for r in rank.items()]
    # print(rank_values)
    rank_values.sort(reverse=True, key=lambda x: key(x[1]) if key else x[1])
    # print(rank)
    return rank_values


def limit(limit_name: str,
          limit: float | int,
          limit_message: str,
          count_limit: int = 1,
          unit: timetools.TimeUnit = timetools.TimeUnit.DAY,
          floor_float: bool = True,
          fails=lambda x: x == False,
          limit_func=None, ):
    """对函数进行限制时间内只能执行数次

    Args:
        limit_name (str): 限制名
        limit (float | int): 多少时间单位后刷新限制
        limit_message (str): 限制时返回的消息
        count_limit (int, optional): 时间内限制次数. Defaults to 1.
        unit (time_tools.TimeUnit, optional): 时间单位. Defaults to time_tools.TimeUnit.DAY.
        floor_float (bool, optional): 是否向下取整时间. Defaults to True.
        fails (func, optional): 函数返回什么会被判定为失败. Defaults to lambda x: x == False.
        limit_func (func, optional): 自定义限制时返回的函数. Defaults to None.
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(session, user: User, *args, **kwargs):
            # print(user.counters)
            if validate_limit(user=user, name=limit_name, limit=limit, count_limit=count_limit, unit=unit,
                              floor_float=floor_float):
                if not limit_func:
                    return await send_session_msg(session, limit_message)
                # 有自定义函数传入情况
                elif inspect.iscoroutinefunction(limit_func):
                    return await limit_func(func, session, user, *args, **kwargs)
                else:
                    return limit_func(func, session, user, *args, **kwargs)
            # user = try_load(session.event.user_id, User(session.event.user_id))
            # print(user.counters)
            result = await func(session, user, *args, **kwargs)
            # print(f"result: {result}")
            if not fails(result):
                print("保存用户数据, 增加计数")
                print("coins", user.coins)
                limit_count_tick(user, limit_name)
                user.save()
            if isinstance(result, str):
                await send_session_msg(session, result)
            return result

        return wrapper

    return decorator

def custom_limit(limit_name: str,
          limit: float | int,
          count_limit: int = 1,
          unit: timetools.TimeUnit = timetools.TimeUnit.DAY,
          floor_float: bool = True,):
    """对函数进行限制时间内只能执行数次，其中判断限制和增加计数由函数自己决定

    Args:
        limit_name (str): 限制名
        limit (float | int): 多少时间单位后刷新限制
        limit_message (str): 限制时返回的消息
        count_limit (int, optional): 时间内限制次数. Defaults to 1.
        unit (time_tools.TimeUnit, optional): 时间单位. Defaults to time_tools.TimeUnit.DAY.
        floor_float (bool, optional): 是否向下取整时间. Defaults to True.
        limit_func (func, optional): 自定义限制时返回的函数. Defaults to None.
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(session, user: User, *args, **kwargs):
            # print(user.counters)
            def count_tick():
                print("保存用户数据, 增加计数")
                limit_count_tick(user, limit_name)
                user.save()
            def validate():
                if validate_limit(user=user, name=limit_name, limit=limit, count_limit=count_limit, unit=unit,
                              floor_float=floor_float):
                    # 已受限
                    print("受到限制")
                    return True
                # 未受限
                print("无限制")
                return False
            # user = try_load(session.event.user_id, User(session.event.user_id))
            # print(user.counters)
            result = await func(session, user, validate, count_tick, *args, **kwargs)
            print(f"result: {result}")
            # if not fails(result):

            # if isinstance(result, str):
            #     await send_session_msg(session, result)
            return result

        return wrapper

    return decorator



def using_user(save_data=False, id=0):
    def decorator(func):
        @wraps(func)
        async def wrapper(session, *args, **kwargs):
            user_id = id
            if not id:
                user_id = session.event.user_id
            print(user_id)
            user = try_load(user_id)
            result = await func(session, user, *args, **kwargs)
            # print(f"result: {result}")
            if save_data and result != False:
                print("保存用户数据中")
                user.save()
            return result

        return wrapper

    return decorator

def load_dict_user(data: dict):
    inventory_data = None
    # print(celestial)
    plugin_datas = {}
    counters = {}
    ai_history = []
    achievements = []
    talked_to_bot = []
    try:
        inventory_data = json.loads(data.get('inventory', None))
        plugin_datas = json.loads(data.get('plugin_datas', "{}"))
        counters = json.loads(data.get('counters', "{}"))
        ai_history = json.loads(data.get('ai_history', "[]"))
        achievements = data.get('achievements', "[]")
        if achievements is None:
            achievements = "[]"
        achievements = json.loads(achievements)
        talked_to_bot = json.loads(data.get('talked_to_bot', "[]"))
    except Exception as ex:
        print(f"加载用户 {data.get('user_id', '未知')} id:{data.get('id', -1)} 出错")
        raise ex
    # print(counters)
    inventory = Inventory()
    # print(inventory_data)
    if inventory_data:
        inventory = Inventory.get_inventory(inventory_data)
    # print(data)
    celestial = data.get('celestial', None)

    return {
            "id": data.get('id', -1),
            "user_id": data["user_id"],
            "coins": data.get('coins', 0),
            "counters": counters,
            "xme_favorability": data.get('xme_favorability', 0),
            "desc": data.get('desc', ""),
            "plugin_datas": plugin_datas,
            "achievements": achievements,
            "inventory": inventory,
            "talked_to_bot": talked_to_bot,
            "celestial": celestial,
            "ai_history": ai_history,
    }

def load_from_dict(data: dict, id: int) -> User:
    inventory_data = json.loads(data.get('inventory', None))
    inventory = Inventory()
    # print(inventory_data)
    if inventory_data:
        inventory = Inventory.get_inventory(inventory_data)
    # print(data)
    celestial = data.get('celestial', None)
    print("celestial", celestial)
    # print(celestial)
    counters = json.loads(data.get('counters', "{}"))
    # timers = json.loads(data.get('timers', "{}"))
    # print(counters)
    achis = data.get('achievements', "[]")
    plugin_datas = json.loads(data.get('plugin_datas', "{}"))
    if not achis:
        achis = "[]"
    user = User(
        id=data.get('id', -1),
        user_id=id,
        coins=data.get('coins', 0),
        inventory=inventory,
        talked_to_bot=json.loads(data.get('talked_to_bot', "[]")),
        desc=data.get('desc', ""),
        celestial_uid=celestial,
        plugin_datas=plugin_datas,
        achievements=json.loads(achis),
        xme_favorability=data.get('xme_favorability', 0),
        counters=counters,
        # timers=timers,
        ai_history=json.loads(data.get('ai_history', "[]")),
    )
    # user.counters = data.get('counters', {})
    # user.xme_favorability = data.get('xme_favorability', 0)
    # user.desc = data.get('desc', "")
    return user