import re

# 中文占比
def chinese_proportion(input_str) -> float:
    tfs = []
    pattern = r'[^\x00-\xff]'
    for c in input_str:
        if re.match(pattern=pattern, string=c):
            tfs.append(True)
        else:
            tfs.append(False)

    true_count = sum(tfs)
    total_count = len(tfs)
    if total_count < 1:
        return 0
    true_ratio = true_count / total_count
    return true_ratio

def characters_only_contains_ch_en_num_udline_horzline(s, replace_to_horzline=False):
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