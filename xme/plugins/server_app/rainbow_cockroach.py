import nonebot
import config
from nonebot import log
from quart import request, jsonify

bot = nonebot.get_bot()  # 在此之前必须已经 init

@bot.server_app.route('/cockroach')
async def cockroach():
    client_ip = request.headers.get('X-Forwarded-For', request.headers.get('X-Real-IP', request.remote_addr))
    if client_ip and ',' in client_ip:
        client_ip = client_ip.split(',')[0].strip()
    log.logger.info(f"bot cockroach 被访问了，访问者 IP: {client_ip}")
    response = r"""
<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Cockroach</title>
        <style>
        .mid {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100svh;
        }
    </style>
    </head>
    <body>
        <div class="mid">
            <a href="https://www.bilibili.com/video/BV1vu4y1A7Am/?spm_id_from=333.1387.favlist.content.click&vd_source=0fe1c8bddb57dde7b4b8430a66b89b7b">
                <img src="https://image.179.life/images/rainbow_cockroach.gif" alt
                style="width: min(100%, 500px)">
            </a>
        </div>
    </body>
</html>
    """
    return response
