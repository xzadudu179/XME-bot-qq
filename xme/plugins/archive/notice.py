from nonebot import on_command, CommandSession
from xme.xmetools.doc_tools import CommandDoc
from xme.xmetools.json_tools import read_from_path, save_to_path
import config
from aiocqhttp import ActionFailed
from character import get_message
from xme.xmetools.command_tools import send_session_msg
CONFIG_PATH = "./data/_botsettings.json"

alias = ['提醒', '群发']
__plugin_name__ = 'notice'
__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    desc=get_message(__plugin_name__, 'desc'),
    # desc='查看系统状态',
    introduction=get_message(__plugin_name__, 'introduction'),
    # introduction='查看运行该 XME-Bot 实例的设备的系统状态',
    usage=f'',
    permissions=["在白名单群内", "在群聊内", "是 SUPERUSER"],
    alias=alias
))

@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda x: x.is_groupchat and x.from_group(config.GROUPS_WHITELIST) and x.is_superuser)
async def _(session: CommandSession):
    message = session.current_arg_text.strip()
    dont_notice = read_from_path(CONFIG_PATH).get("dont_notice", [])
    user_ids = [u["user_id"] for u in (await session.bot.get_group_member_list(group_id=session.event.group_id))]
    await send_session_msg(session, message=get_message(__plugin_name__, 'parsing', count=len(user_ids)))
    total_n_success = [0, 0]
    for user_id in user_ids:
        total_n_success[0] += 1
        if user_id == session.self_id:
            continue
        if user_id in dont_notice:
            print(f"id 为 {user_id} 的用户静音了 bot 消息")
            continue
        print(f"正在发送消息给 {user_id}")
        try:
            await session.bot.send_private_msg(user_id=user_id, message=get_message(__plugin_name__, 'message_send', message=message))
        except ActionFailed:
            print("发送失败")
            continue
        print("发送成功")
        total_n_success[1] += 1
    return await send_session_msg(session, message=get_message(__plugin_name__, 'success', percent=total_n_success[1] / total_n_success[0]))

@on_command('mute', aliases=['静音'], only_to_me=False, permission=lambda x: x.is_groupchat or x.is_privatechat)
async def _(session: CommandSession):
    dont_notice: list = read_from_path(CONFIG_PATH).get("dont_notice", [])
    dont_notice.append(session.event.user_id)
    c = read_from_path(CONFIG_PATH)
    c["dont_notice"] = dont_notice
    save_to_path(CONFIG_PATH, c)
    await send_session_msg(session, get_message(__plugin_name__, 'muted'))