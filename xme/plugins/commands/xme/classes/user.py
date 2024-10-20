# from .database import Xme_database
from xme.xmetools import date_tools
from functools import wraps
import random
from .item import Item

class User:
    """XME 用户类
    """
    MAX_NAME_LENGTH = 20
    def __init__(self, database, id: int, name: str, last_reg_days: int=0, coins: int=0, items: list[Item]=[]) -> None:
        """初始化用户

        Args:
            id (int): 用户 id （建议为 qq 号）
            name (str): 用户名
            coins (int): _description_
            database (Xme_database): _description_

        Raises:
            ValueError: _description_
        """
        if len(name) > self.MAX_NAME_LENGTH:
            raise ValueError(f"name 参数长度过长 (>{self.MAX_NAME_LENGTH})")
        self.id = id
        self.name = name
        self.last_reg_days = last_reg_days
        self.coins = coins
        self.items = items
        self.database = database
        self.database.init_user_info()

    def load_user(database, query: str, search: str):
        """通过数据库表寻找并且返回符合的用户

        Args:
            database (_type_): 数据库
            query (str): 数据库内表的项名
            search (str): 需要查询的值

        Returns:
            list[User]: 用户列表
        """
        results = database.get_user_info(query, search)
        users = []
        for result in results:
            (id, name, last_reg_days, coins) = result
            users.append(User(database, id, name, last_reg_days, coins))
        return users

    def change_name(self, new_name) -> bool:
        if len(new_name) > self.MAX_NAME_LENGTH:
            return False
        self.name = new_name
        return

    def update_user_data(func):
        """用户数据更新装饰函数

        Args:
            func (_type_): 装饰函数
        """
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            result = func(self, *args, **kwargs)  # 调用原始函数
            # 在函数执行完毕后执行的指令
            self.database.save_user_info(self)
            print("用户数据已更新.")
            return result
        return wrapper

    # @update_user_data
    def register(self) -> bool:
        curr_days = date_tools.curr_days()
        # 没到时间不给注册
        if self.last_reg_days >= curr_days:
            return False
        print(self.last_reg_days, curr_days)
        # 注册 or 签到
        add_coins = random.randint(0, 60)
        # 给注册刷新时间
        self.coins += add_coins
        self.last_reg_days = curr_days
        self.database.save_user_info(user=self)
        return True
