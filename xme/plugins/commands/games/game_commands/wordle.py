import math
import random
from itertools import groupby

from nonebot import CommandSession
from nonebot.log import logger
from character import get_message
from xme.plugins.commands.games.play import cmd_name
from xme.plugins.commands.xme_user.classes import user
from xme.xmetools.bottools import permission
from xme.xmetools.cmdtools import is_command
from xme.xmetools.debugtools import debug_msg
from xme.xmetools.imgtools import get_html_image_async
from xme.xmetools.jsontools import read_from_path
from xme.xmetools.msgtools import aget_session_msg, image_msg, send_session_msg

from . import wordle_render
from .game import Game, return_state, limited
from .wordle_dict import get_word_definition

random.seed()

TIMES_LIMIT = 5
BASIC_AWARD = 50
name = 'wordle'
game_meta = {
    "name": name,
    "desc": get_message("plugins", cmd_name, name, 'desc'),
    "introduction": get_message("plugins", cmd_name, name, 'introduction', times_limit=TIMES_LIMIT),
    "args": {
        "c": get_message("plugins", cmd_name, name, 'arg_letters'),
        "t": get_message("plugins", cmd_name, name, 'arg_times_limit'),
    },
    "cost": 10,
    "times_left_message": get_message("plugins", cmd_name, name, 'times_left', times_left='{times_left}'),
    "limited_message": get_message("plugins", cmd_name, name, 'limited'),
    "award_message": get_message("plugins", cmd_name, name, 'award', award="{award}", coins_left='{coins_left}'),
    "no_award_message": get_message("plugins", cmd_name, name, 'no_award'),
}

WORD_LIST_PATH = "./static/wordle_words.json"
MIN_WORD_LENGTH = 4
MAX_WORD_LENGTH = 8
MAX_TIMES = 12

# parse_game_step 的状态码
RESULT_WIN = 0            # 猜中
RESULT_CONTINUE = 1       # 未猜中，继续
RESULT_NO_TIMES = 2       # 次数用完
RESULT_NOT_IN_LIST = -1   # 单词不在词库
RESULT_WRONG_LENGTH = -2  # 长度与答案字数不符
RESULT_GUESSED = -3       # 猜过了

_WORD_LISTS = read_from_path(WORD_LIST_PATH) or {}
_ALLOWED_SETS = {int(n): set(info.get("allowed", []))
                 for n, info in _WORD_LISTS.items() if isinstance(info, dict)}


def has_words(word_length: int) -> bool:
    """判断指定字数是否有可用的答案词库"""
    return bool(_WORD_LISTS.get(str(word_length), {}).get("answers"))


# 语气词表：游戏中的这类输入默认忽略，不报错不消耗次数
# （拉长形式如 ahhh / emmm 会先折叠连续重复字母再匹配此表）
INTERJECTIONS = {
    "ah", "oh", "eh", "hmm", "hm", "mmm", "mm", "umm", "um", "emm", "em",
    "err", "er", "erm", "uhh", "uh", "uhm", "aha", "aah", "ooh", "woah",
    "whoa", "wow", "oops", "ouch", "oof", "yikes", "yay", "yey", "woo",
    "woohoo", "wahoo", "geez", "sheesh", "phew", "tsk", "psst", "shh",
    "shhh", "shhhh", "haha", "hahaha", "hehe", "hehehe", "lol", "lmao",
    "rofl", "xd", "pfft", "hmph", "huh", "duh", "blah", "no", "yes", "ok",
    "yo",
}


def classify_input(word: str, word_length: int, pending: str = "") -> str:
    """分类一条游戏输入，决定它该怎么处理

    语气词默认忽略：语气词表命中，或折叠连续重复字母后
    （ahhh → ah，aaaa → a）命中语气词表 / 只剩单个字母。
    但若它恰好是本长度词库里的合法单词，玩家可能是认真在猜：
    第一次返回 confirm 让调用方提示确认，同一词再次出现才返回 guess。

    Returns:
        str: "guess"（正常猜测）/ "confirm"（疑似认真猜的语气词，提示再发一次）/
             "ignore"（纯语气词，静默忽略）
    """
    collapsed = "".join(k for k, _ in groupby(word))
    if word in INTERJECTIONS:
        repeated = True
    else:
        repeated = len(collapsed) == 1 or collapsed in INTERJECTIONS
    if not repeated:
        return "guess"
    if len(word) == word_length and word in _ALLOWED_SETS.get(word_length, set()):
        return "guess" if pending == word else "confirm"
    return "ignore"


def evaluate_guess(answer: str, guess: str) -> list:
    """按标准 Wordle 规则判定猜测单词每个字母的状态

    双遍处理重复字母：先标出全部绿格并统计剩余字母，
    再把猜出的多余字母按剩余数量标黄。

    Returns:
        list[int]: 每个字母的 TILE_GRAY / TILE_YELLOW / TILE_GREEN
    """
    states = [wordle_render.TILE_GRAY] * len(guess)
    remaining: dict = {}
    for index, (a_letter, g_letter) in enumerate(zip(answer, guess)):
        if g_letter == a_letter:
            states[index] = wordle_render.TILE_GREEN
        else:
            remaining[a_letter] = remaining.get(a_letter, 0) + 1
    for index, g_letter in enumerate(guess):
        if states[index] != wordle_render.TILE_GREEN and remaining.get(g_letter, 0) > 0:
            states[index] = wordle_render.TILE_YELLOW
            remaining[g_letter] -= 1
    return states


class Wordle(Game):
    def __init__(self, word_length: int = 5, max_times: int = 6) -> None:
        super().__init__(word_length=word_length, max_times=max_times)

    def before_starting(self, word_length: int, max_times: int):
        self.word_length = word_length
        self.max_times = max_times
        self.answer = ""
        self.guesses: list = []  # [(单词, [状态...]), ...]

    def start(self) -> str:
        """随机抽取答案单词并返回开场文案
        """
        answers = _WORD_LISTS[str(self.word_length)]["answers"]
        self.answer = random.choice(answers)
        return get_message("plugins", cmd_name, name, 'wordle_start',
            letters=self.word_length,
            max_times=self.max_times)

    def is_guessed(self, word):
        guesses_words = [s[0] for s in self.guesses]
        if word in guesses_words:
            return True
        return False

    def parse_game_step(self, guess_word: str) -> int:
        """校验并判定一次猜测，无效输入不消耗次数

        Returns:
            int: RESULT_WIN / RESULT_CONTINUE / RESULT_NO_TIMES /
                 RESULT_NOT_IN_LIST / RESULT_WRONG_LENGTH
        """
        super().parse_game_step()
        if len(self.guesses) >= self.max_times:
            return RESULT_NO_TIMES
        if len(guess_word) != self.word_length:
            return RESULT_WRONG_LENGTH
        if guess_word not in _ALLOWED_SETS.get(self.word_length, set()):
            return RESULT_NOT_IN_LIST
        if self.is_guessed(guess_word):
            return RESULT_GUESSED

        self.guesses.append((guess_word, evaluate_guess(self.answer, guess_word)))
        if guess_word == self.answer:
            return RESULT_WIN
        if len(self.guesses) >= self.max_times:
            return RESULT_NO_TIMES
        return RESULT_CONTINUE

    def calc_award(self, basic: int) -> int:
        """按词库规模、单词长度、表现与次数限制计算奖励，未猜中为 0

        - 词库规模因子：log2(该长度答案数) / log2(词库最大答案数)，
          该长度的可选单词越多越难命中；
        - 长度因子：字数 / 5，以标准 5 字母为基准，越长越难；
        - 表现因子：1 + (默认次数-已用次数) / 默认次数（下限 0.5），
          以标准限制（字数+1）衡量：猜得越快越高，拖得比标准限制
          还久则打折；
        - 次数限制因子：1 + max(0, 默认次数-限制次数) / 默认次数，
          限制比标准更紧时给加成，更宽松不加成。
        """
        if not self.guesses or self.guesses[-1][0] != self.answer:
            return 0
        answers = _WORD_LISTS.get(str(self.word_length), {}).get("answers") or []
        pools = [len(info.get("answers") or []) for info in _WORD_LISTS.values()
                 if isinstance(info, dict)]
        max_pool = max(pools) if pools else 0
        if len(answers) > 1 and max_pool > 1:
            pool_factor = math.log2(len(answers)) / math.log2(max_pool)
        else:
            pool_factor = 1.0
        default_times = self.word_length + 1
        used = len(self.guesses)
        slack_factor = max(0.5, 1 + (default_times - used) / default_times)
        limit_factor = 1 + max(0, default_times - self.max_times) / default_times
        award = int(basic * pool_factor * (self.word_length / 5) * slack_factor * limit_factor)
        return min(award, 512)


def definition_msg(word: str) -> str:
    """结束消息附带的词语解释文本，无对应释义时为空串"""
    definition = get_word_definition(word)
    if not definition:
        return ""
    return get_message("plugins", cmd_name, name, 'word_definition', definition=definition)


@user.limit(f"{cmd_name}_{name}", 1, "", TIMES_LIMIT, fails=lambda x: x['state'] != "OK", limit_func=limited)
# @permission(lambda sender: sender.is_privatechat, no_perm_result=return_state(f"{get_message('config', 'no_permission', permission='在私聊使用')}", "ERROR"), silent=True)
async def play_game(session: CommandSession, u: user.User, args: dict):
    start_guessing = False
    get_award_times_left = TIMES_LIMIT - user.get_limit_info(u, f"game_{name}")[1] - 1
    settings: dict = args

    try:
        word_length = int(settings.get("c", 5))
    except Exception as ex:
        return return_state(f"{get_message('plugins', cmd_name, name, 'arg_error', ex=ex)}", "ERROR")
    if not MIN_WORD_LENGTH <= word_length <= MAX_WORD_LENGTH:
        return return_state(f"{get_message('plugins', cmd_name, name, 'letters_out_of_range', min=MIN_WORD_LENGTH, max=MAX_WORD_LENGTH)}", "ERROR")
    if not has_words(word_length):
        return return_state(f"{get_message('plugins', cmd_name, name, 'word_list_missing')}", "ERROR")

    try:
        max_times = int(settings.get("t", word_length + 1))
    except Exception as ex:
        return return_state(f"{get_message('plugins', cmd_name, name, 'arg_error', ex=ex)}", "ERROR")
    if not 1 <= max_times <= MAX_TIMES:
        return return_state(f"{get_message('plugins', cmd_name, name, 'times_out_of_range', max_limit=MAX_TIMES)}", "ERROR")

    guess = Wordle(word_length, max_times)
    prefix = get_message("plugins", cmd_name, name, 'guess_prompt_prefix_default',
        start=get_message("plugins", cmd_name, name, 'cost_message', cost=game_meta['cost']) + guess.start(),
    )
    ask_to_guess = True
    pending_word = ""
    quit_inputs = ("!quit", "退出游戏", "退出", "!exit")
    while True:
        user_input = (await aget_session_msg(session, prompt=get_message("plugins", cmd_name, name, 'guess_prompt',
            prefix=prefix,
            quit_input=quit_inputs[0]) if ask_to_guess else None, can_use_command=False)).strip()
        if user_input.lower().strip() in quit_inputs:
            await send_session_msg(session, get_message("plugins", cmd_name, name, 'quit_message') if start_guessing else get_message("plugins", cmd_name, name, 'quit_message_not_start'))
            if start_guessing:
                return return_state(state="OK", data={
                    "limited": False,
                    "times_left": get_award_times_left,
                })
            u.add_coins(game_meta['cost'])
            return return_state(state="EXITED")
        word = user_input.lower().strip()
        if not word.isascii() or not word.isalpha():
            debug_msg("忽略")
            ask_to_guess = False
            if is_command(user_input):
                await send_session_msg(session, get_message("plugins", cmd_name, name, 'cmd_in_game', quit_input=quit_inputs[0]))
            continue
        action = classify_input(word, word_length, pending_word)
        if action == "ignore":
            debug_msg("忽略语气词")
            ask_to_guess = False
            continue
        if action == "confirm":
            pending_word = word
            ask_to_guess = False
            await send_session_msg(session, get_message("plugins", cmd_name, name, 'interjection_confirm', word=word))
            continue
        pending_word = ""
        ask_to_guess = True
        result = guess.parse_game_step(word)
        start_guessing = True
        if result == RESULT_WRONG_LENGTH:
            ask_to_guess = False
            await send_session_msg(session, get_message("plugins", cmd_name, name, 'wrong_length', letters=word_length))
            continue
        if result == RESULT_NOT_IN_LIST:
            ask_to_guess = False
            await send_session_msg(session, get_message("plugins", cmd_name, name, 'invalid_word'))
            continue
        if result == RESULT_GUESSED:
            ask_to_guess = False
            await send_session_msg(session, get_message("plugins", cmd_name, name, 'word_guessed'))
            continue
        try:
            width, height = wordle_render.board_image_size(word_length, max_times)
            board_html = wordle_render.render_board_html(word_length, max_times, guess.guesses)
            board = await image_msg(await get_html_image_async(board_html, height=height, width=width, scale=2))
        except Exception as ex:
            logger.warning(f"wordle 棋盘渲染失败: {ex!r}")
            u.add_coins(game_meta['cost'])
            return return_state(f"{get_message('plugins', cmd_name, name, 'render_error', ex=ex)}", "ERROR")
        # await send_session_msg(session, board)
        result_msg = ""
        if result == RESULT_NO_TIMES:
            # await send_session_msg(session, )
            await send_session_msg(session, board + get_message("plugins", cmd_name, name, 'game_over', answer=guess.answer) + definition_msg(guess.answer))
            return return_state(state="OK", data={
                # "message": board + get_message("plugins", cmd_name, name, 'game_over', answer=guess.answer),
                "award": guess.calc_award(BASIC_AWARD),
                "limited": False,
                "times_left": get_award_times_left,
            })
        if result == RESULT_WIN:
            await send_session_msg(session, board + get_message("plugins", cmd_name, name, 'win_message', answer=guess.answer) + definition_msg(guess.answer))
            # result_msg = board + get_message("plugins", cmd_name, name, 'win_message', answer=guess.answer)
            break
        prefix = board + get_message("plugins", cmd_name, name, 'guess_prompt_prefix_default',
            start=get_message("plugins", cmd_name, name, 'remaining_times', times=guess.max_times - len(guess.guesses)),
        )
    return return_state(data={
        # "message": result_msg,
        "award": guess.calc_award(BASIC_AWARD),
        "limited": False,
        "times_left": get_award_times_left
    })
