from nonebot import on_command, CommandSession
from xme.xmetools.doctools import CommandDoc
import jieba.posseg as pseg
import random
random.seed()
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
    # introduction='让 xme 帮忙决定事情吧！\nxme 会因情况的不同而返回不同的结果，例如只 choice 数字会返回 0~数字的随机数，choice一个数字范围比如 -1~10 会返回 1~10 1~-10 的随机数',
    usage=f'(事情列表(空格分隔)或是任意选择语句)',
    permissions=[],
    alias=alias
))

@on_command(__plugin_name__, aliases=alias, only_to_me=False)
async def _(session: CommandSession):
    random.seed()
    args = session.current_arg_text.strip()
    if not args:
        await send_session_msg(session, get_message("plugins", __plugin_name__, "no_args"),)
        return
    choices = args.split(" ")
    choice = ""
    # 只有一项选择
    if len(choices) <= 1:
        special_choices = [
            another_or_choice(choices[0], "还是"),
            another_or_choice(choices[0], "或者"),
            another_or_choice(choices[0], "或"),
            is_or_not_choice(choices[0]),
            is_or_not_split_choice(choices[0]),
            ends_is_or_not_choice(choices[0]),
            # has_or_not_choice(choices[0]),
        ]
        for c in special_choices:
            print(c)
            if c:
                if all(x == c[0] for x in c):
                    return await send_session_msg(session, get_message("plugins", __plugin_name__, 'no_choice'))
                choice = random.choice(c)
                break
    print("choice is", choice)
    if not choice:
        item = random.choice(choices)
        # choice = x if (x:=num_choice(item)) else item
        choice, can_choice = parse_num_choice(item)
        if all(x == choices[0] for x in choices) and not can_choice:
            return await send_session_msg(session, get_message("plugins", __plugin_name__, 'no_choice'))
    await send_session_msg(session, get_message("plugins", __plugin_name__, 'choice_message', choice=texttools.me_to_you(str(choice))))


# def has_or_not_choice(input_str):
#     # 有没有
#     # *没*
#     splits, split_str = texttools.try_split_left_right_equals(input_str, ["没", "不", "否"], True)
#     try:
#         print(splits, split_str)
#         split_str = split_str.replace("否", "不")
#         if len(splits) < 2: return False
#         # if splits[0][-1] != splits[1][0]:
#         #     return False
#         # choice = random.randint(0, 1)
#         choices = [texttools.merge_positive_negative(splits[0]) + texttools.merge_positive_negative(split_str[0] + splits[1]), texttools.merge_positive_negative(splits[0]) + texttools.merge_positive_negative(split_str[1:] + splits[1])]
#         # return texttools.merge_positive_negative(splits[0]) + ((split_str[0] + splits[1]) if choice else split_str[1:] + splits[1])
#         return choices
#     except Exception as ex:
#         print(ex)
#         return False

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
    return [r.replace("?", "").replace("？", "") for r in result]

def is_or_not_split_choice(text):
    print("isornot")
    split_str, index = texttools.find_symmetric_around(text, "不")
    print(split_str)
    print(len(split_str))
    if not split_str:
        quit()
    prefix = text[:index - len(split_str)]
    suffix = text[index + 1 + len(split_str):]
    print(prefix, suffix)
    splits = [prefix + split_str + suffix, prefix + "不" + split_str + suffix]
    return splits

def ends_is_or_not_choice(text):
    question_strings = ("否", "吗", "嘛")
    if not texttools.remove_punctuation(text).endswith(question_strings):
        return False
    # 使用jieba进行词性标注
    words = list(pseg.cut(text))
    # choice = random.randint(0, 1)
    print(words)
    # 寻找动词作为分割点
    for i, (_, flag) in enumerate(words):
        if flag == 'v':
            prefix = "".join([t for t, _ in words[:i]])
            # is_or_not = "" if choice else "不"
            suffix = texttools.remove_punctuation(texttools.replace_all(*question_strings, "", text="".join([t for t, _ in words[i:]])))
            choices = [f"{prefix}{suffix}", f"{prefix}不{suffix}"]
            if suffix and suffix[0] == "有":
                choices[1] = f"{prefix}没{suffix}"
            if suffix and suffix[0] in ["不", "没"]:
                choices[1] = f"{prefix}{suffix[1:]}"
            return choices
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
    choices = [is_not if first_last == "是" else texttools.merge_positive_negative(is_not), texttools.merge_positive_negative("不" + is_not)]
    choices = [('' if splits[0] in ['我', '你'] else splits[0]) + c for c in choices]
    # message = ('' if splits[0] in ['我', '你'] else splits[0]) + random.choice([is_not if first_last == "是" else texttools.merge_positive_negative(is_not), texttools.merge_positive_negative("不" + is_not)])
    return choices

def parse_num_choice(s):
    s = texttools.replace_chinese_punctuation(s)
    print("numchoice " + s)
    def ra_int(match):

        start, end = map(int, match.group().replace("-", "~").split("~"))
        result = random.randrange(start, end + 1)
        return str(result)
    try:
        return re.sub(r'-?\d+~-?\d+', ra_int, s), True
    except Exception as ex:
        print(ex)
        return s, False