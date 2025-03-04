__plugin_name__ = '实例控制'
from .kill import *
from ...archive.restart import *
from xme.xmetools.doctools import PluginDoc
from character import get_message

commands = ['inst_kill', 'inst_restart']
command_properties = [
    {
        'name': 'inst_kill',
        'introduction': get_message("plugins", __plugin_name__, 'kill_introduction'),
        # 'introduction': '杀死 bot 进程',
        'permission': ["需要 @ bot 或是呼叫 bot", "是 SUPERUSER"],
        'usage': ''
    },
    {
        'name': 'inst_restart',
        'introduction': get_message("plugins", __plugin_name__, 'restart_introduction'),
        # 'introduction': '使机器人实例重新启动',
        'permission': ["需要 @ bot 或是呼叫 bot", "是 SUPERUSER"],
        'usage': ''
    }
]

__plugin_usage__ = str(PluginDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    # desc="机器人实例相关指令",
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    # introduction="全部用于控制后台机器人实例的指令，需要 SUPERUSER 才可使用。",
    contents=[f"{prop['name']}: {prop['introduction']}" for prop in command_properties],
    usages=[f"{prop['name']} {prop['usage']}" for prop in command_properties],
    permissions=[prop['permission'] for prop in command_properties],
    alias_list=[kill_alias, restart_alias]
))