from nonebot import on_websocket_connect
import aiocqhttp
import xme.xmetools.color_manage as c
import xme.xmetools.num_tools as n
import nonebot
import config
import bot_variables as var
import character

@on_websocket_connect
async def connect(event: aiocqhttp.Event):
    bot = nonebot.get_bot()
    print(c.gradient_text("#dda3f8","#66afff" ,text=f"{character.get_item('bot_info', 'name')} 准备好啦~"))
    if not n.is_prime(var.currentpid):
        message = f"[DEBUG] {character.get_item('bot_info', 'name')} 准备好啦~"
        if not config.DEBUG: return
    else:
        # 我不觉得它有可能是质数
        message = f"我的 PID 是质数诶~ ({var.currentpid})"
    for group_id in config.GROUPS_WHITELIST:
        await bot.api.send_group_msg(group_id=group_id, message=message)