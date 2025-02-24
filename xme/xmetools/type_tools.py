
def try_parse(item, t, default=None):
    """尝试转换到指定类型"""
    if type(t) is not type:
        raise ValueError("t 需要为类型")
    try:
        return t(item)
    except:
        return default