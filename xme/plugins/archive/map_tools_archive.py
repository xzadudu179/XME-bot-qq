from PIL import Image, ImageDraw, ImageFont, ImageFilter
import random
import math

def gen_node_lines(node_xys: list[tuple], draw: ImageDraw, color, radius=1, width=1):
    # print(node_xys)
    for line in node_xys:
        # print(line)
        draw.line([line[0], line[1]], fill=color, width=width)
        draw.ellipse((line[0][0] - radius, line[0][1] - radius, line[0][0] + radius, line[0][1] + radius), fill=color)
        draw.ellipse((line[1][0] - radius, line[1][1] - radius, line[1][0] + radius, line[1][1] + radius), fill=color)

def draw_polygon(draw: ImageDraw, center: tuple[int, int], radius: int, sides: int, angle: float, color, width=1):
    """绘制多边形

    Args:
        draw (ImageDraw): 图形绘制对象
        center (tuple[int, int]): 中心点
        radius (int): 半径
        sides (int): 多边形边数
        angle (float): 旋转角度
        color : 颜色
        width (int, optional): 线条宽度. Defaults to 1.
    """
    if sides < 3:
        raise ValueError("没有小于 3 边的多边形")
    points = []
    for i in range(sides):
        theta = 2 * math.pi * i / sides  # 计算每个顶点的角度
        x = center[0] + radius * math.cos(theta)
        y = center[1] + radius * math.sin(theta)
        points.append((x, y))
    rotated_points = rotate_points(points, angle, center)
    # 绘制图形
    draw.polygon(rotated_points, outline=color, width=width)

def rotate_points(points, angle, center) -> list:
    """将点按照某坐标旋转

    Args:
        angle (float): 角度
        center (中心点): tuple[int, int]

    Returns:
        list: _description_
    """
    rotated_points = []
    for x, y in points:
        # 将点移动到原点，旋转，然后再移回
        x_rotated = center[0] + (x - center[0]) * math.cos(angle) - (y - center[1]) * math.sin(angle)
        y_rotated = center[1] + (x - center[0]) * math.sin(angle) + (y - center[1]) * math.cos(angle)
        rotated_points.append((x_rotated, y_rotated))
    return rotated_points


def random_node_lines(draw, count, node_range: tuple[int, int], lightness_range: tuple[int, int], line_width, width, height, max_length=50, node_size=1):
    # 随机生成线条
    for _ in range(count):
        line_points = []
        start = (random.randint(0, width), random.randint(0, height))
        for _ in range(random.randint(node_range[0], node_range[1])):
            # 随机起点
            # 随机角度生成终点，保证长度不超过 max_length
            angle = random.uniform(0.5, 2 * math.pi)
            end_x = int(start[0] + random.randint(0, max_length) * math.cos(angle))
            end_y = int(start[1] + random.randint(0, max_length) * math.sin(angle))
            end = (max(0, min(width, end_x)), max(0, min(height, end_y)))  # 确保终点在图像范围内
            line_points.append((start, end))
            start = end
        # 设置颜色
        lightness = random.randint(lightness_range[0], lightness_range[1])
        color = (lightness, lightness + int(lightness * 0.3), lightness + int(lightness * 0.3))
        # 生成线条
        gen_node_lines(line_points, draw, color, node_size, line_width)

def mark_point(draw: ImageDraw, point, regular_point, sides_or_cross: int, color, line_width, radius, name='', font_size=12, text_space=8):
    # 标记坐标点
    if sides_or_cross < 3:
        write_crosshair(draw, point, radius * 0.8, int(radius * 0.7) * 0.8, color, line_width)
    else:
        draw_polygon(draw, point, radius, sides_or_cross, (random.randint(0, 314) / 100), color, line_width)
    # draw.ellipse((point[0] - 1, point[1] - 1, point[0] + 1, point[1] + 1), fill=color)
    draw_text_on_image(draw, str(regular_point), (point[0] + radius, point[1] + radius), font_size, color, text_space)
    draw_text_on_image(draw, name, (point[0] + radius + text_space, point[1] - radius), font_size, color, text_space)



def write_grid(draw, grid_spacing, width, height, color='#102735', line_width=1):
    """绘制网格

    Args:
        grid_spacing (int): 网格间隔
        width (int): 宽度
        height (int): 高度
    """
        # 计算中心点
    center_x = width // 2
    center_y = height // 2

    # 绘制垂直网格线
    for x in range(center_x, width , grid_spacing):
        draw.line([(x, 0), (x, height)], fill=color, width=line_width)
    for x in range(center_x, 0 , -grid_spacing):
        draw.line([(x, 0), (x, height)], fill=color, width=line_width)

    # 绘制水平网格线
    for y in range(center_y, height, grid_spacing):
        draw.line([(0, y), (width, y)], fill=color, width=line_width)
    for y in range(center_y, 0, -grid_spacing):
        draw.line([(0, y), (width, y)], fill=color, width=line_width)

    # 绘制正中心的十字线
    draw.line([(center_x, 0), (center_x, height)], fill=color, width=line_width)  # 垂直中心线
    draw.line([(0, center_y), (width, center_y)], fill=color, width=line_width)   # 水平中心线

    # # 绘制纵向网格线
    # for x in range(0, width, grid_spacing):
    #     draw.line([(x, 0), (x, height)], fill=color, width=line_width)  # 绘制纵向线

    # # 绘制横向网格线
    # for y in range(0, height, grid_spacing):
    #     draw.line([(0, y), (width, y)], fill=color, width=line_width)  # 绘制横向线

def write_crosshair(draw, point: tuple[int, int], radius: int, lineout: int, color, width: int=2):
    """绘制准心

    Args:
        draw (_type_): draw对象
        point (tuple[int, int]): 绘制的位置
        radius (int): 圆半径
        lineout (int): 准心线条超出圆的长度
        color (_type_): 颜色
        width (int, optional): 线条宽度. Defaults to 2.
    """
    x, y = point
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), outline=color, width=width)
    # 绘制十字
    draw.line((x - radius - lineout, y, x + radius + lineout, y), fill=color, width=width)  # 水平线
    draw.line((x, y - radius - lineout, x, y + radius + lineout), fill=color, width=width)  # 垂直线

def draw_text_on_image(draw: ImageDraw, text, position, font_size, color, spacing=4):
    # 创建字体对象
    # try:
        # font = ImageFont.truetype("static/fonts/Cubic_11.ttf", font_size)  # 使用字体
    # except IOError:
        # font = ImageFont.load_default()  # 加载默认字体
    font = ImageFont.load_default()  # 加载默认字体
    # 在指定位置绘制文字
    draw.text(position, text, font=font, fill=color, spacing=spacing)

# 计算像素亮度
def calculate_brightness(r, g, b):
    return 0.299 * r + 0.587 * g + 0.114 * b

if __name__ == "__main__":
    # 图表大小
    # 星图绘制中心
    center = (125, 125)
    img_zoom = 3
    zoom_factor = 1
    size_factor = 1
    ui_zoom_factor = 1
    map_width, map_height = 250, 250
    zoom_width, zoom_height = map_width // zoom_factor // 2, map_height // zoom_factor // 2
    append = (((-center[0] + zoom_width) * zoom_factor), (-center[1] + zoom_height) * zoom_factor)
    padding = 100

    # 计算图像宽高
    width, height = int(zoom_width * 2 * zoom_factor + padding * 2) * img_zoom, int(zoom_height * 2 * zoom_factor + padding * 2) * img_zoom
    print(width, height)
    # 坐标点列表，(x, y)
    regular_points = []
    # 随便绘制一些物体的位置
    for i in range(25):
        regular_points.append((random.randint(0, map_width), random.randint(0, map_height)))

    points = [(int(point[0] * zoom_factor + padding + append[0]) * img_zoom, int(point[1] * zoom_factor + padding + append[1]) * img_zoom) for point in regular_points]

    # 创建画布
    img = Image.new('RGB', (width, height), 'black')
    draw = ImageDraw.Draw(img)

    line_width = 1

    # 背景
    # 绘制随机线条
    random_node_lines(draw, 50, (2, 6), (10, 30), int(line_width * zoom_factor) * img_zoom, width * (width // (zoom_width * 2)), height * (height // (zoom_height * 2)), max_length=int(50 * zoom_factor * img_zoom), node_size=int(1 * zoom_factor))
    # 绘制网格
    write_grid(draw, int(35 * zoom_factor * img_zoom), width, height, '#102735', int(1 * zoom_factor * img_zoom))

    font_size = 12

    # 前景
    # 绘制多边形
    # draw_polygon(draw, points[2], 12, 3, (random.randint(0, 314) / 100), 'green', line_width)
    names = {
        3: "测试空间站",
        4: "测试舰队",
        5: "测试行星"
    }
    colors = ["#FE4A56", "#FEF060", "#44ff6c", "#e58bff", "#AAAACC", "#44a0ff"]
    # colors = ["#FF0000", "#FFFF00", "#0F0", "#0FF", "#AAA", "#F0F"]
    relas = {
        colors[0]: "敌对",
        colors[1]: "中立",
        colors[2]: "友好",
        colors[3]: "玩家",
        colors[4]: "无所属",
        colors[5]: "联盟",
    }

    for i, point in enumerate(regular_points):
        if i == 0: continue
        side = random.randint(3, 5)
        color = random.choice(colors)
        mark_point(draw, points[i], point, side, color, int(line_width * ui_zoom_factor), int(10 * ui_zoom_factor), f'[{relas[color]}] {names[side]}{i}', int(font_size * ui_zoom_factor))

    # 绘制圆加十字
    mark_point(draw, points[0],regular_points[0], 0, 'cyan', int(line_width * ui_zoom_factor), int(10 * ui_zoom_factor),'xzadudu179 (你)', int(font_size * ui_zoom_factor))

    text = f'[HIUN 星图终端]\n[用户] xzadudu179\n坐标轴中心: {center}  缩放倍率: {zoom_factor}x | {ui_zoom_factor}x\n你在坐标 [{regular_points[0][0]}, {regular_points[0][1]}]'
    draw_text_on_image(draw, text, (int(15 * ui_zoom_factor), int(height - 40 * ui_zoom_factor - font_size * (text.count('\n') + 1) * ui_zoom_factor)), int(font_size * ui_zoom_factor), 'white', spacing=10)
    # draw_text_on_image(draw, 'Test File HIUN\nYesyt', (15, 1080 - font_size), font_size, 'white')
    # 保存图片
    # img.save('data/images/temp/chart.png')

    # 显示图片
    img.show()