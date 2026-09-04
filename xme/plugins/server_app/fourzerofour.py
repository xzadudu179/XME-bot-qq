from quart import Quart
from character import get_message
import nonebot
bot = nonebot.get_bot()



@bot.server_app.errorhandler(404)
async def page_not_found(error):
    return {
        "code": 404,
        "state": "Content Not Found.",
        "tip": get_message("bot_info", "tips"),
    }