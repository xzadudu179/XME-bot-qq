from nonebot import on_command, CommandSession
from xme.xmetools import request_tools
from character import get_message
from xme.xmetools.doc_gen import CommandDoc
from xme.xmetools.command_tools import send_msg
import json

alias = ["涩图", "setu", "色图" ]
__plugin_name__ = 'setu'

__plugin_usage__= str(CommandDoc(
    name=__plugin_name__,
    desc=get_message(__plugin_name__, 'desc'),
    # desc='涩图？',
    introduction=get_message(__plugin_name__, 'introduction'),
    # introduction='返回一张涩图？',
    usage=f'',
    permissions=[],
    alias=alias
))

@on_command(__plugin_name__, aliases=alias, only_to_me=False)
async def setu(session: CommandSession):
    # api_url = "https://api.lolicon.app/setu/v2?r18=0&excludeAI=true&size=small"
    # result = await fetch_image_data(api_url)
    # if result:
    #     # await send_msg(session, "已找到图片，正在发送...")
    #     print(result.url)
    #     await send_msg(session, f"""
    #     图片标题: {result.title}
    #     图片pid: {result.pid}
    #     作者: {result.author}
    #     tags: {result.tags}
    #     --------------------
    #     [CQ:image,file={result.url}]""".strip())
    # else:
    #     await send_msg(session, "无法获取图片信息.")
    await send_msg(session, get_message(__plugin_name__, 'not_setu_msg').format(image_name='彩虹蟑螂', image='[CQ:image,file=https://image.179.life/images/rainbow_cockroach.gif]'))
    # await send_msg(session, "哪有涩图，XME找不到涩图呜，但是有彩虹蟑螂！\n[CQ:image,file=https://image.179.life/images/rainbow_cockroach.gif]")


class ImageData:
    def __init__(self, title, url, pid, author, tags):
        self.title = title
        self.url = url
        self.pid = pid
        self.author = author
        self.tags = tags
async def fetch_image_data(url):
    response = await request_tools.fetch_data(url)
    data = json.loads(response)
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

