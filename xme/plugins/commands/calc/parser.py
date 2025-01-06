import re
from xme.xmetools.text_tools import replace_chinese_punctuation, valid_var_name
from . import func
# import func
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

def parse_polynomial(formula, vars=None):
    """处理多项式

    Args:
        formula (str): 算式字符串
        vars (dict | None): 变量字典. Defaults to None
    """
    formula = replace_chinese_punctuation(formula).strip()
    formula = formula.replace("×", '*').replace("÷", "/").replace("^", "**")
    original_formula = formula
    formula = parse_vars(formula, vars)
    # print(f"formula: {formula}")
    if "=" in formula:
        formula = "0"
    monomials = [item.strip() for item in formula.split("+")]
    results = []
    for monomial in monomials:
        results.append(parse_monomial(monomial))
    result_formula = '+'.join(results)
    # print(f"poly result: {result_formula}")

    return original_formula.replace(" ", ''), sympify(result_formula)

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
    all_vars = {}
    if vars:
        all_vars = vars
    all_vars = all_vars | get_vars(formula, all_vars)
    # print("formula: ", formula)
    # print("vars: ", all_vars)
    for key in all_vars.keys():
        # print("key: ", key, "formula: ", formula, "keyin: ", key in formula)
        if key in formula: break
        return formula.split("\r")[-1]
    for name, value in all_vars.items():
        formula = formula.replace(name, value)
    return formula.split("\r")[-1]


def get_vars(formula: str, all_vars: dict | None = None) -> dict:
    if not all_vars:
        all_vars = {}
    for line in formula.split("\r"):
        if not "=" in line: continue
        name = line.split("=")[0].strip()
        value = line.split("=")[1].strip()
        func_names = [func.split("(")[0] for func in get_func(formula)]
        if name in func_names:
            raise ValueError("变量名不能和函数重名")
        if not valid_var_name(name):
            raise ValueError("变量名不符合规范（只由数字，字母，下划线组成且不能是数字开头）")
        value = str(parse_polynomial(value, all_vars)[1])
        all_vars[name] = value
    return all_vars

def parse_func(formula):
    """处理函数

    Args:
        formula (str): 函数字符串

    Returns:
        str: 函数结果
    """
    funcs = find_funcs(formula)
    # print(f"funcs: {funcs}")
    for f in funcs:
        func_name = f.split("(")[0]
        if func_name not in func.funcs.keys(): continue
        func_body = '('.join(f.split("(")[1:])[:-1]
        print(f"func body: {func_body}")
        _, args = parse_polynomial(func_body)
        print(f"args: {args}")
        result = func.funcs[func_name]['func'](*args)
        print(f"func \"{f}\" result: {result}")
        formula = formula.replace(f, str(result))
    return formula


def parse_monomial(monomial):
    monomial = parse_func(monomial)
    return monomial