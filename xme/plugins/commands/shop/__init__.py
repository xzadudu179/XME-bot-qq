from xme.plugins.commands.drift_bottle import __plugin_name__ as bottle_plugin_name
from xme.plugins.commands.xme_user.classes.user import User, using_user
import random
from xme.xmetools.filetools import b64_encode_file
from xme.xmetools.numtools import to_nums_base
from xme.xmetools.dicttools import set_value
import string
from PIL.Image import Image
random.seed()
from xme.xmetools.msgtools import send_session_msg
from xme.xmetools.imgtools import read_image, image_to_base64, image_msg
from nonebot import on_command, CommandSession
# from xme.plugins.commands.jrrp.luck_algorithm import get_luck
from xme.xmetools.imgtools import get_html_image
from xme.xmetools.doctools import CommandDoc
from character import get_message

alias = ["星币商店" , "商店"]
__plugin_name__ = 'shop'

__plugin_usage__= str(CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    usage=f'shop <物品序号>',
    permissions=[],
    alias=alias
))

COLORS = """
:root {
    --color-primary: #97DAFF;
    --color-primary2: #78B9FF;
    --bg-color: #020211;
    --text-color: #E7ECFF;
    --grey-color: #8187AA;
    --code-color: #8187AA55;
    --border-color: #5D617D;
}
"""
FONTS_STYLE = f"""
@font-face {{
    font-family: 'Melete';
    src: url(data:font/otf;base64,{b64_encode_file('./static/fonts/Melete/Melete-Regular.otf')}) format('opentype');
    font-weight: normal;
    font-style: normal;
}}
@font-face {{
    font-family: 'Melete';
    src: url(data:font/otf;base64,{b64_encode_file('./static/fonts/Melete/Melete-Light.otf')}) format('opentype');
    font-weight: 300;
    font-style: normal;
}}
@font-face {{
    font-family: 'Melete';
    src: url(data:font/otf;base64,{b64_encode_file('./static/fonts/Melete/Melete-UltraLight.otf')}) format('opentype');
    font-weight: 100;
    font-style: normal;
}}
@font-face {{
    font-family: 'Melete';
    src: url(data:font/otf;base64,{b64_encode_file('./static/fonts/Melete/Melete-Medium.otf')}) format('opentype');
    font-weight: 500;
    font-style: normal;
}}
@font-face {{
    font-family: 'Melete';
    src: url(data:font/otf;base64,{b64_encode_file('./static/fonts/Melete/Melete-Bold.otf')}) format('opentype');
    font-weight: 600;
    font-style: normal;
}}
@font-face {{
    font-family: 'Orbitron';
    src: url(data:font/ttf;base64,{b64_encode_file('./static/fonts/Orbitron/Orbitron Medium.ttf')}) format('truetype');
    font-weight: normal;
    font-style: normal;
}}
@font-face {{
    font-family: 'Orbitron';
    src: url(data:font/ttf;base64,{b64_encode_file('./static/fonts/Orbitron/Orbitron Light.ttf')}) format('truetype');
    font-weight: 300;
    font-style: normal;
}}
@font-face {{
    font-family: 'Orbitron';
    src: url(data:font/ttf;base64,{b64_encode_file('./static/fonts/Orbitron/Orbitron Bold.ttf')}) format('truetype');
    font-weight: 600;
    font-style: normal;
}}
@font-face {{
    font-family: 'Orbitron';
    src: url(data:font/ttf;base64,{b64_encode_file('./static/fonts/Orbitron/Orbitron Black.ttf')}) format('truetype');
    font-weight: 700;
    font-style: normal;
}}
"""

class Good:
    # 商品
    def __init__(self, id: int, name: str, introduction: str, image: str | Image | None = None, introduction_html: str | None = None, price: int = -1, buy_func=None, **kwargs):
        # 商品 id 用于判断是否已购买
        self.id: int = id
        # 商品名
        self.name: str = name
        # 商品介绍
        self.introduction: str = introduction
        self.introduction_html: str = introduction_html if introduction_html is not None else introduction
        # 商品价格
        self.price: int = price
        # 商品展示图
        if image is not None:
            self.image: Image = image if isinstance(image, Image) else read_image(image)
        else:
            self.image = read_image("./static/img/desert.avif")
        self.buy_func = buy_func
        self.kwargs = kwargs
        # TODO 商品头像
        ...


    def is_user_bought(self, user: User):
        return self.id in user.plugin_datas.get(__plugin_name__, [])

    def __str__(self):
        return f"- {self.name} -\n---------------------------\n{self.introduction}\n---------------------------"

    def get_html_information(self) -> str:
        introduction = '\n'.join(['<p>' + n + '</p>' for n in self.introduction_html.split('\n')])
        return """
            <!DOCTYPE html>
            <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>shopcheck</title>
                    <style>
                        """ + COLORS + FONTS_STYLE + """
                        .orbitron {
                            font-family: "Orbitron";
                            letter-spacing: 0.05em;
                        }

                        .electrolize {
                            font-family: "Electrolize";
                        }

                        .melete {
                            font-family: "Melete";
                        }

                        * {
                            margin: 0;
                            padding: 0;
                            box-sizing: border-box;
                        }

                        body {
                            font-family: "Geist Variable", -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", "Heiti SC", "WenQuanYi Micro Hei", sans-serif;
                            background: transparent;
                            color: var(--text-color);
                        }

                        main {
                            background: var(--bg-color);
                            width: 800px;
                            /* min-height: 600px; */
                            border-radius: 30px;
                            padding: 30px;
                            /* border: 4px solid var(--border-color); */
                        }

                        .colored {
                            color: var(--color-primary);
                        }

                        .shopimg {
                            max-width: 700px;
                            border-radius: 30px;
                        }

                        .img-container {
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            margin-top: 20px;
                        }

                        .info {
                            margin-top: 30px;
                            font-size: 1.1rem;
                        }

                        h2 {
                            text-align: center;
                            font-weight: normal;
                            font-size: 1.5rem;
                        }

                        h1 {
                            text-align: center;
                            font-size: 1.8em;
                            margin: 0;
                            font-weight: normal;
                        }

                        .code {
                            background-color: var(--code-color);
                            padding: 5px 8px;
                            border-radius: 10px;
                        }

                        .introduction {
                            line-height: 2.2rem;
                            padding: 15px 20px;
                            margin: 20px;
                            border: 2px solid var(--border-color);
                            border-top: 0;
                            border-bottom: 0;
                            border-radius: 10px;
                        }

                        .price {
                            text-align: right;
                        }
                    </style>
                </head>
        """ + f"""
                <body>
                    <main>
                        <h1 class="melete">- INFOMATION -</h1>
                        <div class="img-container">
                            <img src="data:image/png;base64,{image_to_base64(self.image)}" alt class="shopimg">
                        </div>
                        <div class="info orbitron">
                            <h2 class="colored">- {self.name} -</h2>
                            <div class="introduction">
                                {introduction}
                                <p class="colored price">${self.price}</p>
                            </div>
                        </div>
                    </main>
                </body>
            </html>"""

    async def spend(self, session, user: User) -> bool:
        """花费方法

        Args:
            session: 发消息所用的 session
            user (User): 购买商品的用户

        Returns:
            bool: 是否花费成功
        """
        # 默认花费星币
        if self.price == -1:
            raise ValueError(f"未定义商品 \"{self.name}\" 的花费方法")
        if self.price == 0:
            return True
        stats, _ = user.spend_coins(self.price)
        coins_left = user.coins
        if self.is_user_bought(user):
            await send_session_msg(session, get_message("plugins", __plugin_name__, 'has_bought', coins=self.price, good=self.name, coins_left=coins_left), tips=True)
            return False
            # raise ValueError(f"商品 \"{self.name}\" 已被购买")
        if stats:
            await send_session_msg(session, get_message("plugins", __plugin_name__, 'default_buy', coins=self.price, good=self.name, coins_left=coins_left), tips=True)
        else:
            await send_session_msg(session, get_message("plugins", __plugin_name__, 'default_buy_error', price=self.price, good=self.name, coins_left=coins_left),  tips=True)
        return stats

    async def buy(self, session, user: User):
        """购买物品

        Args:
            session (CommandSession): 用户会话
            user (User): 用户
        """
        if self.buy_func is None:
            raise ValueError(f"未定义商品 \"{self.name}\" 的购买方法")
        result = await self.spend(session, user)
        buy_result = self.buy_func(self, result, user, **self.kwargs)
        if user.plugin_datas.get(__plugin_name__, None) is None:
            user.plugin_datas[__plugin_name__] = []
        user.plugin_datas[__plugin_name__].append(self.id)
        return buy_result


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
        introduction="漂流瓶卡片的装饰物，购买后会添加到漂流瓶卡片皮肤收藏。\n使用 \"/custom bottle\" 来改变你的漂流瓶样式。",
        image=None,
        introduction_html='漂流瓶卡片的装饰物，购买后会添加到漂流瓶卡片皮肤收藏。\n使用 <span class="code">/custom bottle</span> 来改变你的漂流瓶样式。',
        price=400,
        buy_func=bottle_card_func,
        card_name="漂流瓶卡片-基础黄色",
    ),
    Good(
        id=1,
        name="漂流瓶卡片-基础红色",
        introduction="漂流瓶卡片的装饰物，购买后会添加到漂流瓶卡片皮肤收藏。\n使用 \"/custom bottle\" 来改变你的漂流瓶样式。",
        image=None,
        introduction_html='漂流瓶卡片的装饰物，购买后会添加到漂流瓶卡片皮肤收藏。\n使用 <span class="code">/custom bottle</span> 来改变你的漂流瓶样式。',
        price=400,
        buy_func=bottle_card_func,
        card_name="漂流瓶卡片-基础红色",
    ),
    Good(
        id=2,
        name="漂流瓶卡片-基础绿色",
        introduction="漂流瓶卡片的装饰物，购买后会添加到漂流瓶卡片皮肤收藏。\n使用 \"/custom bottle\" 来改变你的漂流瓶样式。",
        image=None,
        introduction_html='漂流瓶卡片的装饰物，购买后会添加到漂流瓶卡片皮肤收藏。\n使用 <span class="code">/custom bottle</span> 来改变你的漂流瓶样式。',
        price=400,
        buy_func=bottle_card_func,
        card_name="漂流瓶卡片-基础绿色",
    ),
    Good(
        id=3,
        name="漂流瓶卡片-基础粉色",
        introduction="漂流瓶卡片的装饰物，购买后会添加到漂流瓶卡片皮肤收藏。\n使用 \"/custom bottle\" 来改变你的漂流瓶样式。",
        image=None,
        introduction_html='漂流瓶卡片的装饰物，购买后会添加到漂流瓶卡片皮肤收藏。\n使用 <span class="code">/custom bottle</span> 来改变你的漂流瓶样式。',
        price=400,
        buy_func=bottle_card_func,
        card_name="漂流瓶卡片-基础粉色",
    ),
]

def get_good_from_id(id: int) -> Good:
    goods = DECORATIONS
    for g in goods:
        if id != g.id:
            continue
        return g
    return None

class CoinShop:
    def __init__(self, goods: dict[str, list[Good]]):
        self.goods = goods
        self.good_serials = {}
        self.gen_good_serials()

    def get_good_from_serial(self, serial: str) -> Good | None:
        serial = serial.upper()
        return get_good_from_id(self.good_serials.get(serial, None))

    def gen_good_serials(self):
        """生成当前商品序号
        """
        for i, (good_type, goods) in enumerate(self.goods.items()):
            letter = to_nums_base(i, list(string.ascii_uppercase))
            # print(i, letter, goods)
            for j, g in enumerate(goods):
                self.good_serials[f"{letter}{j}"] = g.id

    def get_good_item_html(self, serial: str, user: User):
        good: Good | None = self.get_good_from_serial(serial)
        if good is None:
            raise ValueError(f"序号 {serial} 所对应的商品不存在")
        p_class = 'class="grey"' if good.is_user_bought(user) else ""
        return f"""<div class="item">
                    <p {p_class}><span class="grey">{serial}.</span>{good.name}</p>
                    <p class="colored">${good.price}</p>
                </div>"""

    def get_goods_html(self, user: User):
        result = ""
        serials = {v: k for k, v in self.good_serials.items()}
        # print(serials)
        for good_type, goods in self.goods.items():
            htmls = []
            result += f"""<div class="subtitle orbitron">
                            <h2># {good_type}</h2>
                        </div>"""
            for g in goods:
                htmls.append(self.get_good_item_html(serials[g.id], user))
            result += '<div class="items orbitron">' + "\n".join(htmls) + '</div>'
        return result
    def get_html_card(self, user: User):
        return """
                    <!DOCTYPE html>
                    <html lang="en">
                        <head>
                            <meta charset="UTF-8">
                            <meta name="viewport" content="width=device-width, initial-scale=1.0">
                            <title>shopcheck</title>
                            <style>
                                """ + COLORS + FONTS_STYLE + """
                    .orbitron {
                        font-family: "Orbitron";
                        letter-spacing: 0.05em;
                    }

                    .electrolize {
                        font-family: "Electrolize";
                    }

                    .melete {
                        font-family: "Melete";
                    }

                    * {
                        margin: 0;
                        padding: 0;
                        box-sizing: border-box;
                    }

                    body {
                        font-family: "Geist Variable", -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", "Heiti SC", "WenQuanYi Micro Hei", sans-serif;
                        background: transparent;
                        color: var(--text-color);
                    }

                    main {
                        background: var(--bg-color);
                        width: 1200px;
                        /* min-height: 600px; */
                        border-radius: 30px;
                        padding: 30px;
                        /* border: 4px solid var(--border-color); */
                    }

                    .colored {
                        color: var(--color-primary);
                    }

                    h1 {
                        text-align: center;
                        font-size: 2em;
                        margin: 0;
                        font-weight: normal;
                    }

                    h2 {
                        font-weight: normal;
                        margin: 0;
                    }

                    .items {
                        display: grid;
                        grid-template-columns: repeat(3, minmax(0, 1fr));
                        gap: 12px;
                        border-radius: 10px;
                        padding: 10px 0;
                        border: 2px solid var(--border-color);
                        border-top: 0;
                        border-bottom: 0;
                    }

                    .title {
                        margin-bottom: 30px;
                    }

                    .grey {
                        color: var(--grey-color);
                    }

                    .item {
                        /* border: 1px solid red; */
                        padding: 5px 0;
                        margin: 0 20px;
                        font-size: 1.2rem;
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                    }

                    .subtitle {
                        margin: 10px;
                        font-size: 1.2em;
                    }

                </style>
            </head>
            <body>
                <main class="melete">
                    <div class="title">
                        <h1>-- STARSHOP --</h1>
                    </div>
                        """ + self.get_goods_html(user) + """
                    </main>
                </body>
            </html>"""



SHOP = CoinShop({
    "Decorations": DECORATIONS
})

@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda _: True)
@using_user(save_data=True)
async def _(session: CommandSession, user: User):
    arg = session.current_arg_text.strip()
    if not arg:
        # 默认展示商店
        img = get_html_image(SHOP.get_html_card(user))
        return await send_session_msg(session, get_message("plugins", __plugin_name__, "shop_card", image=await image_msg(img)), tips=True)

    # 有参数情况下
    good: Good | None = SHOP.get_good_from_serial(arg)
    if good is None:
        return await send_session_msg(session, get_message("plugins", __plugin_name__, "no_good", serial=arg), tips=True)
    good_image = get_html_image(good.get_html_information())
    # 有商品情况下
    good_img_msg = await image_msg(good_image)
    if good.is_user_bought(user):
        return await send_session_msg(session, get_message("plugins", __plugin_name__, "good_card_bought", image=good_img_msg), tips=True)
    reply = await session.aget(prompt=get_message("plugins", __plugin_name__, "good_card", image=good_img_msg, price=good.price))
    if reply != "y":
        return False
    result = await good.buy(session, user)
    return result