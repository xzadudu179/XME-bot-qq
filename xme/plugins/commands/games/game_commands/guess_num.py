from nonebot import CommandSession
from xme.plugins.commands.games.play import cmd_name
from .game import Game
from xme.xmetools.bottools import permission
from xme.xmetools.cmdtools import get_cmd_by_alias
from xme.plugins.commands.xme_user.classes import user
from xme.plugins.commands.xme_user.classes.user import coin_name, coin_pronoun
from character import get_message
import random
random.seed()
import math
from xme.xmetools.msgtools import send_session_msg, aget_session_msg

TIMES_LIMIT = 10
name = 'guess'
game_meta = {
    "name": name,
    "desc": get_message("plugins", cmd_name, name, 'desc'),
    # "desc": "猜数字游戏",
    "introduction": get_message("plugins", cmd_name, name, 'introduction',  times_limit=TIMES_LIMIT),
    # "introduction": "指定一个数字范围并且生成一个随机数字，然后不断猜测直到猜中随机的数字。\n每次猜测时会说目标数字比猜测的数字大还是小",
    "args": {
        "r": get_message("plugins", cmd_name, name, 'arg_range'),
        # "r": "数字范围 (r=范围开始~范围结束)",
        "t": get_message("plugins", cmd_name, name, 'arg_times_limit'),
        # "t": "猜测次数限制 (t=次数限制)"
    },
    "cost": 2,
    "times_left_message": get_message("plugins", cmd_name, name, 'times_left', times_left='{times_left}'),
    "limited_message": get_message("plugins", cmd_name, name, 'limited'),
    "award_message": get_message("plugins", cmd_name, name, 'award', award="{award}", coins_left='{coins_left}'),
    "no_award_message": get_message("plugins", cmd_name, name, 'no_award'),
}

class GuessNum(Game):
    def __init__(self, number_range=(0, 100), max_guessing_times=7) -> None:
        super().__init__(number_range=number_range, max_guessing_times=max_guessing_times)

    def before_starting(self, number_range, max_guessing_times):
        self.number_range = number_range
        self.answer_num = -1
        self.guessing_times = 0
        self.max_guessing_times = max_guessing_times
        # print("准备好开始了")

    def start(self):
        """游戏开始的方法
        """
        # self.starting = True
        self.answer_num = random.randint(self.number_range[0], self.number_range[1])
        # print("答案:", self.answer_num)
        self.guessing_times = 0
        return get_message("plugins", cmd_name, name, 'guess_start',
            max_guessing_times=self.max_guessing_times,
            number_min=self.number_range[0],
            number_max=self.number_range[1])

    def parse_game_step(self, guess):
        """处理游戏的每一步的方法
        """
        super().parse_game_step()
        self.guessing_times += 1
        if guess == self.answer_num:
            return 0
        if self.guessing_times >= self.max_guessing_times:
            return 2
        if guess > self.answer_num:
            return 1
        elif guess < self.answer_num:
            return -1
        return 0

def return_state(message: str="", state: str="OK", data: dict={}) -> str:
    return {
        "state": state,
        "message": message,
        "data": data
    }

def calc_award(basic, game: GuessNum):
    range_len = game.number_range[1] - game.number_range[0]
    theorical_times = math.log2(range_len)
    times_addition = 2 ** abs(theorical_times - game.guessing_times) // 20
    times_addition = -times_addition if theorical_times - game.guessing_times < 0 else times_addition
    award = int(basic + times_addition + min(2 * theorical_times, theorical_times ** 2))
    if game.guessing_times >= range_len:
        award = 0
    award = min(award, 1024)
    return int(max(0, award) / 2)


async def limited(func, session: CommandSession, user: user.User, *args, **kwargs):
    print(args, kwargs)
    result = await func(session, user, *args, **kwargs)
    print(result)
    if result['state'] == 'OK':
        result['data']['limited'] = True
    return result

@user.limit(f"{cmd_name}_{name}", 1, "", TIMES_LIMIT, fails=lambda x: x['state'] != "OK", limit_func=limited)
@permission(lambda sender: sender.is_privatechat, no_perm_result=return_state(f"{get_message('config', 'no_permission', permission='在私聊使用')}", "ERROR"), silent=True)
async def play_game(session: CommandSession, u: user.User, args: dict):
    BASIC_AWARD = 25
    MAX_RANGE = 34359738368
    MAX_LIMIT = 35
    start_guessing = False
    get_award_times_left = TIMES_LIMIT - user.get_limit_info(u, f"game_{name}")[1] - 1
    settings: dict = args

    try:
        num_range = (int(settings.get("r", "0~100").split("~")[0]), int(settings.get("r", "0~100").split("~")[1]))
    except Exception as ex:
        return return_state(f"{get_message('plugins', cmd_name, name, 'range_error', ex=ex)}", "ERROR")

    default_times_limit = min(int(math.log2(sum([abs(num) for num in num_range])) + 2), MAX_LIMIT)

    try:
        times_limit = x if (x:=int(settings.get("t", default_times_limit))) > 0 else default_times_limit
    except Exception as ex:
        return return_state(f"{get_message('plugins', cmd_name, name, 'times_limit_error', ex=ex)}", "ERROR")

    if abs(num_range[0]) > MAX_RANGE or abs(num_range[1]) > MAX_RANGE:
        return return_state(f"{get_message('plugins', cmd_name, name, 'range_out_of_range', max_range=format(MAX_RANGE, ','))}", "ERROR")
    elif num_range[0] > num_range[1]:
        num_range[0], num_range[1] = num_range[1], num_range[0]
    elif num_range[0] == num_range[1]:
        return return_state(f"{get_message('plugins', cmd_name, name, 'range_equals')}", "ERROR")
    if times_limit > MAX_LIMIT:
        return return_state(f"{get_message('plugins', cmd_name, name, 'times_out_of_range', max_limit=format(MAX_LIMIT, ','))}", "ERROR")

    guess = GuessNum(num_range, times_limit)
    prefix = get_message("plugins", cmd_name, name, 'guess_prompt_prefix_default',
        start=get_message("plugins", cmd_name, name, 'cost_message', cost=game_meta['cost'],  ) + guess.start(),
    )
    # prefix = f"{guess.start()}\n请"
    ask_to_guess = True
    quit_inputs = ("quit", "退出游戏", "退出", "exit")
    while True:
        user_input = (await aget_session_msg(session, prompt=f'[CQ:at,qq={session.event.user_id}] ' + get_message("plugins", cmd_name, name, 'guess_prompt',
            prefix=prefix,
            quit_input=quit_inputs[0]) if ask_to_guess else "")).strip()
        # 退出游戏
        if user_input.lower().strip() in quit_inputs:
            await send_session_msg(session, get_message("plugins", cmd_name, name, 'quit_message') if start_guessing else get_message("plugins", cmd_name, name, 'quit_message_not_start', ))
            # await send_msg(session, f" 退出游戏啦 ovo")
            if start_guessing:
                return return_state(state="OK", data={
                    "limited": False,
                    "times_left": get_award_times_left,
                })
            return return_state(state="EXITED")
        # ----------------
        try:
            num = int(user_input)
            ask_to_guess = True
        except:
            print("忽略")
            ask_to_guess = False
            if get_cmd_by_alias(user_input) != False:
                await send_session_msg(session, get_message("plugins", cmd_name, name, 'cmd_in_game'))
            continue
        result = guess.parse_game_step(num)
        start_guessing = True
        if result == 2:
            await send_session_msg(session, get_message("plugins", cmd_name, name, 'game_over', answer=format(guess.answer_num, ',')))
            # await send_msg(session, f" 你的猜测次数用完啦，正确答案应该是 {guess.answer_num} ovo")
            return return_state(state="OK", data={
                    "limited": False,
                    "times_left": get_award_times_left,
            })
        message = get_message("plugins", cmd_name, name, 'guess_result',
            num=format(num, ','),
            result= get_message("plugins", cmd_name, name, 'num_too_big_result') if
                    result == 1 else
                    get_message("plugins", cmd_name, name, 'num_too_small_result') if
                    result == -1 else
                    get_message("plugins", cmd_name, name, 'num_right_result')
        )
        # message = f"{num} {'大啦' if result == 1 else '小啦' if result == -1 else '正确~'}"
        if result == 0:
            await send_session_msg(session, message)
            if times_limit == default_times_limit and num_range == (0, 100) and guess.guessing_times == 1 and get_award_times_left >= 0:
                await u.achieve_achievement(session, "One Shot")
            break
        message += f"\n" + get_message("plugins", cmd_name, name, 'remaining_times', times=guess.max_guessing_times - guess.guessing_times)
        prefix = get_message("plugins", cmd_name, name, 'guess_prompt_prefix_default',
            start=message,
        )
        # prefix = f"{message}\n请"
    return return_state(data={
        "award": calc_award(BASIC_AWARD, guess),
        "limited": False,
        "times_left": get_award_times_left
    })