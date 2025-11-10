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
        return default
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

def set_value(*keys: str, search_dict: dict, set_method=lambda value: value, delete=False):
    """设置字典对应键的值

    Args:
        *keys (str): 指定的键，会从左到右查找，类似于 dict[key0][key1][key2]...
        search_dict (dict): 用于搜索的字典.
        set_method (function): 设置成什么
    """
    v = search_dict.get(keys[0], None)
    if len(keys) > 1:
        if v is None:
            search_dict[keys[0]] = {}
            v = search_dict[keys[0]]
        return set_value(*keys[1:], search_dict=v, set_method=set_method, delete=delete)
    if delete:
        del  search_dict[keys[0]]
        return
    search_dict[keys[0]] = set_method(v)