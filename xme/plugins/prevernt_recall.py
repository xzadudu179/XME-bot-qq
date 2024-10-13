# -- coding: utf-8 --**
import json
import config
from nonebot import on_command, CommandSession

alias = ['防撤回', "precall", "防撤", '防撤回功能']
__plugin_name__ = 'prevrecall'
__plugin_usage__ = rf"""
指令 {__plugin_name__}
简介：防撤回
作用：防撤回功能相关
用法：
- {config.COMMAND_START[0]}{__plugin_name__} <开|关|T|F>
权限/可用范围：在群聊内 & 是 SUPERUSER
别名：{', '.join(alias)}
""".strip()

@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda sender: (sender.is_groupchat and (sender.is_superuser)))
async def _(session: CommandSession):
    group_id = str(session.event.group_id)
    settings = {}
    try:
        with open("./data/botsettings.json", 'r', encoding='utf-8') as jsonfile:
            settings = json.load(jsonfile)
    except:
        settings = {
            "prevent_recall": {}
        }
    # print(settings)
    prev = settings['prevent_recall'].get(group_id, False)
    message = f"本群 ({group_id}) 的防撤回功能：{'已开启' if prev else '已关闭'}"
    arg = session.current_arg_text.strip()
    if arg.capitalize() == "开" or arg.capitalize() == "T":
        settings['prevent_recall'][group_id] = True
        await session.send("防撤回功能已开owo")
    elif arg.capitalize() == "关" or arg.capitalize() == "F":
        settings['prevent_recall'][group_id] = False
        await session.send("防撤回功能已关ovo")
    else:
        await session.send(message)
    with open ("./data/botsettings.json", 'w', encoding='utf-8') as jsonfile:
        jsonfile.write(json.dumps(settings, indent=4))