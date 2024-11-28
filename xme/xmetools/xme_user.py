from xme.xmetools import json_tools
from xme.xmetools import time_tools
from functools import wraps
import config
import math
import traceback

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

def is_limit(user: User, name: str, limit: float | int, unit: time_tools.TimeUnit=time_tools.TimeUnit.DAY, floor_float: bool=True) -> bool:
    """是否在时间限制内，如果找不到时间限制名则创建

    Args:
        user (User): 用户
        name (str): 时间限制名
        limit (float | int): 限制时间
        unit (date_tools.TimeUnit, optional): 时间单位. Defaults to date_tools.TimeUnit.DAY.
        floor_float (bool, optional): 是否向下取整. Defaults to True.

    Returns:
        bool: 是否在时间限制内
    """
    if name in user.timers:
        time_now = time_tools.timenow() / unit.value
        time_now = time_now if not floor_float else math.floor(time_now)
        if time_now - user.timers[name] < limit:
            return True
        else:
            return False
    user.timers[name] = time_tools.timenow() / unit.value
    user.save()
    return False

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