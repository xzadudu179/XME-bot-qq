from collections.abc import Iterable
import config

DEFAULT_PERMISSIONS = "在群内使用"

class Doc():
    def __init__(self, name: str, desc: str, introduction: str) -> None:
        self.name = name
        self.desc = desc
        self.introduction = introduction

class PluginDoc(Doc):
    def __init__(self, name, desc, introduction, contents: Iterable[str], usages: Iterable[str], permissions: Iterable[Iterable[str]] = [[]], alias_list: Iterable[Iterable[str]] = [[]], simple_output: bool = False, other_info="") -> None:
        super().__init__(name, desc, introduction)
        self.permissions = permissions
        self.contents = contents
        self.usages = usages
        self.alias_list = alias_list
        self.simple_output = simple_output
        self.other_info = other_info

    def __str__(self) -> str:
        alias_lines = ""
        usages_lines = ('\n  ' + config.COMMAND_START[0]).join(self.usages)
        contents_lines = ''
        permissions_lines = ""
        for i, content in enumerate(self.contents):
            line_head = f'  {content.split(": ")[0]}: '
            try:
                alias_lines += f"{line_head}{', '.join(self.alias_list[i])}\n"
            except:
                alias_lines += f"{line_head}无\n"
            try:
                # print(self.permissions[i])
                permissions_lines += f"{line_head}{DEFAULT_PERMISSIONS if len(self.permissions[i]) < 1 else ' & '.join(self.permissions[i])}\n"
            except:
                permissions_lines += f"{line_head}无\n"
            contents_lines += f"  {content}\n"
        not_simple_output = f"""
##所有指令用法##：
  {config.COMMAND_START[0]}{usages_lines}
##权限/可用范围##：
{permissions_lines}##别名##：
{alias_lines}
""".strip()
        return rf"""
[插件] {self.name}
简介：{self.desc}
作用：{self.introduction}
##内容##：
{contents_lines}
""".strip() + ("\n" + not_simple_output + "\n" + self.other_info if not self.simple_output else "\n" + self.other_info + "/////OUTER/////" + not_simple_output)

class CommandDoc(Doc):

    def __init__(self, name, desc, introduction, usage, permissions: Iterable[str]=[], alias: Iterable[str]=[]) -> None:
        super().__init__(name, desc, introduction)
        self.usage = usage
        self.alias = alias
        self.permissions = permissions

    def __str__(self) -> str:
        return f"""
[指令] {self.name}
简介：{self.desc}
作用：{self.introduction}
##用法##：
  {config.COMMAND_START[0]}{self.name} {self.usage}
权限/可用范围：{DEFAULT_PERMISSIONS if len(self.permissions) < 1 else ' & '.join(self.permissions)}
别名：{'无' if len(self.alias) < 1 else ', '.join(self.alias)}
""".strip()

class SpecialDoc(Doc):
    def __init__(self, name, desc, introduction) -> None:
        super().__init__(name, desc, introduction)

    def __str__(self) -> str:
        return rf"""
[特殊] {self.name}
简介：{self.desc}
{self.introduction}
""".strip()

def shell_like_usage(option_name, options: list[dict]):
    content = f"{option_name.upper()}:"
    for option in options:
        content += f"\n\t-{option['abbr']}, --{option['name']}\t{option['desc']}"
    return content