from .kill import *
from .restart import *
from xme.xmetools.doc_gen import PluginDoc

commands = ['kill', 'restart']
command_properties = [
    {
        'name': 'kill',
        'introduction': '杀死 bot 进程',
        'permission': ["需要 @ bot 或是呼叫 bot", "是 SUPERUSER"]
    },
    {
        'name': 'restart',
        'introduction': '使机器人实例重新启动',
        'permission': ["需要 @ bot 或是呼叫 bot", "是 SUPERUSER"]
    }
]

__plugin_name__ = '实例控制'
__plugin_usage__ = str(PluginDoc(
    name=__plugin_name__,
    desc="机器人实例相关指令",
    introduction="全部用于控制后台机器人实例的指令，需要 SUPERUSER 才可使用。",
    contents=[f"{prop['name']}: {prop['introduction']}" for prop in command_properties],
    usages=[f'{__plugin_name__}', 'cancanneedwife (at用户)'],
    permissions=[prop['permission'] for prop in command_properties],
    alias_list=[kill_alias, restart_alias]
))