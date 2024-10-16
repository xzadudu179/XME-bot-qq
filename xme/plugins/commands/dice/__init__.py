from .simdice import *
import config
from xme.xmetools.doc_gen import PluginDoc

commands = ['dice']
command_properties = [
    {
        'name': 'dice',
        'introduction': '投指定面数 * 指定数量的骰子',
        'usage': '(骰子面数) <骰子数量>',
        'permission': []
    }
]
aliases = [
    dicealias
]
__plugin_name__ = '骰子'
__plugin_usage__ = str(PluginDoc(
    name=__plugin_name__,
    desc="骰子相关指令",
    introduction="自定义面数or规则的骰子",
    contents=[f"{prop['name']}: {prop['introduction']}" for prop in command_properties],
    usages=[f"{prop['name']} {prop['usage']}" for prop in command_properties],
    permissions=[prop['permission'] for prop in command_properties],
    alias_list=aliases
))