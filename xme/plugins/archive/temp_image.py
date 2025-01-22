import nonebot
import traceback
from nonebot import log
bot = nonebot.get_bot()  # 在此之前必须已经 init

@bot.server_app.route('/temp/<filename>')
async def route_img(filename: str):
    print(filename)
    log.logger.info("bot 图像被访问了")
    try:
        folder_path = './data/images/temp'
        # files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
        # latest_file = max(files, key=lambda f: os.path.getctime(os.path.join(folder_path, f)))
        with open(folder_path + '/' + filename, 'rb') as image:
            # return base64.b64encode(image.read()).decode('utf-8')
            ib = image.read()
        return ib
    except Exception as ex:
        print(ex)
        print(traceback.format_exc())
        return "ERROR"