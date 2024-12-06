import random


def create_pairs(lst: list[int]) -> list[tuple[int, int]]:
    # print(f"seed: {random.seed}")
    random.shuffle(lst)  # 打乱顺序
    pairs = []

    # 每次取出两个作为一组，如果剩下一个，则单独作为一组
    for i in range(0, len(lst) - 1, 2):
        pairs.append((lst[i], lst[i + 1]))

    if len(lst) % 2 != 0:
        pairs.append((lst[-1],))  # 如果剩下一个，单独作为一组
    return pairs


def find_pair(pairs, item):
    for pair in pairs:
        # print(pair)
        if item in pair:
            # print(item)
            # 如果找到，返回配对的那个值，如果没有配对则返回""
            try:
                return pair[1] if pair[0] == item else pair[0]
            except KeyError:  # TODO 241206 稳定性不详，需要测试！
                return ""
    return ""
