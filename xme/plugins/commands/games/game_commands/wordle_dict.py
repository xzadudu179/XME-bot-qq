"""Wordle 答案词语解释：本地中文词典查询

词典来自 static/wordle_defs_zh.json（批量翻译 + 校对 + 本地核对预生成，
覆盖全部答案词）。无对应释义的词返回 None，游戏消息不显示解释段；
扩充词库后需重新生成该词典。
"""
from xme.xmetools.jsontools import read_from_path

DEFS_PATH = "./static/wordle_defs_zh.json"

_DEFS: dict = read_from_path(DEFS_PATH) or {}


def get_word_definition(word: str) -> str | None:
    """查询单词的中文释义，无对应释义返回 None"""
    return _DEFS.get(word.lower().strip()) or None
