from xme.xmetools.rss_tools import *
import nonebot
import config
from xme.xmetools.doc_gen import CommandDoc
from nonebot import on_command, CommandSession
from character import get_message

alias = ["九九文章", "rss179", "posts179", "blogposts", "posts", "post"]
__plugin_name__ = 'xmeposts'

__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    desc=get_message(__plugin_name__, 'desc'),
    # desc='查看九九最近的文章',
    introduction=get_message(__plugin_name__, 'introduction'),
    # introduction='通过 RSS 订阅并查看九九最近的 n 个文章，默认 1 个',
    usage=f'<文章数>',
    permissions=[],
    alias=alias
))

@on_command(__plugin_name__, aliases=alias, only_to_me=False)
async def _(session: CommandSession):
    max_count = 10
    arg = session.current_arg_text.strip()
    try:
        count = 1 if not arg else int(arg)
        if count > max_count:
            return await session.send(get_message(__plugin_name__, 'too_many').format(max=max_count))
            # return await session.send(f"最多查看 10 个文章哦")
        elif count <= 0:
            return await session.send(get_message(__plugin_name__, 'invalid_count'))
    except:
        return await session.send(get_message(__plugin_name__, 'invalid_count'))
        # return await session.send(f"请输入正确的文章数量哦")
    await session.send(f"[CQ:at,qq={session.event.user_id}] " + get_message(__plugin_name__, 'post_msg').format(count=count, posts=show_rss(catch_179rss(), count)))
    # await session.send(f"[CQ:at,qq={session.event.user_id}] 以下是九九最新的 {count} 个文章哦！\n{show_rss(catch_179rss(), count)}")