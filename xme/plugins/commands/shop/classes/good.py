from xme.plugins.commands.shop import __plugin_name__
from PIL.Image import Image
from xme.plugins.commands.xme_user.classes.user import User
import random
random.seed()
from xme.xmetools.msgtools import send_session_msg
from xme.xmetools.imgtools import read_image, image_to_base64
from character import get_message
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
        from ..static.templates import COLORS, FONTS_STYLE
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
