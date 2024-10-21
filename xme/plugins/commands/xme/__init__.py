from xme.xmetools.doc_gen import PluginDoc
from .register import *
from .user_info import *
from .change_name import *
from .change_bio import *
from .add_item import *

commands = ['register', 'userinfo']
command_properties = [
    {
        'name': 'register',
        'introduction': '签到',
        'usage': '',
        'permission': ['在内测群组中使用', '需要呼叫机器人']
    },
    {
        'name': 'userinfo',
        'introduction': '查看用户当前个人信息',
        'usage': '',
        'permission': ['在内测群组中使用', '需要呼叫机器人']
    },
    {
        'name': 'changename',
        'introduction': '更改自己的用户名',
        'usage': '[新用户名]',
        'permission': ['在内测群组中使用', '需要呼叫机器人']
    },
    {
        'name': 'changebio',
        'introduction': '更改自己的用户介绍',
        'usage': '[新用户介绍]',
        'permission': ['在内测群组中使用', '需要呼叫机器人']
    },
]

__plugin_name__ = 'XME'
__plugin_usage__ = str(PluginDoc(
    name=__plugin_name__,
    desc="XME 相关指令 (内部测试中)",
    introduction="XME 虚空之领宇宙相关功能 \n（注意：所有相关功能都需要 at 机器人或者输入 xme 前缀 例如 xme.r）\n主要需要测试的地方：\n1. SQL 注入\n2. 功能是否完善",
    contents=[f"{prop['name']}: {prop['introduction']}" for prop in command_properties],
    usages=[f"{prop['name']} {prop['usage']}" for prop in command_properties],
    permissions=[prop['permission'] for prop in command_properties],
    alias_list=[register_alias, user_info_alias, change_name_alias, change_bio_alias]
))