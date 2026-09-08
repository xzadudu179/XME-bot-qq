"""calc 求值入口：在沙箱子进程内完成"解析 → sympify → doit → 浮点转换"全流程。

本模块只返回 JSON 纯数据（CalcResult，经沙箱回传时自动转为 dict，由调用方
重建），sympy 表达式对象不跨进程，
从根本上避免主进程执行未求值表达式的 doit()——历史上大整数幂运算会在
主进程内占死事件循环，导致整个 bot 卡死且无法超时销毁。
"""

from dataclasses import dataclass, field

from xme.plugins.commands.calc.constants import MAX_INT_DIGITS, RESULT_STR_MAX
from xme.plugins.commands.calc.parser import check_integer_size, parse_polynomial


@dataclass
class CalcResult:
    """单次计算的完整结果（可跨进程传输的纯数据）。

    Attributes:
        formula (str): 归一化后的算式，用于 success 文案
        result_str (str): sympy 结果字符串（未求值形式，供展示）
        float_str (str | None): 数值近似结果字符串，无法浮点化时为 None
        draw_mode (int): 0 无绘图 / 1 绘制 2D / 2 绘制 3D
        draw_exprs (list[str]): 绘图表达式列表（draw_mode 非 0 时有效）
    """
    formula: str
    result_str: str
    float_str: str | None
    draw_mode: int
    draw_exprs: list[str] = field(default_factory=list)


def evaluate_formula(arg: str) -> CalcResult:
    """完整求值一个算式，只返回纯字符串结果。

    Args:
        arg (str): 用户输入的原始算式（可含变量定义行与 ":" / "::" 绘图行）

    Returns:
        CalcResult: 求值结果
    """
    formula, result, draw_mode = parse_polynomial(arg)
    if draw_mode:
        return CalcResult(formula=formula, result_str="", float_str=None,
                          draw_mode=draw_mode, draw_exprs=list(result))
    check_integer_size(result, MAX_INT_DIGITS)
    result_str = str(result)
    if len(result_str) > RESULT_STR_MAX:
        raise ValueError("算式结果过大")
    float_str = None
    try:
        float_str = str(float(result.doit()))
    except Exception:
        # 符号结果/浮点溢出等无法小数化的情况不展示小数行，与历史行为一致
        float_str = None
    return CalcResult(formula=formula, result_str=result_str, float_str=float_str, draw_mode=0)
