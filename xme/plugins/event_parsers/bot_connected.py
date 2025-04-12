from nonebot import on_websocket_connect
import aiocqhttp
import xme.xmetools.colortools as c
import xme.xmetools.numtools as n
import nonebot
from xme.xmetools.jsontools import read_from_path, save_to_path
import config
import bot_variables as var
import character

@on_websocket_connect
async def connect(event: aiocqhttp.Event):
    global self_id
    bot = nonebot.get_bot()
    print(c.gradient_text("#dda3f8","#66afff" ,text=f"{character.get_message('bot_info', 'name')} 准备好啦~"))
    vars = read_from_path("data/bot_vars.json")
    vars["self_id"] = event.self_id
    save_to_path("data/bot_vars.json", vars)
    if not n.is_prime(var.currentpid):
        message = f"[DEBUG] {character.get_message('bot_info', 'name')} 准备好啦~"
        if not config.DEBUG: return
    # else:
        # 我不觉得它 在 windows 上有可能是质数
        # message = f"我的 PID 是质数诶~ ({var.currentpid})"
        message = character.get_message('config', 'pid_prime', pid=var.currentpid)
    # for group_id in config.GROUPS_WHITELIST:
        # await bot.api.send_group_msg(group_id=group_id, message=message)