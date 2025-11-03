from nonebot import on_command, CommandSession
from xme.xmetools.doctools import CommandDoc
import os
from character import get_message
from xme.xmetools.msgtools import send_session_msg
from xme.xmetools.imgtools import image_msg
import random
random.seed()
from pathlib import Path
from datetime import datetime

alias = ['peek99', 'kk99', 'kk179']
__plugin_name__ = 'peek179'
__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    usage=f'',
    permissions=["无"],
    alias=alias
))

PEEK_PATH = rf"./static/img/179"
images = os.listdir(PEEK_PATH)
random.shuffle(images)
# index = 0
indexs = {}

@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda _: True)
async def _(session: CommandSession):
    global images
    global indexs
    if not indexs.get(str(session.event.group_id), False):
        indexs[str(session.event.group_id)] = {}
    # global index
    index: int = indexs.get(str(session.event.group_id), {}).get("index", 0)
    img_list: list = indexs.get(str(session.event.group_id), {}).get("img_list", [])
    if len(images) != len(os.listdir(PEEK_PATH)) or index == len(img_list) or not img_list:
        print("刷新图片列表")
        img_list = os.listdir(PEEK_PATH)
        random.shuffle(img_list)
        indexs[str(session.event.group_id)]["img_list"] = img_list
    if index == len(img_list):
        index = 0
    name = img_list[index]
    # print(indexs, index)
    index += 1
    path = PEEK_PATH + "/" + name
    file_path = Path(path)
    creation_time = datetime.fromtimestamp(file_path.stat().st_ctime)
    modification_time = datetime.fromtimestamp(file_path.stat().st_mtime)
    print(path)
    indexs[str(session.event.group_id)]["index"] = index
    return await send_session_msg(session, get_message("plugins", __plugin_name__, 'result', image=await image_msg(path, 1200), name=name, creation_time=creation_time, modification_time=modification_time), tips=True, tips_percent=30)