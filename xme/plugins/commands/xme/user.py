from .database import Xme_database

class User:
    """XME 用户类
    """
    MAX_NAME_LENGTH = 20
    def __init__(self, name: str, last_reg_days: int, coins: int, database: Xme_database) -> None:
        if len(name) > self.MAX_NAME_LENGTH:
            raise ValueError(f"name 参数长度过长 (>{self.MAX_NAME_LENGTH})")
        self.name = name
        self.last_reg_days = last_reg_days
        self.coins = coins
        self.database = database

    def change_name(self, new_name) -> bool:
        if len(new_name) > self.MAX_NAME_LENGTH:
            return False
        self.name = new_name
        return

    def update_user_data(self, func, database):
        """用户数据更新装饰函数

        Args:
            func (_type_): 装饰函数
        """
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)  # 调用原始函数
            # 在函数执行完毕后执行的指令
            database.save_user_info(self)
            print("用户数据已更新.")
            return result
        return wrapper

    def register(self):
        pass
