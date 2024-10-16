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

# print(chinese_proportion("你这个 situation 我觉得很 weird"))