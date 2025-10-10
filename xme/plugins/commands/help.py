import nonebot
import config
from xme.xmetools.doctools import CommandDoc
from xme.plugins.commands.xme_user.classes import user as u
from xme.xmetools.timetools import TimeUnit
from xme.xmetools.cmdtools import send_cmd, get_cmd_by_alias
from xme.xmetools.listtools import split_list
from xme.xmetools.msgtools import send_session_msg
from xme.plugins.commands.xme_user import get_userhelp
from xme.xmetools.msgtools import change_group_message_content, send_forward_msg
from xme.xmetools.imgtools import image_msg
from nonebot import on_command, CommandSession, MessageSegment
from character import get_message
from xme.xmetools.texttools import most_similarity_str

alias = ["usage", "docs", "帮助", "h"]
__plugin_name__ = 'help'

__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    # desc='显示帮助',
    desc=get_message("plugins", __plugin_name__, 'desc'),
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    # introduction='显示帮助，或某个指令的帮助，功能名若填写数字则是翻到数字所指的页数',
    usage=f'<功能名>',
    permissions=["无"],
    alias=alias
))

async def arg_help(arg, plugins, session):
    if arg[0] in config.COMMAND_START:
        arg = arg[1:]
    ask_for_help = get_cmd_by_alias(arg, False)
    if not ask_for_help:
        ask_for_help = x[-1][0] if (x:=most_similarity_str(arg, [p.name.lower() for p in plugins], 0.65)) else None
    else:
        ask_for_help = ask_for_help.name[0]
    print(ask_for_help)
    ask_cmd = ask_for_help
    if not ask_for_help:
        return False
    for pl in plugins:
        if f"{pl.usage.split(']')[0]}]" in ["[插件]"] and ask_for_help in [i.split(":")[0].strip().split(" ")[0] for i in pl.usage.split("##内容##：")[1].split("##所有指令用法##：")[0].split("\n")[:] if i]:
            ask_for_help = pl.name.lower()
        if pl.name.lower() != ask_for_help: continue
        if pl.name.lower() == "xme 宇宙" and ask_cmd != "xme 宇宙":
            print("发送用户帮助")
            return await send_session_msg(session, get_userhelp(ask_cmd).replace("\n\n", "\n"), tips=True)
        return await send_session_msg(session, pl.usage.split("/////OUTER/////")[0].replace("\n\n", "\n") if pl.usage.split("/////OUTER/////")[0] else get_message("plugins", __plugin_name__, 'no_usage'), at=True, tips=True)

@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda _: True)
@u.using_user(save_data=False)
@u.limit(__plugin_name__, 30, get_message("plugins", __plugin_name__, 'limited'), unit=TimeUnit.SECOND, count_limit=2)
async def _(session: CommandSession, user: u.User):
    plugins = list(filter(lambda p: p.name, nonebot.get_loaded_plugins()))
    arg = session.current_arg_text.strip().lower()
    # 如果发了参数则发送相应命令的使用帮助
    print("发送帮助")
    if arg and await arg_help(arg, plugins, session) != False: return False
    # help_list_str = ""
    PAGE_LENGTH = 20
    IMG_PATH = "./static/img/help_img"
    # 分段
    pages = []
    index = 0
    total_pages = ""
    plugin_pages = ""
    for p in plugins:
        index += 1
        try:
            if p.usage.split(']')[0] in '[指令':
                total_pages += "\n" + f"{p.usage.split(']')[0]}] {config.COMMAND_START[0] if p.usage.split(']')[0] in '[指令' else ''}{p.name}    " + p.usage.split('简介：')[1].split('\n')[0].strip()
            else:
                plugin_pages += "\n" + f"{p.usage.split(']')[0]}] {p.name}    " + p.usage.split('简介：')[1].split('\n')[0].strip()
        except:
            plugin_pages += "\n" + f"[未知] {p.name}"

    if len(total_pages.split("\n")) < 1:
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'no_cmds', prefix=prefix))
        # await send_msg(session, f"{prefix}\n{get_info('name')}现在还没有任何指令哦")
        return True

    pages = ['\n'.join(item) for item in split_list(total_pages.split("\n")[1:], PAGE_LENGTH)]
    pages_plugin = ['\n'.join(item) for item in split_list(plugin_pages.split("\n")[1:], PAGE_LENGTH)]
    # print(pages)
    prefix = get_message("plugins", __plugin_name__, 'prefix', command_seps='"' + '"、"'.join(config.COMMAND_START) + '"', version=config.VERSION)
    # prefix = f'[XME-Bot V0.1.2]\n指令以 {" ".join(config.COMMAND_START)} 中任意字符开头\n当前功能列表'
    suffix = get_message("plugins", __plugin_name__, 'suffix', docs_link="http://docs.xme.xzadudu179.top/#/help")
    new_messages: list[MessageSegment] = []
    msg_dict = {
        "sender": await session.bot.api.get_group_member_info(group_id=session.event.group_id, user_id=session.self_id) if session.event.group_id else await session.bot.api.get_stranger_info(user_id=session.self_id)
    }
    new_messages.append(change_group_message_content(msg_dict, prefix + '\n' + suffix))
    for page in pages:
        new_messages.append(change_group_message_content(msg_dict, page))
    # new_messages.append(change_group_message_content(msg_dict,  get_message("plugins", __plugin_name__, "other_help_2")))
    for page in pages_plugin:
        new_messages.append(change_group_message_content(msg_dict, page))
    # new_messages.append(change_group_message_content(msg_dict, get_message("plugins", __plugin_name__, "other_help_2")))
    # await send_session_msg(session, await image_msg(IMG_PATH + "/other_help.png"), at=False)
    await send_session_msg(session, "注：如果没有看到即将发送的聊天记录，可以尝试私聊发送 /help", at=False)
    await send_forward_msg(session.bot, session.event, new_messages)
    return True