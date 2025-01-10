from anyio import sleep
# from itsdangerous import base64_encode
import nonebot
import random
from xme.xmetools.command_tools import send_session_msg
from nonebot import on_command, CommandSession
from xme.xmetools.time_tools import curr_days
# from xme.plugins.commands.jrrp.luck_algorithm import get_luck
from xme.xmetools import random_tools
from xme.xmetools.doc_tools import CommandDoc
from character import get_message

alias = ["今日人品" , "luck"]
__plugin_name__ = 'jrrp'

__plugin_usage__= str(CommandDoc(
    name=__plugin_name__,
    desc=get_message(__plugin_name__, 'desc'),
    # desc='今日人品',
    introduction=get_message(__plugin_name__, 'introduction'),
    # introduction='查看当前 qq 号今日的人品或群友人品排名~\n参数填写整数，正数为人品最高排名，负数为最低。填写 avg 为群员平均值',
    usage=f'jrrp <参数>',
    permissions=[],
    alias=alias
))



@on_command(__plugin_name__, aliases=alias, only_to_me=False)
async def jrrp(session: CommandSession):
    args = session.current_arg_text.strip()
    # print()
    qq = session.event.user_id
    max_rank_length = 15
    if args:
        members = await jrrp_rank(session)
        if args == 'avg':
            avg = int(sum([member['jrrp'] for member in members]) / len(members))
            await send_session_msg(session,
                get_message(
                    __plugin_name__, 'avg_message', avg=avg,
                    reaction=
                    get_message(__plugin_name__, 'reaction>60') if
                    avg > 60 else
                    get_message(__plugin_name__, 'reaction>20') if
                    avg > 20 else
                    get_message(__plugin_name__, 'reaction<=20')
                )
            )
            # await send_msg(session, f"今日群员人品的平均值是 {avg} {'owo' if avg > 60 else 'ovo' if avg > 20 else 'uwu'}")
            return
        try:
            count = int(args)
        except:
            await send_session_msg(session, get_message(__plugin_name__, 'rank_error'))
            # await send_msg(session, f"成员数量需要是整数哦ovo")
            return
        if abs(count) > max_rank_length:
            await send_session_msg(session, get_message(__plugin_name__, 'rank_too_long', max=max_rank_length))
            # await send_msg(session, f"指定的成员数量太多了哦uwu，范围是 -15 ~ 15")
            return
        elif count == 0:
            count = 5
            # return
        message = get_message(
            __plugin_name__,
            'rank_message',
            high_or_low='高' if count > 0 else '低',
            count=abs(count),
            reaction=get_message(__plugin_name__, 'reaction>60') if
            count > 0 else
            get_message(__plugin_name__, 'reaction<=20'))
        # message = f"这是今天人品最{'高' if count > 0 else '低'}的前 {abs(count)} 位群员排名 {get_message(__plugin_name__, 'jrrp>60') if count > 0 else get_message(__plugin_name__, 'jrrp<=20')}"
        if count > 0:
            enum_list = members[:count]
        elif count < 0:
            enum_list = members[count:]
            enum_list.reverse()
        for i, member in enumerate(enum_list):
            message += get_message(__plugin_name__, 'jrrp_row', index=i + 1, card=member['card'], id=str(member['id']), jrrp=member['jrrp'])
            # message += f"\n{i + 1}. {member['card']} ({member['id']})：今日人品值为 {member['jrrp']}"
        await send_session_msg(session, message)
        return
    # key = base64_encode("嘿嘿嘿...179....嘿嘿嘿")
    # result = get_luck(qq, key)
    # random.seed(int(str(curr_days()) + str(qq)))
    result = jrrp_gen(qq)
    content = get_message(__plugin_name__, 'jrrp_prefix')
    if result < 0:
        await send_session_msg(session, content + get_message(__plugin_name__, 'jrrp<0', result=result))
        # await send_msg(session, content + f"{result}...？ xwx")
    elif result < 10:
        await send_session_msg(session, content + get_message(__plugin_name__, 'jrrp<10', result=result))
        # await send_msg(session, content + f"....{result}？uwu")
    elif result > 100:
        await send_session_msg(session, content + get_message(__plugin_name__, 'jrrp>100', result=result))
        # await send_msg(session, content + f"{result}.0000%！All Perfect+ owo！！")
    elif result >= 90:
        await send_session_msg(session, content + get_message(__plugin_name__, 'jrrp>=90', result=result))
        # await send_msg(session, content + f"{result}！owo！")
    else:
        await send_session_msg(session, content + get_message(__plugin_name__, 'jrrp_default', result=result))
        # await send_msg(session, content + f"{result} ovo")

@random_tools.change_seed()
def jrrp_gen(id):
    random.seed(int(str(curr_days()) + str(id)))
    return random.randint(-1, 101)

async def jrrp_rank(session: CommandSession):
    members_full = await nonebot.get_bot().get_group_member_list(group_id=session.event.group_id)
    members = [{"id": member['user_id'], "card": member['card'] if member['card'] else member['nickname'], "jrrp": jrrp_gen(member['user_id'])} for member in members_full]
    members.sort(key=lambda x: (x['jrrp'], x['id']), reverse=True)
    return members
