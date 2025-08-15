from html2image import Html2Image
from PIL import Image, ImageChops
from xme.xmetools.texttools import limit_str_len
from xme.xmetools.randtools import messy_string, random_percent
import os
from xme.xmetools.imgtools import crop_transparent_area
hti = Html2Image()

def get_comment_html(messy_rate: int | float, comment_list: list[dict]):
    infos = [
        "[{id}] {name}",
        '："{comment_content}"',
        '点赞 {likes} - 混乱程度 {messy}%',
        '还有 {comments} 条留言...',
    ]
    comment_html = """<p><span class="colored">{info0}</span>{info1}<span class="colored small-like">{info2}</span></p>"""
    # comment_suffix = """<p style="color: #bbb;">{info3}</p>"""
    if len(comment_list) < 1:
        comment_content = f"""<p style="color: #bbb;">{messy_string('什么都没有呢...', messy_rate)}</p>"""
        return comment_content
    comment_htmls = []
    for i, comment in enumerate(comment_list):
        card_messy_rate = min(100, max(0, messy_rate - (comment["likes"] * 3)))
        comment_html_content = comment_html.format(
            info0=messy_string(infos[0].format(id=f"#{i + 1}", name=limit_str_len(comment["sender"], 12)), card_messy_rate),
            info1=messy_string(infos[1].format(comment_content=comment["content"]), card_messy_rate),
            info2=messy_string(infos[2].format(likes=comment["likes"], messy=card_messy_rate), card_messy_rate) + "\n")

        if len(comment_htmls) < 1:
            comment_htmls.append(comment_html_content)
            continue
        comment_htmls.append(comment_html_content)
    return "\n".join(comment_htmls)

def get_bottle_card_html(id, messy_rate_str, messy_rate: int | float, date, content, sender, group, views, likes, comments_list, custom_suffix=""):
    content = f'"{content}"'
    comments = get_comment_html(messy_rate, comments_list)
    formated_content = [f'<p class="main_content">{messy_string(c, messy_rate).replace("<", "&lt;").replace(">", "&gt;").replace(" ", "&nbsp;")}</p>' for c in content.replace("\n", "\r").split("\r")]
    info_texts = [
        "#{id} - 混乱程度：{messy_rate}".format(id=id, messy_rate=messy_rate_str),
        date,
        'by "{sender}"（来自群 "{group}"）'.format(sender=limit_str_len(sender, 10), group=limit_str_len(group, 10)),
        "拾取 {views} - 点赞 {likes}".format(views=views, likes=likes),
        "- 漂流瓶留言 -",
    ]
    info_texts = [messy_string(i, messy_rate).replace("<", "&lt;").replace(">", "&gt;").replace(" ", "&nbsp;") for i in info_texts]
    # print(info_texts)
    default_suffix = """<p class="colored">- 发送下面的消息来执行对应操作 -</p>
                <ul class="operateul">
                    <li><p><span class="code">-like</span> / <span class="code">-rep</span> / <span class="code">-pure</span></p><p>点赞 / 举报 / 申请纯净</p></li>
                    <li><p><span class="code">-say <span style="color: #3cd3d8;">(留言内容)</span></span> / <span class="code">-likesay <span style="color: #3cd3d8;">(留言编号)</span></span></p><p>留言 / 点赞留言</p></li>
                </ul>"""
    html_style = """<style>
                body {
        font-family: "Helvetica Neue", "Segoe UI", sans-serif;
        background-color: transparent;
        color: #333;
        margin: 0;
        padding: 20px;
        }

        main {
        background-color: #1B1F26;
        color: #eee;
        max-width: 600px;
        margin: auto;
        border-radius: 12px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05);
        padding: 20px;
        }

        .main_content {
            font-size: 1.2em;
            font-weight: bold;
            text-indent: 2em;
        }

        .small {
        font-size: 0.9em;
        color: #666;
        display: flex;
        justify-content: space-between;
        align-items: center;
        }

        .info {
        font-weight: bold;
        color: #3cd3d8;
        }

        hr {
        border: none;
        border-top: 1px solid #444;
        margin: 15px 0;
        }

        p {
        line-height: 1.6;
        margin: 10px 0;
        }

        .colored {
        color: #3cd3d8;
        font-weight: 500;
        }

        .infoul, .operateul {
        list-style: none;
        padding: 0;
        margin: 0;
        }

        .infoul {
            display: flex;
            align-items: center;
            justify-content: space-between;
            color: #ddd;
        }

        .small-like {
            float: right;
            font-size: 0.9em;
            padding-top: 5px;
            padding-right: 10px;
        }

        .operateul li {
        margin-bottom: 8px;
        }

        .infoul li.colored {
        font-weight: bold;
        color: #3cd3d8;
        }

        .comments p {
        background: #292b33;
        padding: 10px 12px;
        border-radius: 8px;
        margin: 6px 0;
        font-size: 0.95em;
        }

        .comments span.colored {
        color: #3cd3d8;
        font-weight: 500;
        }

        .code {
        font-family: "Courier New", monospace;
        background: #292b33;
        padding: 2px 6px;
        border-radius: 6px;
        color: #d63384;
        }

        .operateul {
            padding: 0 10px;
        }

        .operateul li {
            display: flex;
            justify-content: space-between;
        }

        .operateul li p:first-child {
        margin-bottom: 4px;
        }

        .operateul li p {
        margin: 0;
        font-size: 0.95em;
        }

        .operateul span {
        display: inline-block;
        }

            </style>"""
    html_text = """
    <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Document</title>
    <body>
            <main>
                <p style="padding: 0 10px;" class="small">
                    <span class="info">{info0}</span>
                    <span
                        style="color: #aaa; float: right; padding: 2px 5px;">{info1}</span>
                </p>
                <hr>
                {info2}
                <hr>
                <ul class="infoul">
                    <li>{info3}</li>
                    <li class="colored">{info4}</li>
                </ul>
                <hr>
                <p class="colored">{info5}</p>
                <div class="comments">
                    {comments}
                </div>
                <hr>
                {suffix}
            </main>
        </body>
    </html>
    """
    return html_style + html_text.format(info0=info_texts[0], info1=info_texts[1], info2="\n".join(formated_content), info3=info_texts[2], info4=info_texts[3], info5=info_texts[4], comments=comments, suffix=default_suffix if not custom_suffix else custom_suffix)


def get_card_image(html_str) -> Image.Image:
    hti.screenshot(html_str=html_str, save_as="bottlecard.png", size=(1920, 2500))
    image = crop_transparent_area("bottlecard.png")
    os.remove("bottlecard.png")
    return image