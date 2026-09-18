# some are made by Deepseek-v4-flash-vison-exp at Deepseek Harness
"""世界观/资料类工具：星球时钟状态与技能文档读取。"""
from xme.xmetools.filetools import is_safe_custom_name
from xme.xmetools.timetools import TELIA_CLOCK

def get_telia_clock_state():
    return TELIA_CLOCK.get_current_state()

def get_skill_md(name: str, agent=None):
    """读取 static/skills 下名为 name.md 的技能文档；读取失败或为空时返回占位文案。"""
    if not is_safe_custom_name(name):
        return {"result": "[skill 名不合法：仅允许中英文/数字/_-.，不含路径分隔符]", "no_compress": True}
    skill = ""
    try:
        with open(f"./static/skills/{name}.md", 'r', encoding="utf-8") as file:
            skill = file.read()
    except Exception:
        pass
    agent.activate_skills.append(name)
    if skill == "":
        return {"result": "[这个 skill 似乎是空白的。]", "no_compress": True}
    return {"result": skill, "no_compress": True}

