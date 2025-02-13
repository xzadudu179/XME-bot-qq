__plugin_name__ = '今日老婆'
from .wife import *
# from .cancanneedwife import *
from character import get_message
from xme.xmetools.doc_tools import PluginDoc

commands = ['wife']
command_properties = [
    {
        'name': 'wife',
        'introduction': get_message("plugins", __plugin_name__, 'wife_introduction'),
        'usage': '<at想看的人>',
        'permission': ['在群内使用']
    },
]
aliases = [
    wife_alias,
]
__plugin_usage__ = str(PluginDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    # desc="今日老婆相关指令",
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    # introduction="查看自己的今日老婆，或者是别人的今日老婆~",
    contents=[f"{prop['name']}: {prop['introduction']}" for prop in command_properties],
    usages=[f"{prop['name']} {prop['usage']}" for prop in command_properties],
    permissions=[prop['permission'] for prop in command_properties],
    alias_list=aliases
))