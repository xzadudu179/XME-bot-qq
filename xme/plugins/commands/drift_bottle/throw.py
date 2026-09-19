from uuid import uuid4

from PIL.Image import Image

from xme.xmetools.timetools import TimeUnit
from datetime import datetime
from .pickup import report
from character import get_message
from xme.plugins.commands.xme_user.classes import user as u
from xme.xmetools.msgtools import is_text_can_send, send_session_msg
# from xme.plugins.commands.drift_bottle.tools.cards import CUSTOM_CARD_NAMES
from xme.xmetools.bottools import permission
from xme.plugins.commands.drift_bottle import __plugin_name__
from . import DriftBottle
from . import BOTTLE_IMAGES_PATH
from xme.xmetools.texttools import get_images_from_message, remove_invisible, is_url
from xme.xmetools.imgtools import get_url_image, is_images_can_send, limit_size, detect_qrcode
from xme.xmetools.animtools import (
    ANIM_STORE_MARGIN,
    GIF_OUTPUT_MAX_BYTES,
    QR_SAMPLE_FRAMES,
    AnimSequence,
    compress_anim_sequence,
    is_animated,
    load_anim_sequence,
    sample_frames,
    save_anim_sequence,
)
from traceback import format_exc
import config
import re
from xme.xmetools.debugtools import debug_msg
from nonebot.log import logger
import os
from nonebot import CommandSession
from xme.xmetools.plugintools import on_command

async def is_image_has_qr(image):
    # image = await get_url_image(image_url)
    result, links = detect_qrcode(image)
    logger.info(f"{result}, {links}")
    for link in links:
        if result and is_url(link):
            logger.warning(f"检测到二维码链接：{link}")
            return True
    return False


throw_alias = ["扔瓶子", "扔漂流瓶", "扔瓶"]
command_name = 'throw'
@on_command(command_name, aliases=throw_alias, only_to_me=False, permission=lambda _: True)
@u.using_user(save_data=False)
@u.limit(command_name, 1, get_message("plugins", __plugin_name__, 'throw_limited'), unit=TimeUnit.HOUR, count_limit=5)
@permission(lambda x: x.is_groupchat, permission_help="在群聊内")
async def _(session: CommandSession, user):
    MAX_LENGTH = 500
    MAX_LINES = 20
    MAX_IMAGES = 3

    arg = remove_invisible(session.current_arg.strip())
    logger.info(f"arg is {arg}")
    debug_msg(arg)
    try:
        # pattern = r"\[CQ:image,(?![^\]]*emoji_id=)[^\]]*file=[^\]]*?\]"
        # matches = re.findall(pattern, arg)
        image_objects, matches = await get_images_from_message(session.bot, arg)
        image_urls = [x["file"] for x in image_objects]
        image_names = [x["file_name"] for x in image_objects]
        logger.info(f"urls {image_urls}")
        # 动图读取帧序列（帧数预算内按时长补偿均匀抽帧，长度不变），
        # 静图与单帧动图统一按静图缩放存储 WEBP；
        # sequences 与 images 按下标一一对应，动图槽位为帧序列、静图槽位为 None
        sequences: list[AnimSequence | None] = []
        images = []
        for image_url in image_urls:
            image = await get_url_image(image_url)
            sequence = load_anim_sequence(image) if is_animated(image) else None
            if sequence is not None and len(sequence.frames) > 1:
                sequences.append(sequence)
                images.append(sequence.frames[0])
            else:
                sequences.append(None)
                images.append(limit_size(sequence.frames[0] if sequence else image, 700))
        # 动图抽首/中/尾帧送审，防止违规内容藏在后续帧
        if len(images) > 0:
            await send_session_msg(session, get_message("plugins", __plugin_name__, "check_image"))
        moderation_images = []
        for image, sequence in zip(images, sequences):
            moderation_images.extend(sample_frames(sequence, 3) if sequence is not None else [image])
        if not (await is_images_can_send(session.bot, session.event, moderation_images, session)):
            await send_session_msg(session, get_message("plugins", __plugin_name__, "image_has_risk"))
            return False
        # 二维码检测逐帧抽样，防止二维码藏在动图后续帧
        for image, sequence in zip(images, sequences):
            for frame in (sample_frames(sequence, QR_SAMPLE_FRAMES) if sequence is not None else [image]):
                if await is_image_has_qr(frame):
                    logger.warning(f"用户 {session.event.user_id} 在 {session.event.group_id} 投掷的漂流瓶包含二维码")
                    await send_session_msg(session, get_message("plugins", __plugin_name__, "content_has_qr_code"))
                    return False
        image_filenames = [
            os.path.splitext(os.path.basename(name))[0] + (".GIF" if sequence is not None else ".WEBP")
            for name, sequence in zip(image_names, sequences)
        ]
    except Exception as ex:
        await send_session_msg(session, get_message("plugins", __plugin_name__, "throw_error", ex=ex))
        logger.exception(format_exc())
        return False

    for i, image_cq in enumerate(matches):
        filename = ".".join(image_filenames[i].split(".")[:-1])
        debug_msg("filename " + filename)
        arg = arg.replace(image_cq, "{" + filename + "}")
    arg = re.sub(r"\[[^\[\]]*\]", "", arg).replace("&#91;", "[").replace("&#93;", "]").strip()
    if not arg:
        await send_session_msg(session, get_message("plugins", __plugin_name__, "nothing_to_throw", command_name=f"{config.COMMAND_START[0]}{command_name}"))
        return False
    ## 文本风险控制
    moderation_result = await is_text_can_send(session, arg, 4)
    can_send = moderation_result["result"]
    reason = moderation_result["reason"]
    if not can_send:
        await send_session_msg(session, get_message("config", "moderation_danger_input", reason=reason))
        return False

    check = DriftBottle.check_duplicate_bottle(arg)
    debug_msg("查重 " + str(check['content']))
    if not check['status']:
        await send_session_msg(session, get_message("plugins", __plugin_name__, "content_already_thrown"))
        return False

    user: u.User = await session.bot.get_group_member_info(group_id=session.event.group_id, user_id=session.event.user_id)
    group = await session.bot.get_group_info(group_id=session.event.group_id)
    bottle_id = DriftBottle.get_max_bottle_id() + 1
    debug_msg(bottle_id)
    # custom_card = user.get_custom_setting(__plugin_name__, "custom_cards")
    bottle_content = {
        "id": -1,
        "bottle_id": bottle_id,
        "content": arg,
        # "images": str(images),
        "sender": user['nickname'],
        "likes": 0,
        'views': 0,
        "from_group": group["group_name"],
        "send_time": datetime.now().strftime(format="%Y年%m月%d日 %H:%M:%S"),
        "sender_id": user['user_id'],
        "comments": "[]",
        "is_broken": False,
        # "skin": custom_card if custom_card in CUSTOM_CARD_NAMES else "",
        # "pure_vote_users": {},
        "group_id": user['group_id'],
    }

    bottle: DriftBottle = DriftBottle.form_dict(bottle_content)
    formatted_arg = bottle.get_formatted_content("0%", 0)
    # debug_msg(formatted_arg, len(formatted_arg))
    # debug_msg(arg, len(arg))
    image_len = 0
    for image in images:
        image_len += image.height
    image_len = image_len / 50 * 30
    logger.info(f"args {formatted_arg} image_len {image_len}")
    if len(formatted_arg) + image_len > MAX_LENGTH:
        await send_session_msg(session, get_message("plugins", __plugin_name__, "content_too_many", max_length=MAX_LENGTH, text_len=len(formatted_arg) + image_len))
        return False
    if arg.count('\n') >= MAX_LINES or arg.count('\r') >= MAX_LINES:
        await send_session_msg(session, get_message("plugins", __plugin_name__, "lines_too_many", max_lines=MAX_LINES))
        return False

    # if arg.count("")
    if len(image_urls) > MAX_IMAGES:
        await send_session_msg(session, get_message("plugins", __plugin_name__, "images_too_many", max_images=MAX_IMAGES))
        return False

    # 处理图片
    total_height = 0

    # 动图入库压缩阶梯：透明裁边 → 缩放 → 降色 → 抽帧（时长补偿不裁长度），
    # 预算按动图数量均分并预留留言增长余量；超预算时拾取端仍有循环抽帧兜底
    store_plans = {}
    anim_indexes = [i for i, s in enumerate(sequences) if s is not None]
    if anim_indexes:
        budget = int(GIF_OUTPUT_MAX_BYTES * ANIM_STORE_MARGIN) // len(anim_indexes)
        for i in anim_indexes:
            store_seq, scale_pct, colors = compress_anim_sequence(sequences[i], budget)
            store_plans[i] = (store_seq, colors)
            logger.info(f"动图入库压缩：缩放 {scale_pct}% / {colors} 色 / {len(store_seq.frames)} 帧")
    for i, image in enumerate(images):
        total_height += image.height
        if total_height > 800:
            await send_session_msg(session, get_message("plugins", __plugin_name__, "images_too_height", max_images=MAX_IMAGES))
            return False
        path = BOTTLE_IMAGES_PATH + image_filenames[i]
        check_image = DriftBottle.check_duplicate_image(image)
        if not check_image["status"]:
            await send_session_msg(session, get_message("plugins", __plugin_name__, "content_already_thrown"))
            # debug_msg("查重图片：", check_image)
            logger.info("查重图片：" + str(check_image))
            return False
        # 存储图片：动图按压缩阶梯处理后存 GIF（保留动画与长度），静图/单帧动图存 WEBP
        if sequences[i] is not None:
            store_seq, colors = store_plans[i]
            save_anim_sequence(store_seq, path, colors=colors)
        else:
            image.save(path)

    bottle.images = image_filenames
    bottle.save()
    debug_msg(bottle)

    await report(session, bottle, user['user_id'], "发送了一个漂流瓶", False)
    await send_session_msg(session, get_message("plugins", __plugin_name__, 'throwed', id=bottle_id), tips=True)
    # await send_msg(session, f"[CQ:at,qq={user['user_id']}] 瓶子扔出去啦~ 这是大海里的第 {id} 号瓶子哦 owo")
    return True