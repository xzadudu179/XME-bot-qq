from nonebot import on_command, CommandSession
from xme.xmetools.doc_gen import CommandDoc
import random
from xme.xmetools import text_tools

alias = ['选择', 'cho', '决定']
__plugin_name__ = 'choice'
__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    desc='随机决定事情',
    introduction='让 xme 帮忙决定事情吧！',
    usage=f'(事情列表(空格分隔))',
    permissions=[],
    alias=alias
))

@on_command(__plugin_name__, aliases=alias, only_to_me=False)
async def _(session: CommandSession):
    args = session.current_arg_text.strip()
    if not args:
        await session.send(f"[CQ:at,qq={session.event.user_id}] 你还没有说我要决定的事情哦 ovo")
        return
    choices = args.split(" ")
    # print(len(choices), choices)
    await session.send(f"[CQ:at,qq={session.event.user_id}] 我觉得可以选择 \"{random.choice(choices)}\"！")