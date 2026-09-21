import nonebot
import config
from quart import request, jsonify
from xme.plugins.server_app.client_info import log_visit

bot = nonebot.get_bot()  # 在此之前必须已经 init

@bot.server_app.route('/info')
async def botinfo():
    log_visit("信息", request)
    try:
        data = {
            "code": 200,
            "name": "XME-bot",
            "author": "xzadudu179",
            "author_qq": "1795886524",
            "desc": "自己做的 qq 机器人，主要是拿来玩玩用的",
            "version": f"v{config.VERSION}"
        }

    except Exception:
        data = {
            "code": 500,
            "state": "ERROR: 无法读取数据"
        }
    finally:
        response = jsonify(data)
        response.json_module.ensure_ascii = False
        return response