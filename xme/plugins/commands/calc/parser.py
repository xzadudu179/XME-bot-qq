import re
from xme.xmetools.text_tools import replace_chinese_punctuation, valid_var_name, fullwidth_to_halfwidth
from . import func
from sympy import sympify, Integer

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
    print(f"func get: {func_get}")
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

def parse_polynomial(formula):
    """处理多项式

    Args:
        formula (str): 算式字符串
        vars (dict | None): 变量字典. Defaults to None
    """
    print("parsing")
    formula = fullwidth_to_halfwidth(replace_chinese_punctuation(formula)).strip()
    formula = formula.replace("×", '*').replace("÷", "/").replace("^", "**").replace(";", "\r").replace("\n", '\r')
    original_formula = formula
    # formula = parse_vars(formula, vars)
    print(formula)
    all_vars = get_vars(formula)
    result_formulas = [f.strip() for f in formula.split("\r")]
    need_to_draw = False
    draws = []
    draws_3d = []
    for f in result_formulas:
        if f.startswith("::"):
            # 绘制 3D 图像
            draws_3d.append(parse_func(f[2:]))
            need_to_draw = True
        elif f.startswith(":"):
            draws.append(parse_func(f[1:]))
            need_to_draw = True
    print("ntd", need_to_draw, draws)
    if len(draws) != 0 and len(draws_3d) != 0:
        raise ValueError("不能同时绘制 3D 图像和 2D 图像")
    if need_to_draw:
        if len(draws) > 0:
            # filename, use_temp = draw_exprs(*draws)
            return original_formula.replace(" ", ''), draws, 1
        elif len(draws_3d) > 0:
            # print("draws3d:", draws_3d)
            # filename, use_temp = draw_3d_exprs(*draws_3d)
            return original_formula.replace(" ", ''), draws_3d, 2

    result_formula = parse_func(result_formulas[-1])
    print(result_formulas, result_formula)
    if not result_formula:
        result_formula = "0"
    try:
        result = sympify(result_formula).subs({k: sympify(v) for k, v in all_vars.items()})
    except Exception as ex:
        if len(all_vars.items()) < 1:
            result = sympify(result_formula)
        else:
            raise ex

    return original_formula.replace(" ", ''), result, 0

def check_integer_size(expr, max_digits=1000):
    for atom in expr.atoms(Integer):
        if len(str(atom)) > max_digits:
            raise ValueError(f"{expr} 算式整数过大")

def parse_vars(formula: str, vars=None):
    """处理变量

    Args:
        formula (str): 表达式
        vars (dict | None): 变量字典. Defaults to None

    Returns:
        str: 处理完的表达式
    """
    original_formula = formula
    all_vars = {}
    if vars:
        all_vars = vars
    all_vars = all_vars | get_vars(formula, all_vars)
    # print("formula: ", formula)
    # print("vars: ", all_vars)
    formula = '\r'.join([formula.split("\r")[i].strip() for i, _ in enumerate(original_formula.split("\r")) if not is_var_line(original_formula, original_formula.split("\r")[i].strip())])
    for key in all_vars.keys():
        # print("key: ", key, "formula: ", formula, "keyin: ", key in formula)
        if key in formula: break
        return formula.split("\r")[-1]
    # for name, value in all_vars.items():
    #     formula = str(parse_polynomial(formula)[1].subs(name, value))
    return formula

def get_vars(formula: str, all_vars: dict | None = None) -> dict:
    if not all_vars:
        all_vars = {}
    print("formula", formula)
    for line in formula.split("\r"):
        print("line is", line)
        var_info = is_var_line(formula, line)
        if not var_info:
            continue
        name, value = var_info
        # for n, v in all_vars.items():
        value = parse_polynomial(value)[1]
        print("value:", value)
        all_vars[name] = value

    return all_vars

def is_var_line(formula, line: str) -> bool | tuple:
    if not "=" in line or line.startswith(":"): return False
    print("line:", line)
    name = line.split("=")[0].strip()
    value = "=".join(line.split("=")[1:]).strip()
    # 排除 == >= <=
    if value.startswith("=") or name.endswith((">", "<")):
        return False
    func_names = [func.split("(")[0] for func in get_func(formula)]
    print("var name is", name)
    if not valid_var_name(name):
        raise ValueError("变量名不符合规范（只由数字，字母，下划线组成且不能是数字开头）")
    if name in func_names:
        raise ValueError("变量名不能和函数重名")
    # if name in ["x", "y"]:
    #     raise ValueError("变量名不能是 x 或 y")
    return (name, value)

def parse_func(formula):
    """处理函数

    Args:
        formula (str): 函数字符串

    Returns:
        str: 函数结果
    """
    funcs = find_funcs(formula)
    print(f"funcs: {funcs}")
    for f in funcs:
        func_name = f.split("(")[0]
        print(f"func name: {func_name}")
        if func_name not in func.funcs.keys(): continue
        func_body = '('.join(f.split("(")[1:])[:-1]
        print(f"func body: {func_body}")
        args = []
        for arg in func_body.split(","):
            args.append(parse_polynomial(arg.strip())[-1])
        # _, args = parse_polynomial(func_body)
        print(f"args: {args}")
        result = func.funcs[func_name]['func'](*args)
        print(f"func \"{f}\" result: {result}")
        formula = formula.replace(f, str(result))
    return formula
