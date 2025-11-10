from ..classes.good import Good
from ..tools.good import get_good_from_id
from ..static.templates import COLORS, FONTS_STYLE
from xme.plugins.commands.xme_user.classes.user import User
import string
from xme.xmetools.numtools import to_nums_base

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

