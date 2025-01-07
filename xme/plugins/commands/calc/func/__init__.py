from . import dich
from . import if_func

builtins = {
    "pi": "圆周率",
    "E": "自然常数",
    "I": "虚数单位",
    "sin(x)": "正弦",
    "cos(x)": "余弦",
    "tan(x)": "正切",
    "sec(x)": "正割",
    "csc(x)": "余割",
    "cot(x)": "余切",
    "asin(x)": "反正弦",
    "acos(x)": "反余弦",
    "atan(x)": "反正切",
    "exp(x)": "指数函数",
    "log(x)": "自然对数",
    "log(x, base)": "可指定底数的对数",
    "sinh(x)": "双曲正弦",
    "cosh(x)": "双曲余弦",
    "tanh(x)": "双曲正切",
    "asinh(x)": "反双曲正弦",
    "acosh(x)": "反双曲余弦",
    "atanh(x)": "反双曲正切",
    "sqrt(x)": "平方根",
    "abs(x)": "绝对值",
    "sign(x)": "符号函数",
    "gamma(x)": "gamma 函数",
    "factorial(x)": "阶乘",
    "floor(x)": "向下取整",
    "ceil(x)": "向上取整",
    "factor(x)": "因式分解",
    "expand(x)": "展开多项式",
    "simplify(x)": "简化表达式",
    "diracdelta(x)": "delta 函数",
    "Heaviside(x)": "单位阶跃函数",
    "integrate(x)": "符号积分",
    "diff(x)": "符号微分",
}

funcs = {
    dich.func_name: dich.func_info,
    if_func.func_name: if_func.func_info
}