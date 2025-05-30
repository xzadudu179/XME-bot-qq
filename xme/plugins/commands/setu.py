from nonebot import on_command, CommandSession
from xme.xmetools import reqtools
from character import get_message
from xme.xmetools.doctools import CommandDoc
from xme.xmetools.randtools import random_percent
import random
random.seed()
import os
from xme.xmetools.msgtools import send_session_msg
from xme.xmetools.imgtools import image_msg

alias = ["涩图", "setu", "色图" ]
__plugin_name__ = 'setu'

__plugin_usage__= str(CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    # desc='涩图？',
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    # introduction='返回一张涩图？',
    usage=f'',
    permissions=["无"],
    alias=alias
))
PATH_179 = rf"./data/images/179"
@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda _: True)
async def setu(session: CommandSession):
    image_name = "彩虹蟑螂"
    # is_179 = random_percent(30)
    # if is_179:
    #     print("是 179，看看")
    #     image_name = "九九"
    image = "[CQ:image,file=https://image.179.life/images/rainbow_cockroach.gif]"
    await send_session_msg(session, get_message("plugins", __plugin_name__, 'not_setu_msg', image_name=image_name, image=image))
    # await send_msg(session, "哪有涩图，XME找不到涩图呜，但是有彩虹蟑螂！\n[CQ:image,file=https://image.179.life/images/rainbow_cockroach.gif]")


class ImageData:
    def __init__(self, title, url, pid, author, tags):
        self.title = title
        self.url = url
        self.pid = pid
        self.author = author
        self.tags = tags
async def fetch_image_data(url):
    data = await reqtools.fetch_data(url)
    print(data)

    if data.get('error'):
        print(f"Error: {data['error']}")
        return None

    image_data = data['data'][0]
    return ImageData(
        title=image_data['title'],
        url=image_data['urls']['small'],
        pid=image_data['pid'],
        author=image_data['author'],
        tags=image_data['tags']
    )

