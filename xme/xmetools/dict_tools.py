

def get_value(*keys, search_dict: dict, default=None):
    """得到字典键对应的值

    Args:
        search_dict (dict): 搜索的字典
        default (any): 默认返回值

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
