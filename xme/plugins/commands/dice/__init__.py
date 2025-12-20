__plugin_name__ = '骰子'
from .simdice import *
from character import get_message
from xme.xmetools.doctools import PluginDoc

commands = ['dice']
command_properties = [
    {
        'name': 'dice',
        'introduction': get_message("plugins", __plugin_name__, 'dice_introduction'),
        # 'introduction': '投指定面数 * 指定数量的骰子',
        'usage': '(骰子面数) <骰子数量>',
        'permission': []
    }
]
aliases = [
    dicealias
]
__plugin_usage__ = PluginDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    # desc="骰子相关指令",
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    # introduction="自定义面数or规则的骰子",
    contents=[f"{prop['name']}: {prop['introduction']}" for prop in command_properties],
    usages=[f"{prop['name']} {prop['usage']}" for prop in command_properties],
    permissions=[prop['permission'] for prop in command_properties],
    alias_list=aliases
)