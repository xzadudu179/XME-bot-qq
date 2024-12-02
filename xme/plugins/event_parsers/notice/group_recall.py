from nonebot import on_notice, NoticeSession, log
from datetime import datetime
from xme.xmetools import color_manage as c
from character import get_message
import json
from xme.xmetools.command_tools import send_msg
from nonebot import Message
from xme.xmetools import json_tools
from xme.xmetools.request_tools import fetch_data


# 撤回
@on_notice('group_recall')
async def _(session: NoticeSession):
    settings = {}
    settings = json_tools.read_from_path("./data/_botsettings.json")
    try:
        recalled_message = await session.bot.api.get_msg(message_id=session.event['message_id'])
    except:
        print("无法获取撤回信息")
        return
    # print(session.event.group_id, session.event.user_id)
    user = await session.bot.get_group_member_info(group_id=session.event.group_id, user_id=session.event.operator_id)
    sender =  await session.bot.get_group_member_info(group_id=session.event.group_id, user_id=session.event.user_id)
    group = await session.bot.get_group_info(group_id=session.event.group_id)

    # 读取 qq 等级
    try:
        user_qq_data = await fetch_data(f"https://apis.kit9.cn/api/qq_material/api.php?qq={session.event.operator_id}")
        # print(c.gradient_text("#dda3f8","#66afff" ,text=user_qq_data))
        user_qq_level = json.loads(user_qq_data)['data']['level']
    except Exception as ex:
        print(ex)
        user_qq_level = "无法获取"
    try:
        sender_qq_data = await fetch_data(f"https://apis.kit9.cn/api/qq_material/api.php?qq={sender['user_id']}")
        # print(c.gradient_text("#dda3f8","#66afff" ,text=sender_qq_data))
        sender_qq_level = json.loads(sender_qq_data)['data']['level']
    except Exception as ex:
        print(ex)
        sender_qq_level = "无法获取"

    # 输出内容
    recall_info = f"群 \"{group['group_name']}[{session.event.group_id}]\": 来自 {sender['nickname']}[{sender['user_id']}] 的消息被 {user['nickname']}[{session.event.user_id}]撤回，内容为：{recalled_message['message']}"
    recall_detail = f"消息发送者信息:\n\tQQ号: {sender['user_id']}\n\tQQ等级: {sender_qq_level}\n\t昵称: {sender['nickname']}\n\t群名片/备注: {sender['card']}\n\t群活跃等级: {sender['level']}\n\t加群时间: {datetime.fromtimestamp(sender['join_time'])}\n\t是否有不良记录: {sender['unfriendly']}\n消息撤回者信息:\n\tQQ号: {user['user_id']}\n\tQQ等级: {user_qq_level}\n\t昵称: {user['nickname']}\n\t群名片/备注: {user['card']}\n\t群活跃等级: {user['level']}\n\t加群时间: {datetime.fromtimestamp(user['join_time'])}\n\t是否有不良记录: {user['unfriendly']}\n消息信息:\n\t内容: {recalled_message['message']}\n\t被撤回时间: {datetime.fromtimestamp(session.event['time'])}\n\t消息ID: {recalled_message['message_id']}\n\t消息真实ID: {recalled_message['real_id']}"
    log.logger.info(recall_info)
    # print(c.gradient_text("#dda3f8","#66afff" ,text=f"{recall_info}\n{recall_detail}"))

    # 保存文件
    with open(f'./logs/recall_info/{datetime.now().strftime(format="%Y-%m-%d")}_recallmessages.log', 'a', encoding='utf-8') as file:
        file.write(("-" * 50) + f"\n[{datetime.fromtimestamp(session.event['time'])}][GROUP_RECALL]{recall_info}\n{recall_detail}\n" + ("-" * 50) + "\n")
    is_prev_recall = settings['prevent_recall'].get(str(session.event.group_id), False)
    if (str(session.event.user_id) != str(session.event.operator_id)) and is_prev_recall:
        return await send_msg(session, get_message("event_parsers", "other_recalled_info").format(
            operator=f"[CQ:at,qq={session.event.operator_id}]",
            user='我' if session.event.user_id == session.self_id else '别人'))
        # return await send_msg(session, f"刚刚 [CQ:at,qq={session.event.operator_id}] 撤回了一条{'我' if session.event.user_id == session.self_id else '别人'}的消息ovo")

    # 防撤回
    if is_prev_recall:
        str_message = ""
        try:
            cqmessage = str(Message(recalled_message['message']))
            str_message = cqmessage
        except:
            str_message = recalled_message['message']
        await send_msg(session, get_message("event_parsers", "prevented_recall_info").format(
            operator=f"[CQ:at,qq={session.event.operator_id}]",
            recalled_message=str_message))
        # await send_msg(session, f"↓ 刚刚 [CQ:at,qq={session.event.operator_id}] 撤回了以下消息ovo ↓\n{str_message}")