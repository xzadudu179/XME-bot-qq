from xme.xmetools.texttools import limit_str_len
from xme.xmetools.randtools import html_messy_string
from xme.plugins.commands.drift_bottle.tools.cards import CARD_SKINS
from xme.plugins.commands.drift_bottle import DriftBottle
def get_card_item(item_name: str, skin_name="默认卡片") -> str | dict | int | bool:
    item = CARD_SKINS.get(skin_name, CARD_SKINS["默认卡片"]).get(item_name, CARD_SKINS["默认卡片"][item_name])
    return item

def get_custom_card_html(skin_name="默认卡片"):
    colors: dict = get_card_item("colors", skin_name)
    styles = get_card_item("styles", skin_name)
    body = get_card_item("html_body", skin_name)
    color_vars = "\n".join([f"--{k}: {v};" for k, v in colors.items()])
    colors_str = f"""
        :root {{
            {color_vars}
        }}
    """
    html_style = "<style>" + colors_str + styles + "</style>"
    html_text = """
    <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Card</title>
    """+ body + "</html>"
    operate_tip = get_card_item("operate_tip", skin_name)
    return html_style, html_text, operate_tip

def get_comment_html(messy_rate: int | float, comment_list: list[dict], skin_name="默认卡片"):
    comment_html = get_card_item("comment", skin_name)
    no_comment = get_card_item("no_comment", skin_name)
    comment_content = get_card_item("comment_content", skin_name)
    infos = [
        "[{id}] {name}",
        comment_content,
        '点赞 {likes} - 混乱程度 {messy}%',
        '还有 {comments} 条留言...',
    ]
    # comment_html = """<p><span class="colored">{info0}</span>{info1}<span class="colored small-like">{info2}</span></p>"""
    comment_suffix = get_card_item("comment_suffix", skin_name)
    # print(comment_html)
    if len(comment_list) < 1:
        comment_content = no_comment.format(content=html_messy_string('什么都没有呢...', messy_rate))
        return comment_content
    comment_htmls = []
    for i, comment in enumerate(comment_list):
        card_messy_rate = min(100, max(0, messy_rate - (comment["likes"] * 3)))
        comment_html_content = comment_html.format(
            info0=html_messy_string(infos[0].format(id=f"#{i + 1}", name=limit_str_len(comment["sender"], get_card_item("comment_name_len", skin_name))), card_messy_rate),
            info1=html_messy_string(infos[1].format(comment_content=comment["content"]), card_messy_rate),
            info2=html_messy_string(infos[2].format(likes=comment["likes"], messy=card_messy_rate), card_messy_rate) + "\n")

        if len(comment_htmls) < 1:
            comment_htmls.append(comment_html_content)
            continue
        # 留言大于十条
        if i + 1 > 10:
            comment_htmls.append(comment_suffix.format(comments=len(comment_htmls - 10)))
            break
        comment_htmls.append(comment_html_content)
    return "\n".join(comment_htmls)

def get_example_bottle(skin_name="默认卡片"):
    from xme.plugins.commands.drift_bottle import EXAMPLE_BOTTLE
    return get_class_bottle_card_html(EXAMPLE_BOTTLE, skin_name=skin_name)

def get_class_bottle_card_html(bottle: DriftBottle, messy_rate=None, messy_rate_str=None, custom_tip="", skin_name="默认卡片"):
    if messy_rate is None:
        messy_rate = min(100, max(0, bottle.views * 2 - bottle.likes * 3))
    if messy_rate_str is None:
        messy_rate_str = f"{messy_rate}%"
    return get_bottle_card_html(
        id=bottle.bottle_id,
        messy_rate_str=messy_rate_str,
        messy_rate=messy_rate,
        date=bottle.send_time,
        content=bottle.content.format(views=bottle.views, likes=bottle.likes, messy_rate=messy_rate_str, sender=bottle.sender, group=bottle.from_group, id=bottle.bottle_id),
        sender=bottle.sender,
        group=bottle.from_group,
        views=bottle.views,
        likes=bottle.likes,
        comments_list=bottle.comments,
        custom_tip=custom_tip,
        skin_name=skin_name,
    )

def get_bottle_card_html(id, messy_rate_str, messy_rate: int | float, date, content, sender, group, views, likes, comments_list, custom_tip="", skin_name="默认卡片"):
    content = f'"{content}"'
    str_len = get_card_item("str_len", skin_name)
    comments = get_comment_html(messy_rate, comments_list, skin_name=skin_name)
    formated_content = [f'<p class="main_content">{html_messy_string(c, messy_rate)}</p>' for c in content.replace("\n", "\r").split("\r")]
    info_texts = [
        "#{id} - 混乱程度：{messy_rate}".format(id=id, messy_rate=messy_rate_str),
        date,
        limit_str_len('by "{sender}"（来自 "{group}"）'.format(sender=sender, group=group), str_len),
        "拾取 {views} - 点赞 {likes}".format(views=views, likes=likes),
        # "- 漂流瓶留言 -",
        get_card_item("comment_message", skin_name),
    ]
    info_texts = [html_messy_string(i, messy_rate) for i in info_texts]
    html_style, html_text, operate_tip = get_custom_card_html(skin_name)
    operate_tip = operate_tip if not custom_tip else custom_tip
    return html_style + html_text.format(info0=info_texts[0], info1=info_texts[1], info2="\n".join(formated_content), info3=info_texts[2], info4=info_texts[3], info5=info_texts[4], comments=comments, suffix=operate_tip)