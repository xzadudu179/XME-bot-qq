"""舞萌DX 插件：绑定水鱼账号、B50 查分、导入成绩 Token、解绑。

单入口指令 mai（别名 舞萌/maimai/mma），通过 ".mai <操作>" 调用，
操作分发到同目录模块：query（b50 查分）/ bind（绑定）/
update（导入 Token）/ unbind（解绑）。
"""
__plugin_name__ = 'maimai'
from xme.xmetools.moduletools import format_operation

from .constants import CMD_MAI, MAI_ALIAS  # noqa: E402

cmd_name = CMD_MAI
alias = MAI_ALIAS

# 子模块依赖上面的 __plugin_name__，需在 import 前定义
from . import query, bind, update, unbind, sync  # noqa: E402,F401
from character import get_message  # noqa: E402
from nonebot import CommandSession  # noqa: E402
from xme.plugins.commands.xme_user.classes.user import using_user  # noqa: E402
from xme.xmetools.doctools import CommandDoc  # noqa: E402
from xme.xmetools.msgtools import send_session_msg  # noqa: E402
from xme.xmetools.plugintools import on_command  # noqa: E402

# 操作名/别名 -> 子模块
sub_modules = [query, bind, update, unbind]
alias_map: dict = {}
for module in sub_modules:
    alias_map[module.cmd_name] = module
    for a in module.alias:
        alias_map[a] = module


# 操作清单（名称、参数提示、简介来自各子模块的 usage），填入文档的 {operations}



operations = "\n".join(format_operation(module) for module in sub_modules)

__plugin_usage__ = CommandDoc(
    name=cmd_name,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    introduction=get_message("plugins", __plugin_name__, 'introduction', operations=operations),
    usage='<操作>',
    permissions=[],
    alias=alias,
)


@on_command(cmd_name, aliases=alias, only_to_me=False, permission=lambda _: True)
@using_user(save_data=False)
async def _(session: CommandSession, user):
    arg_text = session.current_arg.strip()  # 用原始串，保留 at 的 CQ 码供子命令识别
    parts = arg_text.split(None, 1)
    sub = parts[0].lower() if parts else ''
    rest = parts[1].strip() if len(parts) > 1 else ''
    if not sub or sub.lower() == "help":
        # 无操作时输出帮助
        await send_session_msg(session, str(__plugin_usage__), at=False)
        return True
    module = alias_map.get(sub)
    if module is None:
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'no_sub', sub=sub))
        return False
    reply = await module.handle(session, user, rest)
    if reply:
        await send_session_msg(session, reply)
    return True
