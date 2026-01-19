from nonebot import CommandSession
from xme.xmetools.debugtools import debug_msg
from nonebot.log import logger
from xme.xmetools.plugintools import on_command
from xme.xmetools.doctools import CommandDoc
from xme.xmetools import imgtools
from character import get_message
from xme.xmetools.texttools import get_at_id
from xme.xmetools.imgtools import image_msg
from xme.xmetools.msgtools import send_session_msg
import traceback
from PIL import Image

async def gen_maifriend(qq, size=640):
    avatar = (await imgtools.get_qq_avatar(qq, size)).resize((int(size * 0.8), int(size * 0.8))).convert("RGBA")
    frame = Image.open("./static/img/frame.png").resize((size, size))
    # 创建一个新的空白画布，大小为最大图片的尺寸
    new_image = Image.new("RGB", (frame.width, frame.height))

    # 计算中心位置
    avatar_x = (frame.width - avatar.width) // 2
    avatar_y = (frame.height - avatar.height) // 2 + int(size * 0.03)

    # 粘贴图片
    new_image.paste(avatar, (avatar_x, avatar_y))
    new_image.paste(frame, (0, 0), frame.convert("RGBA").getchannel('A'))
    # new_image.save(path, "PNG")
    return new_image


alias = ['旅行伙伴', 'maif']
__plugin_name__ = 'maifriend'
__plugin_usage__ = CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    usage=f'<at 用户>',
    permissions=["无"],
    alias=alias
)

@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda _: True)
async def _(session: CommandSession):
    arg = session.current_arg.strip()
    qq_id = session.event.user_id
    try:
        if arg.startswith("[CQ:at,qq="):
            qq_id = get_at_id(arg)
        image = await gen_maifriend(qq_id)
    except:
        logger.exception(traceback.format_exc())
        return await send_session_msg(session, get_message("plugins", __plugin_name__, 'error'), tips=True)
    return await send_session_msg(session, await image_msg(image), tips=True, tips_percent=20)