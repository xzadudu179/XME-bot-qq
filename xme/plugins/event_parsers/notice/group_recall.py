from nonebot import on_notice, NoticeSession
# from xme.xmetools.debugtools import debug_msg
from nonebot.log import logger
from bot_variables import command_msgs

async def recall(session: NoticeSession):
    logger.info(f"{command_msgs}")
    try:
        recalled_message = await session.bot.api.get_msg(message_id=session.event['message_id'])
    except Exception:
        logger.warning("无法获取撤回信息")
        return
    msg_id = recalled_message['message_id']
    cmd_msg_id = command_msgs.get(msg_id, None)
    if cmd_msg_id is None:
        return
    is_open = cmd_msg_id.get("open", False)
    # 还没结束指令也不允许撤回
    logger.info(f"is open {is_open}")
    if is_open:
        return
    ids = cmd_msg_id.get("ids", [])
    if ids is None:
        ids = []
    for i in ids:
        logger.info(f"尝试撤回 {i['message_id']}")
        await session.bot.delete_msg(message_id=i["message_id"], self_id=session.self_id)
    del command_msgs[msg_id]

@on_notice('group_recall')
async def _(session: NoticeSession):
    return await recall(session)

@on_notice('friend_recall')
async def _(session: NoticeSession):
    return await recall(session)