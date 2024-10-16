from xme.xmetools.rss_tools import *
import nonebot
import config
from xme.xmetools.doc_gen import CommandDoc
from nonebot import on_command, CommandSession

alias = ["九九文章", "rss179", "atom179", "xmeatom", "rss"]
__plugin_name__ = 'xmerss'

__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    desc='查看九九最近的文章',
    introduction='通过 RSS 订阅并查看九九最近的 n 个文章，默认 5 个',
    usage=f'<文章数>',
    permissions=[],
    alias=alias
))

@on_command(__plugin_name__, aliases=alias, only_to_me=False)
async def _(session: CommandSession):
    count = 5
    arg = session.current_arg_text.strip()
    if arg:
        try:
            count = int(arg)
            if count > 10:
                print("最多查看 10 个文章哦")
        except:
            return await session.send(f"请输入正确的文章数量哦")
    await session.send(f"[CQ:at,qq={session.event.user_id}] 以下是九九最近的 {count} 个文章哦！\n{show_rss(catch_179rss(), count)}")