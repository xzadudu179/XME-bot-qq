import time

import nonebot
from quart import abort, request, send_file
from keys import FILE_TOKENS
from xme.plugins.server_app.client_info import log_visit
# from xme.xmetools.filetools import send_file

bot = nonebot.get_bot()  # 在此之前必须已经 init

@bot.server_app.route('/file/<token>')
async def get_file(token: str):
    log_visit("文件", request)
    info = FILE_TOKENS.get(token, None)
    if info is None:
        abort(404)
    if time.time() > info["expires_at"]:
        FILE_TOKENS.pop(token, None)
        abort(410)
    try:
        return await send_file(info["path"])
    except FileNotFoundError:
        abort(404)


@bot.server_app.after_request
async def security_headers(response):
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response