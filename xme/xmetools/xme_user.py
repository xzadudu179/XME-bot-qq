from xme.xmetools import json_tools
from xme.xmetools import time_tools
from functools import wraps
import config
import inspect
import math
from xme.xmetools.command_tools import send_msg

class User():
    def __init__(self, user_id: int, coins: int=0):
        self.id = user_id
        # self.name = user_name
        self.coins = coins
        self.timers = {}

    def __str__(self):
        return str(self.__dict__)

    def load(id: int):
        return load_from_dict(json_tools.read_from_path(config.USER_PATH)['users'][str(id)], id)

    def save(self):
        data_to_save = {
            "coins": self.coins,
            "timers": self.timers
        }
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
    if not name in user.timers or type(user.timers[name]) != dict:
        user.timers[name] = {}
        user.save()
    user.timers[name].setdefault("time", 0)
    user.timers[name].setdefault("count", 0)

def reset_limit(user: User, name: str, unit: time_tools.TimeUnit=time_tools.TimeUnit.DAY, floor_float: bool=True):
    """重置限制时间和数量

    Args:
        user (User): 用户
        name (str): 时间限制名
        unit (time_tools.TimeUnit, optional): 时间单位. Defaults to time_tools.TimeUnit.DAY.
        floor_float (bool, optional): 是否向下取整. Defaults to True.
    """
    time_now = time_tools.timenow() / unit.value
    time_now = time_now if not floor_float else math.floor(time_now)
    user.timers[name]["time"] = time_now
    if user.timers[name]["count"] != 0:
        user.timers[name]["count"] = 0
    # user.timers[name]["count"] += 1
    # user.save()

def limit_count_tick(user: User, name: str):
    """增加一次计数器计数

    Args:
        user (User): 用户
        name (str): 时间限制名
    """
    user.timers[name]["count"] += 1
    user.save()

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
    if time_now - user.timers[name]["time"] < limit:
        print("时间受限制")
        time_limit = True
        # return (True, True)
    if user.timers[name]["count"] >= count_limit:
        print("次数受限制")
        c_limit = True
    return (time_limit, c_limit)

def get_limit_info(user, name):
    """返回限制情况

    Args:
        user (User): 用户
        name (str): 时间限制名

    Returns:
        tuple(int | float, int): (当前记录时间, 当前记录次数)
    """
    return (user.timers[name]["time"], user.timers[name]["count"])


def limit(limit_name: str, limit: float | int, limit_message: str, count_limit: int=1, unit: time_tools.TimeUnit=time_tools.TimeUnit.DAY, floor_float: bool=True, limit_func=None, *limit_func_args, **limit_func_kwargs):
    """对函数进行限制时间内只能执行数次

    Args:
        limit_name (str): 限制名
        limit (float | int): 限制时间
        limit_message (str): 限制时返回的消息
        count_limit (int, optional): 时间内限制次数. Defaults to 1.
        unit (time_tools.TimeUnit, optional): 时间单位. Defaults to time_tools.TimeUnit.DAY.
        floor_float (bool, optional): 是否向下取整时间. Defaults to True.
        limit_func (func, optional): 自定义限制时返回的函数. Defaults to None.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(session, user, *args, **kwargs):
            if (is_limit:=validate_limit(user=user, name=limit_name, limit=limit, count_limit=count_limit, unit=unit, floor_float=floor_float))[0] and is_limit[1]:
                if not limit_func:
                    return await send_msg(session, limit_message)
                # 有自定义函数传入情况
                elif inspect.iscoroutinefunction(limit_func):
                    return await limit_func(session, *limit_func_args, **limit_func_kwargs)
                else:
                    return limit_func(session, *limit_func_args, **limit_func_kwargs)
            # user = try_load(session.event.user_id, User(session.event.user_id))
            result = await func(session, user, *args, **kwargs)
            print(result, is_limit)
            if result == True and not is_limit[0] and not is_limit[1]:
                print("重置计数器")
                reset_limit(user, limit_name, unit, floor_float)
            elif result == True and is_limit[0] and not is_limit[1]:
                print("更新计数器")
                limit_count_tick(user, limit_name)
            return
        return wrapper
    return decorator


def using_user(save_data=False):
    def decorator(func):
        @wraps(func)
        async def wrapper(session, *args, **kwargs):
            print(session.event.user_id)
            user = try_load(session.event.user_id, User(session.event.user_id))
            await func(session, user, *args, **kwargs)
            if save_data:
                user.save()
            return
        return wrapper
    return decorator

def load_from_dict(data: dict, id: int) -> User:
    user = User(id, data.get('coins', 0))
    user.timers = data.get('timers', {})
    return user