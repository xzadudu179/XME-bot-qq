from nonebot import on_command, CommandSession
from xme.xmetools.msgtools import send_session_msg, aget_session_msg
from xme.xmetools.doctools import CommandDoc
from xme.xmetools.cmdtools import use_args, send_cmd
from xme.xmetools.typetools import try_parse
from config import COMMAND_START
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

def get_custom_items(*keys, user: User, none_message = "什么都没有呢...使用 \"/shop\" 去商店看看吧",default_value=""):
    items_value: list | None = get_value(*keys, search_dict=user.plugin_datas)
    if items_value is None:
        return (False, none_message)
    results = []
    index = 0
    if default_value:
        results.append(f"{index + 1}. {default_value}")
        index += 1
    for item in items_value:
        results.append(f"{index + 1}. {item}")
        index += 1
    return (True, "\n".join(results))

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
        stats, result = get_custom_items(*keys, user=user, default_value=default)
        suffix = "" if not stats else get_message("plugins", __plugin_name__, 'custom_info_suffix')

        message = get_message("plugins", __plugin_name__, 'custom_info', items_name=items_name, items=result, suffix=suffix, curr_custom=curr_custom)
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