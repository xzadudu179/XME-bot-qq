def jaccard_similarity(str1: str, str2: str) -> float:
    """计算字符串集合的交集与并集的比例相似度

    Args:
        str1 (str): 第一个字符串
        str2 (str): 第二个字符串

    Returns:
        float: 相似度(0~1)
    """
    set1 = set(str1)
    set2 = set(str2)
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    return intersection / union