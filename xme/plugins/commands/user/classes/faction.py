from functools import wraps
class Faction:
    """阵营
    """

    def __init__(self, id, name, desc, color: str, relations: dict={}, price_ratios: dict={}, creator=None, is_active=True, tradeable=True) -> None:
        self.id = id
        self.name = name
        self.desc = desc
        self.color = color
        self.relations = relations
        # 是否活跃于星域
        self.active = is_active
        # 是否可交易
        self.tradeable = tradeable
        # 阵营创建者
        self.creator = creator
        # 价格波动表
        self.price_ratios = price_ratios
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

    def change_price_ratio(self, id, ratio):
        """修改售卖某物品的基准价格比值

        Args:
            id (int): 物品 id
            ratio (float): 价格比值
        """
        self.price_ratios[id] = ratio

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


factions = {
    0: Faction(
        id=0,
        name="HIUN",
        desc="人类星际联合国（HIUN）原本是属于地球联合国的一支大型远征探索舰队，但在执行任务期间人类发生内战，导致这个舰队失去了与母星的联系。无法获得地球联合国联系的远征舰队仅靠自身的空间场燃料是无法回到地球的，只好继续完成他们的任务。\n星历 9265 年 5 月（公元 2481 年 5 月）远征队执行完了设定的任务，并在距太阳系约7500光年外的双星系统 MER-308R 中发现一颗较宜居的”超级地球”忒利亚（Telia）。这支远征队便在此安家，并逐步发展为这片星域最大的人类阵营。",
        color="",
        relations={},
        price_ratios={3: 1.1},
        creator=None,
        is_active=True
    ),
    1: Faction(
        id=1,
        name="地球联合国",
        desc="在23世纪创造了先进的空间技术后，人类的目光开始放向浩瀚的星海，探索欲的驱使下，人类组建了半联合的联邦“地球联合国”，旨在让人类航空资源共享，互帮互助，探索无边无际的深空。但如今，地球联合国已经在战争下失去了大多的联合度，基本已经变成了一个空壳。",
        color="",
        relations={},
        price_ratios={},
        is_active=False
    ),
    2: Faction(
        id=2,
        name="涅普顿军团",
        desc="人类的另一派系，和 HIUN 一样由失联的远征队而来，但不同的是，他们没有找到像忒利亚一样宜居的星球，只能在完成任务后在一颗布满岩石的凯罗尔（Carol）星布置基地。\n涅普顿军团没有真正的母星，所有人口都在各母舰与支持舰队上，他们会不断在宇宙中游走，收集路上的各种资源。",
        color="",
        relations={},
        price_ratios={},
        is_active=False
    ),
    3: Faction(
        id=3,
        name="虚空之影",
        desc="...未知...",
        color="",
        relations={},
        price_ratios={},
        is_active=True
    ),
}