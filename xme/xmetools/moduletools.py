import types
import sys

def get_module_funcs(key, value, name):
    print(name)
    current_module = sys.modules[name]
    module_names = [
        name for name in dir(current_module)
        if not name.startswith("__")  # 排除特殊方法或变量
    ]

    funcs = {}
    for module_name in module_names:
        module = getattr(current_module, module_name)
        # print(module, isinstance(module, types.ModuleType))
        if isinstance(module, types.ModuleType):
            funcs[getattr(module, key, None)] = getattr(module, value, None)
    # 删除 None 键值对（如果子模块缺少属性会返回 None）
    # print(funcs)
    funcs = {k: v for k, v in funcs.items() if k is not None and v is not None}
    # print(funcs)
    return funcs