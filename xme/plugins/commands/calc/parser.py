import re
from xme.xmetools.text_tools import replace_chinese_punctuation
from . import func
# import func
from sympy import sympify

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

def parse_polynomial(formula):
    """处理多项式

    Args:
        formula (str): 算式字符串
    """
    formula = replace_chinese_punctuation(formula).strip()
    formula = formula.replace("×", '*').replace("÷", "/").replace("^", "**")
    # print(f"formula: {formula}")
    monomials = [item.strip() for item in formula.split("+")]
    results = []
    for monomial in monomials:
        results.append(parse_monomial(monomial))
    result_formula = '+'.join(results)
    # print(f"poly result: {result_formula}")
    return formula.replace(" ", ''), sympify(result_formula)


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
        # print(f"func body: {func_body}")
        _, args = parse_polynomial(func_body)
        # print(f"args: {args}")
        result = func.funcs[func_name]['func'](*args)
        # print(f"func \"{f}\" result: {result}")
        formula = formula.replace(f, str(result))
    return formula


def parse_monomial(monomial):
    monomial = parse_func(monomial)
    return monomial