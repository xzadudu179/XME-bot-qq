from ..classes.good import Good
from .templates import IMG_PREFIX
from xme.xmetools.dicttools import set_value
from xme.plugins.commands.xme_user.classes.user import User
from xme.plugins.commands.drift_bottle import __plugin_name__ as bottle_plugin_name

def bottle_card_func(_: Good, spend_result: bool, user: User, card_name: str):
    # 购买失败
    if not spend_result:
        return False
    # 购买成功
    set_value(bottle_plugin_name, "custom_cards", search_dict=user.plugin_datas, set_method=lambda value: value + [card_name] if isinstance(value, list) else [card_name])
    return True


DECORATIONS = [
    Good(
        id=0,
        name="漂流瓶卡片-基础黄色",
        introduction="漂流瓶卡片的装饰物，购买后会添加到漂流瓶卡片皮肤收藏。\n使用 \"/cus bottle\" 指令来设置你的漂流瓶样式。",
        image=IMG_PREFIX + "bottle_examples/yellow.png",
        introduction_html='漂流瓶卡片的装饰物，购买后会添加到漂流瓶卡片皮肤收藏。\n使用 <span class="code">/cus bottle</span> 指令来设置你的漂流瓶样式。',
        price=300,
        buy_func=bottle_card_func,
        card_name="漂流瓶卡片-基础黄色",
    ),
    Good(
        id=1,
        name="漂流瓶卡片-基础红色",
        introduction="漂流瓶卡片的装饰物，购买后会添加到漂流瓶卡片皮肤收藏。\n使用 \"/cus bottle\" 指令来设置你的漂流瓶样式。",
        image=IMG_PREFIX + "bottle_examples/red.png",
        introduction_html='漂流瓶卡片的装饰物，购买后会添加到漂流瓶卡片皮肤收藏。\n使用 <span class="code">/cus bottle</span> 指令来设置你的漂流瓶样式。',
        price=300,
        buy_func=bottle_card_func,
        card_name="漂流瓶卡片-基础红色",
    ),
    Good(
        id=2,
        name="漂流瓶卡片-基础绿色",
        introduction="漂流瓶卡片的装饰物，购买后会添加到漂流瓶卡片皮肤收藏。\n使用 \"/cus bottle\" 指令来设置你的漂流瓶样式。",
        image=IMG_PREFIX + "bottle_examples/green.png",
        introduction_html='漂流瓶卡片的装饰物，购买后会添加到漂流瓶卡片皮肤收藏。\n使用 <span class="code">/cus bottle</span> 指令来设置你的漂流瓶样式。',
        price=300,
        buy_func=bottle_card_func,
        card_name="漂流瓶卡片-基础绿色",
    ),
    Good(
        id=3,
        name="漂流瓶卡片-基础粉色",
        introduction="漂流瓶卡片的装饰物，购买后会添加到漂流瓶卡片皮肤收藏。\n使用 \"/cus bottle\" 指令来设置你的漂流瓶样式。",
        image=IMG_PREFIX + "bottle_examples/pink.png",
        introduction_html='漂流瓶卡片的装饰物，购买后会添加到漂流瓶卡片皮肤收藏。\n使用 <span class="code">/cus bottle</span> 指令来设置你的漂流瓶样式。',
        price=300,
        buy_func=bottle_card_func,
        card_name="漂流瓶卡片-基础粉色",
    ),
    Good(
        id=4,
        name="漂流瓶卡片-基础蓝色",
        introduction="漂流瓶卡片的装饰物，购买后会添加到漂流瓶卡片皮肤收藏。\n使用 \"/cus bottle\" 指令来设置你的漂流瓶样式。",
        image=IMG_PREFIX + "bottle_examples/blue.png",
        introduction_html='漂流瓶卡片的装饰物，购买后会添加到漂流瓶卡片皮肤收藏。\n使用 <span class="code">/cus bottle</span> 指令来设置你的漂流瓶样式。',
        price=300,
        buy_func=bottle_card_func,
        card_name="漂流瓶卡片-基础蓝色",
    ),
    Good(
        id=5,
        name="漂流瓶卡片-基础白色",
        introduction="漂流瓶卡片的装饰物，购买后会添加到漂流瓶卡片皮肤收藏。\n使用 \"/cus bottle\" 指令来设置你的漂流瓶样式。",
        image=IMG_PREFIX + "bottle_examples/white.png",
        introduction_html='漂流瓶卡片的装饰物，购买后会添加到漂流瓶卡片皮肤收藏。\n使用 <span class="code">/cus bottle</span> 指令来设置你的漂流瓶样式。',
        price=300,
        buy_func=bottle_card_func,
        card_name="漂流瓶卡片-基础白色",
    ),
]
