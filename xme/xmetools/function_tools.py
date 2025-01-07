from concurrent.futures import TimeoutError, ThreadPoolExecutor
import multiprocessing
from functools import wraps
import sympy as sp
from xme.xmetools.color_manage import hex_to_rgb, gradient_hex_color
from xme.xmetools.text_tools import limit_str_len, base64_encode
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

def thread_set_timeout(seconds=10, timeout_message="函数执行超时", callback=None):
    """设置超时装饰器（非大量计算）

    Args:
        seconds (int, optional): 超时秒数. Defaults to 10.
        timeout_message (str, optional): 若未填写回调函数时超时的报错消息. Defaults to "函数执行超时".
        callback (function, optional): 回调函数，参数是被装饰的函数的参数. Defaults to None.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = thread_run_with_timeout(func, seconds, *args, **kwargs)
            except TimeoutError:
                if callback:
                    result = callback(*args, **kwargs)
                else:
                    raise TimeoutError(timeout_message)
            return result
        return wrapper
    return decorator

def run_with_timeout(func, timeout_seconds, error_message="函数执行超时", *args, **kwargs):
    """设置函数执行超时

    Args:
        func (function): 需要执行的函数
        timeout_seconds (float): 超时秒数
        error_message (str): 超时报错消息

    Raises:
        TimeoutError: 超时

    Returns:
        Any: 函数结果
    """
    # 使用 multiprocessing.Pool 来执行长时间计算
    with multiprocessing.Pool(1) as pool:
        result = pool.apply_async(func, args=args, kwds=kwargs)
        try:
            return result.get(timeout=timeout_seconds)  # 获取计算结果，设定超时
        except multiprocessing.TimeoutError:
            pool.terminate()  # 超时后终止进程池
            raise TimeoutError(error_message)
    process = multiprocessing.Process(target=worker)
    process.start()
    process.join(timeout=timeout_seconds)  # 设置超时

    if process.is_alive():
        process.terminate()  # 超时后终止进程
        raise TimeoutError(error_message)

    return result_queue.get()

def thread_run_with_timeout(func, timeout_seconds=2, *args, **kwargs):
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func, *args, **kwargs)
        try:
            result = future.result(timeout=timeout_seconds)  # 获取计算结果，设定超时
            return result
        except TimeoutError:
            future.cancel()  # 超时后取消任务
            raise TimeoutError("函数执行超时")

def draw_expr(expr_str, color: str | tuple = "blue", range=(-10, 10, 500)):
    x = sp.symbols('x')
    expr = sp.sympify(expr_str)
    f_num = sp.lambdify(x, expr, "numpy")
    # 数值范围
    x_vals = np.linspace(*range)
    y_vals = f_num(x_vals)

    plt.plot(x_vals, y_vals, label=expr_str, color=color)

def draw_exprs(*expr_strs, path_folder="./data/images/temp"):
    prop = font_manager.FontProperties(fname=rf'./fonts/Cubic_11.ttf')
    font_size = 16
    plt.rcParams['font.family'] = prop.get_name()
    font_color = (200 / 255, 248 / 255, 251 / 255)
    bg_color = (4 / 255, 23 / 255, 32 / 255)
    sec_color = (93 / 255, 238 / 255, 246 / 255)
    grid_color = (57 / 255, 84 / 255, 91 / 255)

    colors = [[i / 255 for i in hex_to_rgb(item)] for item in gradient_hex_color("#75ff8c", "#448fff", len(expr_strs))]
    print(colors)
    # 绘制图像
    plt.figure(figsize=(8, 6), facecolor=bg_color)
    for i, s in enumerate(expr_strs):
        draw_expr(s, colors[i])
    # 添加标题和标签
    title = f"函数 {limit_str_len(','.join([es for es in expr_strs]), 30)} 的结果"
    plt.title(title, fontsize=font_size, color=font_color)
    plt.xlabel("x", fontsize=font_size, color=font_color)
    plt.ylabel("y", fontsize=font_size, color=font_color)
    ax = plt.gca()
    ax.set_facecolor(bg_color)
    for spine in ax.spines.values():
        spine.set_color(grid_color)
    ax.tick_params(axis='x', colors=(200 / 1.5 / 255, 248 / 1.5 / 255, 251 / 1.5 / 255))
    ax.tick_params(axis='y', colors=(200 / 1.5 / 255, 248 / 1.5 / 255, 251 / 1.5 / 255))
    ax.set_xlabel('x', fontsize=font_size, color=font_color)
    ax.set_ylabel('y', fontsize=font_size, color=font_color)
    # 显示网格
    plt.grid(True,  color=grid_color, linestyle='--', linewidth=1)

    # 添加图例
    plt.legend(fontsize=12, facecolor=bg_color, edgecolor=sec_color, labelcolor=font_color)
    title = base64_encode(title)
    name = f"func_image_{title}.png"
    plt.savefig(path_folder + "/" + name, dpi=200, bbox_inches="tight")
    return name