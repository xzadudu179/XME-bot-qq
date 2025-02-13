from nonebot import on_command, CommandSession
from xme.xmetools.doc_tools import CommandDoc
import os
from character import get_message
from xme.xmetools.command_tools import send_session_msg
from xme.xmetools.image_tools import image_msg
import random
from pathlib import Path
from datetime import datetime

alias = ['看看179', '看看九九', '看看九镹', 'peek99', '看看99']
__plugin_name__ = 'peek179'
__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    usage=f'',
    permissions=["无"],
    alias=alias
))

PEEK_PATH = rf"./data/images/179"
images = os.listdir(PEEK_PATH)
random.shuffle(images)
index = 0

@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda _: True)
async def _(session: CommandSession):
    global images
    global index
    if len(images) != len(os.listdir(PEEK_PATH)) or index == len(images):
        print("刷新图片列表")
        images = os.listdir(PEEK_PATH)
        random.shuffle(images)
    if index == len(images):
        index = 0
    name = images[index]
    print(index)
    index += 1
    path = PEEK_PATH + "/" + name
    file_path = Path(path)
    creation_time = datetime.fromtimestamp(file_path.stat().st_ctime)
    modification_time = datetime.fromtimestamp(file_path.stat().st_mtime)
    print(path)
    return await send_session_msg(session, get_message("plugins", __plugin_name__, 'result', image=await image_msg(path, 1200), name=name, creation_time=creation_time, modification_time=modification_time))