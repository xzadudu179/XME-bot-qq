from nonebot import on_command, CommandSession
from xme.xmetools.doctools import CommandDoc
import jieba.posseg as pseg
import random
import re
from xme.xmetools import texttools
from character import get_message
from xme.xmetools.msgtools import send_session_msg

alias = ['选择', 'cho', '决定']
__plugin_name__ = 'choice'
__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    # desc='随机决定事情',
    desc=get_message("plugins", __plugin_name__, "desc"),
    introduction=get_message("plugins", __plugin_name__, "introduction"),
    # introduction='让 xme 帮忙决定事情吧！\nxme 会因情况的不同而返回不同的结果，例如只 choice 数字会返回 0~数字的随机数，choice一个数字范围比如 1~10 会返回 1~10 的随机数',
    usage=f'(事情列表(空格分隔)或是任意选择语句)',
    permissions=[],
    alias=alias
))

@on_command(__plugin_name__, aliases=alias, only_to_me=False)
async def _(session: CommandSession):
    args = session.current_arg_text.strip()
    if not args:
        await send_session_msg(session, get_message("plugins", __plugin_name__, "no_args"),)
        return
    choices = args.split(" ")
    choice = ""
    # 只有一项选择
    if len(choices) <= 1:
        special_choices = [
            has_or_not_choice(choices[0]),
            is_or_not_choice(choices[0]),
            ends_is_or_not_choice(choices[0]),
            another_or_choice(choices[0], "还是"),
            another_or_choice(choices[0], "或者"),
            another_or_choice(choices[0], "或"),
            is_or_not_split_choice(choices[0])
        ]
        for c in special_choices:
            if c:
                choice = c
                break
    if not choice:
        item = random.choice(choices)
        choice = x if (x:=num_choice(item)) else item
    choice = parse_num_choice(choice)
    await send_session_msg(session, get_message("plugins", __plugin_name__, 'choice_message', choice=texttools.me_to_you(str(choice))))


def has_or_not_choice(input_str):
    # 有没有
    # *没*
    splits, split_str = texttools.try_split_left_right_equals(input_str, ["没", "不", "否"], True)
    try:
        print(splits, split_str)
        split_str = split_str.replace("否", "不")
        if len(splits) < 2: return False
        # if splits[0][-1] != splits[1][0]:
        #     return False
        choice = random.randint(0, 1)
        return texttools.merge_positive_negative(splits[0]) + ((split_str[0] + splits[1]) if choice else split_str[1:] + splits[1])
    except Exception as ex:
        print(ex)
        return False

def another_or_choice(input_str, another_text="还是"):
    # 还是
    result = []
    asks = input_str.split(another_text)
    if ''.join(asks[1:]) == '':
        return False
    temp = ''
    for i, ask in enumerate(asks):
        if ask == '':
            temp += '还是'
            if i == len(asks) - 1:
                result[-1] = result[-1] + temp
            continue
        result.append(temp + ask)
        temp = ''
    if len(result) <= 1:
        return False
    return random.choice(result).replace("?", "").replace("？", "")

def is_or_not_split_choice(text):
    splits = [text.split("不")[0], "不".join(text.split("不")[1:])]
    if splits[0] == splits[1]:
        splits[0] = "不" + splits[0]
        return random.choice(splits)
    return False

def ends_is_or_not_choice(text):
    question_strings = ("否", "吗", "嘛")
    if not texttools.remove_punctuation(text).endswith(question_strings):
        return False
    # 使用jieba进行词性标注
    words = list(pseg.cut(text))
    choice = random.randint(0, 1)
    print(words)
    # 寻找动词作为分割点
    for i, (_, flag) in enumerate(words):
        if flag == 'v':
            prefix = "".join([t for t, _ in words[:i]])
            is_or_not = "" if choice else "不"
            suffix = texttools.remove_punctuation(texttools.replace_all(*question_strings, "", text="".join([t for t, _ in words[i:]])))
            return f"{prefix}{is_or_not}{suffix}"
            # return ("".join([t for t, _ in words[:i]]), text_tools.remove_punctuation(text_tools.replace_all(*question_strings, "", text="".join([t for t, _ in words[i:]]))))

    # 如果没有找到特殊标志词，则返回
    return False

def is_or_not_choice(input_str):
    # 是否
    splits = input_str.split("是否")
    # print(splits)
    if len(splits) <= 1 or "是否".join(splits[1:]) == '':
        return False
    is_not = "是否".join(splits[1:])
    try:
        first_last = splits[0][-1]
    except:
        first_last = ""
    message = ('' if splits[0] in ['我', '你'] else splits[0]) + random.choice([is_not if first_last == "是" else texttools.merge_positive_negative(is_not), texttools.merge_positive_negative("不" + is_not)])
    return message

def num_choice(input_str, one_num=False):
    # 选择数字
    input_str = texttools.replace_chinese_punctuation(input_str)
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

def parse_num_choice(s):
    def ra_int(match):
        start, end = map(int, match.group().split("~"))
        result = random.randrange(start, end + 1)
        return str(result)
    try:
        return re.sub(r'\d+~\d+', ra_int, s)
    except:
        return s