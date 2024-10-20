from .register import *
from xme.xmetools.doc_gen import PluginDoc

commands = ['register']
command_properties = [
    {
        'name': 'register',
        'introduction': '签到 / 自动注册并签到',
        'usage': '',
        'permission': ['在内测群组中使用', '需要呼叫机器人']
    },
]

__plugin_name__ = 'xme'
__plugin_usage__ = str(PluginDoc(
    name=__plugin_name__,
    desc="xme 相关指令 (内部测试中)",
    introduction="xme 虚空之领宇宙相关功能 \n（注意：所有相关功能都需要 at 机器人或者输入 xme 前缀 例如 xme.r）",
    contents=[f"{prop['name']}: {prop['introduction']}" for prop in command_properties],
    usages=[f"{prop['name']} {prop['usage']}" for prop in command_properties],
    permissions=[prop['permission'] for prop in command_properties],
    alias_list=[register_alias]
))