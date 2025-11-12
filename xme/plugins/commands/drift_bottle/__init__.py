__plugin_name__ = '漂流瓶'
from xme.xmetools import texttools
from xme.xmetools.doctools import PluginDoc
from xme.xmetools.imgtools import image_to_base64, get_image
from xme.xmetools.randtools import messy_image
from character import get_message
from keys import BOTTLE_IMAGE_KEY
from xme.xmetools.dbtools import DATABASE
from xme.xmetools.texttools import FormatDict, html_text
import json
BOTTLE_IMAGES_PATH = "./data/images/driftbottle/"

class DriftBottle:
    def __init__(self, bottle_id: str="我是妖妻酒", id=-1, content='', sender='', likes=0, views=0, from_group='', send_time='', sender_id=0, comments: list=[], group_id=0, is_broken=False, skin="", images=[]):
        self.id = id
        self.bottle_id: str = bottle_id
        self.content: str = content
        self.sender = sender
        self.likes = likes
        self.views = views
        self.from_group = from_group
        self.send_time = send_time
        self.sender_id = sender_id
        self.comments = comments
        self.group_id = group_id
        self.is_broken = is_broken
        self.skin = skin
        # 存储图片文件名
        self.images = images

    def get_formatted_content(self, messy_rate_str, messy_rate):
        try:
            return self.content.format_map(
                FormatDict(
                    views=self.views,
                    likes=self.likes,
                    messy_rate=messy_rate_str,
                    sender=self.sender,
                    group=self.from_group,
                    id=self.bottle_id,
                    **{'.'.join(i.split(".")[:-1]): f'\n<img alt="{BOTTLE_IMAGE_KEY}" src="data:image/png;base64,{image_to_base64(messy_image(get_image(BOTTLE_IMAGES_PATH + i), messy_rate=messy_rate, max_messy_break=True))}" alt class="img">\n' for i in self.images},
                )
            )
        except:
            return self.content

    def get_table_name():
        return DriftBottle.__name__

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "bottle_id": self.bottle_id,
            "content": self.content,
            "sender": self.sender,
            "likes": self.likes,
            "views": self.views,
            "from_group": self.from_group,
            "send_time": self.send_time,
            "sender_id": self.sender_id,
            "comments": json.dumps(self.comments, ensure_ascii=False),
            "group_id": self.group_id,
            "is_broken": self.is_broken,
            "skin": self.skin,
            "images": json.dumps(self.images, ensure_ascii=False)
        }

    def exec_query(query: str, params=(), dict_data=False):
        return DATABASE.exec_query(query=query, params=params, dict_data=dict_data)

    def check_duplicate_bottle(content: str):
        bottles: list[DriftBottle] = [DriftBottle.form_dict(b) for b in DriftBottle.exec_query(query=f"SELECT * FROM {DriftBottle.get_table_name()}", dict_data=True)]
        for bottle in bottles:
            if not bottle.bottle_id.isdigit():
                continue
            if texttools.difflib_similar(content, bottle.content, False) > 0.75 and bottle.views < 114514 and (bottle.likes <= bottle.views // 2) and not bottle.is_broken:
                return {
                    "status": False,
                    "content": bottle.content,
                    "duplicate_bottle_id": bottle.bottle_id
                }
        return {
            "status": True,
            "content": '',
            "duplicate_bottle_id": None,
        }

    def remove_self(self):
        """从数据表里移除自己并保存（改为 标记为broken）
        """
        # DATABASE.remove(DriftBottle.get_table_name(), f"bottle_id = '{self.bottle_id}'")
        self.is_broken = True
        self.save()

    def get_max_bottle_id():
        query = f"""SELECT COALESCE(MAX(CAST(bottle_id AS REAL)), 0)
                    FROM {DriftBottle.__name__}
                    WHERE bottle_id GLOB '[0-9]*';"""
        result = DriftBottle.exec_query(query=query, dict_data=True)[0]
        print(result)
        return int(result['COALESCE(MAX(CAST(bottle_id AS REAL)), 0)'])

    def get(bottle_id: str) -> 'DriftBottle':
        result = DATABASE.load_class(select_keys=(bottle_id,), query="SELECT * FROM {table_name} WHERE bottle_id = ?", cl=DriftBottle)
        if result is None:
            return None
        return result

    def save(self):
        self.id = DATABASE.save_to_db(self)

    def form_dict(data: dict) -> 'DriftBottle':
        # print(data)
        images = data.get('images', '[]')
        if images is None:
            images = '[]'
        return DriftBottle(
            id=data["id"],
            bottle_id=data["bottle_id"],
            content=data["content"],
            sender=data['sender'],
            likes=data['likes'],
            views=data['views'],
            from_group=data['from_group'],
            send_time=data['send_time'],
            sender_id=data['sender_id'],
            comments=json.loads(data['comments']),
            group_id=data['group_id'],
            is_broken=data.get('is_broken', False),
            skin=data.get('skin', ""),
            images=json.loads(images),
        )


def get_random_bottle() -> DriftBottle:
    table_name = DriftBottle.get_table_name()
    return DriftBottle.form_dict(DriftBottle.exec_query(query=f"SELECT * FROM {table_name} WHERE is_broken != TRUE ORDER BY RANDOM() LIMIT 1", dict_data=True)[0])

commands = ['throw', 'pickup']
command_properties = [
    {
        'name': 'throw',
        'introduction': get_message("plugins", __plugin_name__, 'throw_introduction'),
        'usage': '(瓶子内容)',
        'permission': ['在群内使用']
    },
    {
        'name': 'pickup',
        'introduction': get_message("plugins", __plugin_name__, 'pickup_introduction'),
        'usage': '',
        'permission': []
    },
    {
        'name': 'cthulhu',
        'introduction': get_message("plugins", __plugin_name__, 'cthulhu_introduction'),
        'usage': '(瓶子id 以空格分隔)',
        'permission': ['是 SUPERUSER']
    },
    {
        'name': 'check',
        'introduction': get_message("plugins", __plugin_name__, 'check_introduction'),
        'usage': '(瓶子id)',
        'permission': ['是 SUPERUSER']
    },
    {
        'name': 'seek',
        'introduction': get_message('plugins', __plugin_name__, 'seek_introduction'),
        'usage': '<操作>',
        'permission': ''
    }
]
DATABASE.create_class_table(DriftBottle())


from .throw import *
from .pickup import *
from .cthulhu import *
from .check import *
from .pure import *
from .seek import *

aliases = [
    throw_alias,
    pickup_alias,
    cthulhu_alias
]
__plugin_usage__ = str(PluginDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    # desc="漂流瓶相关指令",
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    # introduction="扔/捡来自各个群组的漂流瓶~",
    contents=[f"{prop['name']}: {prop['introduction']}" for prop in command_properties],
    usages=[f"{prop['name']} {prop['usage']}" for prop in command_properties],
    permissions=[prop['permission'] for prop in command_properties],
    alias_list=aliases
))

EXAMPLE_BOTTLE = DriftBottle(
    bottle_id="1179?",
    content="这是一个用来演示漂流瓶卡片效果的瓶子~\n\n这个瓶子是虚拟的哦",
    sender="漠月和他的550W",
    likes=5,
    views=10,
    from_group="世界之外的一个神秘区域...",
    send_time="2025年11月11日 11:23:45",
    sender_id=0,
    comments=[
        {"sender": "九镹_xzadudu179", "sender_id": 1795886524, "content": "好诶，是漠月~ 那我就在这里留下一条长长的评论吧~", "likes": 1},
        {"sender": "九镹_xzadudu179", "sender_id": 1795886524, "content": "摸摸漠月~ 第二次捡到了", "likes": 1}

    ],
)