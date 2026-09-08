"""爱发电插件：发电排行、OAuth 账号绑定、个人发电状态与经营统计。

一个指令多个操作：入口指令 afdian（别名 afd/爱发电/发电），
通过 ``.afdian <操作>`` 调用，操作分发到同目录模块：
rank（排行）/ login（绑定）/ me（我的发电）/ stat（统计，仅 SUPERUSER）。
"""
__plugin_name__ = 'afdian'
cmd_name = 'afdian'
alias = ['afd', '爱发电', '发电']

# 子模块依赖上面的 __plugin_name__，需在 import 前定义
from . import constants, login, me, rank, stat, unbind  # noqa: F401,E402
from nonebot import CommandSession  # noqa: E402
from xme.xmetools.plugintools import on_command  # noqa: E402
from xme.xmetools.msgtools import send_session_msg  # noqa: E402
from character import get_message  # noqa: E402
from xme.xmetools.doctools import CommandDoc  # noqa: E402

# 操作名/别名 -> 子模块
sub_modules = [rank, login, me, stat, unbind]
alias_map: dict[str, object] = {}
for module in sub_modules:
    alias_map[module.cmd_name] = module
    for a in module.usage.get("alias", []):
        alias_map[a] = module

# 操作清单（名称、参数提示、简介来自各子模块的 usage），填入文档的 {operations}
def format_operation(module) -> str:
    """把单个操作的名称、参数提示与简介拼成一行清单文案。"""
    name = " ".join(filter(None, (module.cmd_name, module.usage.get("usage", ""))))
    return f"{name}：{module.usage['desc']}"


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
async def _(session: CommandSession):
    arg_text = session.current_arg_text.strip()
    parts = arg_text.split(None, 1)
    sub = parts[0].lower() if parts else ''
    rest = parts[1].strip() if len(parts) > 1 else ''
    if not sub:
        # 无操作时输出帮助
        await send_session_msg(session, str(__plugin_usage__), at=False)
        return True
    module = alias_map.get(sub)
    if module is None:
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'no_sub', cmd=sub))
        return False
    reply = await module.handle(session, rest)
    if reply:
        await send_session_msg(session, reply)
    return True
