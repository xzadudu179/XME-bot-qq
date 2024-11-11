import nonebot
import config
from xme.xmetools.doc_gen import CommandDoc
from xme.xmetools.command_tools import send_cmd
from xme.xmetools.list_ctrl import split_list
from nonebot import on_command, CommandSession
from xme.xmetools.text_tools import most_similarity_str

alias = ["usage", "docs", "帮助"]
__plugin_name__ = 'help'

__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    desc='显示帮助',
    introduction='显示帮助，或某个指令的帮助',
    usage=f'<功能名>',
    permissions=[],
    alias=alias
))

async def arg_help(arg, plugins, session):
    arg = arg.replace("/", "")
    p = x[-1] if (x:=most_similarity_str(arg, [p.name.lower() for p in plugins], 0.65)) else None
    print(x)
    if p:
        for pl in plugins:
            if pl.name.lower() != p[0]: continue
            return await session.send(pl.usage if pl.usage else "无内容")
        # return await session.send(p.usage if p.usage else "无内容")
    print(p)
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
    page_item_length = 6
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
        await session.send(f"{prefix}\nXME-Bot 现在还没有任何指令哦")
        return

    pages = ['\n'.join(item) for item in split_list(total_pages.split("\n")[1:], page_item_length)]
    # print(pages)
    prefix = f'[XME-Bot V0.1.2]\n指令以 {" ".join(config.COMMAND_START)} 中任意字符开头\n当前功能列表'
    # 展示页数
    suffix = f'帮助文档: http://docs.xme.xzadudu179.top/#/help\n使用 \"{config.COMMAND_START[0]}help 功能名\" 查看某功能的详细介绍哦\n在下面发送 \">\" \"<\" 或 \"》\" \"《\" 翻页'
    content = f"({curr_page_num} / {len(pages)}页)：\n" + pages[0]
    await session.send(prefix + content + '\n' + suffix)
    if len(pages) <= 1:
        return
    # 翻页
    while True:
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
        if curr_page_num < 1:
            reply_message = "页数不能小于 1 啦 xwx"
            await session.send(reply_message)
            return
        elif curr_page_num > len(pages):
            reply_message = f"页数 {curr_page_num} 超过最大页数啦 xwx，我就给你展示最后一页吧~"
            await session.send(reply_message)
            curr_page_num = len(pages)
        content = f"({curr_page_num} / {len(pages)}页)：\n" + pages[curr_page_num - 1]
        await session.send(prefix + content + '\n' + suffix)


