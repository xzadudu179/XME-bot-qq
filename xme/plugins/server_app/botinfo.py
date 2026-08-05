import nonebot
import config
from nonebot import log
from quart import request, jsonify

bot = nonebot.get_bot()  # 在此之前必须已经 init

@bot.server_app.route('/info')
async def botinfo():
    client_ip = request.headers.get('X-Forwarded-For', request.headers.get('X-Real-IP', request.remote_addr))
    if client_ip and ',' in client_ip:
        client_ip = client_ip.split(',')[0].strip()
    log.logger.info(f"bot 信息被访问了，访问者 IP: {client_ip}")
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