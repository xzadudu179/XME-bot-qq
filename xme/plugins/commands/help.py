import nonebot
import config
from xme.xmetools.doc_tools import CommandDoc
from xme.xmetools.command_tools import send_cmd, get_cmd_by_alias
from xme.xmetools.list_ctrl import split_list
from xme.xmetools.command_tools import send_cmd_msg
from nonebot import on_command, CommandSession
from character import get_message
from xme.xmetools.text_tools import most_similarity_str

alias = ["usage", "docs", "帮助", "h"]
__plugin_name__ = 'help'

__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    # desc='显示帮助',
    desc=get_message(__plugin_name__, 'desc'),
    introduction=get_message(__plugin_name__, 'introduction'),
    # introduction='显示帮助，或某个指令的帮助，功能名若填写数字则是翻到数字所指的页数',
    usage=f'<功能名>',
    permissions=[],
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
    if ask_for_help:
        for pl in plugins:
            if f"{pl.usage.split(']')[0]}]" in ["[插件]"] and ask_for_help in [i.split(":")[0].strip().split(" ")[0] for i in pl.usage.split("##内容##：")[1].split("##所有指令用法##：")[0].split("\n")[:] if i]:
                ask_for_help = pl.name.lower()
            if pl.name.lower() != ask_for_help: continue
            return await send_cmd_msg(session, pl.usage if pl.usage else get_message(__plugin_name__, 'no_usage'), at=True)
            # return await send_msg(session, pl.usage if pl.usage else "无内容")
    # print(p)
    return False

@on_command(__plugin_name__, aliases=alias, only_to_me=False)
async def _(session: CommandSession):
    plugins = list(filter(lambda p: p.name, nonebot.get_loaded_plugins()))
    arg = session.current_arg_text.strip().lower()
    # 如果发了参数则发送相应命令的使用帮助
    curr_page_num = 1
    print("发送帮助")
    if arg:
        try:
            curr_page_num = int(arg)
        except:
            # 如果不能成数字那就是功能
            if await arg_help(arg, plugins, session) != False: return
    # help_list_str = ""
    page_item_length = 10
    # 分页
    pages = []
    index = 0
    total_pages = ""
    for p in plugins:
        index += 1
        try:
            total_pages += "\n\t" + f"{p.usage.split(']')[0]}] {p.name}    " + p.usage.split('简介：')[1].split('\n')[0].strip()
        except:
            total_pages += "\n\t" + f"[未知] {p.name}"

    if len(total_pages.split("\n")) < 1:
        await send_cmd_msg(session, get_message(__plugin_name__, 'no_cmds', prefix=prefix))
        # await send_msg(session, f"{prefix}\n{get_info('name')}现在还没有任何指令哦")
        return

    pages = ['\n'.join(item) for item in split_list(total_pages.split("\n")[1:], page_item_length)]
    # print(pages)
    prefix = get_message(__plugin_name__, 'prefix', command_seps=" ".join(config.COMMAND_START), version=config.VERSION)
    # prefix = f'[XME-Bot V0.1.2]\n指令以 {" ".join(config.COMMAND_START)} 中任意字符开头\n当前功能列表'
    # 展示页数
    suffix = get_message(__plugin_name__, 'suffix', docs_link="http://docs.xme.xzadudu179.top/#/help", cmd_sep=config.COMMAND_START[0])
    # suffix = f'帮助文档: http://docs.xme.xzadudu179.top/#/help\n使用 \"{config.COMMAND_START[0]}help 功能名\" 查看某功能的详细介绍哦\n在下面发送 \">\" \"<\" 或 \"》\" \"《\" 翻页'
    curr_page_num = await verify_page(session, curr_page_num, pages)
    if not curr_page_num:
        return
    content = f"({curr_page_num} / {len(pages)}页)：\n" + pages[curr_page_num - 1]
    await send_cmd_msg(session, prefix + content + '\n' + suffix)
    if len(pages) <= 1:
        return
    # 翻页
    while True:
        # 每次刷新前缀和后缀
        prefix = get_message(__plugin_name__, 'prefix', command_seps=" ".join(config.COMMAND_START), version=config.VERSION)
        suffix = get_message(__plugin_name__, 'suffix', docs_link="http://docs.xme.xzadudu179.top/#/help", cmd_sep=config.COMMAND_START[0])
        reply: str = (await session.aget()).strip()
        reply = reply.replace("》", ">").replace("《", "<")
        more_page = 0
        if not reply.startswith((">", "<", "翻页")):
            await send_cmd(reply, session)
            return
        elif reply.startswith((">", "<")):
            for c in reply:
                if c == ">":
                    more_page += 1
                elif c == "<":
                    more_page -= 1
                else:
                    # 不可以有除了那两个箭头之外的字符
                    await send_cmd(reply, session)
                    return
        else:
            try:
                more_page += int(reply.split("翻页")[1])
            except:
                return
        curr_page_num += more_page
        curr_page_num = await verify_page(session, curr_page_num, pages)
        if not curr_page_num:
            return
        # if curr_page_num < 1:
        #     reply_message = get_message(__plugin_name__, 'page_too_small')
        #     # reply_message = "页数不能小于 1 啦 xwx"
        #     await send_msg(session, reply_message)
        #     return
        # elif curr_page_num > len(pages):
        #     reply_message = get_message(__plugin_name__, 'page_too_big', curr_page_num=curr_page_num)
        #     # reply_message = f"页数 {curr_page_num} 超过最大页数啦 xwx，我就给你展示最后一页吧~"
        #     await send_msg(session, reply_message)
        #     curr_page_num = len(pages)
        content = f"({curr_page_num} / {len(pages)}页)：\n" + pages[curr_page_num - 1]
        await send_cmd_msg(session, prefix + content + '\n' + suffix)


async def verify_page(session, page_num: str, pages) -> bool | int:
    if page_num < 1:
        reply_message = get_message(__plugin_name__, 'page_too_small')
        await send_cmd_msg(session, reply_message)
        return False
    elif page_num > len(pages):
        reply_message = get_message(__plugin_name__, 'page_too_big', curr_page_num=page_num)
        await send_cmd_msg(session, reply_message)
        return len(pages)
    return page_num