from xme.xmetools.rsstools import show_rss, catch_179rss
from xme.xmetools.msgtools import send_session_msg
from xme.xmetools.doctools import CommandDoc
from nonebot import CommandSession
from xme.xmetools.plugintools import on_command
from character import get_message
from xme.xmetools.debugtools import debug_msg
# from nonebot.log import logger

alias = ["九九文章", "rss179", "posts179", "blogposts", "posts", "post"]
__plugin_name__ = 'xmeposts'

__plugin_usage__ = CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    # desc='查看九九最近的文章',
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    # introduction='通过 RSS 订阅并查看九九最近的 n 个文章，默认 1 个',
    usage='<文章数>',
    permissions=["无"],
    alias=alias
)

@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda _: True)
async def _(session: CommandSession):
    max_count = 10
    arg = session.current_arg_text.strip()
    try:
        count = 1 if not arg else int(arg)
        if count > max_count:
            return await send_session_msg(session, get_message("plugins", __plugin_name__, 'too_many', max=max_count))
            # return await send_msg(session, f"最多查看 10 个文章哦")
        elif count <= 0:
            return await send_session_msg(session, get_message("plugins", __plugin_name__, 'invalid_count'))
    except Exception:
        return await send_session_msg(session, get_message("plugins", __plugin_name__, 'invalid_count'))
        # return await send_msg(session, f"请输入正确的文章数量哦")
    debug_msg("rss" + show_rss(catch_179rss(), count))
    await send_session_msg(session, get_message("plugins", __plugin_name__, 'post_msg', count=count, posts=show_rss(catch_179rss(), count).replace("xzadudu179.github.io", "blog.xzadudu179.top")), tips=True, tips_percent=20)