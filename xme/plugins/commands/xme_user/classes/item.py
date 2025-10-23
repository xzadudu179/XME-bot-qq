from enum import Enum
import inspect
from . import item_methods
from xme.xmetools import listtools

class Rarity(Enum):
    """稀有度"""
    COMMON = "常见"
    UNCOMMON = "少见"
    RARE = "稀有"
    EPIC = "罕见"
    LEGEND = "传奇"
    MYSTIC = "神秘"

class Tag(Enum):
    """物品标签"""
    WEAPON = "武器"
    FOOD = "食物"
    DRINK = "饮料"
    RESOURCE = "资源"
    SPECIAL = "特殊"
    SALEABLE = "可出售"
    MATERIAL = "材料"
    ARMOR = "护甲"
    WEARABLE = "可穿戴"
    CANNOT_DROP = "不可丢弃"
    PROHIBITED = "违禁品"

class Item:
    """一般物品
    """
    def has_tag(self, tag: Tag):
        return tag in self.tags

    def __init__(self, id: int, name: str, desc: str, rarity: Rarity, tags: list[Tag]=[], maxcount: int=1, price=0, pronoun="个", action_args: dict = {}, **kwargs) -> None:
        """创建一个物品

        Args:
            id (int): 物品唯一 ID
            name (str): 物品名
            desc (str): 物品介绍
            rarity (Rarity): 物品稀有度
            tags (list[Tag], optional): 物品所包含标签. Defaults to [].
            maxcount (int, optional): 物品最大堆叠数量. Defaults to 1.
            price (int, optional): 物品价格. Defaults to 0.
            pronoun (str, optional): 量词，例如 "个"
            **actions: 物品包含的自定义函数.
        """
        self.id = id
        self.name = name
        self.desc = desc
        self.rarity =rarity
        self.tags = tags
        self.maxcount = maxcount
        self.pronoun = pronoun
        self.price = price
        self.actions = {k: v for k, v in kwargs.items() if callable(v)}
        self.action_args = action_args

    def __getstate__(self):
        return self.id

    def can_drop(self) -> bool:
        """是否可丢弃

        Returns:
            bool: 判断结果
        """
        if self.has_tag(Tag.CANNOT_DROP):
            return False
        return True

    def __setstate__(self, id):
        self.get_item(id)

    def __str__(self) -> str:
        return self.name

    @staticmethod
    def get_item(id):
        return item_table.get(id, None)

    @staticmethod
    def get_item_by_name(name: str, fuzzy: bool = False, fuzzy_threshold: float = 80.0, items: list | None = None, key=lambda x: x.name):
        print(f"name: {name}")
        if items is None:
            items = list(item_table.values())
        if not fuzzy:
            for item in items:
                if item.name != name:
                    continue
                return item
            return None
        sim = listtools.top_k_sim(items, name, 1, fuzzy_threshold, key)
        if len(sim) < 1:
            return None
        return Item.get_item_by_name(sim[0][0])

    def can_sell(self):
        """是否可出售

        Returns:
            bool: 判断结果
        """
        if not self.has_tag(Tag.SALEABLE) or self.price <= 0:
            return False
        return True

    def info(self, count=1) -> str:
        """返回物品信息

        Returns:
            str: 物品信息字符串
        """
        price = '\n总价值: ' + str(self.price * count) if self.has_tag(Tag.SALEABLE) else ''
        return f"""
[{self.rarity.value}] {self.name} {'*' + str(count) if count > 1 else ''}
标签：{(', '.join([tag.value for tag in self.tags])) if self.tags else '无'}{price}
-------------------------
{self.desc}
-------------------------
最大堆叠数量: {self.maxcount}
    """.strip()

    def set_action(self, name: str, action):
        self.actions[name] = action

    def has_action(self, name: str) -> bool:
        return name in self.actions and self.actions[name]

    async def call_action(self, action_name: str, **kwargs):
        """使用物品自定方法

        Args:
            action_name (str): 方法名

        Returns:
            tuple[bool, Any]: 是否执行成功，以及自定方法返回的结果
        """
        if action_name in self.actions and self.actions[action_name]:
            if inspect.iscoroutinefunction(self.actions[action_name]):
                return (True, await self.actions[action_name](self, **self.action_args.get(action_name, {}), **kwargs))
            return (True, self.actions[action_name](self, **kwargs))
        else:
            return (False, None)


item_table = {
    0: Item(
        id=0,
        name="几何挂件",
        desc="HIUN 中常见的小挂件，可以散发清香，几何体可以随意编辑样式。",
        rarity=Rarity.COMMON,
        tags=[Tag.SALEABLE],
        maxcount=20,
        price=5,
        pronoun="个",
    ),
    1: Item(
        id=1,
        name="漂流瓶",
        desc="一个空空的，在发抖的瓶子，似乎有点脆弱...？",
        rarity=Rarity.COMMON,
        tags=[Tag.SALEABLE],
        maxcount=10,
        price=10,
        pronoun="个"
    ),
    2: Item(
        id=2,
        name="垣矿",
        desc="一标准单位的垣矿，是一种受坭晶石能量影响转变的物质，密度很高，也很坚硬。",
        rarity=Rarity.UNCOMMON,
        tags=[Tag.SALEABLE, Tag.RESOURCE],
        maxcount=100,
        price=25,
        pronoun="块"
    ),
    3: Item(
        id=3,
        name="坭晶石",
        desc="忒利亚星地壳下的水晶，采集难度很大，但是极具价值，HIUN 的大多科技都是建立在坭晶石的基础上而成的。\n因其构造很不稳定，建议使用特殊的容器保存。",
        rarity=Rarity.RARE,
        tags=[Tag.SALEABLE, Tag.RESOURCE],
        maxcount=20,
        price=110,
        pronoun="块"
    ),
    4: Item(
        id=4,
        name="坭晶石粉末",
        desc="坭晶石因外力破碎时粉碎成的细末，失去了原本的能量，但是也有一定的价值。",
        rarity=Rarity.UNCOMMON,
        tags=[Tag.SALEABLE],
        maxcount=50,
        price=30,
        pronoun="袋"
    ),
    5: Item(
        id=5,
        name="MAZE-MK IV 型通用外骨骼防护套装",
        desc="旧世纪 MAZE 雇佣兵团通用的基本防护套装，可用于抵御部分外界的伤害。",
        rarity=Rarity.RARE,
        tags=[Tag.ARMOR, Tag.WEARABLE],
        maxcount=1,
        price=0,
        pronoun="套"
    ),
    6: Item(
        id=6,
        name="\"Astraios\" 外太空生命维持系统",
        desc="旧世纪常见的生命维持系统，因其低廉的价格和高效的性能被 MAZE 雇佣兵团作为标准生命维持工具。",
        rarity=Rarity.RARE,
        tags=[Tag.WEARABLE],
        maxcount=1,
        price=0,
        pronoun="件"
    ),
    7: Item(
        id=7,
        name="\"保卫者\" 轻型手枪",
        desc="来自 MAZE 雇佣兵团的基本防护工具套装，是兼具便携性和杀伤性的武器，可惜已经脱离时代太久了。",
        rarity=Rarity.COMMON,
        tags=[Tag.WEAPON],
        maxcount=1,
        price=0,
        pronoun="把"
    ),
    8: Item(
        id=8,
        name="嶙矿",
        desc="凯罗尔星特产矿石，是涅普顿军团最常用的材料之一。这种矿石拥有两种冶炼方法，能够冶炼出坚硬，高强度或轻盈，高韧性的合金材料，涅普顿军团的舰体装甲中常常包含这种合金材料。",
        rarity=Rarity.UNCOMMON,
        tags=[Tag.RESOURCE, Tag.SALEABLE],
        maxcount=150,
        price=24,
        pronoun="块"
    ),
    9: Item(
        id=9,
        name="小狗模型？",
        desc="一只可爱的，身上有着橙灰色花纹的小狗模型...戴着三角巾，额头上还有一个白色类似月亮的印记，且印记边缘是橙色的。\n这只小狗似乎住在忒利亚星的沙漠里...？",
        rarity=Rarity.EPIC,
        tags=[Tag.SPECIAL],
        maxcount=1,
        price=0,
        pronoun="个"
    ),
    10: Item(
        id=10,
        name="通讯器",
        desc="一个奇怪的通讯器...上面有些许紫色纹路",
        rarity=Rarity.MYSTIC,
        tags=[Tag.SPECIAL],
        maxcount=1,
        price=0,
        pronoun="个",
        use=item_methods.talk_to_bot
    ),
    11: Item(
        id=11,
        name="刮奖彩票（20）",
        desc="一张价值 20 星币的刮奖彩票，刮一刮尝试一下？",
        rarity=Rarity.COMMON,
        tags=[Tag.SALEABLE],
        maxcount=10,
        price=20,
        pronoun="张",
        action_args={
            "use": {
                "price": 20,
            }
        },
        use=item_methods.use_ticket
    ),
    12: Item(
        id=12,
        name="飞船补给",
        desc="用于舰船维护的生活补给品，需要消耗一定数量用于远征。",
        rarity=Rarity.COMMON,
        tags=[Tag.SALEABLE],
        maxcount=225,
        price=22,
        pronoun="箱",
        action_args={
        },
    ),
    13: Item(
        id=13,
        name="废旧金属",
        desc="生锈与破损的金属外壳，或许可以拿去回收？",
        rarity=Rarity.COMMON,
        tags=[Tag.SALEABLE],
        maxcount=100,
        price=8,
        pronoun="块",
        action_args={
        },
    ),
    14: Item(
        id=14,
        name="矿石",
        desc="高纯度的各类矿石，蕴含很高的商业与加工价值。",
        rarity=Rarity.COMMON,
        tags=[Tag.SALEABLE],
        maxcount=250,
        price=15,
        pronoun="块",
        action_args={
        },
    ),
    15: Item(
        id=15,
        name="坭能电池",
        desc="相比于传统电池不同，这类电池存储坭能，且体积较大，拥有足够的能量供于飞船。",
        rarity=Rarity.UNCOMMON,
        tags=[Tag.SALEABLE],
        maxcount=10,
        price=500,
        pronoun="块",
        action_args={
        },
    ),
    16: Item(
        id=16,
        name="零件",
        desc="加工所用的工业零件，在制作或维修物品方面会有需要。当然，也是很不错的交易材料。",
        rarity=Rarity.COMMON,
        tags=[Tag.SALEABLE],
        maxcount=200,
        price=10,
        pronoun="盒",
        action_args={
        },
    ),
}