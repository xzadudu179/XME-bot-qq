from nonebot import on_command, CommandSession
from xme.xmetools.doc_tools import CommandDoc
from xme.xmetools.message_tools import send_session_msg
from character import get_message

alias = ['set_title', '设置头衔', '头衔']
__plugin_name__ = 'title'
__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    usage=f'(at想要设置的群友) (头衔名 填写 -delete 删除头衔)',
    permissions=["是管理员", "是 SUPERUSER"],
    alias=alias
))

@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda sender: (sender.is_admin or sender.is_superuser))
async def _(session: CommandSession):
    try:
        args = session.current_arg.strip()
        at = args.split(" ")[0]
        name = args.split(" ")[1] if len(args.split(" ")) > 1 else ""
        if not name:
            return await send_session_msg(session, get_message("plugins", __plugin_name__, 'no_name_arg'))
        if at and "[CQ:at,qq=" in at:
            at_id = int(at.split("[CQ:at,qq=")[1].split(",")[0])
        else:
            await send_session_msg(session, get_message("plugins", __plugin_name__, 'no_at_arg'))
            return
        print(at_id, name)
        await session.bot.set_group_special_title(group_id=session.event.group_id, user_id=at_id, special_title=name if name != "-delete" else "", duration=0)
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'successful' if name != "-delete" else 'deleted'))
    except Exception as e:
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'failed', ex=e))