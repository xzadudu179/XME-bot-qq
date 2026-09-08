"""AST 白名单校验：在 sympify 之前拒绝一切非纯算术语法。

sympify 底层基于 Python 求值，官方明确不可用于不可信输入。本模块只放行
"数字、四则/乘方运算、已知函数名调用、比较" 这类纯算术语法，属性访问、
下标、字符串常量、lambda、推导式等语法在进入 sympify 前即被拒绝，
从语法层堵死 __import__、__class__ 链等已知逃逸载荷。
"""

import ast

_ALLOWED_BINOPS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.FloorDiv)
_ALLOWED_UNARYOPS = (ast.UAdd, ast.USub)
_ALLOWED_CMPOPS = (ast.Gt, ast.Lt, ast.GtE, ast.LtE, ast.Eq, ast.NotEq)
_DENIED_FUNC_NAMES = frozenset((
    "eval", "exec", "compile", "open", "input", "breakpoint",
    "getattr", "setattr", "delattr", "globals", "locals", "vars",
    "type", "super", "object", "__build_class__",
))


def assert_safe_syntax(expr: str) -> None:
    """校验表达式仅为纯算术/函数调用语法，不合法时抛异常。

    Args:
        expr (str): 待送入 sympify 的表达式

    Raises:
        SyntaxError: 表达式本身不是合法 Python 表达式（交由上层 syntaxerror 文案）
        ValueError: 表达式包含白名单之外的语法
    """
    tree = ast.parse(expr, mode="eval")
    _check_node(tree.body)


def _check_node(node: ast.AST) -> None:
    """递归校验 AST 节点，遇到白名单之外的节点抛 ValueError。"""
    if isinstance(node, ast.BinOp):
        if not isinstance(node.op, _ALLOWED_BINOPS):
            raise ValueError(f"表达式不允许的运算符: {type(node.op).__name__}")
        _check_node(node.left)
        _check_node(node.right)
    elif isinstance(node, ast.UnaryOp):
        if not isinstance(node.op, _ALLOWED_UNARYOPS):
            raise ValueError(f"表达式不允许的一元运算符: {type(node.op).__name__}")
        _check_node(node.operand)
    elif isinstance(node, ast.Compare):
        if not all(isinstance(op, _ALLOWED_CMPOPS) for op in node.ops):
            raise ValueError("表达式不允许的比较运算符")
        _check_node(node.left)
        for comparator in node.comparators:
            _check_node(comparator)
    elif isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("只允许直接调用函数名")
        if node.func.id in _DENIED_FUNC_NAMES or "__" in node.func.id:
            raise ValueError(f"不允许调用函数: {node.func.id}")
        if node.keywords:
            raise ValueError("函数调用不允许关键字参数")
        _check_node(node.func)
        for arg in node.args:
            _check_node(arg)
    elif isinstance(node, ast.Name):
        if "__" in node.id:
            raise ValueError(f"表达式不允许的名称: {node.id}")
    elif isinstance(node, ast.Constant):
        if not isinstance(node.value, (int, float, complex)):
            raise ValueError(f"表达式不允许的常量: {type(node.value).__name__}")
    elif isinstance(node, ast.Tuple):
        for elt in node.elts:
            _check_node(elt)
    else:
        raise ValueError(f"表达式包含不允许的语法: {type(node).__name__}")
