from nonebot import on_command, CommandSession
from xme.xmetools.doctools import CommandDoc
from xme.xmetools.msgtools import send_session_msg
from character import get_message, CHARACTER
from xme.xmetools.bottools import permission

alias = [f'{get_message("bot_info", "name")}退群', f'{get_message("bot_info", "name")}退出群聊', f'{CHARACTER}_exit']
permissions = ["是管理 或 是群主 或 是 SUPERUSER", "在群聊内"]
__plugin_name__ = 'bot_leave'
__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    # desc='机器人退群',
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    # introduction='使机器人退出群聊',
    usage=f'',
    permissions=permissions,
    alias=alias
))

@on_command(__plugin_name__, aliases=alias, only_to_me=False)
@permission(lambda sender: (sender.is_superuser or sender.is_admin or sender.is_owner) and sender.is_groupchat, permission_help=" & ".join(permissions))
async def _(session: CommandSession):

    result = (await session.aget(prompt=get_message("plugins", __plugin_name__, 'leaving')))
    print("result", result)
    if result != "Y":
        return
    await send_session_msg(session, get_message("plugins", __plugin_name__, 'leave_message'))
    # await send_msg(session, "正在退出群聊...")
    await session.bot.api.set_group_leave(group_id=session.event.group_id)