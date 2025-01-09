from concurrent.futures import TimeoutError, ThreadPoolExecutor
import multiprocessing
from functools import wraps
import sympy as sp
from xme.xmetools.color_manage import hex_to_rgb, gradient_hex_color
from xme.xmetools.text_tools import limit_str_len, base64_encode
from xme.xmetools.file_tools import has_file
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

bg_color = (4 / 255, 23 / 255, 32 / 255)
prop = font_manager.FontProperties(fname=rf'./fonts/Cubic_11.ttf')
plt.rcParams['font.family'] = prop.get_name()
FIG = plt.figure(figsize=(8, 6), facecolor=bg_color)

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

def draw_expr(expr_str, color: str | tuple = "blue", range_x=(-10, 10, 1000), range_y=None, labels=[]):
    expr = sp.sympify(expr_str)
    free_symbols = list(expr.free_symbols)
    if len(free_symbols) == 1:
        x = free_symbols[0]
        f_num = sp.lambdify(x, expr, "numpy")
        x_vals = np.linspace(*range_x)
        y_vals = f_num(x_vals)
        plt.plot(x_vals, y_vals, color=color, label=expr_str)
    elif len(free_symbols) == 2:
        x, y = free_symbols
        if range_y is None:
            range_y = range_x  # 如果未指定 y 的范围，使用 x 的范围
        f_num = sp.lambdify((x, y), expr, "numpy")
        x_vals = np.linspace(*range_x)
        y_vals = np.linspace(*range_y)
        X, Y = np.meshgrid(x_vals, y_vals)
        z = f_num(X, Y)
        contains_invalid = np.any(np.isnan(z)) or np.any(np.isinf(z))
        if contains_invalid:
            print("有无效值")
            plt.text(10, 11 - 0.8 * len(labels), "警告：函数有无效值", color=color, fontsize=8)
        z = np.nan_to_num(z, nan=0.0)
        plt.contour(X, Y, z, levels=[0], colors=color, linewidths=2)
        # plt.clabel(cs, inline=True, fontsize=16)
    labels.append(expr_str)
    return labels

def draw_3d_expr(expr_str, ax, color: str | tuple = "blue", range_x=(-10, 10, 500), range_y=None, labels=[]):
    print("绘制3D")
    # expr = sp.sympify(expr_str)
    # fig = plt.figure()
    expr = sp.sympify(expr_str)
    free_symbols = list(expr.free_symbols)
    if len(free_symbols) == 1:
        free_symbols = free_symbols, None
    x, y = free_symbols
    print(free_symbols)
    if range_y is None:
        range_y = range_x  # 如果未指定 y 的范围，使用 x 的范围
    f_num = sp.lambdify((x, y) if y is not None else x, expr, "numpy")

    x_vals = np.linspace(*range_x)
    y_vals = np.linspace(*range_y) if y is not None else np.zeros_like(x_vals)
    X, Y = np.meshgrid(x_vals, y_vals)
    z = f_num(X, Y) if y is not None else f_num(X)

    # 检查无效值并处理
    contains_invalid = np.any(np.isnan(z)) or np.any(np.isinf(z))
    if contains_invalid:
        print("有无效值")
        # ax.text(-40 + 1.5 * len(labels) * 1.5, 30 - 2 * len(labels) * 1.5, z=0, s="警告：函数有无效值", color=color, fontsize=8)
        # ax.text(0.05, 0.95, s='警告：函数有无效值', z=0, transform=ax.transAxes, fontsize=8, color=color, verticalalignment='top', horizontalalignment='left')
        expr_str = "(有无效值) " + expr_str

        # ax.text(-72 + 1.5 * len(labels) * 1.5, 44 - 2 * 2 * 1.5, z=0, s="WARNING: INVALID", color=color, fontsize=8)
    z = np.nan_to_num(z, nan=0.0)

    ax.plot_surface(X, Y, z, cmap="plasma", edgecolor=color, alpha=0.7, linewidth=0.5)
    labels.append(expr_str)
    return labels


def draw_3d_exprs(*expr_strs, path_folder="./data/images/temp"):
    print("3d:exprs", expr_strs)
    ax = FIG.add_subplot(111, projection='3d')
    return draw_exprs(*expr_strs, path_folder=path_folder, draw_function=draw_3d_expr, ax=ax, label_ax=ax, pre="3dfunc_image", parse_func=parse_3d_exprs_label)

def parse_exprs_label(title, font_size, font_color, bg_color, grid_color, labels, sec_color, ax):
    plt.title(title, fontsize=font_size, color=font_color)
    plt.xlabel("x", fontsize=font_size, color=font_color)
    plt.ylabel("y", fontsize=font_size, color=font_color)
    plt.axis("equal")
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
    plt.legend(labels=labels,fontsize=12, facecolor=bg_color, edgecolor=sec_color, labelcolor=font_color)

def parse_3d_exprs_label(title, font_size, font_color, bg_color, grid_color, labels, sec_color, ax):
    ax.view_init(elev=30)
    ax.set_title(title, fontsize=font_size, color=font_color)
    ax.set_facecolor(bg_color)
    ax.grid(True, color=grid_color, linewidth=1, linestyle='--')
    for spine in ax.spines.values():
        spine.set_color(grid_color)
    ax.xaxis.pane.set_edgecolor(grid_color)  # 设置x轴面板边缘颜色
    ax.xaxis.pane.set_facecolor(bg_color)  # 设置x轴面板背景颜色
    ax.xaxis.line.set_color(grid_color)
    ax.xaxis._axinfo['grid'].update(color=grid_color, linewidth=1)

    ax.yaxis.pane.set_edgecolor(grid_color)  # 设置y轴面板边缘颜色
    ax.yaxis.pane.set_facecolor(bg_color)  # 设置y轴面板背景颜色
    ax.yaxis.line.set_color(grid_color)
    ax.yaxis._axinfo['grid'].update(color=grid_color, linewidth=1)

    ax.zaxis.pane.set_edgecolor(grid_color)  # 设置z轴面板边缘颜色
    ax.zaxis.pane.set_facecolor(bg_color)  # 设置z轴面板背景颜色
    ax.zaxis.line.set_color(grid_color)
    ax.zaxis._axinfo['grid'].update(color=grid_color, linewidth=1)

    ax.tick_params(axis='x', colors=(200 / 1.5 / 255, 248 / 1.5 / 255, 251 / 1.5 / 255))
    ax.tick_params(axis='y', colors=(200 / 1.5 / 255, 248 / 1.5 / 255, 251 / 1.5 / 255))
    ax.tick_params(axis='z', colors=(200 / 1.5 / 255, 248 / 1.5 / 255, 251 / 1.5 / 255))
    ax.set_xlabel('x', fontsize=font_size, color=font_color)
    ax.set_ylabel('y', fontsize=font_size, color=font_color)
    ax.set_zlabel('z', fontsize=font_size, color=font_color)
    ax.legend(labels=labels,fontsize=12, facecolor=bg_color, edgecolor=sec_color, labelcolor=font_color)

def draw_exprs(*expr_strs, path_folder="./data/images/temp", draw_function=draw_expr, parse_func=parse_exprs_label, label_ax="default", pre="func_image", **draw_kwargs):
    global bg_color
    print("exprstrs:", expr_strs)
    title = f"{limit_str_len(','.join([es for es in expr_strs]), 30)} 的结果"
    title_name = base64_encode(title)
    name = f"{pre}_{title_name}.png"
    path = path_folder + "/" + name
    if has_file(path):
        print("使用缓存")
        return name, True

    font_size = 16
    font_color = (200 / 255, 248 / 255, 251 / 255)
    sec_color = (93 / 255, 238 / 255, 246 / 255)
    grid_color = (57 / 255, 84 / 255, 91 / 255)
    labels = []

    colors = [[i / 255 for i in hex_to_rgb(item)] for item in gradient_hex_color("#75ff8c", "#448fff", len(expr_strs))]
    # print(colors)
    # 绘制图像
    for i, s in enumerate(expr_strs):
        # draw_expr(s, colors[i], labels=labels)
        draw_function(s, color=colors[i], labels=labels, **draw_kwargs)
    if label_ax == "default":
        label_ax = plt.gca()
    labels = [limit_str_len(label, 30) for label in labels]
    parse_func(title, font_size, font_color, bg_color, grid_color, labels, sec_color, label_ax)

    plt.savefig(path, dpi=400, bbox_inches="tight")
    return name, False