from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
import config
from xme.xmetools import mdtools
from xme.xmetools.texttools import pinyin_sort_key

DEFAULT_PERMISSIONS = "无/未标注"
# 插件把「没有权限限制」写成这几种，渲染文档时统一成 DEFAULT_PERMISSIONS
NO_PERMISSION_TEXTS = ("无", "无/未标注")
PERMISSION_SEPARATOR = " & "
ALIAS_SEPARATOR = "、 "

# 只有 SUPERUSER 能用的指令（权限逐项就是这个字符串），docs.md 里单独归到文末一栏
SUPERUSER_PERMISSION = "是 SUPERUSER"
DOCS_SUPERUSER_HEADING = "## SUPERUSERS 可用指令"

# 文档标题级别：插件条目为 MD_TITLE_LEVEL，其子指令用下一级；子指令块整体缩进
MD_TITLE_LEVEL = 3
MD_SUB_INDENT = "  "

# bot 启动时（bot_init.gen_doc_md）生成的指令文档，路径相对项目根目录
DOC_MD_PATH = "docs.md"


def read_doc_md(path: str | Path = DOC_MD_PATH) -> str | None:
    """读取指令文档 markdown 原文；文件不存在或读取失败时返回 None。"""
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError:
        return None


def permissions_text(permissions: Iterable[str] = ()) -> str:
    """权限列表渲染成一行文本；空列表或只写了「无」这类占位值时输出 DEFAULT_PERMISSIONS。"""
    perms = [p.strip() for p in permissions or () if p and p.strip()]
    if not perms or all(p in NO_PERMISSION_TEXTS for p in perms):
        return DEFAULT_PERMISSIONS
    return PERMISSION_SEPARATOR.join(perms)


def aliases_text(aliases: Iterable[str] = ()) -> str:
    """别名列表渲染成一行（`a`、 `b`）；没有别名时输出「无」。"""
    names = [a.strip() for a in aliases or () if a and a.strip()]
    return ALIAS_SEPARATOR.join(f"`{name}`" for name in names) if names else "无"


def is_superuser_only(permissions: Iterable[str] = ()) -> bool:
    """权限是否只有 SUPERUSER 一条（用于把仅超管可用的指令单独归类）。

    逐条精确比对：写成「是管理 或 是群主 或 是 SUPERUSER」这种复合条件不算仅超管可用。
    """
    perms = [p.strip() for p in permissions or () if p and p.strip()]
    return bool(perms) and all(p == SUPERUSER_PERMISSION for p in perms)


def check_can_show(perms):
    """权限列表是否适合展示给普通用户（供 /help 的纯文本列表使用）。

    只要有一条权限不只是 SUPERUSER 就认为可展示；空列表视为可展示。
    """
    # print(perms)
    show = True
    for p in perms:
        if "是 SUPERUSER" not in p:
            # print(p, "不是 superuser")
            break
        show = False
    return show


def _at(items: Iterable, index: int, default):
    """按下标取子指令的某个字段；插件少写了一项时返回 default。"""
    items = list(items or ())
    return items[index] if index < len(items) else default


@dataclass
class MarkdownEntry:
    """一条要写进 docs.md 的 markdown 块；name（指令名/插件名）只用于排序。"""
    name: str
    text: str


@dataclass
class DocMarkdown:
    """一份文档渲染出的条目：普通条目与仅 SUPERUSER 可用的条目分开，供 docs.md 分组与排序。"""
    normal: list[MarkdownEntry] = field(default_factory=list)
    superuser_only: list[MarkdownEntry] = field(default_factory=list)


class Doc():
    """插件文档基类：name / desc / introduction 是三类文档的公共字段。"""

    kind = "文档"

    def __init__(self, name: str, desc: str, introduction: str) -> None:
        self.name = name
        self.desc = desc
        self.introduction = introduction

    def to_markdown(self, level: int = MD_TITLE_LEVEL) -> DocMarkdown:
        """渲染成 docs.md 的条目（按 SUPERUSER 是否专用分到两组）；由子类实现。"""
        raise NotImplementedError


class PluginDoc(Doc):
    kind = "插件"

    def __init__(
            self,
            name,
            desc,
            introduction,
            contents: Iterable[str],
            usages: Iterable[str],
            permissions: Iterable[Iterable[str]] = [[]],
            alias_list: Iterable[Iterable[str]] = [[]],
            simple_output: bool = False,
            other_info="",
            sub_docs: Iterable["CommandDoc"] | None = None,
        ) -> None:
        super().__init__(name, desc, introduction)
        self.permissions = permissions
        self.contents = contents
        self.usages = usages
        self.alias_list = alias_list
        self.simple_output = simple_output
        self.other_info = other_info
        self.sub_docs = list(sub_docs) if sub_docs else []

    def __str__(self) -> str:
        alias_lines = ""
        usages_lines = ('\n  ' + config.COMMAND_START[0]).join(self.usages)
        contents_lines = ''
        permissions_lines = ""
        for i, content in enumerate(self.contents):
            show = check_can_show(self.permissions[i])
            if not show:
                continue
            line_head = f'  {content.split(": ")[0]}: '
            try:
                alias_lines += f"{line_head}{', '.join(self.alias_list[i])}\n"
            except Exception:
                alias_lines += f"{line_head}无\n"
            try:
                # print(self.permissions[i])
                permissions_lines += f"{line_head}{DEFAULT_PERMISSIONS if len(self.permissions[i]) < 1 else ' & '.join(self.permissions[i])}\n"
            except Exception:
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

    def _command_docs(self) -> list["CommandDoc"]:
        """把按下标对齐的 contents / usages / permissions / alias_list 还原成每条子指令的 CommandDoc。

        contents 的格式是「指令名 [用法]: 作用」。子指令本身有现成的 CommandDoc（sub_docs，
        如用户功能那批按指令注册的）时直接用，作用写成简介更完整；按名字查找，找不到就退回
        用并列字段拼出来的版本。
        """
        docs = []
        for i, content in enumerate(self.contents):
            name = content.split(":")[0].split(" ")[0].strip()
            sub_doc = next((doc for doc in self.sub_docs if doc.name == name), None)
            if sub_doc is not None:
                docs.append(sub_doc)
                continue
            usage = _at(self.usages, i, "").strip()
            docs.append(CommandDoc(
                name=name,
                desc="",
                introduction=content.split(": ", 1)[1].strip() if ": " in content else "",
                usage=usage[len(name):].strip() if usage.startswith(name) else usage,
                permissions=_at(self.permissions, i, []),
                alias=_at(self.alias_list, i, []),
            ))
        return docs

    def to_markdown(self, level: int = MD_TITLE_LEVEL) -> DocMarkdown:
        command_docs = sorted(self._command_docs(), key=lambda doc: pinyin_sort_key(doc.name))
        blocks = []
        superuser_entries = []
        for doc in command_docs:
            if not is_superuser_only(doc.permissions):
                blocks.append(doc.markdown_block(level + 1, MD_SUB_INDENT))
                continue
            # 仅超管可用的子指令从插件块里抽出来，作为顶层条目放进 SUPERUSERS 栏
            superuser_entries.append(MarkdownEntry(doc.name, doc.markdown_block(level)))
        normal = []
        # 子指令全是超管专用时插件块本身也归到 SUPERUSERS 栏，不在普通栏留空壳
        if blocks or not command_docs:
            sections = [
                f"{'#' * level} [{self.kind}] {self.name}",
                mdtools.markdown_section("作用", self.introduction),
            ]
            if blocks:
                sections.append("- **指令列表：**\n\n" + "\n".join(blocks))
            normal.append(MarkdownEntry(self.name, "\n\n".join(sections)))
        return DocMarkdown(normal=normal, superuser_only=superuser_entries)


class CommandDoc(Doc):
    kind = "指令"

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

    def markdown_block(self, level: int = MD_TITLE_LEVEL, indent: str = "") -> str:
        """渲染成 markdown 块（不含分组信息，也可被 PluginDoc 当作子指令块使用）。"""
        return mdtools.command_markdown(
            name=self.name,
            kind=self.kind,
            introduction=self.introduction,
            usage_line=f"{config.COMMAND_START[0]}{self.name} {self.usage}".strip(),
            permissions=permissions_text(self.permissions),
            aliases=aliases_text(self.alias),
            level=level,
            indent=indent,
        )

    def to_markdown(self, level: int = MD_TITLE_LEVEL) -> DocMarkdown:
        entry = MarkdownEntry(self.name, self.markdown_block(level))
        if is_superuser_only(self.permissions):
            return DocMarkdown(superuser_only=[entry])
        return DocMarkdown(normal=[entry])


class SpecialDoc(Doc):
    kind = "特殊"

    def __init__(self, name, desc, introduction, usage) -> None:
        super().__init__(name, desc, introduction)
        self.usage = usage

    def __str__(self) -> str:
        return rf"""
[特殊] {self.name}
简介：{self.desc}
##用法##:
  {self.usage}
{self.introduction}
""".strip()

    def to_markdown(self, level: int = MD_TITLE_LEVEL) -> DocMarkdown:
        block = "\n\n".join([
            f"{'#' * level} [{self.kind}] {self.name}",
            mdtools.markdown_section("作用", self.introduction),
            f"- **用法**\n\n" + mdtools.markdown_code_block(self.usage),
        ]) + "\n\n---"
        return DocMarkdown(normal=[MarkdownEntry(self.name, block)])


def shell_like_usage(option_name, options: list[dict]):
    content = f"{option_name.upper()}:"
    for option in options:
        content += f"\n\t-{option['abbr']}, --{option['name']}\t{option['desc']}"
    return content


def doc_to_markdown(doc, level: int = MD_TITLE_LEVEL) -> DocMarkdown:
    """把插件 __plugin_usage__ 里的 Doc 渲染成 markdown；不是 Doc（如历史遗留的裸字符串）时返回空条目。"""
    if isinstance(doc, Doc):
        return doc.to_markdown(level)
    return DocMarkdown()


def _entry_sort_key(entry: MarkdownEntry) -> str:
    """docs.md 条目的排序键：中文按拼音、大小写同级。"""
    return pinyin_sort_key(entry.name)


def _quotes_to_inline_code(text: str) -> str:
    """把双引号换成反引号：角色文本里用 "xxx" 表示要原样输入的内容，文档里渲染成行内代码。"""
    return text.replace('"', "`")


def build_docs_md(docs: Iterable[DocMarkdown]) -> str:
    """把各插件的渲染结果拼成 docs.md 全文。

    普通条目按名字拼音序排在前，仅 SUPERUSER 可用的条目统一放到文末的 SUPERUSERS 一栏。
    """
    normal = sorted((entry for doc in docs for entry in doc.normal), key=_entry_sort_key)
    superuser_only = sorted((entry for doc in docs for entry in doc.superuser_only), key=_entry_sort_key)
    sections = [entry.text for entry in normal]
    if superuser_only:
        sections.append(DOCS_SUPERUSER_HEADING)
        sections.extend(entry.text for entry in superuser_only)
    return _quotes_to_inline_code("\n\n".join(sections))
