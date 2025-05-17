import sympy as sp
from xme.xmetools.colortools import hex_to_rgb, gradient_hex_color
from xme.xmetools.texttools import limit_str_len, hash_text
from xme.xmetools.filetools import has_file
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

bg_color = (4 / 255, 23 / 255, 32 / 255)
prop = font_manager.FontProperties(fname=rf"static/fonts/Cubic_11.ttf")
plt.rcParams['font.family'] = prop.get_name()
FIG = plt.figure(figsize=(8, 6), facecolor=bg_color)

def draw_expr(expr_str, color: str | tuple = "blue", range_x=(-10, 10, 800), range_y=None, labels=[]):
    expr = sp.sympify(expr_str,  evaluate=False)
    free_symbols = [s for s in expr.free_symbols if s.name in ('x', 'y')]
    print("free symbols", free_symbols)
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

def draw_3d_expr(expr_str, ax, color: str | tuple = "blue", range_x=(-10, 10, 100), range_y=None, labels=[]):
    print("绘制3D")
    # expr = sp.sympify(expr_str)
    # fig = plt.figure()
    expr = sp.sympify(expr_str,  evaluate=False)
    free_symbols = [s for s in expr.free_symbols if s.name in ('x', 'y')]
    print(free_symbols)
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
    print("xyz", X, Y, z)
    # 检查无效值并处理
    contains_invalid = np.any(np.isnan(z)) or np.any(np.isinf(z))
    if contains_invalid:
        print("有无效值")
        expr_str = "(有无效值) " + expr_str

        # ax.text(-72 + 1.5 * len(labels) * 1.5, 44 - 2 * 2 * 1.5, z=0, s="WARNING: INVALID", color=color, fontsize=8)
    z = np.nan_to_num(z, nan=0)

    ax.plot_surface(X, Y, z, cmap="winter", edgecolor=color, alpha=0.7, linewidth=0.5)
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
    # plt.axis("equal")
    # 获取 x 轴范围
    x_min, x_max = plt.xlim()

    # 以 x 轴范围为基准，设置 y 轴范围
    y_center = 0  # y 轴范围中心点（可以根据实际需要调整）
    y_range = (x_max - x_min) / 2  # 确保 x 和 y 的比例一致
    plt.ylim(y_center - y_range, y_center + y_range)
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
    name = hash_text(f"{pre}_{title}") + ".png"
    path = path_folder + "/" + name
    if has_file(path):
        print("使用缓存")
        return path, True

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

    plt.savefig(path, dpi=200, bbox_inches="tight")
    return path, False