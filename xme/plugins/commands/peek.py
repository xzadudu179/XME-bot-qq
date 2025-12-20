from nonebot import on_command, CommandSession
from xme.xmetools.doctools import CommandDoc
from xme.xmetools import imgtools
from aiocqhttp import MessageSegment
from xme.xmetools import jsontools
from xme.xmetools import colortools as c
import traceback
try:
    import pygetwindow as gw
except:
    pass
import config
from character import get_message
from xme.xmetools.msgtools import send_session_msg

alias = ['视奸', '视奸179', 'peekbot']
__plugin_name__ = 'peek'
__plugin_usage__ = CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    usage=f'<显示器序号>',
    permissions=['在可视奸的群组内'],
    alias=alias
)

@on_command(__plugin_name__, aliases=alias, only_to_me=False)
async def _(session: CommandSession):
    if session.event.group_id not in config.PEEK_GROUP:
        return await send_session_msg(session, get_message("plugins", __plugin_name__, 'not_in_peek_group'))
    private_window_names = jsontools.read_from_path('./private_window_names.json')['private']
    try:
        current_window = gw.getActiveWindow()
    except:
        current_window = None
    is_private = False
    if current_window:
        for name in private_window_names:
            print(name, isinstance(name, list))
            if isinstance(name, list):
                if current_window.title not in name: continue
                is_private = True
                break
            if name in current_window.title:
                is_private = True
                break
    if is_private:
        return await send_session_msg(session, get_message("plugins", __plugin_name__, 'is_private', title=current_window.title))
    print(c.gradient_text("#FF5287", "#FF5257", "#FF8257", text=f"{'=' * 20}\n{'=' * 20}\n{'=' * 20}\n===👁你被视奸👁了===\n{'=' * 20}\n{'=' * 20}\n{'=' * 20}"))
    arg = session.current_arg_text.strip()
    monitor_num = 1
    arg_state = True
    if arg:
        try:
            monitor_num = int(arg)
        except TypeError:
            monitor_num = 1
            arg_state = False
    try:
        path, state = imgtools.take_screenshot(monitor_num)
    except:
        print(traceback.format_exc())
        print("无法截图")
        return await send_session_msg(session, get_message("plugins", __plugin_name__, 'error'))
    # path = "file:///" + path.split(":")[0] + ":\\" + path.split(":")[1]
    # path = f'http://server.xzadudu179.top:17980/screenshot'
    if arg_state and monitor_num != 0:
        message = get_message("plugins", __plugin_name__, 'successful', monitor_num=monitor_num)
    elif state and arg_state and monitor_num == 0:
        message = get_message("plugins", __plugin_name__, 'successful_all', monitor_num=monitor_num)
    else:
        message = get_message("plugins", __plugin_name__, 'default_monitor')
    # image_msg = f"[CQ:image,file={path}]"
    image_msg = await imgtools.image_msg(path)
    # print(image_msg)
    await send_session_msg(session, message + '\n' + image_msg)