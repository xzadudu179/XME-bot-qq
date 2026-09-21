"""把指令文档（docs.md）渲染成一个可直接看的 HTML 页面，供 /docs 路由使用。

用 markdown-it-py：和文档站（VitePress）是同一套渲染引擎，输出基本一致；同时关掉了
原始 HTML 透传，插件文档里的 "<指令名>" 这类尖括号会被转义成文本而不是当成标签吞掉。
"""
from markdown_it import MarkdownIt

PAGE_TITLE = "XME-Bot 指令文档"

# 解析器无状态，建一次复用；commonmark 下 html=False，再补表格与删除线
_MARKDOWN = MarkdownIt("commonmark", {"html": False}).enable(["table", "strikethrough"])

# 无外部资源（字体/CDN 都不引），跟着页面走，暗色模式靠 color-scheme 自适应
_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root {{ color-scheme: light dark; }}
body {{ margin: 0; padding: 2.5rem 1.25rem 5rem;
  font: 16px/1.75 system-ui, -apple-system, "Segoe UI", "Noto Sans CJK SC", "Microsoft YaHei", sans-serif; }}
main {{ max-width: 46rem; margin: 0 auto; }}
h1 {{ font-size: 1.55rem; margin: 0 0 .5rem; }}
h2 {{ font-size: 1.3rem; margin: 3rem 0 .75rem; padding-top: 1.5rem; border-top: 1px solid rgba(128,128,128,.28); }}
h3 {{ font-size: 1.15rem; margin: 2.5rem 0 .75rem; padding-top: 1.5rem; border-top: 1px solid rgba(128,128,128,.28); }}
h4 {{ font-size: 1rem; margin: 1.6rem 0 .5rem; }}
p, li {{ margin: .5rem 0; }}
ul {{ padding-left: 1.4rem; }}
code {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: .88em;
  background: rgba(128,128,128,.16); padding: .12em .35em; border-radius: 4px; }}
pre {{ background: rgba(128,128,128,.16); padding: .85rem 1rem; border-radius: 8px; overflow-x: auto; }}
pre code {{ background: none; padding: 0; }}
hr {{ border: none; border-top: 1px solid rgba(128,128,128,.28); margin: 2.5rem 0; }}
a {{ color: inherit; }}
.lead {{ margin: 0 0 2rem; font-size: .9rem; opacity: .7; }}
</style>
</head>
<body>
<main>
<header>
<h1>{title}</h1>
<p class="lead">本页由 bot 启动时生成的指令文档渲染，原始 markdown 见 <a href="/docs.md">/docs.md</a>。</p>
</header>
{body}
</main>
</body>
</html>
"""


def render_markdown(text: str) -> str:
    """把 markdown 渲染成 HTML 片段（不透传原始 HTML）。"""
    return _MARKDOWN.render(text)


def render_docs_page(text: str, title: str = PAGE_TITLE) -> str:
    """把指令文档 markdown 渲染成完整 HTML 页面。"""
    return _PAGE_TEMPLATE.format(title=title, body=render_markdown(text))
