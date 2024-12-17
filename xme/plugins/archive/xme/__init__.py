
from .xme_config import *
from xme.xmetools.doc_gen import SpecialDoc
from nonebot import on_command, CommandSession
from config import *
from .register import *
from .user_info import *
from .change_name import *
from .change_bio import *
from .add_item import *
from .show_inventory import *
from .drop_item import *
from .check_item import *


commands = ['register', 'userinfo', 'changename', 'changebio', 'showinv', 'dropitem']
command_properties = [
    {
        'name': 'register',
        'desc': '签到',
        'introduction': '签到，一般可获得一定数量的虚拟星币',
        'usage': '',
        'permission': ['在内测群组中使用', '需要呼叫机器人'],
        'alias': register_alias,
    },
    {
        'name': 'userinfo',
        'desc': '个人信息',
        'introduction': '查看用户当前个人信息',
        'usage': '',
        'permission': ['在内测群组中使用', '需要呼叫机器人'],
        'alias': user_info_alias,
    },
    {
        'name': 'changename',
        'desc': '改名',
        'introduction': '更改自己的用户名',
        'usage': '(新用户名)',
        'permission': ['在内测群组中使用', '需要呼叫机器人'],
        'alias': change_name_alias,
    },
    {
        'name': 'changebio',
        'desc': '更改介绍',
        'introduction': '更改自己的用户介绍',
        'usage': '(新用户介绍)',
        'permission': ['在内测群组中使用', '需要呼叫机器人'],
        'alias': change_bio_alias,
    },
    {
        'name': 'showinv',
        'desc': '查看物品栏',
        'introduction': '查看自己的物品栏',
        'usage': '',
        'permission': ['在内测群组中使用', '需要呼叫机器人'],
        'alias': show_inv_alias,
    },
    {
        'name': 'dropitem',
        'desc': '扔掉物品',
        'introduction': '扔掉物品栏里的物品',
        'usage': '(物品栏序号) <数量>',
        'permission': ['在内测群组中使用', '需要呼叫机器人'],
        'alias': dropitem_alias,
    },
    {
        'name': 'checkitem',
        'desc': '查看物品',
        'introduction': '查看物品栏里的物品详细信息',
        'usage': '(物品栏序号)',
        'permission': ['在内测群组中使用', '需要呼叫机器人'],
        'alias': checkitem_alias,
    },
]

__plugin_name__ = 'XME'
__plugin_usage__ = str(SpecialDoc(
    name=__plugin_name__,
    desc="XME 相关功能",
    introduction=rf"""
XME 虚空之领宇宙相关功能
（注意：所有相关功能都需要 at 机器人或者输入 xme 前缀 例如 xme.r）
请使用 {COMMAND_START[0]}xmehelp 查看详细帮助。
主要需要测试的地方：
\t1. SQL 注入问题
\t2. 功能是否完善
""".strip()))


register_alias = ["xme帮助"]
@on_command('xmehelp', aliases=register_alias, only_to_me=False)
async def _(session: CommandSession):
    """查看帮助"""
    # user_id = session.event.user_id
    message = "以下是和 XME 虚空之领宇宙有关的帮助 owo\n"
    arg = session.current_arg_text.strip()
    result = None
    for prop in command_properties:
        if prop['name'] == arg:
            result = prop
        elif arg in prop['alias']:
            result = prop
    if result:
        message = f"""
[指令] {result['name']}
简介：{result['desc']}
作用：{result['introduction']}
用法：
- xme{COMMAND_START[0]}{result['name']} {result['usage']}
权限/可用范围：{', '.join(result['permission'])}
别名：{', '.join(result['alias'])}""".strip()
    else:
        for prop in command_properties:
            message += f"{COMMAND_START[0]}{prop['name']}\t{prop['desc']}\n"
        message += f"使用 \"{COMMAND_START[0]}xmehelp 指令名或别名\" 来查看某个指令详细的帮助哦"
    await send_msg(session, message)
