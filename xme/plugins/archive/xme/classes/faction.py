from functools import wraps
from .database import Xme_database
from .db_readable import DbReadable

class Faction(DbReadable):
    """阵营
    """

    def __init__(self, id, name, desc, database: Xme_database, relations: dict={}, prices: dict={}, creator=None) -> None:
        self.id = id
        self.name = name
        self.desc = desc
        self.relations = relations
        self.database: Xme_database = database
        # 阵营创建者
        self.creator = creator
        # 价格波动表
        self.prices = prices
        # 阵营包含的用户
        self.users = {}
        # 用户黑名单
        self.blacklist = []
        # 阵营拥有的舰船？
        # self.ships = []

    def add_user(self, user):
        self.users[user.id] = user
        user.faction = self

    def add_blacklist(self, user):
        """添加黑名单
        """
        if user == self.creator:
            return False
        if user in self.users:
            self.remove_user(user)
        self.blacklist.append(user)
        return True

    def remove_user(self, user):
        """移除用户

        Args:
            user (User): 用户
        """
        del self.users[user.id]

    def get_users_id_list(self):
        """获取阵营所包含的用户 id 列表

        Returns:
            list[int]: 用户 id 列表
        """
        return [user.id for user in self.users]

    def set_relation(self, faction, value):
        """设置好感度

        Args:
            faction (Faction): 阵营
            value (int): 好感度
        """
        if value > 1000 or value < -1000:
            raise ValueError("好感度超过范围。")
        self.relations[faction.id] = value

    def add_relation(self, faction, value):
        """增加好感度

        Args:
            faction (Faction): 阵营
            value (int): 增加的好感度值
        """
        self.set_relation(faction, self.relations[faction.id] + value)