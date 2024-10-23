import requests as req
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from . import color_manage as c
from math import ceil
import json
import re
from lxml import etree


colors = {}
with open('yunhei_colors.json', 'r', encoding='utf-8') as file:
    colors = json.load(file)



def check_cblack(qq_id, return_colorful_text=True):
    """检查目标云黑

    Args:
        qq_id (str): 目标
        return_colorful_text (bool, optional): 是否返回带颜色的字符. Defaults to True.

    Returns:
        str: 云黑查询结果
    """
    yunhei_url = "https://yunhei.furrynet.top/oldindex.php"
    # 启动浏览器
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 启用无头模式
    chrome_options.add_argument("--disable-gpu")  # 如果不需要GPU加速，可以禁用
    chrome_options.add_argument("--window-size=1920,1080")  # 设置窗口大小，避免某些元素无法加载
    driver = webdriver.Chrome(options=chrome_options)
    # 等待页面加载并获取动态生成的内容
    sec = 1
    driver.get(yunhei_url)
    # 找到表单元素并提交
    input_element = driver.find_element(By.ID, 'qq')
    input_element.send_keys(qq_id)
    # 找到提交按钮并点击
    submit_button = driver.find_element(By.CLASS_NAME, 'auth-submit')
    submit_button.click()

    content = driver.find_element(By.CLASS_NAME, 'auth-forgot-password1')
    html = etree.HTML(content.get_attribute("outerHTML"))
    searchs = html.xpath('//font[not(descendant::label) and not(descendant::font)] | //br | //label[not(descendant::label) and not(descendant::font)]')
    no_cb_searchs = html.xpath('//font[not(descendant::label) and not(descendant::font)] | //br| //div[@class="auth-forgot-password1"]//label[not(descendant::label) and not(descendant::font)]')
    center = html.xpath('//div[@class="auth-forgot-password1"]//center')
    # 关闭浏览器
    driver.quit()
    # contents = []
    # 行
    # print(no_cb_searchs)
    # print(searchs)
    # print(center)
    lines = []
    lines.append(c.gradient_text("#dda3f8","#4bceff" ,text="------------------内容查询完毕------------------"))
    not_cb = None
    qun_text = False
    # 每行的内容

    for ce in center:
        direct_text = ce.text if ce.text else ""
        full = ''.join(ce.itertext()).strip()
        # 遍历<a>标签的子元素
        for child in ce:
            if child.tail:
                direct_text += child.tail  # 获取子标签后的文本 (anotherText)
        # print(direct_text)
        if direct_text and "暂无云黑." in direct_text:
            # print("center insert")
            qun_text = True
            not_cb = True
            lines.insert(1, direct_text.strip())
        if "上黑" in full:
            not_cb = False

    def parse_yunhei_lines(searchs):
        line_content = ''
        for search in searchs:
            full_text = ''.join(search.itertext()).strip()
            # print(full_text)
            # print(search)
            if search.tag == 'br':
                # contents.append("\n")
                # print(f"line append {line_content}")
                lines.append(line_content)
                line_content = ""
                continue
            cc = search.get('color')
            if not cc:
                cc = search.get('class')
            color_attr: str = cc if cc else ""
            color = colors.get(color_attr.lower(), color_attr)
            text_content: str = full_text if full_text else ""
            # if not text_content.startswith("-") and just_br:
            #     text_content = f"    {text_content}"
            # print(color_attr, color, text_content)
            if color == "":
                new_content = f"{text_content}"
                if not_cb != None and not not_cb:
                    r, g, b= c.hex_to_rgb("#ff8e90")
                    new_content = c.rgb_text(new_content, (r, g, b))

            elif type(color) == list:
                # print(color, text_content)
                new_content = c.gradient_text(tuple(color), text=text_content, use_list=True)
            else:
                # print(color)
                r, g, b= c.hex_to_rgb(color)
                new_content = c.rgb_text(text_content, (r, g, b))
            # contents.append(new_content)
            line_content += new_content.strip()

    for search in searchs:
        full_text = ''.join(search.itertext())
        # print(full_text)
        if full_text and ("暂无云黑" in full_text):
            not_cb = True
    if not_cb and not qun_text:
        parse_yunhei_lines(no_cb_searchs)
    else:
        parse_yunhei_lines(searchs)


    if not_cb != None and not not_cb:
        r, g, b= c.hex_to_rgb("#fe6a68")
        yunhei_text = c.rgb_text("账号已被登记为云黑", (r, g, b))
        lines.insert(1, yunhei_text)
    elif not_cb == None:
        r, g, b= c.hex_to_rgb("#ff8e80")
        yunhei_text = c.rgb_text("查询出现错误！", (r, g, b))
        lines.insert(1, yunhei_text)
    # print([remove_ansi_escape_sequences(line) for line in lines if line != "\n"])
    print(c.gradient_text("#dda3f8","#4bceff" ,text="正在返回处理的数据..."))
    if return_colorful_text:
        return [line for line in lines if line != "\n"]
    else:
        return [c.clear_text_color(line) for line in lines if line != "\n"]

def calc_len(text):
    # 移除ANSI转义序列
    text = c.clear_text_color(text);
    pattern = r'[^\x00-\xff]'
    length = 0
    for char in text:
        # print(char)
        # 如果是中文字符，加2
        if re.match(pattern, char):
            length += 2
        else:
            # 如果是其他字符，加1
            length += 1
    return length

if __name__ == "__main__":
    # qq_id = input("请输入查询qq号或群号:")
    qq_id = 1608374672
    print(c.gradient_text("#dda3f8","#4bceff" ,text="正在连接浏览器并查询..."))
    lines = check_cblack(qq_id, True)
    # 居中处理
    # print(lines)
    max_length = 0
    for line in lines:
        line_len = calc_len(line)
        max_length = line_len if line_len > max_length else max_length
    # print(max_length)
    for line in lines:
        # 需要空的格数
        space_count = ceil((max_length - calc_len(line)) / 2)
        line = space_count * " " +  line
        print(line)
    # input()