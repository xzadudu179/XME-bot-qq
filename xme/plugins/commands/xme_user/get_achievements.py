from xme.plugins.commands.xme_user import __plugin_name__
from nonebot import CommandSession
from xme.xmetools.plugintools import on_command
from xme.xmetools.msgtools import send_session_msg, aget_session_msg
from xme.xmetools.bottools import permission
from xme.xmetools.typetools import try_parse
from xme.xmetools.bottools import get_group_name
from xme.xmetools.texttools import replace_chinese_punctuation, fuzzy_search
from xme.xmetools.cmdtools import send_cmd, get_cmd_by_alias
from .classes import user as u
import math
from xme.plugins.commands.xme_user.classes.user import User
from character import get_message
from xme.plugins.commands.xme_user.classes.achievements import get_achievements, get_achievement_details
from xme.xmetools.debugtools import debug_msg
from nonebot.log import logger

alias = ['查看成就', '成就', 'achi']
cmd_name = 'achievement'
usage = {
    "name": cmd_name,
    "desc": get_message("plugins", __plugin_name__, cmd_name, 'desc'),
    "introduction": get_message("plugins", __plugin_name__, cmd_name, 'introduction', ),
    "usage": f'<成就关键词或序号>',
    "permissions": [],
    "alias": alias
}

def get_achievement_items(achievements: list):
    total_achievements: dict = get_achievements()
    messages = []
    messages_dict = {}
    current_index = 0
    for k, achi in total_achievements.items():
        achieved = False
        suffix = ""
        if k in achievements:
            suffix = "\t(已完成)"
            achieved = True
        if achi["hidden"] and not achieved:
            continue
        # messages.append(get_message("plugins", __plugin_name__, cmd_name, "achievement_item", achi_name=achi_dict["name"], achi_desc=achi_dict["desc"], award=achi_dict["award"]))
        messages.append(f'{current_index + 1}. {k}{suffix}')
        messages_dict[current_index + 1] = k
        current_index += 1
    if messages == []:
        messages = [get_message("plugins", __plugin_name__, cmd_name, "nothing_here")]
    return messages, messages_dict

async def get_details(text: str, user: User, use_search=True):
    achievements = get_achievements()
    search = text
    if use_search:
        search = fuzzy_search(text, list(achievements.keys()), ratio=0.5)
        if search is None:
            return None
    achievement = user.get_achievement(search)
    # achievement = achievements[search]
    achieved = False
    achieved_time = ""
    achieved_from = ""
    if achievement is None and achievements[search]["hidden"] == True:
        # 处理隐藏成就，不显示
        return None
    if achievement is not None:
        achieved = bool(achievement)
        achieved_time = achievement["achieve_time"]
        achieved_from = await get_group_name(achievement["from"], "[未知群聊]")
    return get_achievement_details(achievement_name=search, achieved=achieved, achieved_time=achieved_time, achieved_from=achieved_from)

@on_command(cmd_name, aliases=alias, only_to_me=False, permission=lambda _: True)
@u.using_user(save_data=False)
async def _(session: CommandSession, user: User):
    arg = session.current_arg_text.strip()
    page = 1
    achievements: list = [a["name"] for a in user.achievements]
    achi_items_total, achi_dict = get_achievement_items(achievements)
    debug_msg("d", achi_dict)
    if arg:
        if (arg_int:=try_parse(arg, int)) is not None:
            try:
                arg = achi_dict.get(arg_int, arg)
                details = await get_details(text=arg, user=user, use_search=False)
            except ValueError:
                return await send_session_msg(session, get_message("plugins", __plugin_name__, cmd_name, "no_index", index=arg_int))
        else:
            details = await get_details(text=arg, user=user, use_search=True)
        if details is None:
            return await send_session_msg(session, get_message("plugins", __plugin_name__, cmd_name, "no_arg", text=arg), tips=True)
        return await send_session_msg(session, details)
    while True:
        PAGE_ITEM_COUNT = 15
        pages = [achi_items_total[i : i+PAGE_ITEM_COUNT] for i in range(0, len(achi_items_total), PAGE_ITEM_COUNT)]
        total_pages = len(pages)

        if page > total_pages:
            return await send_session_msg(session, get_message("plugins", __plugin_name__, cmd_name, "too_large_page", page=page, total_pages=total_pages), tips=True)
        elif page < 1:
            return await send_session_msg(session, get_message("plugins", __plugin_name__, cmd_name, "too_small_page"), tips=True)

        achievement_items = pages[page - 1]
        # message = prefix + '\n'.join(achievement_items) +
        message = get_message("plugins", __plugin_name__, cmd_name, "get_achievement", page_now=page, total_pages=total_pages, achievement_items='\n'.join(achievement_items)) + (get_message("plugins", __plugin_name__, cmd_name, "turn_page_tips") if total_pages > 1 else "")
        await send_session_msg(session, message, tips=True)
        if total_pages <= 1:
            return False
        reply = (await aget_session_msg(session, can_use_command=True)).strip()
        if reply == "CMD_END":
            return False
        reply = replace_chinese_punctuation(reply)
        if reply in ["<", ">"]:
            if reply == "<":
                page -= 1
            else:
                page += 1
            continue
        return True