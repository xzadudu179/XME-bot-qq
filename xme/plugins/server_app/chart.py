import nonebot
import traceback
from nonebot import log

bot = nonebot.get_bot()  # 在此之前必须已经 init

@bot.server_app.route('/map')
async def route_map():
    # await bot.send_private_msg(user_id=1795886524, message='你的主页被访问了')
    log.logger.info("bot 星图被访问了")
    try:
        with open('./data/images/temp/chart.png', 'rb') as image:
            # return base64.b64encode(image.read()).decode('utf-8')
            return image.read()
    except Exception as ex:
        print(ex)
        print(traceback.format_exc())
        return "ERROR"

@bot.server_app.route('/usermap')
async def route_user_map():
    # await bot.send_private_msg(user_id=1795886524, message='你的主页被访问了')
    log.logger.info("bot 用户星图被访问了")
    try:
        with open('./data/images/temp/chartinfo.png', 'rb') as image:
            # return base64.b64encode(image.read()).decode('utf-8')
            return image.read()
    except Exception as ex:
        print(ex)
        print(traceback.format_exc())
        return "ERROR"