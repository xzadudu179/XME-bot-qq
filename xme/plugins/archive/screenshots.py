import nonebot
import os
import traceback
from nonebot import log

bot = nonebot.get_bot()  # 在此之前必须已经 init

@bot.server_app.route('/screenshot')
async def route_screenshot():
    # await bot.send_private_msg(user_id=1795886524, message='你的主页被访问了')
    log.logger.info("bot 截图被访问了")
    try:
        folder_path = './screenshots'
        files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
        latest_file = max(files, key=lambda f: os.path.getctime(os.path.join(folder_path, f)))
        with open(folder_path + '/' + latest_file, 'rb') as image:
            # return base64.b64encode(image.read()).decode('utf-8')
            return image.read()
    except Exception as ex:
        print(ex)
        print(traceback.format_exc())
        return "ERROR"