from .database import Xme_database
from xme.xmetools import date_tools
from functools import wraps


class User:
    """XME 用户类
    """
    MAX_NAME_LENGTH = 20
    def __init__(self,id: int, name: str, coins: int, database: Xme_database) -> None:
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
        self.last_reg_days = 0
        self.coins = coins
        self.database = database

    def load_user(database: Xme_database, user_id: int):
        """通过数据库表寻找并且返回用户

        Args:
            database (Xme_database): 数据库
            user_id (int): 用户id
        """
        pass

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
            result = func(*args, **kwargs)  # 调用原始函数
            # 在函数执行完毕后执行的指令
            self.database.save_user_info(self)
            print("用户数据已更新.")
            return result
        return wrapper

    @update_user_data
    def try_register(self) -> bool:
        self.database.init_user_info()
        curr_days = date_tools.curr_days()
        if self.last_reg_days >= curr_days:
            return False
        self.last_reg_days = curr_days
        # self.database.save_user_info(user=self)
        pass
