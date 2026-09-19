import asyncio

import numpy as np
import PIL.Image
from PIL.Image import Image
from xme.xmetools.texttools import limit_str_len
from xme.xmetools.randtools import html_messy_string, messy_string, messy_image
from character import get_message
from xme.xmetools.imgtools import get_html_image_async, get_image
from xme.xmetools.animtools import (
    assemble_composited_gif_within_size,
    find_slot_boxes,
    is_animated,
    load_anim_sequence,
)
from xme.plugins.commands.drift_bottle.tools.cards import CARD_SKINS
from xme.plugins.commands.drift_bottle import BOTTLE_IMAGES_PATH, DriftBottle
from keys import BOTTLE_IMAGE_KEY
from nonebot.log import logger
from xme.xmetools.debugtools import debug_msg

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

def get_comment_html(messy_rate: int | float, messy_rate_str: str, comment_list: list[dict], skin_name="默认卡片"):
    comment_html = get_card_item("comment", skin_name)
    no_comment = get_card_item("no_comment", skin_name)
    comment_content = get_card_item("comment_content", skin_name)
    infos = [
        "[{id}] {name}",
        comment_content,
        '点赞 {likes} - 混乱值: {messy}',
        '还有 {comments} 条留言...',
    ]
    # comment_html = """<p><span class="colored">{info0}</span>{info1}<span class="colored small-like">{info2}</span></p>"""
    comment_suffix = get_card_item("comment_suffix", skin_name)
    if len(comment_list) < 1:
        comment_content = no_comment.format(content=html_messy_string('什么都没有呢...', messy_rate))
        return comment_content
    comment_htmls = []
    for i, comment in enumerate(comment_list):
        card_messy_rate = min(100, max(0, messy_rate - (comment["likes"] * 3)))
        messy_str = f"{card_messy_rate}%" if messy_rate_str not in ["##未知##", "##纯洁无暇##"] else "未知"
        comment_html_content = comment_html.format(
            info0=html_messy_string(infos[0].format(id=f"#{i + 1}", name=limit_str_len(comment["sender"], get_card_item("comment_name_len", skin_name))), card_messy_rate),
            info1=html_messy_string(infos[1].format(comment_content=comment["content"]), card_messy_rate),
            info2=html_messy_string(infos[2].format(likes=comment["likes"], messy=messy_str), card_messy_rate) + "\n")

        if len(comment_htmls) < 1:
            comment_htmls.append(comment_html_content)
            continue
        comment_htmls.append(comment_html_content)
    # 留言大于十条
    if len(comment_list) > 10:
        comment_htmls_total = comment_htmls
        comment_htmls = comment_htmls[-10:]
        comment_htmls.append(comment_suffix.format(info3=infos[3].format(comments=len(comment_htmls_total) - 10)))
        # break
    return "\n".join(comment_htmls)

def has_animated_image(bottle: DriftBottle) -> bool:
    """判断瓶子是否包含动图图片"""
    return bool(bottle.images) and any(is_animated(get_image(BOTTLE_IMAGES_PATH + i)) for i in bottle.images)

async def get_pickedup_bottle_card(bottle: DriftBottle, suffix="", skin_name="默认卡片", image_messy_magni=0.5, view_minus=0) -> 'Image | bytes':
    """拾取卡片唯一入口：含动图的瓶子返回卡片 GIF bytes，否则返回静态卡片图

    动图在入库前已按体积预算校准抽帧，此处一般一次合成即可；
    若留言增长导致超预算，合成内部仍会循环抽帧兜底
    """
    from .. import __plugin_name__, get_messy_rate
    if str(bottle.bottle_id) == "-179" and not suffix:
        # bottle_card += "\n" + get_message("plugins", __plugin_name__, "response_prompt_broken")
        suffix = f'<p style="color: #D40"> -{get_message("plugins", __plugin_name__, "response_prompt_broken")}- </p>'
    messy_rate, messy_rate_string = get_messy_rate(bottle, view_minus)
    skin = skin_name if not bottle.skin else bottle.skin
    html_render = (not bottle.bottle_id.isdecimal() and "PURE " not in bottle.bottle_id) or bottle.bottle_id == "-179"
    if has_animated_image(bottle):
        # 动图卡片合成失败（如槽位定位失败、体积超限）时回退静态卡片
        gif_bytes = await get_animated_bottle_card(
            bottle=bottle,
            messy_rate=messy_rate,
            messy_rate_str=messy_rate_string,
            suffix=suffix,
            skin_name=skin,
            html_render=html_render,
            image_messy_magni=image_messy_magni,
        )
        if gif_bytes is not None:
            return gif_bytes
    bottle_card = messy_image(await get_html_image_async(get_class_bottle_card_html(
        bottle=bottle,
        messy_rate=messy_rate,
        messy_rate_str=messy_rate_string,
        custom_tip=suffix,
        skin_name=skin,
        html_render=html_render,
    )), messy_rate * image_messy_magni)
    return bottle_card

async def get_animated_bottle_card(bottle: DriftBottle, messy_rate, messy_rate_str, suffix="", skin_name="默认卡片", html_render=False, image_messy_magni=0.5) -> bytes | None:
    """合成含动图槽位的漂流瓶卡片 GIF（独立入口，供其他功能复用）

    卡片壳静态渲染一次并做整卡混乱处理，动图槽位以总时长最长的序列为主轴
    逐帧贴图，槽位区域每帧单独做混乱扰动（rate>=100 时为逐帧全噪声）；
    体积超限时循环抽帧并比对（时长补偿，长度不变），压不进预算返回 None
    （调用方回退静态卡片）
    """
    sequences = []
    for name in bottle.images:
        image = get_image(BOTTLE_IMAGES_PATH + name)
        if is_animated(image):
            sequences.append(load_anim_sequence(image))
    if not sequences:
        return None
    shell = await get_html_image_async(get_class_bottle_card_html(
        bottle=bottle,
        messy_rate=messy_rate,
        messy_rate_str=messy_rate_str,
        custom_tip=suffix,
        skin_name=skin_name,
        html_render=html_render,
        animated_placeholder=True,
    ))
    return await asyncio.to_thread(
        _compose_animated_card, shell, sequences, messy_rate, image_messy_magni)

def _cover_slot_colors(shell: Image, boxes: list[tuple[int, int, int, int]]) -> None:
    """把占位色块连同抗锯齿过渡边缘一起用局部背景色覆盖（就地修改）

    占位块渲染边缘有 1~2px 与背景混合的过渡像素，仅按定位框覆盖会残留
    紫色描边（混乱搬移后尤其明显），因此向外扩 2px 填充，颜色取占位块
    周边外圈像素的中位色以贴合渐变皮肤；填充随后被逐帧贴图覆盖大部分区域
    """
    arr = np.asarray(shell.convert("RGB"))
    height, width = arr.shape[:2]
    for x1, y1, x2, y2 in boxes:
        px1, py1, px2, py2 = max(0, x1 - 2), max(0, y1 - 2), min(width, x2 + 2), min(height, y2 + 2)
        ox1, oy1, ox2, oy2 = max(0, x1 - 8), max(0, y1 - 8), min(width, x2 + 8), min(height, y2 + 8)
        ix1, iy1, ix2, iy2 = max(0, x1 - 2), max(0, y1 - 2), min(width, x2 + 2), min(height, y2 + 2)
        strips = [arr[oy1:iy1, ox1:ox2], arr[iy2:oy2, ox1:ox2],
                  arr[iy1:iy2, ox1:ix1], arr[iy1:iy2, ix2:ox2]]
        ring = np.concatenate([s.reshape(-1, 3) for s in strips if s.size])
        fill = tuple(int(v) for v in np.median(ring, axis=0)) if len(ring) else (32, 34, 40)
        shell.paste(PIL.Image.new("RGB", (px2 - px1, py2 - py1), fill), (px1, py1))

def _compose_animated_card(shell: Image, sequences, messy_rate, image_messy_magni) -> bytes | None:
    """同步合成动图卡片：槽位定位、整卡混乱一次、逐帧贴图扰动与编码

    CPU 密集（逐帧量化编码），必须经后台线程执行
    """
    try:
        boxes = find_slot_boxes(shell, len(sequences))
    except ValueError as e:
        logger.warning(f"动图卡片槽位定位失败：{e}")
        return None
    _cover_slot_colors(shell, boxes)
    # 壳乱一次：与静态卡片同一参数，文字部分的混乱观感保持一致
    shell = messy_image(shell, messy_rate * image_messy_magni)

    def frame_messy(frame, frame_boxes):
        for box in frame_boxes:
            region = frame.crop(box)
            messy_region = messy_image(region, messy_rate, max_messy_break=True)
            # 带 alpha 蒙版回贴，透明底动图的透明区域保持透出卡片背景
            frame.paste(messy_region, box[:2], messy_region)
        return frame

    result = assemble_composited_gif_within_size(base_card=shell, paste_boxes=boxes,
                                                 sequences=sequences, frame_messy=frame_messy)
    if result is None:
        logger.warning("动图卡片体积超限，回退静态卡片")
        return None
    return result[0]

def get_example_bottle(skin_name="默认卡片"):
    # from xme.plugins.commands.drift_bottle import EXAMPLE_BOTTLE
    from xme.plugins.commands.drift_bottle import create_example_bottles
    return get_class_bottle_card_html(create_example_bottles()["EXAMPLE_BOTTLE"], skin_name=skin_name)

def get_class_bottle_card_html(bottle: DriftBottle, messy_rate=None, messy_rate_str=None, custom_tip="", skin_name="默认卡片", html_render=False, animated_placeholder=False):
    """构造瓶子卡片的完整 HTML；animated_placeholder 仅动态卡片合成时开启"""
    if messy_rate is None:
        messy_rate = min(100, max(0, bottle.views * 2 - bottle.likes * 3))
    if messy_rate_str is None:
        messy_rate_str = f"{messy_rate}%"
    html = get_bottle_card_html(
        id=bottle.bottle_id,
        messy_rate_str=messy_rate_str,
        messy_rate=messy_rate,
        date=bottle.send_time,
        content=bottle.get_formatted_content(messy_rate_str, messy_rate, animated_placeholder),
        sender=bottle.sender,
        group=bottle.from_group,
        views=bottle.views,
        likes=bottle.likes,
        comments_list=bottle.comments,
        custom_tip=custom_tip,
        skin_name=skin_name,
        html_render=html_render,
        images=bottle.images
    )
    # logger.info(html)
    return html

def get_bottle_card_html(id, messy_rate_str, messy_rate: int | float, date, content, sender, group, views, likes, comments_list, custom_tip="", images=[], skin_name="默认卡片", html_render=False):
    content: str = f'{content}'
    str_len = get_card_item("str_len", skin_name)
    comments = get_comment_html(messy_rate, messy_rate_str, comments_list, skin_name=skin_name)
    formatted_content = []
    # logger.info(content)
    # logger.info(str(content.replace("\n", "\r").split("\r")))
    for c in content.replace("\n", "\r").split("\r"):
        image_item_count = 0
        # logger.info(c)
        content = ""
        # 防止注入html的问题
        if c.startswith(f'<img alt="{BOTTLE_IMAGE_KEY}" src="data:image/png;base64,') and len(images) > 0 and image_item_count < len(images):
            debug_msg("处理图片")
            content = f'<p>{c}</p>'
            image_item_count += 1
            formatted_content.append(content)
            continue
        # 空行
        elif not c.rstrip():
            content = '<p></p>'
            formatted_content.append(content)
            continue
        content = f'<p class="main_content">{html_messy_string(c, messy_rate) if not html_render else messy_string(c, messy_rate)}</p>'
        formatted_content.append(content)

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
    return html_style + html_text.format(info0=info_texts[0], info1=info_texts[1], info2="\n".join(formatted_content), info3=info_texts[2], info4=info_texts[3], info5=info_texts[4], comments=comments, suffix=operate_tip)