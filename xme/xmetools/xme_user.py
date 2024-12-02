from xme.xmetools import json_tools
from xme.xmetools import time_tools
from xme.xmetools import dict_tools
from functools import wraps
import config
import inspect
import math
from character import get_message
from xme.xmetools.command_tools import send_msg

coin_name = get_message("config", "coin_name")
coin_pronoun = get_message("config", "coin_pronoun")
class User():
    def __init__(self, user_id: int, coins: int=0):
        self.id = user_id
        # self.name = user_name
        self.coins = coins
        self.counters = {}

    def __str__(self):
        try:
            last_sign_time = time_tools.int_to_days(int(self.counters['sign']["time"]))
            sign_message = get_message("config", "sign_message").format(last_sign_time=last_sign_time)
        except:
            sign_message = get_message("config", "no_sign")

        return get_message("config", "user_info_str").format(
            id=self.id,
            coins_count=self.coins,
            coin_name=coin_name,
            coin_pronoun=coin_pronoun,
            sign_message=sign_message
        )

    def spend_coins(self, amount: int) -> bool:
        if amount > self.coins:
            return False
        self.coins -= amount
        return True

    def __dict__(self):
        return {
            "coins": self.coins,
            "counters": self.counters
        }

    def add_coins(self, amount: int) -> bool:
        if amount < 0:
            return False
        self.coins += amount
        return True

    def load(id: int, create_default_user=True):
        user_dict = json_tools.read_from_path(config.USER_PATH)['users'].get(str(id), None)
        if user_dict == None and create_default_user:
            user_dict = {}
        elif user_dict == None:
            return None
        return load_from_dict(user_dict, id)

    def save(self):
        data_to_save = self.__dict__()
        users = json_tools.read_from_path(config.USER_PATH)
        users['users'][str(self.id)] = data_to_save
        json_tools.save_to_path(config.USER_PATH, users)

def try_load(id, default):
    try:
        return User.load(id)
    except Exception as ex:
        # print(f"try load 出现异常：{traceback.format_exc()}")
        return default

def verify_timers(user: User, name: str):
    if not name in user.counters or type(user.counters[name]) != dict:
        user.counters[name] = {}
        user.save()
    user.counters[name].setdefault("time", 0)
    user.counters[name].setdefault("count", 0)

def reset_limit(user: User, name: str, unit: time_tools.TimeUnit=time_tools.TimeUnit.DAY, floor_float: bool=True, count_add=False):
    """重置限制时间和数量

    Args:
        user (User): 用户
        name (str): 时间限制名
        unit (time_tools.TimeUnit, optional): 时间单位. Defaults to time_tools.TimeUnit.DAY.
        floor_float (bool, optional): 是否向下取整. Defaults to True.
    """
    time_now = time_tools.timenow() / unit.value
    time_now = time_now if not floor_float else math.floor(time_now)
    user.counters[name]["time"] = time_now
    if user.counters[name]["count"] != 0:
        user.counters[name]["count"] = 0
    if count_add:
        user.counters[name]["count"] += 1
    # user.save()

def limit_count_tick(user: User, name: str):
    """增加一次计数器计数

    Args:
        user (User): 用户
        name (str): 时间限制名
    """
    user.counters[name]["count"] += 1
    # user.save()

def validate_limit(user: User, name: str, limit: float | int, count_limit: int=1,  unit: time_tools.TimeUnit=time_tools.TimeUnit.DAY, floor_float: bool=True) -> tuple[bool, bool]:
    """是否在时间 / 数量限制内，如果找不到时间限制名则创建

    Args:
        user (User): 用户
        name (str): 时间限制名
        limit (float | int): 限制时间
        count_limit: 限制时间内限制次数 Defaults to 1.
        unit (date_tools.TimeUnit, optional): 时间单位. Defaults to date_tools.TimeUnit.DAY.
        floor_float (bool, optional): 是否向下取整. Defaults to True.

    Returns:
        tuple[bool, bool]: (是否在时间限制内, 是否在数量限制内)
    """
    verify_timers(user, name)

    time_now = time_tools.timenow() / unit.value
    time_now = time_now if not floor_float else math.floor(time_now)
    # True 禁止继续使用指令 因为已受到限制
    time_limit, c_limit = False, False
    print(time_now)
    print(user.counters[name]["time"])
    print(limit)
    if time_now - user.counters[name]["time"] < limit:
        print("时间受限制")
        time_limit = True
    else:
        print("时间过了 刷新")
        reset_limit(user, name, unit, floor_float)
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

def get_rank(*rank_item_key, key=None):
    """获取用户某项内容排名

    Args:
        key (Callable[_T, SupportsRichComparison], optional): 排名方法. Defaults to None.

    Returns:
        dict: 用户: 键对应值
    """
    rank = {}
    users: dict = json_tools.read_from_path(config.USER_PATH)['users']
    for k, v in users.items():
        # print(f"item: {v}")
        value = dict_tools.get_value(*rank_item_key, search_dict=v)
        if value == None: continue
        rank[k] = value
    rank_values = list(rank.items())
    # print(rank_values)
    rank_values.sort(reverse=True, key=lambda x: key(x[1]) if key else x[1])
    # print(rank)
    return rank_values


def limit(limit_name: str,
          limit: float | int,
          limit_message: str,
          count_limit: int=1,
          unit: time_tools.TimeUnit=time_tools.TimeUnit.DAY,
          floor_float: bool=True,
          fails=lambda x: x == False,
          limit_func=None,):
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
            print(user.counters)
            if validate_limit(user=user, name=limit_name, limit=limit, count_limit=count_limit, unit=unit, floor_float=floor_float):
                if not limit_func:
                    return await send_msg(session, limit_message)
                # 有自定义函数传入情况
                elif inspect.iscoroutinefunction(limit_func):
                    return await limit_func(func, session, user, *args, **kwargs)
                else:
                    return limit_func(func, session, user, *args, **kwargs)
            # user = try_load(session.event.user_id, User(session.event.user_id))
            print(user.counters)
            result = await func(session, user, *args, **kwargs)
            print(f"result: {result}")
            if not fails(result):
                print("保存用户数据, 增加计数")
                limit_count_tick(user, limit_name)
                user.save()
            return result
        return wrapper
    return decorator


def using_user(save_data=False):
    def decorator(func):
        @wraps(func)
        async def wrapper(session, *args, **kwargs):
            print(session.event.user_id)
            user = try_load(session.event.user_id, User(session.event.user_id))
            result = await func(session, user, *args, **kwargs)
            print(f"result: {result}")
            if save_data and result != False:
                print("保存用户数据中")
                user.save()
            return result
        return wrapper
    return decorator

def load_from_dict(data: dict, id: int) -> User:
    user = User(id, data.get('coins', 0))
    user.counters = data.get('counters', {})
    return user