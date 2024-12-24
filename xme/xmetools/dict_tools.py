from collections import defaultdict

def get_value(*keys, search_dict: dict, default=None):
    """得到字典键对应的值

    Args:
        search_dict (dict): 搜索的字典

    Returns:
        Any: 返回的值
    """
    try:
        result = search_dict[keys[0]]
    except Exception as ex:
        if default is not None:
            return default
        raise ex
    if len(keys) > 1:
        return get_value(*keys[1:], search_dict=result, default=default)
    return result

def reverse_dict(target_dict: dict, ignore_null: bool = True) -> dict:
    """反转字典，尝试将值变为键，键变为值

    Args:
        target_dict (dict): 目标字典
        ignore_null (bool): 忽略空值

    Returns:
        dict: 反转的字典
    """
    reversed_dict = defaultdict(list)
    for k, v in target_dict.items():
        if ignore_null and not v and v != False:
            continue
        reversed_dict[v].append(k)

    return dict(reversed_dict)