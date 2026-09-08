import re

from sympy import Integer, sympify

from xme.xmetools.debugtools import debug_msg
from xme.xmetools.texttools import fullwidth_to_halfwidth, replace_chinese_punctuation, valid_var_name

from . import func
from .syntax_guard import assert_safe_syntax


def get_func(input_str):
    pattern = r"[a-zA-Z_][a-zA-Z0-9_]*\(.*"
    matches = re.findall(pattern, input_str)
    return matches

def find_funcs(expression):
    results = []
    while expression:
        result = extract_function(expression)
        if not result:
            return results
        expression = expression.replace(result, '')
        results.append(result)
    return results

def extract_function(expression):
    result = ''
    func_get = get_func(expression)
    debug_msg(f"func get: {func_get}")
    if len(func_get) < 1:
        return result
    expression = func_get[0]
    start = False
    level = 0
    for i, char in enumerate(expression):
        if char == "(":
            level += 1
            start = True
        elif char == ")":
            level -= 1
        if start and level == 0:
            result = expression[:i + 1]
            return result
    return result

def check_integer_size(expr, max_digits=1000):
    """检查 sympy 表达式中整数字面量的位数，超限抛 ValueError。

    Args:
        expr (sympy 表达式): 待检查的未求值表达式
        max_digits (int, optional): 允许的最大位数. Defaults to 1000
    """
    for atom in expr.atoms(Integer):
        if len(str(atom)) > max_digits:
            raise ValueError(f"{expr} 算式整数过大")

def _safe_sympify(expr):
    """calc 唯一的 sympify 入口：字符串先过 AST 白名单，再以 evaluate=False 解析。

    Args:
        expr (str | sympy 表达式): 待解析的表达式（变量值可能已是 sympy 对象）

    Returns:
        sympy 表达式: 未求值的 sympy 对象
    """
    if isinstance(expr, str):
        assert_safe_syntax(expr)
    return sympify(expr, evaluate=False)

def _checked_draw_expr(expr):
    """对绘图表达式做 AST 白名单校验（绘图侧 sympify 为 evaluate=True，须前置拦截）。

    Args:
        expr (str): 绘图表达式

    Returns:
        str: 原表达式
    """
    if expr:
        assert_safe_syntax(expr)
    return expr

def parse_polynomial(formula):
    """处理多项式

    Args:
        formula (str): 算式字符串

    Returns:
        tuple[str, Any, int]: (归一化算式, sympy 结果或绘图表达式列表, 绘图模式 0/1/2)
    """
    debug_msg("parsing")
    formula = fullwidth_to_halfwidth(replace_chinese_punctuation(formula)).strip()
    formula = formula.replace("×", '*').replace("÷", "/").replace("^", "**").replace(";", "\r").replace("\n", '\r')
    original_formula = formula
    all_vars = get_vars(formula)
    result_formulas = [f.strip() for f in formula.split("\r")]
    need_to_draw = False
    draws = []
    draws_3d = []
    for f in result_formulas:
        if f.startswith("::"):
            # 绘制 3D 图像
            draws_3d.append(_checked_draw_expr(parse_func(f[2:])))
            need_to_draw = True
        elif f.startswith(":"):
            draws.append(_checked_draw_expr(parse_func(f[1:])))
            need_to_draw = True
    if len(draws) != 0 and len(draws_3d) != 0:
        raise ValueError("不能同时绘制 3D 图像和 2D 图像")
    if need_to_draw:
        if len(draws) > 0:
            return original_formula.replace(" ", ''), draws, 1
        elif len(draws_3d) > 0:
            return original_formula.replace(" ", ''), draws_3d, 2

    result_formula = parse_func(result_formulas[-1])
    debug_msg(result_formulas, result_formula)
    if not result_formula:
        result_formula = "0"
    try:
        result = _safe_sympify(result_formula).subs({k: _safe_sympify(v) for k, v in all_vars.items()})
    except Exception as ex:
        if len(all_vars.items()) < 1:
            result = _safe_sympify(result_formula)
        else:
            raise ex

    return original_formula.replace(" ", ''), result, 0

def get_vars(formula: str, all_vars: dict | None = None) -> dict:
    """扫描算式中的 "变量=值" 行并递归求值，返回变量字典。"""
    if not all_vars:
        all_vars = {}
    for line in formula.split("\r"):
        var_info = is_var_line(formula, line)
        if not var_info:
            continue
        name, value = var_info
        value = parse_polynomial(value)[1]
        all_vars[name] = value

    return all_vars

def is_var_line(formula, line: str) -> bool | tuple:
    """判断一行是否为 "变量=值" 定义，是则返回 (变量名, 值)，否则返回 False。"""
    if "=" not in line or line.startswith(":"):
        return False
    name = line.split("=")[0].strip()
    value = "=".join(line.split("=")[1:]).strip()
    # 排除 == >= <=
    if value.startswith("=") or name.endswith((">", "<")):
        return False
    func_names = [func.split("(")[0] for func in get_func(formula)]
    if not valid_var_name(name):
        raise ValueError("变量名不符合规范（只由数字，字母，下划线组成且不能是数字开头）")
    if name in func_names:
        raise ValueError("变量名不能和函数重名")
    return (name, value)

def parse_func(formula):
    """处理自定函数：把算式中的自定函数调用求值并替换为结果字符串。

    Args:
        formula (str): 函数字符串

    Returns:
        str: 替换后的函数结果
    """
    funcs = find_funcs(formula)
    debug_msg(f"funcs: {funcs}")
    for f in funcs:
        func_name = f.split("(")[0]
        debug_msg(f"func name: {func_name}")
        if func_name not in func.funcs.keys():
            continue
        func_body = '('.join(f.split("(")[1:])[:-1]
        debug_msg(f"func body: {func_body}")
        args = []
        for arg in func_body.split(","):
            # 取结果位 [1]（[-1] 是绘图模式标志，历史上导致自定函数参数恒为 0）
            args.append(parse_polynomial(arg.strip())[1])
        debug_msg(f"args: {args}")
        result = func.funcs[func_name]['func'](*args)
        debug_msg(f"func \"{f}\" result: {result}")
        formula = formula.replace(f, str(result))
    return formula
