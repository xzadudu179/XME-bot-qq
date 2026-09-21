import nonebot
from quart import request
from xme.plugins.server_app.client_info import log_visit

bot = nonebot.get_bot()  # 在此之前必须已经 init

@bot.server_app.route('/cockroach')
async def cockroach():
    log_visit("cockroach", request)
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
