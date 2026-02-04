from nonebot import CommandSession
from xme.xmetools.plugintools import on_command
from xme.xmetools.doctools import CommandDoc
from .apicalls import get_countdown, search
from .cards import get_countdown_cards
from xme.plugins.commands.xme_user.classes.user import User, using_user
from xme.xmetools.cmdtools import use_args
from xme.xmetools.imgtools import get_html_image
from xme.xmetools.typetools import try_parse
import random
from xme.xmetools.msgtools import send_session_msg, aget_session_msg
from xme.xmetools.msgtools import image_msg
from character import get_message
random.seed()

alias = ['兽聚汇总', '兽聚', 'fus']
__plugin_name__ = 'furfusion'
__plugin_usage__ = CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, "desc"),
    introduction=get_message("plugins", __plugin_name__, "introduction"),
    usage='<方法，不填则为兽聚倒计时>',
    permissions=["无"],
    alias=alias
)

search_state = {
    0: "正常运行中",
    1: "举办预告中",
    2: "解散/停止运行",
    3: "信息失联"
}
async def get_search_fusion_data_msg(data):
    msg = get_message(
        "plugins", __plugin_name__, "fusion_data",
        image=await image_msg(data['image'], max_size=300),
        name=data['title'],
        state=search_state.get(data['state'], "未知"),
        groups="\n  " + "\n  ".join(data["groups"]) if len(data["groups"]) > 1 else data["groups"][0],
        correlation="、".join(data["correlation"]) if data["correlation"][0] != "" else "无别名",
    )
    return msg

async def get_countdown_card(u: User):
    response = await get_countdown()
    if response["code"] != "OK":
        return get_message("plugins", __plugin_name__, "error", code=response['code'])
    html_card = get_countdown_cards(response["data"], u)
    msg = get_message("plugins", __plugin_name__, "countdown", image=(await image_msg(get_html_image(html_card, height=5000))))
    return msg

async def search_by_name(session: CommandSession, content, mode):
    response = await search(content=content, mode=mode)
    if response["code"] != "OK":
        return get_message("plugins", __plugin_name__, "error", code=response['code'])
    datas = response['data']['data']
    data = None
    if len(datas) < 1:
        return get_message("plugins", __plugin_name__, "no_search_data", keyword=content)
    if len(datas) == 1:
        data = datas[0]
    # 搜索到多个结果
    else:
        titles = "\n".join([f"{i + 1}. {d['title']}" for i, d in enumerate(datas)][:15]) + (f"\n还有 {len(datas) - 15} 个内容" if len(datas) > 15 else "")
        valid = False
        fors = 0
        await send_session_msg(session, get_message("plugins", __plugin_name__, "search_mutiple", datas=titles))
        while not valid and fors < 3:
            index = await aget_session_msg(session, can_use_command=True)
            if index == "CMD_END":
                return "CMD_END"
            index_num = try_parse(index, int)
            if index_num is None:
                await send_session_msg(session, get_message("plugins", __plugin_name__, "index_not_num"))
                continue
            if index_num - 1 < 0 or index_num - 1 >= min(len(datas), 15):
                await send_session_msg(session, get_message("plugins", __plugin_name__, "index_out_of_range"))
                continue
            valid = True

        data = datas[index_num - 1]
    return await get_search_fusion_data_msg(data)


@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda _: True)
@using_user(False)
@use_args(arg_len=2)
async def _(session: CommandSession, u: User, arg_list):
    arg = arg_list
    # 默认为 countdown
    mode = "countdown"
    match arg[0]:
        case "s":
            mode = "search"
            search = arg[1]
    if arg[0] and mode == "countdown":
        mode = "search"
        search = arg[0]
    msg = ""
    match mode:
        case "countdown":
            msg = await get_countdown_card(u)
        case "search":
            #                                              ↓TODO 更多种类搜索
            msg = await search_by_name(session, search, "name")
    if msg == "CMD_END":
        return
    await send_session_msg(session, msg, tips=True, tips_percent=30)
    return