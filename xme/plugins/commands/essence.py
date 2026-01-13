from nonebot import CommandSession
from xme.xmetools.plugintools import on_command
from xme.xmetools.doctools import CommandDoc
from datetime import datetime
from character import get_message
from xme.xmetools.imgtools import image_msg
from xme.xmetools.msgtools import send_session_msg
import random
from aiocqhttp import ActionFailed
from xme.xmetools.imgtools import get_qq_avatar
from xme.xmetools.bottools import bot_call_action
from nonebot import Message
from nonebot.log import logger
alias = ['ess']
__plugin_name__ = 'essence'
__plugin_usage__ = CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    usage=f'',
    permissions=["无"],
    alias=alias
)

@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda _: True)
async def _(session: CommandSession):
    await send_session_msg(session, get_message("plugins", __plugin_name__, 'searching'))
    try:
        essences = await session.bot.api.call_action("get_essence_msg_list", group_id=session.event.group_id)
    except ActionFailed:
        return await send_session_msg(session, get_message("plugins", __plugin_name__, 'no_essence'))
    essence = random.choice(essences)
    logger.debug("精华消息数量：", len(essences))
    if len(essences) < 2:
        return await send_session_msg(session, get_message("plugins", __plugin_name__, 'no_essence'))
    logger.debug("ESSENCE", essence)
    await send_session_msg(session, get_message(
        "plugins",
        __plugin_name__,
        'result',
        avatar=await image_msg(await get_qq_avatar(essence["sender_id"]), max_size=64, to_jpeg=False),
        sender=essence["sender_nick"],
        operator=essence["operator_nick"],
        operator_id=f'{essence["operator_id"]}',
        date=datetime.fromtimestamp(essence['operator_time']),
        sender_id=f'{essence["sender_id"]}',
        essence=Message(essence["content"])
    ))
