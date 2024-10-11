import nonebot
from nonebot import log

bot = nonebot.get_bot()  # 在此之前必须已经 init

@bot.server_app.route('/info')
async def admin():
    # await bot.send_private_msg(user_id=1795886524, message='你的主页被访问了')
    log.logger.info("bot 信息被访问了")
    with open(f'./data/botinfo.json', 'r', encoding='utf-8') as file:
        return file.read()