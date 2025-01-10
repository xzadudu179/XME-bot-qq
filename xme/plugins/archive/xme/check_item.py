
from .xme_config import *
from .classes.user import *
from .classes.database import *
import config
from nonebot import on_command, CommandSession
from .tools.pre_checks import *
from .tools.find_item import *

checkitem_alias = ["查看物品", "check"]
@on_command('checkitem', aliases=checkitem_alias, only_to_me=True, permission=lambda x: x.from_group(config.GROUPS_WHITELIST))
@pre_check() # 执行前检查
async def _(session: CommandSession, user: User):
    args = session.current_arg_text.strip().split(" ")
    if not args:
        await send_session_msg(session, "请符合指令格式输入哦 ovo\ncheckitem (物品栏编号)")
        return
    index = int(args[0]) - 1
    item = user.inventory.find_item_by_index(index)
    if not item:
        await send_session_msg(session, f"呜呜 没有物品栏编号为 {index + 1} 对应的物品...")
        return
    await send_session_msg(session, item.info())
    # (stats, left) = user.del_item(item, count)
    # if stats:
    #     await send_msg(session, f"{user.name}，你成功丢弃了 {count} 个 \"{item.name}\"哦 owo")
    # else:
    #     await send_msg(session, f"{user.name}: 丢弃物品 \"{item.name}\" *{count} 失败 xwx\n还需要 {left} 个物品")