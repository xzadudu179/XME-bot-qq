__plugin_name__ = '漂流瓶'
from .throw import *
from .pickup import *
from .cthulhu import *
from xme.xmetools.doctools import PluginDoc
from character import get_message

commands = ['throw', 'pickup']
command_properties = [
    {
        'name': 'throw',
        'introduction': get_message("plugins", __plugin_name__, 'throw_introduction'),
        # 'introduction': '扔一个漂流瓶',
        'usage': '(瓶子内容)',
        'permission': ['在群内使用']
    },
    {
        'name': 'pickup',
        'introduction': get_message("plugins", __plugin_name__, 'pickup_introduction'),
        # 'introduction': '尝试捡一个漂流瓶',
        'usage': '',
        'permission': []
    },
    {
        'name': 'cthulhu',
        'introduction': get_message("plugins", __plugin_name__, 'cthulhu_introduction'),
        # 'introduction': '尝试捡一个漂流瓶',
        'usage': '(瓶子id 以空格分隔)',
        'permission': ['是 SUPERUSER']
    }
]
aliases = [
    throw_alias,
    pickup_alias,
    cthulhu_alias
]
__plugin_usage__ = str(PluginDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    # desc="漂流瓶相关指令",
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    # introduction="扔/捡来自各个群组的漂流瓶~",
    contents=[f"{prop['name']}: {prop['introduction']}" for prop in command_properties],
    usages=[f"{prop['name']} {prop['usage']}" for prop in command_properties],
    permissions=[prop['permission'] for prop in command_properties],
    alias_list=aliases
))