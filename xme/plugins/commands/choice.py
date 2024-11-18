from nonebot import on_command, CommandSession
from xme.xmetools.doc_gen import CommandDoc
import random
from xme.xmetools import text_tools
from character import get_message

alias = ['选择', 'cho', '决定']
__plugin_name__ = 'choice'
__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    # desc='随机决定事情',
    desc=get_message(__plugin_name__, "desc"),
    introduction=get_message(__plugin_name__, "introduction"),
    # introduction='让 xme 帮忙决定事情吧！\nxme 会因情况的不同而返回不同的结果，例如只 choice 数字会返回 0~数字的随机数，choice一个数字范围比如 1~10 会返回 1~10 的随机数',
    usage=f'(事情列表(空格分隔))',
    permissions=[],
    alias=alias
))

@on_command(__plugin_name__, aliases=alias, only_to_me=False)
async def _(session: CommandSession):
    args = session.current_arg_text.strip()
    if not args:
        await session.send(f"[CQ:at,qq={session.event.user_id}] " + get_message(__plugin_name__, "no_args"),)
        # await session.send(f"[CQ:at,qq={session.event.user_id}] 你还没有说我要决定的事情哦 ovo")
        return
    choices = args.split(" ")
    choice = ""
    # 只有一项选择
    if len(choices) <= 1:
        if (x:=num_choice(choices[0], True)) != False:
            choice = x
        is_or_not = is_or_not_choice(choices)
        if is_or_not:
            choice = is_or_not
    if not choice:
        item = random.choice(choices)
        choice = x if (x:=num_choice(item)) else item
    await session.send(f"[CQ:at,qq={session.event.user_id}] " + get_message(__plugin_name__, 'choice_message').format(choice=choice))

def is_or_not_choice(input_str):
    # 是否
    split = input_str.split("是否")
    if len(split) <= 1:
        return False
    message = random.choice([split[1], "不" + split[1]])
    return message

def num_choice(input_str, one_num=False):
    # 选择数字
    input_str = text_tools.replace_chinese_punctuation(input_str)
    try:
        input_num = int(input_str)
        if one_num:
            return random.randint(0, input_num)
        return False
    except:
        range_str_list = input_str.split("~")
        if len(range_str_list) < 2:
            return False
        try:
            num_range = [int(i.strip()) for i in range_str_list]
            return random.randint(min(num_range), max(num_range))
        except:
            return False
