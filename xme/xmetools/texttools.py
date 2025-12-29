import re
from pypinyin import lazy_pinyin
import itertools
import base64
from nonebot import MessageSegment, Message
import string
import hashlib
from difflib import SequenceMatcher
import enchant

d = enchant.Dict("en_US")
def is_valid_english_word(word: str) -> bool:
    return d.check(word)

async def get_image_files_from_message(bot, msg):
    images = [(await bot.get_image(file=image))["file"] for image in re.findall(r"\[CQ:image,(?![^\]]*emoji_id=)[^\]]*?file=([^,]+),", msg)]
    return images

def only_positional_fields(s: str) -> str:
    return re.sub(r"{(\d+)}", r"{{\1}}", s)

def replace_formatted(s: str, **formats):
    result = s
    for k, v in formats.items():
        result = result.replace("{" + k + "}", str(v))
    return result


class FormatDict(dict):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __missing__(self, key):
        return '{' + key + '}'

class SQLInjectionDetector:
    """
    一个简化版的 SQL 注入检测器
    """
    # 常见的 SQL 注入关键字 / 操作符
    SQL_PATTERNS = [
        r"(?i)['|\"]\s+\bunion\b\s+\bselect\b",   # UNION SELECT
        r"(?i)['|\"]\s+\bor\b\s+1\s*=\s*1",       # OR 1=1
        r"(?i)['|\"]\s+\bor\b\s+'1'\s*=\s*'1",       # OR 1=1
        r"(?i)['|\"]\s+\band\b\s+1\s*=\s*1",      # AND 1=1
        r"(?i)['|\"]\s+\band\b\s+'1'\s*=\s*'1",      # AND 1=1
        r"(?i)['|\"]\s+\bdrop\b\s+\btable\b",     # DROP TABLE
        r"(?i)['|\"]\s+\binsert\b\s+\binto\b",    # INSERT INTO
        r"(?i)['|\"]\s+\bupdate\b\s+\b.*\bset\b", # UPDATE ... SET
        r"(?i)['|\"]\s+\bdelete\b\s+\bfrom\b",    # DELETE FROM
        r"(?i)['|\"]\s+\bsleep\s*\(",             # SLEEP()
        r"(?i)['|\"]\s+@@",                       # @@version, @@user 等
        r"(?i)['|\"]\s+\bxp_cmdshell\b",          # SQL Server 特有
        r"(?i)['|\"]\s+\bexec\b\s+\b",            # EXEC 调用
    ]

    def is_suspect(self, value: str) -> bool:
        """检测单个输入值是否疑似 SQL 注入"""
        if not isinstance(value, str):
            return False

        for pattern in self.SQL_PATTERNS:
            if re.search(pattern, value):
                return True
        return False

    def scan_params(self, param_input: str) -> dict:
        """
        检查参数字典 {param: value} 是否包含注入
        """
        status = False
        if self.is_suspect(param_input):
            status = True

        return status

def is_danger_sql(text):
    detector = SQLInjectionDetector()
    return detector.scan_params(text)

def difflib_similar(a: str, b: str, get_pinyin=True, ignore_case=False) -> float:
    """使用 difflib 判断字符串相似度

    Args:
        a (str): 字符串 a
        b (str): 字符串 b

    Returns:
        float: 相似度比例
    """
    if get_pinyin:
        a = ''.join(lazy_pinyin(a))
        b = ''.join(lazy_pinyin(b))
    if ignore_case:
        a = a.lower()
        b = b.lower()
    return SequenceMatcher(None, a, b).ratio()

def fuzzy_search(text, contents, ratio=0.65):
    """模糊搜索一个内容

    Args:
        text (str): 搜索文本
        contents (list[str]): 文本列表

    Returns:
        str: 搜索到的文本（来自文本列表）
    """
    return x[-1][0] if (x:=most_similarity_str_diff(text, [c for c in contents], ratio)) else None

def find_symmetric_around(s: str, center: str) -> tuple[str, str]:
    if center not in s:
        return "", 0
    idx = s.find(center)
    max_len = min(idx, len(s) - idx - 1)
    # print(max_len)
    result_list = []
    for l in range(max_len, 0, -1):
        left = s[idx - l:idx]
        right = s[idx + 1:idx + 1 + l]
        if left == right:
            result_list.append(left)
    # print(result_list)
    if result_list:
        result = max(result_list, key=len)
        return result, idx
    re_detect, new_index = find_symmetric_around(s[idx + 1:], center)
    # print(re_detect)
    if not re_detect:
        return "", 0
    return re_detect, new_index + idx + 1

def base64_encode(text):
    """将文本使用 base64 进行编码

    Args:
        text (str): 文本内容

    Returns:
        str: 编码文本
    """
    text_bytes = text.encode('utf-8')
    base64_encoded = base64.b64encode(text_bytes)
    base64_string = base64_encoded.decode('utf-8')
    return base64_string

def contains_blacklisted(expr: str) -> bool:
    blacklist = ['__', 'import', 'eval', 'exec', 'os', 'system', 'subprocess', 'open', 'attr']
    blacklist_whitelist = ['cos']
    return any(bad in expr for bad in blacklist) and not any(c in expr for c in blacklist_whitelist)

def limit_str_len(s: str, max_len: int):
    """限制字符串长度

    Args:
        s (str): 字符串
        max_len (int): 最大长度

    Returns:
        str: 限制后的字符串
    """
    if len(s) > max_len:
        s = s[:max_len] + "..."
    return s

def valid_var_name(name: str):
    """验证变量名是否符合规范

    Args:
        name (str): 变量名

    Returns:
        bool: 结果
    """
    pattern = r"^[a-zA-Z_][a-zA-Z0-9_]*$"
    return bool(re.match(pattern, name))

def remove_prefix(text: str, prefix: tuple | str) -> str:
    """判断字符串前缀并去除前缀

    Args:
        text (str): 目标字符串
        prefix (tuple | str): 前缀字符串

    Returns:
        str: 结果
    """
    if isinstance(prefix, str):
        prefix = (prefix,)
    prefix = tuple(sorted(prefix, key=len, reverse=True))
    for p in prefix:
        if text.startswith(p):
            return text[len(p):]
    return text

def remove_suffix(text: str, suffix: tuple | str) -> str:
    """判断字符串后缀并去除前缀

    Args:
        text (str): 目标字符串
        prefix (tuple | str): 后缀字符串

    Returns:
        str: 结果
    """
    if isinstance(suffix, str):
        suffix = (suffix,)
    suffix = tuple(sorted(suffix, key=len, reverse=True))
    for p in suffix:
        if text.endswith(p):
            return text[:-len(p)]
    return text

def is_chinese(c) -> bool:
    pattern = r'[^\x00-\xff]'
    if re.match(pattern=pattern, string=c):
        return True
    return False

def get_msg_len(texts: Message) -> int:
    """获取用于 qq 消息的长度，字母算 1， 中文算 2，会计算空行占用

    Args:
        text (str): qq 消息文本

    Returns:
        int: 消息总长度
    """
    def get_text_len(text):
        format_text = text.strip().replace("\r", "\n")
        total_line_count = 0
        texts = text.split("\n")
        if len(texts) <= 1:
            return calc_len(format_text)
        for t in texts[:-1]:
            print(t)
            total_line_count += 36 - calc_len(t) % 36
        return total_line_count + calc_len(format_text.replace("\n", ""))
    total = 0
    for t in texts.extract_plain_text():
        total += get_text_len(t)
    return total

# 中文占比
def chinese_proportion(input_str) -> float:
    tfs = []
    for c in input_str:
        tfs.append(is_chinese(c))

    true_count = sum(tfs)
    total_count = len(tfs)
    if total_count < 1:
        return 0
    true_ratio = true_count / total_count
    return true_ratio

def calc_spacing(texts: list[str], target: str, padding: int=0) -> int:
    return calc_len(max(texts, key=lambda x: calc_len(x))) - calc_len(target) + padding

def calc_len(text):
    length = 0
    for char in text:
        # 如果是中文字符，加2
        if is_chinese(char):
            length += 2
        else:
            length += 1
    return length


def get_at_id(at_str) -> int:
    return int(at_str.split("[CQ:at,qq=")[-1].split("]")[0].split(",")[0])

def get_image_str(raw_message):
    """仅保留并获取 qq 原消息中的图片

    Args:
        raw_message (str): 原本的消息

    Returns:
        tuple[str, tuple]: 返回待格式化消息和图片元组
    """
    images = [item.split(",")[0] for item in raw_message.split('[CQ:image,file=')[1:]]
    raw_message = re.sub(r'\[CQ:image,.*?\]', '{}', raw_message)
    raw_message = re.sub(r'\[CQ:.*?\]', '', raw_message)
    return (raw_message, tuple(images))

def to_spec_string(s, replace_to_horzline=False):
    """返回只包含中文 英文 数字 下划线 横线的字符串

    Args:
        s (str): 需要检测的字符串
        replace_to_horzline (bool, optional): 是否将非法字符替换成横线 否则是下划线. Defaults to False.

    Returns:
        str: 合法字符串
    """
    # 使用正则表达式替换不符合的字符（保留换行符）
    return re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9_\n-]', '_' if not replace_to_horzline else '-', s).replace("\n", "")
# print(chinese_proportion("你这个 situation 我觉得很 weird"))

def hash_text(text):
    """使用 SHA-256 将字符串转为 16 进制 HASH

    Args:
        text (str): 输入的字符串

    Returns:
        str: 输出的字符串
    """
    # 使用 SHA-256 哈希算法
    hash_object = hashlib.sha256(text.encode('utf-8'))
    # 将哈希值转换为十六进制字符串
    hex_result = hash_object.hexdigest()
    return hex_result.upper()


def hash_byte(byte):
    """使用 SHA-256 将字节码转为 16 进制 HASH

    Args:
        byte (Any): 输入

    Returns:
        str: 输出的字符串
    """
    # 使用 SHA-256 哈希算法
    hash_object = hashlib.sha256(byte)
    # 将哈希值转换为十六进制字符串
    hex_result = hash_object.hexdigest()
    return hex_result.upper()

def fullwidth_to_halfwidth(text):
    """将字符串中的全角字符替换为半角字符。（注意：中文标点【】之类的不算可替换的全角字符）

    Args:
        text (str): 输入字符串

    Returns:
        str: 返回的内容
    """
    result = []
    for char in text:
        # 判断是否是全角字符（全角字符的 Unicode 编码范围：65281~65374）
        code_point = ord(char)
        if 65281 <= code_point <= 65374:
            # 将全角字符转换为半角字符
            result.append(chr(code_point - 0xFEE0))
        elif code_point == 12288:
            # 处理全角空格（全角空格的 Unicode 编码是 12288，对应半角空格是 32）
            result.append(chr(32))
        else:
            # 非全角字符保持不变
            result.append(char)
    return ''.join(result)

def replace_chinese_punctuation(text: str) -> str:
    """替换中文标点到英文

    Args:
        text (str): 需要替换的字符串

    Returns:
        str: 替换好的字符串
    """
    punctuation_map = {
        "，": ",",
        "。": ".",
        "！": "!",
        "？": "?",
        "：": ":",
        "；": ";",
        "“": "\"",
        "＃": "#",
        "”": "\"",
        "‘": "'",
        "’": "'",
        "（": "(",
        "）": ")",
        "【": "[",
        "】": "]",
        "《": "<",
        "》": ">",
        "、": ",",
        "＝": "=",
        "｜": "|",
        "～": "~",
        "—": "-",
        "…": "...",
        "＾": "^",
        "＊": "*",
    }
    for chinese_punc, english_punc in punctuation_map.items():
        text = re.sub(re.escape(chinese_punc), english_punc, text)
    return text

def me_to_you(content: str) -> str:
    content = content.replace("你", "<>WO1-<>").replace("我", "你").replace("<>WO1-<>", "我")
    content = content.replace("敌众你寡", "敌众我寡").replace("我追你赶", "你追我赶").replace("彼竭你盈", "彼竭我盈").replace("自你意识", "自我意识").replace("自我意识到", "自你意识到")
    return content

def doubt_to_excl(content):
    content = replace_chinese_punctuation(content)
    return content.replace("嘛?", "!").replace("吗", "").replace("?", "!")

def merge_positive_negative(content):
    result_is = content.replace("不不", "是")
    result_is = re.sub(r"(.*?)是是", lambda match: prefix + "是是" if (prefix:=match.group(1)) else prefix + "是", result_is)
    return result_is

def html_text(text):
    return text.replace("<", "&lt;").replace(">", "&gt;").replace(" ", "&nbsp;").replace('"', "&quot;")

def try_split_left_right_equals(text, splits, total_split_return=False):
    """以 ABA 的格式分隔字符

    Args:
        text (str): 输入的文本
        splits (str): 分割字符B
        total_split_return (bool): 是否返回完整的被分割字符

    Returns:
        tuple(list, str): 分割完的字符，第一项为前后缀，第二项为被分割的字符
    """
    result = []
    split_return = []
    for s in splits:
        pattern = rf"(.*?(.){s}\2)(.*)"
        pt2 = rf".*((.){s}\2)"
        match_split = re.match(pt2, text)
        match = re.match(pattern, text)
        if match is None: continue
        prefix = match.groups()[0]
        split_return = s
        if total_split_return:
            split_return = match_split.groups()[0]
        result = list((prefix.split(match_split.groups()[0])[0], match.groups()[-1]))
        break
    return (result, split_return)

def replace_all(*replace_strings: tuple[str, str] | tuple[str], text):
    result = text
    try:
        for o, n in replace_strings:
            result = result.replace(o, n)
    except ValueError:
        for o in replace_strings:
            result = result.replace(o, "")
    return result

def remove_punctuation(text: str) -> str:
    """移除标点

    Args:
        text (str): 输入的文本

    Returns:
        str: 移除标点的文本
    """
    text = replace_chinese_punctuation(text)
    return text.translate(str.maketrans('', '', string.punctuation))


def jaccard_similarity(str1: str, str2: str, get_pinyin=True, ignore_case=False) -> float:
    """计算字符串集合的交集与并集的比例相似度（中文会被转换为拼音）

    Args:
        str1 (str): 第一个字符串
        str2 (str): 第二个字符串

    Returns:
        float: 相似度(0~1)
    """
    if get_pinyin:
        str1 = ''.join(lazy_pinyin(str1))
        str2 = ''.join(lazy_pinyin(str2))
    # str1 = ''.join(lazy_pinyin(str1))
    # str2 = ''.join(lazy_pinyin(str2))
    set1 = set(str1)
    set2 = set(str2)
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    return intersection / union

def text_combinations(text: tuple[str] | str, **kwargs: tuple[str] | str):
    """字符串排列组合

    Args:
        text (tuple[str] | str): 主要字符串 （需要可被 format）
        **kwargs (tuple[str] | str): format 字符串

    Returns:
        list: 获得的排列组合
    """
    result_strs = []
    items = []
    for k, v in kwargs.items():
        if isinstance(v, str):
            v = v,
        items.append((k, v))
    results = list(itertools.product(*tuple([i[1] for i in items])))
    for result in results:
        result_dict = {}
        for i in range(len(kwargs)):
           result_dict[items[i][0]] = result[i]
        if isinstance(text, str):
            result_strs.append(text.format(**result_dict))
            continue
        for t in text:
            result_strs.append(t.format(**result_dict))
    return result_strs

def most_similarity_str(input_str: str, str_list: list[str], threshold: float=0) -> list[tuple[str, int]]:
    similarities = []
    for s in str_list:
        similarities.append((s, jaccard_similarity(input_str, s)))
    return [x for x in sorted(similarities,key=lambda x: x[1]) if x[1] > threshold]

def most_similarity_str_diff(input_str: str, str_list: list[str], threshold: float=0) -> list[tuple[str, int]]:
    similarities = []
    for s in str_list:
        similarities.append((s, difflib_similar(input_str, s, ignore_case=True)))
    return [x for x in sorted(similarities,key=lambda x: x[1]) if x[1] > threshold]


# def is_question_product(question, question_of):
#     # 加载中文模型
#     nlp = spacy.load("zh_core_web_sm")

#     # 处理句子
#     doc = nlp(question)

#     # 识别实体
#     for ent in doc.ents:
#         if ent.text == question_of:
#             return True
#     return False
