import nonebot
import config
from xme.xmetools.doctools import CommandDoc
from xme.xmetools.cmdtools import send_cmd, get_cmd_by_alias
from xme.xmetools.listtools import split_list
from xme.xmetools.msgtools import send_session_msg
from xme.plugins.commands.xme_user import get_userhelp
from xme.xmetools.msgtools import change_group_message_content, send_forward_msg
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
            return await send_session_msg(session, get_userhelp(ask_cmd).replace("\n\n", "\n"))
        return await send_session_msg(session, pl.usage.split("/////OUTER/////")[0].replace("\n\n", "\n") if pl.usage.split("/////OUTER/////")[0] else get_message("plugins", __plugin_name__, 'no_usage'), at=True)

@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda _: True)
async def _(session: CommandSession):
    plugins = list(filter(lambda p: p.name, nonebot.get_loaded_plugins()))
    arg = session.current_arg_text.strip().lower()
    # 如果发了参数则发送相应命令的使用帮助
    curr_page_num = 1
    print("发送帮助")
    if arg and await arg_help(arg, plugins, session) != False: return
    # help_list_str = ""
    PAGE_LENGTH = 20
    # 分页
    pages = []
    index = 0
    total_pages = ""
    for p in plugins:
        index += 1
        try:
            total_pages += "\n" + f"{p.usage.split(']')[0]}] {config.COMMAND_START[0] if p.usage.split(']')[0] in '[指令' else ''}{p.name}    " + p.usage.split('简介：')[1].split('\n')[0].strip()
        except:
            total_pages += "\n" + f"[未知] {p.name}"

    if len(total_pages.split("\n")) < 1:
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'no_cmds', prefix=prefix))
        # await send_msg(session, f"{prefix}\n{get_info('name')}现在还没有任何指令哦")
        return

    pages = ['\n'.join(item) for item in split_list(total_pages.split("\n")[1:], PAGE_LENGTH)]
    # print(pages)
    prefix = get_message("plugins", __plugin_name__, 'prefix', command_seps='"' + '""'.join(config.COMMAND_START) + '"', version=config.VERSION)
    # prefix = f'[XME-Bot V0.1.2]\n指令以 {" ".join(config.COMMAND_START)} 中任意字符开头\n当前功能列表'
    # 展示页数
    suffix = get_message("plugins", __plugin_name__, 'suffix', docs_link="http://docs.xme.xzadudu179.top/#/help")
    # suffix = f'帮助文档: http://docs.xme.xzadudu179.top/#/help\n使用 \"{config.COMMAND_START[0]}help 功能名\" 查看某功能的详细介绍哦\n在下面发送 \">\" \"<\" 或 \"》\" \"《\" 翻页'
    # curr_page_num = await verify_page(session, curr_page_num, pages)
    if not curr_page_num:
        return
    # content = f"({curr_page_num} / {len(pages)}页)：\n" + pages[curr_page_num - 1]
    # await send_session_msg(session, prefix + content + '\n' + suffix)
    # if len(pages) <= 1:
        # return
    new_messages: list[MessageSegment] = []
    msg_dict = {
        "sender": await session.bot.api.get_group_member_info(group_id=session.event.group_id, user_id=session.self_id) if session.event.group_id else await session.bot.api.get_stranger_info(user_id=session.self_id)
    }
    new_messages.append(change_group_message_content(msg_dict, prefix + '\n' + suffix))
    for page in pages:
        new_messages.append(change_group_message_content(msg_dict, page))
    return await send_forward_msg(session.bot, session.event, new_messages)
    # 翻页
#     while True:
#         # 每次刷新前缀和后缀
#         prefix = get_message("plugins", __plugin_name__, 'prefix', command_seps=" ".join(config.COMMAND_START), version=config.VERSION)
#         suffix = get_message("plugins", __plugin_name__, 'suffix', docs_link="http://docs.xme.xzadudu179.top/#/help")
#         reply: str = (await session.aget()).strip()
#         reply = reply.replace("》", ">").replace("《", "<")
#         more_page = 0
#         if not reply.startswith((">", "<", "翻页")):
#             await send_cmd(reply, session)
#             return
#         elif reply.startswith((">", "<")):
#             for c in reply:
#                 if c == ">":
#                     more_page += 1
#                 elif c == "<":
#                     more_page -= 1
#                 else:
#                     # 不可以有除了那两个箭头之外的字符
#                     await send_cmd(reply, session)
#                     return
#         else:
#             try:
#                 more_page += int(reply.split("翻页")[1])
#             except:
#                 return
#         curr_page_num += more_page
#         curr_page_num = await verify_page(session, curr_page_num, pages)
#         if not curr_page_num:
#             return
#         content = f"({curr_page_num} / {len(pages)}页)：\n" + pages[curr_page_num - 1]
#         await send_session_msg(session, prefix + content + '\n' + suffix)


# async def verify_page(session, page_num: str, pages) -> bool | int:
#     if page_num < 1:
#         reply_message = get_message("plugins", __plugin_name__, 'page_too_small')
#         await send_session_msg(session, reply_message)
#         return False
#     elif page_num > len(pages):
#         reply_message = get_message("plugins", __plugin_name__, 'page_too_big', curr_page_num=page_num)
#         await send_session_msg(session, reply_message)
#         return len(pages)
#     return page_num