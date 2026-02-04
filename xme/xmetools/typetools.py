
def try_parse(item, t, default=None):
    """尝试转换到指定类型"""
    if type(t) is not type:
        raise ValueError("t 需要为类型")
    try:
        return t(item)
    except Exception:
        return default

def use_attribute(obj, attr_name):
    # getattr 会返回 obj.attr_name 的值
    if hasattr(obj, attr_name):
        return getattr(obj, attr_name)
    else:
        raise AttributeError(f"{attr_name} not found in {obj.__class__.__name__}")
