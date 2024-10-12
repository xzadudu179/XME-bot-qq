from nonebot import on_notice, NoticeSession, log
from nonebot import Message
import json

# 撤回
@on_notice('group_recall')
async def _(session: NoticeSession):
    settings = {}
    with open ("./data/botsettings.json", 'r', encoding='utf-8') as jsonfile:
        settings = json.load(jsonfile)
    recalled_message = await session.bot.api.get_msg(message_id=session.event['message_id'])
    log.logger.info(f"消息被撤回，内容为：{recalled_message['message']}")
    is_prev_recall = settings['prevent_recall'].get(str(session.event.group_id), False)
    if (str(session.event.user_id) != str(session.event.operator_id)) and is_prev_recall:
        return await session.send(f"刚刚 [CQ:at,qq={session.event.operator_id}] 撤回了一条{'我' if session.event.user_id == session.self_id else '别人'}的消息ovo")
    if is_prev_recall:
        str_message = ""
        try:
            cqmessage = str(Message(recalled_message['message']))
            str_message = cqmessage
        except:
            str_message = recalled_message['message']
        await session.send(f"↓ 刚刚 [CQ:at,qq={session.event.operator_id}] 撤回了以下消息ovo ↓\n{str_message}")