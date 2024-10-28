import heapq
from . import text_tools as sim

def heap_top_k(nums: list, k: int) -> list[int]:
    """使用最小堆的 top k

    Args:
        nums (list): 数字列表
        k (int): 设置前k个最大的元素数

    Returns:
        list[int]: 前k个最大的元素列表
    """
    heap = []
    for i in range(k):
        heapq.heappush(heap, nums[i])
        for i in range(k, len(nums)):
            if nums[i] <= heap[0]:
                continue
            heapq.heappop(heap)
            heapq.heappush(heap, nums[i])
    return heap

def str_list_sim(strings: list[str], target_str: str) -> dict:
    """字符串在字符串列表里与每个元素的相似度

    Args:
        strings (list[str]): 字符串列表
        target_str (str): 要比较的字符串

    Returns:
        dict: 相似度字典(字符串:相似度)
    """
    similars = {}
    for string in strings:
        similars[string] = sim.jaccard_similarity(string, target_str)
    return similars

def top_k_sim(l: list[str], target_str: str, k: int=5, min: float=0.5) -> list[str]:
    """返回字符串列表里前k个与目标字符串相似的项

    Args:
        l (list[str]): 字符串列表
        target_str (str): 目标字符串
        k (int, optional): 返回的列表最大长度. Defaults to 5.
        min (float, optional): 相似度最小值. Defaults to 0.5.

    Returns:
        list[str]: 前k个字符串
    """
    # 相似查找
    sim_topk_items = sorted(str_list_sim(l, target_str).items(), key=lambda item: item[1], reverse=True)[:k]
    sim_topk_items = [item for item in sim_topk_items if item[1] >= min]
    return sim_topk_items

def split_list(lst, chunk_size=10):
    # 使用列表切片将列表分割成 chunk_size 大小的子列表
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]