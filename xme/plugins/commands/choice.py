from nonebot import CommandSession
from xme.xmetools.plugintools import on_command
from xme.xmetools.doctools import CommandDoc
import jieba.posseg as pseg
import random
from xme.xmetools.texttools import FormatDict, replace_formatted, chinese_proportion
from xme.xmetools.bottools import get_group_member_name, get_stranger_name
random.seed()
import re
from xme.xmetools import texttools
from character import get_message
from xme.xmetools.msgtools import send_session_msg

alias = ['选择', 'cho', '决定']
__plugin_name__ = 'choice'
__plugin_usage__ = CommandDoc(
    name=__plugin_name__,
    # desc='随机决定事情',
    desc=get_message("plugins", __plugin_name__, "desc"),
    introduction=get_message("plugins", __plugin_name__, "introduction"),
    # introduction='让 xme 帮忙决定事情吧！\nxme 会因情况的不同而返回不同的结果，10~1例如只 choice 数字会返回 0~数字的随机数，choice一个数字范围比如 -1~10 会返回 1~10 1~-10 的随机数',
    usage=f'(事情列表或是任意选择语句)',
    permissions=[],
    alias=alias
)

@on_command(__plugin_name__, aliases=alias, only_to_me=False)
async def _(session: CommandSession):
    random.seed()
    args = session.current_arg_text.strip()
    if not args:
        await send_session_msg(session, get_message("plugins", __plugin_name__, "no_args"),)
        return
    elif len(args) > 300:
        await send_session_msg(session, get_message("plugins", __plugin_name__, "args_too_long", count=len(args)),)
        return
    # split_str = " " if chinese_proportion(args) > 0 else ","
    # TODO: 分割英文
    split_str = " "
    choices = args.split(split_str)
    choice = ""
    can_choice = True
    # 只有一项选择
    if len(choices) <= 1:
        special_choices = [
            another_or_choice(choices[0], "还是"),
            another_or_choice(choices[0], "或者"),
            another_or_choice(choices[0], "或"),
            is_or_not_choice(choices[0]),
            is_or_not_split_choice(choices[0]),
            ends_can_choice(choices[0]),
            ends_is_or_not_choice(choices[0]),
            # has_or_not_choice(choices[0]),
        ]
        for c in special_choices:
            print(c)
            if c:
                # if all(x == c[0] for x in c):
                #     return await send_session_msg(session, get_message("plugins", __plugin_name__, 'no_choice'), tips=True)
                choices = c
                item = random.choice(c)
                choice, can_choice = parse_num_choice(item)
                break
    print("choice is", choice)
    if not choice:
        item = random.choice(choices)
        # choice = x if (x:=num_choice(item)) else item
        choice, can_choice = parse_num_choice(item)
        print("choice", choice, "canchoice", can_choice)
    formats = FormatDict(
        member=await get_random_group_member(session, session.event.group_id)
    )
    print(all(x == choices[0] for x in choices), can_choice, choices, has_valid_placeholders(choice, ['member']))
    if all(x == choices[0] for x in choices) and not can_choice and not has_valid_placeholders(choice, ["member"]):
            return await send_session_msg(session, get_message("plugins", __plugin_name__, 'no_choice'), tips=True)
    choice = replace_formatted(texttools.me_to_you(str(choice)), **formats)
    # try:
    #     choice = choice.format_map(formats)
    # except ValueError as ex:
    #     print("error", ex)
    #     pass
    await send_session_msg(
            session,
            get_message(
                "plugins",
                __plugin_name__,
                'choice_message',
                choice=choice,
            ),
            tips=True,
            tips_percent=20,
        )

def has_valid_placeholders(s: str, allowed: list[str]) -> bool:
    # 匹配是否有指定的字符串format
    matches = re.findall(r"{([^{}]+)}", s)
    # print(matches)
    if not matches:
        return False
    print([m in allowed for m in matches])
    return len([m for m in matches if m in allowed ]) > 0

async def get_random_group_member(session: CommandSession, group_id):
    if group_id is None:
        return random.choice([await get_stranger_name(session.event.user_id), await get_stranger_name(session.self_id)])
    return await get_group_member_name(group_id=group_id, user_id=random.choice(await session.bot.get_group_member_list(group_id=group_id))["user_id"], card=True)

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
    pn = "不"
    split_str, index = texttools.find_symmetric_around(text, "不")
    if not split_str:
        split_str, index = texttools.find_symmetric_around(text, "没")
        pn = "没"
    print(split_str)
    print(len(split_str))
    if not split_str:
        return False
    prefix = text[:index - len(split_str)]
    suffix = text[index + 1 + len(split_str):]
    print(prefix, suffix)
    splits = [prefix + split_str + suffix, prefix + pn + split_str + suffix]
    return splits

def ends_can_choice(text):
    print("text", text)
    question_strings = ("否", "吗", "嘛")
    if not texttools.remove_punctuation(text).endswith(question_strings):
        return False
    if "可以" not in text:
        return False
    prefix = text.split("可以")[0]
    split_text = "可以".join(text.split("可以")[1:])
    choices = [f'{prefix}不可以{split_text}', f'{prefix}可以{split_text}']
    choices = [texttools.remove_punctuation(texttools.replace_all(*question_strings, text=c)) for c in choices]
    print("ends choices", choices)
    return choices

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
            # if prefix.endswith("可以"):
                # prefix = prefix[:-2]
                # choices = [f"{prefix}可以{suffix}", f"{prefix}不可以{suffix}"]
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
        if end > 10000000000000000000000000000000000:
            raise ValueError("数字太大")
        if start >= end:
            raise ValueError("start数字大于等于end数字")
        result = random.randrange(start, end + 1)
        return str(result)
    try:
        if re.search(r'-?\d+~-?\d+', s):
            print("匹配", re.match(r'-?\d+~-?\d+', s))
            return re.sub(r'-?\d+~-?\d+', ra_int, s), True
        print("无匹配")
        return s, False
    except Exception as ex:
        print(ex)
        return s, False