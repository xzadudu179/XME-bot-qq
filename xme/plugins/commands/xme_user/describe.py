from xme.plugins.commands.xme_user import __plugin_name__
from nonebot import on_command, CommandSession
from xme.xmetools.msgtools import send_session_msg, aget_session_msg
from xme.xmetools import texttools
from .classes import user as u
from xme.plugins.commands.xme_user.classes.user import User, coin_name, coin_pronoun
from character import get_message
from xme.xmetools.cmdtools import use_args
from xme.xmetools.texttools import is_danger_sql


alias = ['bio', 'intro', 'desc']
cmd_name = 'describe'
usage = {
    "name": cmd_name,
    "desc": get_message("plugins", __plugin_name__, cmd_name, 'desc'),
    "introduction": get_message("plugins", __plugin_name__, cmd_name, 'introduction', ),
    "usage": f'<个人资料文本>',
    "permissions": [],
    "alias": alias
}
@on_command(cmd_name, aliases=alias, only_to_me=False)
@u.using_user(save_data=True)
# @use_args(arg_len=0, split_str=" ")
async def _(session: CommandSession, user: User):
    arg = session.current_arg_text
    if not arg:
        if not user.desc:
            await send_session_msg(session, get_message("plugins", __plugin_name__, cmd_name, 'no_arg'), tips=True)
            return False
        ans = await aget_session_msg(session, prompt=f"[CQ:at,qq={session.event.user_id}] " + get_message("plugins", __plugin_name__, cmd_name, 'desc_info', desc=user.desc))
        if ans == "delete-desc":
            await send_session_msg(session, get_message("plugins", __plugin_name__, cmd_name, 'deleted', desc=user.desc), tips=True)
            user.desc = ""
            return True
        # await send_session_msg(session, get_message("plugins", __plugin_name__, cmd_name, 'canceled_delete'))
        return False
    desc = arg.strip()
    line_count = max(desc.count("\r"), desc.count("\n"))
    if len(desc) > 500:
        await send_session_msg(session, get_message("plugins", __plugin_name__, cmd_name, 'too_long_desc', count=len(desc)), tips=True)
        return False
    if line_count > 15:
        await send_session_msg(session, get_message("plugins", __plugin_name__, cmd_name, 'too_many_lines', count=line_count), tips=True)
        return False
    user.desc = desc
    await send_session_msg(session, get_message("plugins", __plugin_name__, cmd_name, 'success'))
    if is_danger_sql(user.desc):
        await user.achieve_achievement(session, "想注入漠月")
    return True