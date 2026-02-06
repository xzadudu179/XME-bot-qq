from nonebot import CommandSession
from xme.xmetools.plugintools import on_command
from xme.xmetools.doctools import CommandDoc
from xme.xmetools.bottools import is_group_member_count_legal
from xme.xmetools.msgtools import send_session_msg

alias = []
__plugin_name__ = 'checkgroup'
__plugin_usage__ = CommandDoc(
    name=__plugin_name__,
    desc="检测群",
    introduction="检测群是否都在人数范围",
    usage='',
    permissions=["是 SUPERUSER"],
    alias=alias
)

@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda s: s.is_superuser)
async def _(session: CommandSession):
    groups = await session.bot.get_group_list()
    member_too_few_groups = []
    for group in groups:
        if is_group_member_count_legal(group):
            continue
        member_too_few_groups.append(f"{group['group_name']} ({group['group_id']}) - {group['member_count']} 人")
        # logger.info(f"退出群 {group} 因为人数过低")
    gs = '\n'.join(member_too_few_groups)
    await send_session_msg(session, f"目前有这些群人数过少：\n{gs}")