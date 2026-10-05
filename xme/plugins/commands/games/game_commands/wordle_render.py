"""Wordle 棋盘的 HTML 模板

样式以用户的 wordle_sample.html 重写版为准：
- 调色板变量与内嵌字体前缀复用 xme.xmetools.templates 的 IIUN_COLORS / FONTS_STYLE
- 棋盘专属样式维护在 _STYLE 中；tile 类名与页脚字母类名分开
游戏逻辑（wordle.py）只依赖本模块的常量与两个公共函数。
"""
from html import escape

from xme.xmetools.templates import FONTS_STYLE, IIUN_COLORS

# 瓷砖判定状态：每个字母相对答案的着色结果
TILE_GRAY = 0     # 字母不在答案中
TILE_YELLOW = 1   # 字母存在但位置不对
TILE_GREEN = 2    # 字母与位置都正确

_TILE_CLASS = {TILE_GRAY: "tile-absent", TILE_YELLOW: "tile-present", TILE_GREEN: "tile-correct"}
# 页脚已猜字母的着色类（与瓷砖类分开，取各字母的最优状态）
_LETTER_CLASS = {TILE_GRAY: "absent", TILE_YELLOW: "present", TILE_GREEN: "correct"}

# 布局尺寸常量（board_image_size 与模板必须一起改）
_TILE_SIZE = 56
_TILE_GAP = 8
_PANEL_PADDING = 24
_HEADER_HEIGHT = 48      # 标题行
_FOOTER_HEIGHT = 100     # 页脚已猜字母行（字母多时会折行，预算放宽）
# 视口余量：部分环境下 Chrome 会漏绘制贴近视口底部的内容，
# 视口要比实际内容多留出这份空间，多出的透明部分由裁边裁掉
_VIEWPORT_SLACK = 120

_STYLE = """
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
    color: var(--text-color);
}
:root {
    --correct: #5ec485;
    --correct-text: #71ce95;
    --present: #bbab53;
    --present-text: #d3c368;
    --absent: #2d3449;
    --absent-text: var(--grey-color);
}
body { background: transparent; }
.panel {
    display: inline-block;
    background: var(--bg-color);
    color: var(--text-color);
    padding: PADDINGpx;
    font-family: "Noto Sans CJK SC", "Noto Sans SC", sans-serif;
}
.title {
    font-size: 20px;
    letter-spacing: 0.25em;
    padding-left: 0.05em; /* 略微调整重心 */
    text-align: center;
}
.board {
    margin-top: 18px;
    display: grid;
    gap: GAPpx;
    vertical-align: middle;
}
.row {
    display: grid;
    grid-template-columns: repeat(LETTERS, TILESpx);
    gap: GAPpx;
}
.tile {
    width: TILESpx;
    height: TILESpx;
    display: flex;
    align-items: center;
    padding-top: 5px;
    justify-content: center;
    font-size: 28px;
    line-height: 1;
    text-transform: uppercase;
    border: 2px solid #3d4158;
}
.tile-correct { background: var(--correct); border-color: var(--correct); }
.tile-present { background: var(--present); border-color: var(--present); }
.tile-absent  { background: var(--absent); border-color: var(--absent); }
.footer {
    margin-top: 10px;
    font-size: 12px;
    letter-spacing: 0.1em;
    color: var(--grey-color);
    text-align: center;
    display: flex;
    flex-direction: column;
    gap: 5px;
    padding: 0 4px;
}
.footer .item {
    display: flex;
    justify-content: space-between;
}
.item * {
    color: var(--grey-color);
}

.correct { color: var(--correct-text); }
.present { color: var(--present-text); }
.absent  { color: var(--absent-text); }
"""


def board_image_size(word_length: int, max_times: int) -> tuple:
    """根据棋盘规模计算截图视口的 (width, height)（含防漏绘制的余量）"""
    board_w = word_length * _TILE_SIZE + (word_length - 1) * _TILE_GAP
    board_h = max_times * _TILE_SIZE + (max_times - 1) * _TILE_GAP
    width = board_w + _PANEL_PADDING * 2 + _VIEWPORT_SLACK
    height = _HEADER_HEIGHT + board_h + _FOOTER_HEIGHT + _PANEL_PADDING * 2 + _VIEWPORT_SLACK
    return width, height


def summarize_letters(guesses: list) -> list:
    """按字母表排序汇总已猜过的字母及其最优状态（绿 > 黄 > 灰）"""
    best: dict = {}
    for word, states in guesses:
        for letter, state in zip(word, states):
            if letter not in best or state > best[letter]:
                best[letter] = state
    return sorted(best.items())


def render_board_html(word_length: int, max_times: int, guesses: list) -> str:
    """渲染 Wordle 棋盘的完整 HTML 文档

    Args:
        word_length (int): 单词字数
        max_times (int): 最大猜测次数（决定棋盘总行数）
        guesses (list): [(单词, [状态...]), ...]，状态取 TILE_GRAY/TILE_YELLOW/TILE_GREEN

    Returns:
        str: 完整 HTML，body 透明底供截图后裁边
    """
    rows = []
    for word, states in guesses:
        tiles = "".join(
            f'<div class="tile {_TILE_CLASS.get(state, "tile-absent")}">{escape(letter)}</div>'
            for letter, state in zip(word, states)
        )
        rows.append(f'<div class="row">{tiles}</div>')
    for _ in range(max_times - len(guesses)):
        tiles = '<div class="tile"></div>' * word_length
        rows.append(f'<div class="row">{tiles}</div>')

    letters = summarize_letters(guesses)
    if letters:
        spans = "".join(
            f'<span class="{_LETTER_CLASS[state]}">{escape(letter.upper())}</span>'
            for letter, state in letters
        )
        footer = f'<div class="item"><p>Guessed:</p><p>{spans}</p></div>'
    else:
        footer = ""

    style = (_STYLE
        .replace("PADDING", str(_PANEL_PADDING))
        .replace("GAP", str(_TILE_GAP))
        .replace("TILES", str(_TILE_SIZE))
        .replace("LETTERS", str(word_length)))
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>{IIUN_COLORS}{FONTS_STYLE}{style}</style>
</head>
<body>
<div class="panel">
    <div class="title melete">WORDLE</div>
    <div class="board orbitron">
        {"".join(rows)}
    </div>
    <div class="footer orbitron">{footer}</div>
</div>
</body>
</html>"""
