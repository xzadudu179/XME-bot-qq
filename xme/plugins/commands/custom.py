from nonebot import on_command, CommandSession
from xme.xmetools.msgtools import send_session_msg
from xme.xmetools.doctools import CommandDoc
from xme.xmetools.typetools import try_parse
from xme.xmetools.dicttools import set_value, get_value
from xme.plugins.commands.xme_user.classes.user import User, using_user
from character import get_message

__plugin_name__ = "custom"
alias = ['自定义', '样式', 'cus']
__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    usage=f'<支持的功能>',
    permissions=["无"],
    alias=alias
))

def get_custom_items(*keys, user: User, none_message = "什么都没有呢...使用 \"/shop\" 去商店看看吧"):
    items_value: list | None = get_value(*keys, search_dict=user.plugin_datas)
    if items_value is None:
        return (False, none_message)
    results = []
    for i, item in enumerate(items_value):
        results.append(f"{i + 1}. {item}")
    return (True, "\n".join(results))

@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda _: True)
@using_user(save_data=True)
async def _(session: CommandSession, user: User):
    arg = session.current_arg_text.strip()
    if not arg:
        # 发送帮助之类的
        await send_session_msg(session, __plugin_usage__)
        return False

    keys = ()
    if arg.lower() == "bottle":
        items_name = "漂流瓶卡片"
        from xme.plugins.commands.drift_bottle import __plugin_name__ as bottle_plugin_name
        name = "custom_cards"
        keys = (bottle_plugin_name, name)
        # user.plugin_datas[__plugin_name__].get(bottle_plugin_name)
    else:
        await send_session_msg(session, __plugin_usage__)
        return False
    stats, result = get_custom_items(*keys, user=user)
    suffix = "" if not stats else get_message("plugins", __plugin_name__, 'custom_info_suffix')
    message = get_message("plugins", __plugin_name__, 'custom_info', items_name=items_name, items=result, suffix=suffix)
    if not stats:
        await send_session_msg(session, message, tips=True)
        return False
    # 选择项
    reply: int | None = try_parse(await session.aget(prompt=message), int)
    if reply is None:
        return False
    items: list = get_value(*keys, search_dict=user.plugin_datas, default=[])
    item_result = ""
    try:
        item_result = items[reply - 1]
    except IndexError:
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'index_not_found', index=reply), tips=True)
    set_value(__plugin_name__, *keys, search_dict=user.plugin_datas, set_method=lambda v: item_result)
    await send_session_msg(session, get_message("plugins", __plugin_name__, 'set_success', items_name=items_name, item_result=item_result), tips=True)
    return True