# 注册账号 或签到
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
    try:
        item = find_item_by_id(id)
        if user.add_item(item, count):
            await session.send(f"添加物品 \"{item.name}\" 成功~")
        else:
            await session.send(f"添加物品 \"{item.name}\" 失败 xwx")
    except KeyError:
        await session.send(f"呜呜 没有 ID 为 {id} 的物品...")