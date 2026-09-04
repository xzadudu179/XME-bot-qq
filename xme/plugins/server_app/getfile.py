import time

import nonebot
import config
from nonebot import log
from quart import abort, request, send_file
from keys import FILE_TOKENS
# from xme.xmetools.filetools import send_file

bot = nonebot.get_bot()  # 在此之前必须已经 init

@bot.server_app.route('/file/<token>')
async def get_file(token: str):
    client_ip = request.headers.get('X-Forwarded-For', request.headers.get('X-Real-IP', request.remote_addr))
    log.logger.info(f"bot 文件被访问了，访问者 IP: {client_ip}")
    info = FILE_TOKENS.get(token, None)
    if info is None:
        abort(404)
    if time.time() > info["expires_at"]:
        FILE_TOKENS.pop(token, None)
        abort(410)

    return await send_file(info["path"])


@bot.server_app.after_request
async def security_headers(response):
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response