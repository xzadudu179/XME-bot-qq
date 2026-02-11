from xme.xmetools.timetools import TimeUnit
from datetime import datetime
from .pickup import report
from character import get_message
from xme.plugins.commands.xme_user.classes import user as u
from xme.xmetools.msgtools import send_session_msg
from xme.xmetools.bottools import permission
from xme.plugins.commands.drift_bottle import __plugin_name__
from . import DriftBottle
from . import BOTTLE_IMAGES_PATH
from xme.xmetools.texttools import get_image_files_from_message, remove_invisible, is_url
from xme.xmetools.imgtools import get_image, limit_size, detect_qrcode
from traceback import format_exc
import config
import re
from xme.xmetools.debugtools import debug_msg
from nonebot.log import logger
import os
from nonebot import CommandSession
from xme.xmetools.plugintools import on_command

def is_illegal_image(path_or_image):
    result, link = detect_qrcode(path_or_image)
    # logger.info(f"{result}, {link}")
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
    MAX_IMAGES = 2

    arg = remove_invisible(session.current_arg.strip())

    debug_msg(arg)
    try:
        pattern = r"\[CQ:image,(?![^\]]*emoji_id=)[^\]]*file=[^\]]*?\]"
        matches = re.findall(pattern, arg)
        image_paths = await get_image_files_from_message(session.bot, arg)
        images = [limit_size(get_image(image), 700) for image in image_paths]
        for image in image_paths:
            logger.info("图片: " + image)
            if is_illegal_image(image):
                logger.warning(f"用户 {session.event.user_id} 在 {session.event.group_id} 投掷的漂流瓶包含二维码")
                await send_session_msg(session, get_message("plugins", __plugin_name__, "content_has_qr_code"))
                return False
        # image_filenames = [os.path.splitext(os.path.basename(i))[0] + "." + get_image_format(images[j]) for j, i in enumerate(image_paths)]
        image_filenames = [os.path.splitext(os.path.basename(i))[0] + ".WEBP" for j, i in enumerate(image_paths)]
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
    check = DriftBottle.check_duplicate_bottle(arg)
    debug_msg("查重 " + str(check['content']))
    if not check['status']:
        await send_session_msg(session, get_message("plugins", __plugin_name__, "content_already_thrown"))
        return False

    user = await session.bot.get_group_member_info(group_id=session.event.group_id, user_id=session.event.user_id)
    group = await session.bot.get_group_info(group_id=session.event.group_id)
    bottle_id = DriftBottle.get_max_bottle_id() + 1
    debug_msg(bottle_id)
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
        # "pure_vote_users": {},
        "group_id": user['group_id'],
    }

    bottle: DriftBottle = DriftBottle.form_dict(bottle_content)
    formatted_arg = bottle.get_formatted_content("0%", 0)
    # debug_msg(formatted_arg, len(formatted_arg))
    # debug_msg(arg, len(arg))
    if len(formatted_arg) + len(image_paths) * 100 > MAX_LENGTH:
        await send_session_msg(session, get_message("plugins", __plugin_name__, "content_too_many", max_length=MAX_LENGTH, text_len=len(formatted_arg)))
        return False
    if arg.count('\n') >= MAX_LINES or arg.count('\r') >= MAX_LINES:
        await send_session_msg(session, get_message("plugins", __plugin_name__, "lines_too_many", max_lines=MAX_LINES))
        return False

    # if arg.count("")
    if len(image_paths) > MAX_IMAGES:
        await send_session_msg(session, get_message("plugins", __plugin_name__, "images_too_many", max_images=MAX_IMAGES))
        return False

    # 处理图片

    for i, image in enumerate(images):
        path = BOTTLE_IMAGES_PATH + image_filenames[i]
        check_image = DriftBottle.check_duplicate_image(image)
        if not check_image["status"]:
            await send_session_msg(session, get_message("plugins", __plugin_name__, "content_already_thrown"))
            # debug_msg("查重图片：", check_image)
            logger.info("查重图片：" + str(check_image))
            return False
        # 存储图片
        image.save(path)

    bottle.images = image_filenames
    bottle.save()
    debug_msg(bottle)

    await report(session, bottle, user['user_id'], "发送了一个漂流瓶", False)
    await send_session_msg(session, get_message("plugins", __plugin_name__, 'throwed', id=bottle_id), tips=True)
    # await send_msg(session, f"[CQ:at,qq={user['user_id']}] 瓶子扔出去啦~ 这是大海里的第 {id} 号瓶子哦 owo")
    return True