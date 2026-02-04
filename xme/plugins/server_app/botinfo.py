import nonebot
import config
from nonebot import log

bot = nonebot.get_bot()  # 在此之前必须已经 init

@bot.server_app.route('/info')
async def botinfo():
    # await bot.send_private_msg(user_id=1795886524, message='你的主页被访问了')
    log.logger.info("bot 信息被访问了")
    try:
        return {
            "code": 200,
            "name": "XME-bot",
            "author": "xzadudu179",
            "author_qq": "1795886524",
            "desc": "自己做的 qq 机器人，主要是拿来玩玩用的",
            "version": f"v{config.VERSION}"
        }
    except Exception:
        return {
            "code": 500,
            "state": "ERROR: 无法读取数据"
        }