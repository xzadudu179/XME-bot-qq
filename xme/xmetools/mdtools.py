"""markdown 版式小工具：正文段落、Text 代码块、一条指令的完整块。

只负责「怎么排」，不认识插件文档对象——权限、别名的文案由调用方（doctools）渲染好后传进来。
"""


def markdown_section(title: str, body: str, indent: str = "") -> str:
    """渲染一节正文：`- **标题**` 加缩进正文；多行正文原样保留（markdown 里折叠为同一段）。"""
    lines = [f"{indent}  {line}".rstrip() for line in str(body).split("\n")]
    return f"{indent}- **{title}**\n\n" + "\n".join(lines)


def markdown_code_block(text: str, indent: str = "") -> str:
    """渲染 Text 代码块；整块按 indent 对齐（不超过 3 空格，markdown 仍按围栏块解析）。"""
    lines = [f"{indent}``` Text", *(f"{indent}{line}" for line in str(text).split("\n")), f"{indent}```"]
    return "\n".join(lines)


def command_markdown(name: str, kind: str, introduction: str, usage_line: str,
                     permissions: str, aliases: str, level: int, indent: str = "") -> str:
    """渲染一条指令的 markdown 块，末尾带一条分隔线。

    顶层指令、插件内的子指令、SUPERUSER 栏抽出来的子指令共用这份版式。
    """
    sections = [
        f"{indent}{'#' * level} [{kind}] {name}",
        markdown_section("作用", introduction, indent),
        f"{indent}- **用法**\n\n" + markdown_code_block(usage_line, indent),
        markdown_section("权限/可用范围", permissions, indent),
        markdown_section("别名", aliases, indent),
    ]
    return "\n\n".join(sections) + f"\n\n{indent}---"
