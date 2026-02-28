from character import get_message
coin_name = get_message("user", "coin_name")
coin_pronoun = get_message("user", "coin_pronoun")

import time  # noqa: E402
from datetime import datetime # noqa: E402
from xme.xmetools import timetools # noqa: E402
from xme.xmetools import dicttools # noqa: E402
from .achievements import get_achievements, has_achievement # noqa: E402
from nonebot.session import BaseSession # noqa: E402
from functools import wraps # noqa: E402
from aiocqhttp import ActionFailed # noqa: E402
import json # noqa: E402
from types import FunctionType # noqa: E402
from xme.xmetools.dicttools import get_value # noqa: E402
from xme.xmetools.msgtools import send_to_superusers # noqa: E402
from nonebot import get_bot # noqa: E402
# from ..tools.map_tools import ImageDraw, draw_text_on_image, mark_point # noqa: E402
import inspect # noqa: E402
# from xme.xmetools.imgtools import hash_image # noqa: E402
import math # noqa: E402
from xme.xmetools.msgtools import send_session_msg # noqa: E402
from .inventory import Inventory # noqa: E402
from xme.xmetools.debugtools import debug_msg # noqa: E402
from nonebot.log import logger # noqa: E402
# from .xme_map import get_galaxymap # noqa: E402
from xme.xmetools.dbtools import DATABASE # noqa: E402


# def is_galaxy_loaded():
#     if get_galaxymap():
#         return True
#     return False

# def is_galaxy_initing():
#     return galaxy_initing

class User:
    def form_dict(data: dict):
        return load_from_dict(data, id=data["user_id"])

    @classmethod
    def get_table_name(cls):
        return User.__name__

    async def try_spend(self, session: BaseSession, count, out_of_range_zero=False, no_coin_message="", spent_message=""):
        if count < 0:
            raise ValueError(f"花费的{coin_name}不能小于 0")
        if self.coins < count:
            await send_session_msg(session, (get_message("user", "no_coin", count=count) if not no_coin_message else no_coin_message.format(count=count)))
            return False
        r, spend = self.spend_coins(count, out_of_range_zero)
        if r:
            await send_session_msg(session, (get_message("user", "spent_coin", count=spend) if not spent_message else spent_message.format(count=spend)))
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
            db_id: int = -1,
            coins: int = 0,
            inventory: Inventory | None = None,
            talked_to_bot: list | None = None,
            desc: str = "",
            afdian_id = "",
            xme_favorability=0,
            counters: dict | None = None,
            # timers: dict = {},
            plugin_datas: dict | None = None, # 插件数据，比如 weather 保存用户位置之类的
            achievements: list | None = None,
            ai_history: list[dict] | None = None,
        ):
        self.db_id: int = db_id
        self.id: int = user_id
        self.desc: str = desc
        self.afdian_id: str = afdian_id
        # avoid shared mutable defaults
        self.inventory: Inventory = inventory if inventory is not None else Inventory()
        self.coins: int = coins
        self.xme_favorability: int = xme_favorability
        self.talked_to_bot: list = talked_to_bot if talked_to_bot is not None else []
        self.counters: dict = counters if counters is not None else {}
        self.plugin_datas: dict = plugin_datas if plugin_datas is not None else {}
        # self.timers = timers
        # 注册时间
        # datas = self.plugin_datas.get("datas", {})
        # reg_time = datas.get("register_time", -1)

        self.achievements: list = achievements if achievements is not None else []
        self.ai_history: list = ai_history if ai_history is not None else []
        # debug_msg(self.ai_history)
        # 用户所在天体
        # debug_msg("dbid", self.db_id)
        # self.celestial_uid = celestial_uid
        # self.celestial = None
        self.get_reg_time()
        # if reg_time == -1:
        #     self.plugin_datas["datas"] = {}
        #     self.plugin_datas["datas"]["register_time"] = time.time()
        #     self.save()
        # self.reg_time = self.plugin_datas["datas"]["register_time"]

    def get_reg_time(self):
        time_now = time.time()
        v: float | None = dicttools.get_value("datas", "register_time", search_dict=self.plugin_datas)
        if v is None:
            dicttools.set_value("datas", "register_time", search_dict=self.plugin_datas, set_method=lambda _: time_now)
            # self.reg_time = time_now
            self.save()
            return time_now
        return v


    def get_achievement(self, achievement_name) -> dict | bool:
        # debug_msg("achievement_name:", achievement_name)
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
            debug_msg("已达成成就，不执行")
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
            debug_msg("更新database")
            rows = DATABASE.update_db(obj=self, id=self.db_id, coins=self.coins, achievements=json.dumps(self.achievements, ensure_ascii=False))
            debug_msg("受影响的行数:", rows)
        sent = False
        while not sent:
            try:
                await send_session_msg(session, achievement_message)
                sent = True
            except ActionFailed:
                continue

    # def gen_celestial(self):
    #     """随机获取出生星体
    #     """
    #     map = get_galaxymap()
    #     if not map:
    #         debug_msg("地图未生成")
    #         return
    #     choice_celestials = []
    #     debug_msg("随机生成出生星体中")
    #     # debug_msg("USERRRRRRRRRRRRRRR", map.starfields)
    #     for starfield in map.starfields.values():
    #         if starfield.calc_faction().id != 1:
    #             continue
    #         for c in starfield.celestials.values():
    #             if isinstance(c, Star):
    #                 continue
    #             if isinstance(c, Planet):
    #                 if c.planet_type not in [
    #                     PlanetType.CITY,
    #                     PlanetType.DESOLATE,
    #                     PlanetType.DRY,
    #                     PlanetType.SEA,
    #                     PlanetType.TERRESTRIAL,
    #                 ]:
    #                     continue
    #             choice_celestials.append(c)
    #     if choice_celestials:
    #         self.celestial = random.choice(choice_celestials)
    #         # self.save()
    #     else:
    #         debug_msg("无法获取到合适的行星")

    def __str__(self):
        # debug_msg("self.get_reg_time()", self.get_reg_time())
        try:
            # last_sign_time = time_tools.int_to_days(int(self.counters['sign']["time"]))
            last_sign_time = timetools.int_to_date(int(timetools.get_valuetime(self.counters['sign']["time"], timetools.TimeUnit.DAY)))
            sign_message = get_message("user", "sign_message", last_sign_time=last_sign_time)
        except Exception:
            sign_message = get_message("user", "no_sign")
        _, rank_ratio, _ = get_user_rank(self.id)
        return get_message("user", "user_info_str",
            id=str(self.id),
            reg_time=datetime.strftime(datetime.fromtimestamp(self.get_reg_time()), format=r"%Y-%m-%d %H:%M:%S"),
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
            "afdian_id": self.afdian_id,
            "xme_favorability": self.xme_favorability,
            "desc": self.desc,
            "plugin_datas": self.plugin_datas,
            "inventory": self.inventory.__list__(),
            "talked_to_bot": self.talked_to_bot,
            "achievements": self.achievements,
            "ai_history": self.ai_history,
        }

    def __dict__(self):
        return self.to_dict()

    def add_coins(self, amount: int) -> bool:
        amount = int(amount)
        debug_msg("amount", amount)
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
        c: User = DATABASE.load_class(select_keys=(id,), query='SELECT * FROM {table_name} WHERE user_id = ?', cl=User)
        if c is None and create_default_user:
            debug_msg("创建一个新用户")
            return User(user_id=id)
        elif c is not None:
            c.get_reg_time()
        return c

    def save(self):
        self.db_id = DATABASE.save_to_db(obj=self)


def try_load(id):
    u = User.load(id)
    if u is None:
        logger.info("没有用户，正在尝试创建新用户。")
        u = User(id)
    return u

def verify_counters(user: User, name: str):
    if name not in user.counters or not isinstance(user.counters[name], dict):
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
    if get_value(name, "count", search_dict=user.counters) is None:
        user.counters[name] = {}
        user.counters[name]["count"] = 0
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
        if int(item[0]) != user:
            continue
        debug_msg("匹配到了")
        sender_coins_count = item[1]
        sender_index = index
    rank_ratio = 0
    if sender_coins_count is not None:
        rank_ratio = (len(rank_items[sender_index:]) - 1)/ (len(rank_items) - 1) * 100 if len(rank_items[sender_index:]) > 1 else 100
    return sender_coins_count, rank_ratio, sender_index


def detect_limit(user: User, name: str, interval: float | int, count_limit: int = 1,
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
    if time_now - timetools.get_valuetime(user.counters[name]["time"], unit) < interval:
        debug_msg("时间受限制")
        time_limit = True
    else:
        debug_msg("时间过了 刷新")
        reset_limit(user, name, floor_float)
        return False
        # return (True, True)
    if user.counters[name]["count"] >= count_limit:
        debug_msg("次数受限制")
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
    return (
        get_value(name, "time", search_dict=user.counters, default=0),
        get_value(name, "count", search_dict=user.counters, default=0)
    )
    # return (user.counters[name]["time"], user.counters[name]["count"])


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
        # debug_msg(f"item: {v}")
        value = dicttools.get_value(*rank_item_key, search_dict=v)
        if value is None:
            continue
        rank[v["user_id"]] = value
    if excluding_zero:
        rank_values = [r for r in rank.items() if r[1] > 0]
    else:
        rank_values = [r for r in rank.items()]
    # debug_msg(rank_values)
    rank_values.sort(reverse=True, key=lambda x: key(x[1]) if key else x[1])
    # debug_msg(rank)
    return rank_values


def limit(limit_name: str,
          interval: float | int,
          limit_message: str,
          count_limit: int = 1,
          unit: timetools.TimeUnit = timetools.TimeUnit.DAY,
          floor_float: bool = True,
          fails=lambda x: not x,
          limit_func=None, ):
    """对函数进行限制时间内只能执行数次

    Args:
        limit_name (str): 限制名
        interval (float | int): 多少时间单位后刷新限制
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
            # debug_msg(user.counters)
            if detect_limit(user=user, name=limit_name, interval=interval, count_limit=count_limit, unit=unit,
                              floor_float=floor_float):
                if not limit_func:
                    return await send_session_msg(session, limit_message)
                # 有自定义函数传入情况
                elif inspect.iscoroutinefunction(limit_func):
                    return await limit_func(func, session, user, *args, **kwargs)
                else:
                    return limit_func(func, session, user, *args, **kwargs)
            # user = try_load(session.event.user_id, User(session.event.user_id))
            # debug_msg(user.counters)
            result = await func(session, user, *args, **kwargs)
            # debug_msg(f"result: {result}")
            if not fails(result):
                debug_msg("保存用户数据, 增加计数")
                debug_msg("coins", user.coins)
                limit_count_tick(user, limit_name)
                user.save()
            if isinstance(result, str):
                await send_session_msg(session, result)
            return result

        return wrapper

    return decorator

def custom_limit(limit_name: str | FunctionType,
          interval: float | int,
          count_limit: int = 1,
          unit: timetools.TimeUnit = timetools.TimeUnit.DAY,
          floor_float: bool = True,):
    """对函数进行限制时间内只能执行数次，其中判断限制和增加计数由函数自己决定

    Args:
        limit_name (str): 限制名
        interval (float | int): 多少时间单位后刷新限制
        limit_message (str): 限制时返回的消息
        count_limit (int, optional): 时间内限制次数. Defaults to 1.
        unit (time_tools.TimeUnit, optional): 时间单位. Defaults to time_tools.TimeUnit.DAY.
        floor_float (bool, optional): 是否向下取整时间. Defaults to True.
        limit_func (func, optional): 自定义限制时返回的函数. Defaults to None.
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(session, user: User, *args, **kwargs):
            if inspect.isfunction(limit_name):
                name = limit_name(session, user, *args, **kwargs)
            else:
                name = limit_name
            def count_tick(count=1):
                debug_msg("保存用户数据, 增加计数")
                limit_count_tick(user, name, count)
                user.save()
            def check_invalid():
                if detect_limit(user=user, name=name, interval=interval, count_limit=count_limit, unit=unit,
                              floor_float=floor_float):
                    # 已受限
                    debug_msg("受到限制")
                    return True
                # 未受限
                debug_msg("无限制")
                return False
            result = await func(session, user, check_invalid, count_tick, *args, **kwargs)
            debug_msg(f"result: {result}")
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
            debug_msg(user_id)
            user = try_load(user_id)
            result = await func(session, user, *args, **kwargs)
            # debug_msg(f"result: {result}")
            if save_data and result:
                debug_msg("保存用户数据中")
                user.save()
            return result

        return wrapper

    return decorator

def load_dict_user(data: dict):
    inventory_data = None
    # debug_msg(celestial)
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
        logger.error(f"加载用户 {data.get('user_id', '未知')} id:{data.get('id', -1)} 出错")
        raise ex
    # debug_msg(counters)
    # Do NOT instantiate Inventory objects here during bulk loads to avoid
    # creating many InvItem instances which can increase GC pressure.
    # Keep raw inventory data and construct Inventory objects only when
    # loading a single user via load_from_dict.
    inventory = inventory_data
    # debug_msg(data)
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
    # debug_msg(inventory_data)
    if inventory_data:
        inventory = Inventory.get_inventory(inventory_data)
    # debug_msg(data)
    celestial = data.get('celestial', None)
    debug_msg("celestial", celestial)
    # debug_msg(celestial)
    counters = json.loads(data.get('counters', "{}"))
    # timers = json.loads(data.get('timers', "{}"))
    # debug_msg(counters)
    achis = data.get('achievements', "[]")
    plugin_datas = json.loads(data.get('plugin_datas', "{}"))
    if not achis:
        achis = "[]"
    user = User(
        db_id=data.get('id', -1),
        user_id=id,
        coins=data.get('coins', 0),
        inventory=inventory,
        afdian_id= data.get("afdian_id", ''),
        talked_to_bot=json.loads(data.get('talked_to_bot', "[]")),
        desc=data.get('desc', ""),
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