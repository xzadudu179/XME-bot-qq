# from .database import Xme_database
from xme.xmetools import time_tools
from functools import wraps
import random
from .items.inventory import Inventory
from xme.xmetools import text_tools
from .faction import *
from .db_readable import DbReadable
import sqlite3

class User(DbReadable):
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

    def __init__(self, database, id: int, name: str, bio: str="", last_reg_days: int=0, coins: int=0, permission: int=1, faction=None, inventory: Inventory=Inventory(20)) -> None:
        """初始化用户

        Args:
            database (Xme_Database): 用户数据库
            id (int): 用户 id
            name (str): 名称
            bio (str, optional): 介绍. Defaults to "".
            last_reg_days (int, optional): 上次签到时间. Defaults to 0.
            coins (int, optional): 虚拟星币数. Defaults to 0.
            permission (int, optional): 权限等级. Defaults to 1.
            faction: 所属阵营. Defaults to None
            inventory (Inventory, optional): 物品栏. Defaults to Inventory(20).

        Raises:
            ValueError: 名称过长
        """
        # 更新
        # (database, id, name, bio, last_reg_days, coins, permission, inventory) = self.check_default(database, id, name, bio, last_reg_days, coins, permission, inventory)
        if len(name) > self.MAX_NAME_LENGTH:
            raise ValueError(f"name 参数长度过长 (>{self.MAX_NAME_LENGTH})")
        if len(bio) > self.MAX_BIO_LENGTH:
            raise ValueError(f"bio 参数长度过长 (>{self.MAX_BIO_LENGTH})")
        # text_tools.characters_only_contains_ch_en_num_udline_horzline(name)
        # self.id = id
        self.name = name
        self.bio = bio
        self.permission = permission
        self.last_reg_days = last_reg_days
        self.coins = coins
        self.faction = faction
        self.inventory = inventory
        super().__init__(id, database)
        self.init_table()
        # self.database = database
        # self.database.init_user_info()

    @DbReadable.update_data
    def check_and_replace_username(self, name):
        """将用户名确定为合法字符范围
        """
        self.name = text_tools.characters_only_contains_ch_en_num_udline_horzline(name)
        return True

    @DbReadable.update_data
    def join_faction(self, faction: Faction):
        """加入阵营

        Args:
            faction (Faction): 阵营
        """
        faction.add_user(self)
        self.faction = faction
        return True

    @DbReadable.update_data
    def leave_faction(self):
        """离开阵营

        Args:
            faction (Faction): 阵营
        """
        self.faction.remove_user(self)
        self.faction = None
        return True

    def load_by_id(database, id, table_name='user'):
        """加载用户数据

        Args:
            database (Xme_database): 数据库
            id (int): 类 id
        """
        dict = {}
        try:
            dict = database.load_from_db(id=id, table_name=table_name)
        except:
            # 这个 User只是临时数据
            print("创建用户表中")
            temp_user = User(database, 1, '1', '1')
            temp_user.init_table()
            dict = database.load_from_db(id=id, table_name=table_name)
        return User(**dict) if dict else None

    # def get_user_by_id(database, user_id):
    #     return User.load_user(database, "id", user_id)

    @DbReadable.update_data
    def add_item(self, item, count) -> tuple[bool, int]:
        return self.inventory.add_item(item, count)

    @DbReadable.update_data
    def del_item(self, item, count) -> tuple[bool, int]:
        return self.inventory.del_item(item, count)

    # @DbReadable.update_data
    # def drop_item(self, item, count) -> tuple[bool, int]:
    #     return self.inventory.drop_item(item, count)

    @DbReadable.update_data
    def change_name(self, new_name: str) -> bool:
        """修改名称

        Args:
            new_name (str): 新名称

        Returns:
            bool: 是否成功
        """
        if len(new_name) > self.MAX_NAME_LENGTH:
            return False
        self.check_and_replace_username(new_name)
        return True

    @DbReadable.update_data
    def change_bio(self, new_bio: str) -> bool:
        """修改个人介绍

        Args:
            new_bio (str): 新的个人介绍

        Returns:
            bool: 是否成功
        """
        if len(new_bio) > self.MAX_BIO_LENGTH or new_bio.count('\n') > 15 or new_bio.count('\r') > 15:
            return False
        self.bio = new_bio
        return True

    @DbReadable.update_data
    def register(self) -> bool:
        curr_days = time_tools.curr_days()
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
        coin = f'拥有 {self.coins} 枚虚拟星币' if self.coins > 0 else f'没有任何虚拟星币'
        return f"""
[{self.faction if self.faction else '无阵营'}][{self.PERMISSIONS_DICT[self.permission]}] {self.name}
{bio}----------
目前{coin}
物品栏占用: [{self.inventory.get_space()}/{self.inventory.length}]
上次签到时间: {time_tools.int_to_date(self.last_reg_days) if self.last_reg_days > 0 else '从未签到过'}
""".strip()
