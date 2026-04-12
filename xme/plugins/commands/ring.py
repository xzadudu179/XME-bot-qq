from nonebot import CommandSession
# from xme.xmetools.debugtools import debug_msg
from nonebot.log import logger
from xme.xmetools.plugintools import on_command
from xme.xmetools.doctools import CommandDoc
from xme.xmetools import imgtools
from character import get_message
from xme.xmetools.texttools import get_at_id
from xme.xmetools.msgtools import image_msg
from xme.xmetools.cmdtools import use_args
from xme.xmetools.msgtools import send_session_msg
import traceback
from PIL import Image

async def gen_maifriend(qq, size=640):
    return await get_ring_image(qq, "./static/img/rings/maif.png", size, 0.8, 0, 0.03)

async def gen_google(qq, size=640):
    return await get_ring_image(qq, "./static/img/rings/goog.png", size, 0.88, 0, 0, round_avatar=True)

async def gen_google_thick(qq, size=640):
    return await get_ring_image(qq, "./static/img/rings/goog2.png", size, 0.81, 0, 0, round_avatar=True)

async def get_ring_image(qq, ring_path, size=640, scale=0.8, x_offset_scale=0, y_offset_scale=0, round_avatar=False):
    avatar = (await imgtools.get_qq_avatar(qq, size)).resize((int(size * scale), int(size * scale))).convert("RGBA")
    if round_avatar:
        avatar = imgtools.make_circle_image(avatar)
    frame = Image.open(ring_path).resize((size, size))
    # 创建一个新的空白画布，大小为最大图片的尺寸
    new_image = Image.new("RGBA", (frame.width, frame.height))

    # 计算中心位置
    avatar_x = (frame.width - avatar.width) // 2 + int(size * x_offset_scale)
    avatar_y = (frame.height - avatar.height) // 2 + int(size * y_offset_scale)

    # 粘贴图片
    new_image.paste(avatar, (avatar_x, avatar_y))
    new_image.paste(frame, (0, 0), frame.convert("RGBA").getchannel('A'))
    # new_image.save(path, "PNG")
    return new_image


alias = ['ri', '头像装饰']
__plugin_name__ = 'ring'
__plugin_usage__ = CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    usage='(参数) <at 用户>',
    permissions=["无"],
    alias=alias
)

@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda _: True)
@use_args(arg_len=2, raw=True)
async def _(session: CommandSession, arg_list):
    qq_id = session.event.user_id
    method, at = arg_list
    logger.info(" ".join(("ring arg", str(arg_list), method, at)))
    try:
        if at.startswith("[CQ:at,qq="):
            qq_id = get_at_id(at)
        image = None
        match method:
            case "maif":
                image = await gen_maifriend(qq_id)
            case "goog":
                image = await gen_google(qq_id)
            case "goog2":
                image = await gen_google_thick(qq_id)
        if image is None and not method.startswith("[CQ:at,qq=") and method:
            return await send_session_msg(session, get_message("plugins", __plugin_name__, 'invalid_method'), tips=True)
        elif image is None:
            return await send_session_msg(session, get_message("plugins", __plugin_name__, 'no_method'), tips=True)
    except Exception:
        logger.exception(traceback.format_exc())
        return await send_session_msg(session, get_message("plugins", __plugin_name__, 'error'), tips=True)
    return await send_session_msg(session, await image_msg(image), tips=True, tips_percent=20)