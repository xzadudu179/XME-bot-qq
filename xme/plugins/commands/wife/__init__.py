from .wife import *
# from .cancanneedwife import *
from xme.xmetools.doc_gen import PluginDoc

commands = ['wife']
command_properties = [
    {
        'name': 'wife',
        'introduction': '查看自己或别人的今日老婆，参数填写 at 则会同时 at 你今日的老婆',
        'usage': '<at想看的人>',
        'permission': ['在群内使用']
    },
]
aliases = [
    wife_alias,
]
__plugin_name__ = '今日老婆'
__plugin_usage__ = str(PluginDoc(
    name=__plugin_name__,
    desc="今日老婆相关指令",
    introduction="扔/查看自己的今日老婆，或者是别人的今日老婆~",
    contents=[f"{prop['name']}: {prop['introduction']}" for prop in command_properties],
    usages=[f"{prop['name']} {prop['usage']}" for prop in command_properties],
    permissions=[prop['permission'] for prop in command_properties],
    alias_list=aliases
))