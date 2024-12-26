from xme.xmetools.rss_tools import *
from xme.xmetools.command_tools import send_cmd_msg
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
            return await send_cmd_msg(session, get_message(__plugin_name__, 'too_many', max=max_count))
            # return await send_msg(session, f"最多查看 10 个文章哦")
        elif count <= 0:
            return await send_cmd_msg(session, get_message(__plugin_name__, 'invalid_count'))
    except:
        return await send_cmd_msg(session, get_message(__plugin_name__, 'invalid_count'))
        # return await send_msg(session, f"请输入正确的文章数量哦")
    await send_cmd_msg(session, get_message(__plugin_name__, 'post_msg', count=count, posts=show_rss(catch_179rss(), count)))