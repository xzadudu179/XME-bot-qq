

import requests
from itsdangerous import base64_encode
from nonebot import on_command, CommandSession

from xme.xmetools.doc_gen import CommandDoc

alias = ["涩图" , "setu" , "色图" ]
__plugin_name__ = 'setu'

__plugin_usage__= str(CommandDoc(
    name=__plugin_name__,
    desc='涩图',
    introduction='查看涩图',
    usage=f'setu',
    permissions=[],
    alias=alias
))

@on_command(__plugin_name__, aliases=alias)
async def setu(session: CommandSession):
    api_url = "https://api.lolicon.app/setu/v2?r18=0&excludeAI=true"
    result = fetch_image_data(api_url)
    if result:
        await session.send(f"""
         图片标题: {result.title}
         图片pid: {result.pid}
         作者: {result.author}
         -----------
         [CQ:image , file={base64_encode(result.url)}]
        """)
    else:
        await session.send("无法获取图片信息.")


class ImageData:
    def __init__(self, title, url, pid, author):
        self.title = title
        self.url = url
        self.pid = pid
        self.author = author
def fetch_image_data(url):
    response = requests.get(url)
    data = response.json()

    if data.get('error'):
        print(f"Error: {data['error']}")
        return None

    image_data = data['data'][0]
    return ImageData(
        title=image_data['title'],
        url=image_data['urls']['original'],
        pid=image_data['pid'],
        author=image_data['author']
    )

