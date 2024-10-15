from .wife import *
from .cancanneedwife import *
from xme.xmetools.doc_gen import PluginDoc

commands = ['wife', 'cancanneedwife']
command_properties = [
    {
        'name': 'wife',
        'introduction': '查看你今日的老婆群员',
        'permission': ['在群内使用']
    },
    {
        'name': 'cancanneedwife',
        'introduction': '查看指定群员的今日老婆群员',
        'permission': ['在群内使用']
    }
]

__plugin_name__ = 'wife'
__plugin_usage__ = str(PluginDoc(
    name=__plugin_name__,
    desc="今日老婆相关指令",
    introduction="查看自己的今日老婆，或者是别人的今日老婆",
    contents=[f"{prop['name']}: {prop['introduction']}" for prop in command_properties],
    usages=[f'{__plugin_name__}', 'cancanneedwife (at用户)'],
    permissions=[f"{prop['permission']}" for prop in command_properties],
    alias_list=[wife_alias, cancanneedalias]
))