
from .xme_config import *
from .classes.user import *
from .classes.database import *
import config
from nonebot import on_command, CommandSession
from .tools.pre_checks import *
from .tools.find_item import *

additem_alias = ["添加物品"]
@on_command('additem', aliases=additem_alias, only_to_me=True, permission=lambda x: x.from_group(config.GROUPS_WHITELIST) & x.is_superuser)
@pre_check() # 执行前检查
async def _(session: CommandSession, user: User):
    args = session.current_arg_text.strip().split(" ")
    id = args[0]
    count = int(args[1]) if len(args) > 1 else 1
    item = find_item_by_id(id)
    if item == None:
        await send_msg(session, f"呜呜 没有 ID 为 {id} 的物品...")
        return
    (stats, leftstats) = user.add_item(item, count)
    if stats:
        suffix = "" if stats and leftstats <= 0 else f"\n物品过多了哦，有 {leftstats} 个物品并没有被添加"
        await send_msg(session, f"尝试添加物品 \"{item.name}\" *{count} 成功~{suffix}")
    else:
        suffix = "\n不能添加 0 或小于 0 数量的物品哦" if leftstats == -1 else ""
        await send_msg(session, f"添加物品 \"{item.name}\" *{count} 失败 xwx{suffix}")

    inv = [item.split(",") for item in str(user.inventory).split("|")]
    message = f"{user.name}，以下是你的物品栏 owo：\n"
    has_item = False
    for i, item in enumerate(inv):
        item_info = find_item_by_id(item[0])
        if not item_info:
            continue
        has_item = True
        item_info = item_info.name
        message += f"{i + 1}.\t{item_info} *{item[1]}\n"
    if not has_item:
        message += "唔，好像什么也没有...\n"
    await send_msg(session, message)