import random
import time
random.seed(int(time.time() // 86400))

def create_pairs(lst):
    print(random.seed)
    random.shuffle(lst)  # 打乱顺序
    pairs = []

    # 每次取出两个作为一组，如果剩下一个，则单独作为一组
    for i in range(0, len(lst) - 1, 2):
        pairs.append((lst[i], lst[i+1]))

    if len(lst) % 2 != 0:
        pairs.append((lst[-1],))  # 如果剩下一个，单独作为一组

    return pairs

def find_pair(pairs, item):
    for pair in pairs:
        if item in pair:
            # 如果找到，返回配对的那个值，如果没有配对则返回 0
            try:
                return pair[1] if pair[0] == item else pair[0]
            except:
                return 0
    return 0

# 示例
lst1 = [1, 2, 3, 4, 5, 6]
lst2 = [1, 2, 3, 4, 5]

pairs1 = create_pairs(lst1)
pairs2 = create_pairs(lst2)

print(f"随机配对的结果1: {pairs1}")
print(f"1 的配对值是: {find_pair(pairs1, 1)}")
print(f"6 的配对值是: {find_pair(pairs1, 6)}")
print(f"5 的配对值是: {find_pair(pairs1, 5)}")

print(f"随机配对的结果2: {pairs2}")
print(f"1 的配对值是: {find_pair(pairs2, 1)}")
print(f"2 的配对值是: {find_pair(pairs2, 2)}")
