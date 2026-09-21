from quart import Quart
from character import get_message
import nonebot
bot = nonebot.get_bot()



@bot.server_app.errorhandler(404)
async def page_not_found(error):
    # 只返回 dict 的话状态码会变成 200，客户端（比如文档站构建期）看不出这是 404
    return {
        "code": 404,
        "state": "Content Not Found.",
        "tip": get_message("bot_info", "tips"),
    }, 404
