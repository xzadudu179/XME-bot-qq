"""指令文档的两个视图：/docs.md 给机器，/docs 给人。

/docs.md 返回 bot 启动时生成的文档 markdown 原文，供文档站（VitePress）构建时抓取：
落盘后即可用 <!--@include: ...--> 引入为正文——VitePress 的 include 只解析本地文件，不能写 URL。
/docs 返回同一份内容渲染好的 HTML 页面，方便直接在浏览器里看。
"""
import nonebot
from quart import Response, abort, request
from xme.plugins.server_app.client_info import log_visit
from xme.plugins.server_app.docs_page import render_docs_page
from xme.xmetools.doctools import read_doc_md

bot = nonebot.get_bot()  # 在此之前必须已经 init

MARKDOWN_MIMETYPE = "text/markdown"
HTML_MIMETYPE = "text/html"


def _doc_text() -> str:
    """读取指令文档内容；读不到按 404 处理（文档没生成说明 bot 没正常启动过）。"""
    text = read_doc_md()
    if text is None:
        abort(404)
    return text


@bot.server_app.route('/docs.md')
async def docs_md():
    """返回指令文档 markdown 原文。"""
    log_visit("文档", request)
    return Response(_doc_text(), mimetype=MARKDOWN_MIMETYPE)


@bot.server_app.route('/docs')
async def docs_html():
    """返回渲染成 HTML 页面的指令文档。"""
    log_visit("文档页", request)
    return Response(render_docs_page(_doc_text()), mimetype=HTML_MIMETYPE)
