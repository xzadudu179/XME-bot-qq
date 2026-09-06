# some are made by Deepseek-v4-flash-vison-exp at Deepseek Harness
"""世界观/资料类工具：星球时钟状态与技能文档读取。"""
from xme.xmetools.timetools import TELIA_CLOCK

def get_telia_clock_state():
    return TELIA_CLOCK.get_current_state()

def get_skill_md(name: str, agent=None):
    skill = ""
    content = ""
    try:
        with open(f"./static/skills/{name}.md", 'r', encoding="utf-8") as file:
            skill = file.read()
    except Exception as ex:
        content = f"[寻找 skill 文件发生错误：{ex}]"
    if skill == "":
        content = "[这个 skill 似乎是空白的。]"
    content = skill
    agent.activate_skills.append(name)
    return {"result": content, "no_compress": True}

