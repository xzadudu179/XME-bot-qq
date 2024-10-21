# from .database import Xme_database
from xme.xmetools import date_tools
from functools import wraps
import random
from .items.inventory import Inventory
from xme.xmetools import text_tools

class User:
    """XME 用户类
    """
    MAX_NAME_LENGTH = 20
    MAX_BIO_LENGTH = 100
    PERMISSIONS_DICT = {
        0: "被封禁",
        1: "用户",
        2: "管理员",
        3: "ADMIN",
        4: "ROOT"
    }

    def update_user_data(func):
        """用户数据更新装饰函数

        Args:
            func (_type_): 装饰函数
        """
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            result = func(self, *args, **kwargs)  # 调用原始函数
            if not result:
                # 如果返回 False 等值不执行保存
                return result
            # 在函数执行完毕后执行的指令
            self.database.save_user_info(self)
            print("用户数据已更新.")
            return result
        return wrapper

    def __init__(self, database, id: int, name: str, bio: str="", last_reg_days: int=0, coins: int=0, permission: int=1, inventory: Inventory=Inventory(20)) -> None:
        """初始化用户

        Args:
            database (Xme_Database): 用户数据库
            id (int): 用户 id
            name (str): 名称
            bio (str, optional): 介绍. Defaults to "".
            last_reg_days (int, optional): 上次签到时间. Defaults to 0.
            coins (int, optional): 虚拟星币数. Defaults to 0.
            permission (int, optional): 权限等级. Defaults to 1.
            inventory (Inventory, optional): 物品栏. Defaults to Inventory(20).

        Raises:
            ValueError: 名称过长
        """
        # 更新
        (database, id, name, bio, last_reg_days, coins, permission, inventory) = self.check_default(database, id, name, bio, last_reg_days, coins, permission, inventory)
        if len(name) > self.MAX_NAME_LENGTH:
            raise ValueError(f"name 参数长度过长 (>{self.MAX_NAME_LENGTH})")
        if len(bio) > self.MAX_BIO_LENGTH:
            raise ValueError(f"bio 参数长度过长 (>{self.MAX_BIO_LENGTH})")
        # text_tools.characters_only_contains_ch_en_num_udline_horzline(name)
        self.id = id
        self.name = name
        self.bio = bio
        self.permission = permission
        self.last_reg_days = last_reg_days
        self.coins = coins
        self.inventory = inventory
        self.database = database
        self.database.init_user_info()

    def check_and_replace_username(self):
        """将用户名确定为合法字符范围
        """
        self.name = text_tools.characters_only_contains_ch_en_num_udline_horzline(self.name)

    @update_user_data
    def update(self):
        """把没有默认值的 None 改成有默认值的样子
        """
        self = User(self.database,
                    self.id,
                    self.name,
                    self.bio if self.bio else "",
                    self.last_reg_days if self.last_reg_days else 0,
                    self.coins if self.coins else 0,
                    self.permission if self.permission else 1,
                    self.inventory if self.inventory else Inventory(20))
        return True

    def check_default(self, database, id, name, bio, last_reg_days, coins, permission, inventory):
        """同上 但是用于构造函数等
        """
        name = text_tools.characters_only_contains_ch_en_num_udline_horzline(name)
        return (database,
                    id,
                    name,
                    bio if bio else "",
                    last_reg_days if last_reg_days else 0,
                    coins if coins else 0,
                    permission if permission else 1,
                    inventory if inventory else Inventory(20))

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
            (id, name, last_reg_days, coins, permission, bio, inventory) = result
            users.append(User(database, id, name, bio, last_reg_days, coins, permission, Inventory(20, Inventory.get_itemblocks(inventory))))
        return users

    def get_user_by_id(database, user_id):
        return User.load_user(database, "id", user_id)

    @update_user_data
    def add_item(self, item, count) -> bool:
        return self.inventory.add_item(item, count)

    @update_user_data
    def change_name(self, new_name: str) -> bool:
        """修改名称

        Args:
            new_name (str): 新名称

        Returns:
            bool: 是否成功
        """
        if len(new_name) > self.MAX_NAME_LENGTH:
            return False
        self.check_and_replace_username()
        self.name = new_name
        return True

    @update_user_data
    def change_bio(self, new_bio: str) -> bool:
        """修改个人介绍

        Args:
            new_bio (str): 新的个人介绍

        Returns:
            bool: 是否成功
        """
        if len(new_bio) > self.MAX_BIO_LENGTH or new_bio.count('\n') > 15:
            return False
        self.bio = new_bio
        return True

    @update_user_data
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
        # self.database.save_user_info(user=self)
        return True

    def __str__(self) -> str:
        bio = '----------\n' + self.bio + "\n" if self.bio != "" else ""
        return f"""
[{self.PERMISSIONS_DICT[self.permission]}] {self.name}
{bio}----------
目前拥有 {self.coins} 枚虚拟星币
物品栏占用: [{self.inventory.get_space()}/{self.inventory.length}]
上次签到时间: {date_tools.int_to_days(self.last_reg_days)}
""".strip()
