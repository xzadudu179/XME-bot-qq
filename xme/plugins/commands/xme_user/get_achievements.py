from xme.plugins.commands.xme_user import __plugin_name__
from nonebot import on_command, CommandSession
from xme.xmetools.msgtools import send_session_msg
from xme.xmetools.bottools import permission
from xme.xmetools.typetools import try_parse
from xme.xmetools.texttools import replace_chinese_punctuation, fuzzy_search
from xme.xmetools.cmdtools import send_cmd, get_cmd_by_alias
from .classes import user as u
import math
from xme.plugins.commands.xme_user.classes.user import User
from character import get_message
from xme.plugins.commands.xme_user.classes.achievements import get_achievements, get_achievement_details


alias = ['查看成就', '成就', 'achi']
cmd_name = 'achievement'
usage = {
    "name": cmd_name,
    "desc": get_message("plugins", __plugin_name__, cmd_name, 'desc'),
    "introduction": get_message("plugins", __plugin_name__, cmd_name, 'introduction', ),
    "usage": f'<成就名>',
    "permissions": [],
    "alias": alias
}

def get_achievement_items(achievements: list):
    total_achievements: dict = get_achievements()
    messages = []
    for i, (k, achi) in enumerate(total_achievements.items()):
        achieved = False
        suffix = ""
        if k in achievements:
            suffix = " (已完成)"
            achieved = True
        if achi["hidden"] and not achieved:
            continue
        # messages.append(get_message("plugins", __plugin_name__, cmd_name, "achievement_item", achi_name=achi_dict["name"], achi_desc=achi_dict["desc"], award=achi_dict["award"]))
        messages.append(f'{i + 1}. {k}{suffix}')
    if messages == []:
        messages = [get_message("plugins", __plugin_name__, cmd_name, "nothing_here")]
    return messages

def get_details(text: str, user: User):
    achievements = get_achievements()
    search = fuzzy_search(text, list(achievements.keys()), ratio=0.5)
    print(search)
    if search is None:
        return None
    # print(achievement_messages, index)
    # achievement_name = ".".join(a.split(".")[1:]).split(" (已完成)")[0].strip()
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
        achieved_from = achievement["from"]
    return get_achievement_details(achievement_name=search, achieved=achieved, achieved_time=achieved_time, achieved_from=achieved_from)

@on_command(cmd_name, aliases=alias, only_to_me=False, permission=lambda _: True)
@u.using_user(save_data=False)
async def _(session: CommandSession, user: User):
    arg = session.current_arg_text.strip()
    print("arg", arg)
    page = 1
    achievements: list = [a["name"] for a in user.achievements]
    achi_items_total = get_achievement_items(achievements)
    if arg:
        # if try_parse(arg, int) is None:
            # return await send_session_msg(session, get_message("plugins", __plugin_name__, cmd_name, "error_arg"), tips=True)
        details = get_details(text=arg, user=user)
        if details is None:
            return await send_session_msg(session, get_message("plugins", __plugin_name__, cmd_name, "no_arg", text=arg), tips=True)
        return await send_session_msg(session, details)
    while True:
        PAGE_ITEM_COUNT = 10
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
        reply = (await session.aget()).strip()
        reply = replace_chinese_punctuation(reply)
        if get_cmd_by_alias(reply) != False:
            print("执行指令")
            await send_cmd(reply, session)
            return False
        elif reply in ["<", ">"]:
            if reply == "<":
                page -= 1
            else:
                page += 1
            continue
        return True