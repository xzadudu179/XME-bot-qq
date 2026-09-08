# some are made by Deepseek-v4-flash-vison-exp at Deepseek Harness
"""AI 可调用工具集合（按主题分类）。

分类：
- files.py      文件读写/搜索/改写/转存/发送
- codeexec.py   沙箱内对文件副本执行 Python 分析代码
- web.py        url 下载、网页阅读、web 搜索、图片/视频/文档内容查看
- media.py      图片生成与 OCR
- worldview.py  世界观状态与技能文档
- misc.py       会话交互与杂项（追问、骰子、会话改名、中途汇报）
- _common.py    跨分类共享的常量与私有 helper（不对外暴露工具）

agent 通过本包命名空间查找工具：__tools__ 列出工具名，且每个名字必须能
getattr(functions, name) 取到；tools.json 中的 schema 名单须与之一致。
"""

# AI 用到的函数名列表，需要与实际定义的函数名相符
__tools__ = [
    "get_telia_clock_state",
    "gen_image",
    "get_skill_md",
    "check_file",
    "list_files",
    "save_to_history",
    "find_history_file",
    "write_to_history",
    "write_to_temp",
    "delete_history_file",
    "rename_history_file",
    "clear_history_files",
    "create_history_folder",
    "move_history_file",
    "inprocess_report",
    "ocr_image",
    "view_document_file",
    "view_image",
    "view_video",
    "screenshot_page",
    "read_webpage",
    "web_search",
    "content_search",
    "get_webs_partial",
    "get_user_input_urls",
    "download",
    "send_file",
    "edit_file",
    "syntax_check",
    "run_python",
    "zip_files",
    "extract_archive",
    "name_session",
    "dice",
    "ask_user"
]

from .files import (
    check_file,
    clear_history_files,
    create_history_folder,
    content_search,
    delete_history_file,
    edit_file,
    extract_archive,
    find_history_file,
    get_webs_partial,
    list_files,
    move_history_file,
    rename_history_file,
    save_to_history,
    send_file,
    syntax_check,
    write_to_history,
    write_to_temp,
    zip_files,
)
from .codeexec import run_python
from .media import gen_image, ocr_image
from .misc import ask_user, dice, get_user_input_urls, inprocess_report, name_session
from .web import (
    download,
    read_webpage,
    screenshot_page,
    view_document_file,
    view_image,
    view_video,
    web_search,
)
from .worldview import get_skill_md, get_telia_clock_state
from ._common import GLM_API_BASE
