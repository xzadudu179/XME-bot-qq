from nonebot import CommandSession
from xme.xmetools.plugintools import on_command
from xme.xmetools.msgtools import send_session_msg, aget_session_msg
from xme.xmetools.doctools import CommandDoc
from xme.xmetools.cmdtools import use_args, send_cmd
from xme.xmetools.typetools import try_parse
from config import COMMAND_START
from xme.xmetools.templates import HIUN_COLORS, FONTS_STYLE
from xme.xmetools.dicttools import set_value, get_value
from xme.plugins.commands.xme_user.classes.user import User, using_user
from character import get_message
from xme.xmetools.imgtools import get_html_image, image_msg

__plugin_name__ = "custom"
alias = ['自定义', '样式', 'cus']
__plugin_usage__ = CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    usage=f'<支持的功能>',
    permissions=["无"],
    alias=alias
)

def get_custom_items_html(*keys, user: User, curr_custom: str, none_message = "什么都没有呢...使用 \"/shop\" 去商店看看吧",default_value=""):
    html_head = """
    <!DOCTYPE html>
        <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>shop</title>
                <style>
    """ + HIUN_COLORS + FONTS_STYLE + """
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                font-family: "Geist Variable", -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", "Heiti SC", "WenQuanYi Micro Hei", sans-serif;
                background: transparent;
                color: var(--text-color);
            }

            main {
                background: var(--bg-color);
                width: 1000px;
                /* min-height: 600px; */
                border-radius: 30px;
                padding: 30px;
                /* border: 4px solid var(--border-color); */
            }

            .colored {
                color: var(--color-primary);
            }

            h1 {
                text-align: center;
                font-size: 2em;
                margin: 0;
                font-weight: normal;
            }

            h2 {
                font-weight: normal;
                margin: 0;
            }

            .items {
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 12px;
                border-radius: 10px;
                padding: 10px 0;
                border: 2px solid var(--border-color);
                border-top: 0;
                border-bottom: 0;
            }

            .title {
                margin-bottom: 30px;
            }

            .item {
                /* border: 1px solid red; */
                padding: 5px 0;
                margin: 0 20px;
                font-size: 1.2rem;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }

            .center {
                text-align: center;
                border-radius: 10px;
                padding: 10px 0;
                border: 2px solid var(--border-color);
                border-top: 0;
                border-bottom: 0;
            }
        </style>
    </head>
    """
    items_value: list | None = get_value(*keys, search_dict=user.plugin_datas)
    if items_value is None:
        return (False, html_head + """
    <body>
        <main class="melete">
            <div class="title">
                <h1>-- CUSTOMS --</h1>
            </div>
            <div class="center orbitron">
                <p>什么都没有呢...</p>
            </div>
            </main>
        </body>
    </html>
    """)
    results = []
    index = 0
    if default_value:
        v = 'colored' if default_value == curr_custom else ''
        results.append(f'<div class="item"><p class="{v}"><span class="colored">{index + 1}. </span>{default_value}</p></div>')
        index += 1
    for item in items_value:
        v = 'colored' if item == curr_custom else ''
        results.append(f'<div class="item"><p class="{v}"><span class="colored">{index + 1}. </span>{item}</p></div>')
        index += 1
    html_body = """
    <body>
        <main class="melete">
            <div class="title">
                <h1>-- CUSTOMS --</h1>
            </div>
            <div class="items orbitron">
    """ + "\n".join(results) + """
                </div>
            </main>
        </body>
    </html>
    """
    return (True, html_head + html_body)

@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda _: True)
@use_args(2, arg_types=[str, int])
@using_user(save_data=True)
async def _(session: CommandSession, user: User, arg_list:list[str]):
    # arg = session.current_arg_text.strip()
    setting = arg_list[0]
    if not setting:
        # 发送帮助之类的
        await send_session_msg(session, __plugin_usage__)
        return False

    keys = ()
    default = "default"
    if setting.lower() == "bottle":
        default = "默认卡片"
        items_name = "漂流瓶卡片"
        from xme.plugins.commands.drift_bottle import __plugin_name__ as bottle_plugin_name
        name = "custom_cards"
        keys = (bottle_plugin_name, name)
        # user.plugin_datas[__plugin_name__].get(bottle_plugin_name)
    else:
        # 发送帮助
        await send_session_msg(session, __plugin_usage__)
        return False
    setting_index: int | str = arg_list[1]
    cmd_no_suffix = f"{COMMAND_START[0]}{__plugin_name__} {setting}"
    curr_custom = get_value(__plugin_name__, *keys, search_dict=user.plugin_datas, default=default)
    if setting_index != "" and not isinstance(setting_index, int):
        await send_session_msg(session, get_message("plugins", __plugin_name__, "index_error", index=setting_index, cmd_no_suffix=cmd_no_suffix), tips=True)
        return False
    elif setting_index == "":
        stats, result = get_custom_items_html(*keys, user=user, curr_custom=curr_custom, default_value=default)
        suffix = "" if not stats else get_message("plugins", __plugin_name__, 'custom_info_suffix')
        html_image = await image_msg(get_html_image(result))
        message = get_message("plugins", __plugin_name__, 'custom_info', items_name=items_name, html_image=html_image, suffix=suffix, curr_custom=curr_custom)
        if not stats:
            await send_session_msg(session, message, tips=True)
            return False
        # 选择项
        async def cmd_func(reply):
            print("执行指令")
            user.save()
            await send_cmd(reply, session)
            return None
        reply: int | str | None = try_parse(await aget_session_msg(session, message, can_use_command=True, command_func=cmd_func), int)
        if reply is None:
            return False
        setting_index = reply
    items: list = [default] + get_value(*keys, search_dict=user.plugin_datas, default=[])
    item_result = ""
    # 尝试使用索引
    try:
        if setting_index - 1 < 0:
            raise IndexError()
        item_result = items[setting_index - 1]
        if curr_custom == item_result:
            await send_session_msg(session, get_message("plugins", __plugin_name__, 'index_duplicate'), tips=True)
            return False
    except IndexError:
        await send_session_msg(session, get_message("plugins", __plugin_name__, ('index_not_found' if arg_list[1] == "" else "index_not_found_arg"), index=setting_index, cmd_no_suffix=cmd_no_suffix), tips=True)
        return False
    set_value(__plugin_name__, *keys, search_dict=user.plugin_datas, set_method=lambda v: item_result)
    await user.achieve_achievement(session, "焕然一新")
    await send_session_msg(session, get_message("plugins", __plugin_name__, 'set_success', items_name=items_name, item_result=item_result), tips=True)
    return True