from nonebot import CommandSession
from xme.plugins.commands.games.play import cmd_name
from .game import Game
from xme.xmetools.command_tools import get_cmd_by_alias
from xme.plugins.commands.user.classes import xme_user
from xme.plugins.commands.user.classes.xme_user import coin_name, coin_pronoun
from character import get_message
import random
import math
from xme.xmetools.command_tools import send_cmd_msg

TIMES_LIMIT = 5
name = 'guess'
game_meta = {
    "name": name,
    "desc": get_message(cmd_name, name, 'desc'),
    # "desc": "猜数字游戏",
    "introduction": get_message(cmd_name, name, 'introduction', coin_name=coin_name, times_limit=TIMES_LIMIT),
    # "introduction": "指定一个数字范围并且生成一个随机数字，然后不断猜测直到猜中随机的数字。\n每次猜测时会说目标数字比猜测的数字大还是小",
    "args": {
        "r": get_message(cmd_name, name, 'arg_range'),
        # "r": "数字范围 (r=范围开始~范围结束)",
        "t": get_message(cmd_name, name, 'arg_times_limit'),
        # "t": "猜测次数限制 (t=次数限制)"
    },
    "cost": 2,
    "times_left_message": get_message(cmd_name, name, 'times_left', times_left='{times_left}'),
    "limited_message": get_message(cmd_name, name, 'limited'),
    "award_message": get_message(cmd_name, name, 'award', award="{award}", coins_left='{coins_left}', coin_name='{coin_name}', coin_pronoun='{coin_pronoun}'),
    "no_award_message": get_message(cmd_name, name, 'no_award', coin_name='{coin_name}'),
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
        self.guessing_times = 0
        return get_message(cmd_name, name, 'guess_start',
            max_guessing_times=self.max_guessing_times,
            number_min=self.number_range[0],
            number_max=self.number_range[1])
        # return f"游戏开始~ 你需要在 {self.max_guessing_times} 次尝试内猜出一个范围 {self.number_range[0]} ~ {self.number_range[1]} 的整数！"

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

    # def determine_win(self, step_state) -> bool:
    #     """判断游戏状态
    #     """
    #     if step_state == 0:
    #         self.start = False
    #         return True
    #     return False


def return_state(message: str="", state: str="OK", data: dict={}) -> str:
    return {
            "state": state,
            "message": message,
            "data": data
        }

def calc_award(basic, game: GuessNum):
    range_len = sum([abs(num) for num in game.number_range]) + 1
    theorical_times = math.log2(range_len)
    times_addition = 2 ** abs(theorical_times - game.guessing_times)
    times_addition = -times_addition if theorical_times - game.guessing_times < 0 else times_addition
    award = int(basic + times_addition + min(2 * theorical_times, theorical_times ** 2))
    if game.guessing_times >= range_len:
        award = 0
    award = min(award, 2048)
    return int(max(0, award) / 2)


async def limited(func, session: CommandSession, user: xme_user.User, *args, **kwargs):
    print(args, kwargs)
    result = await func(session, user, *args, **kwargs)
    print(result)
    if result['state'] == 'OK':
        result['data']['limited'] = True
    return result

@xme_user.limit(f"{cmd_name}_{name}", 1, "", TIMES_LIMIT, fails=lambda x: x['state'] != "OK", limit_func=limited)
async def play_game(session: CommandSession, user: xme_user.User, args: dict):
    BASIC_AWARD = 10
    MAX_RANGE = 34359738368
    MAX_LIMIT = 35
    start_guessing = False
    get_award_times_left = TIMES_LIMIT - xme_user.get_limit_info(user, f"game_{name}")[1] - 1
    # print(TIMES_LIMIT, xme_user.get_limit_info(user, f"game_{name}")[1])
    settings: dict = args
    try:
        num_range = (int(settings.get("r", "0~100").split("~")[0]), int(settings.get("r", "0~100").split("~")[1]))
    except Exception as ex:
        return return_state(f"{get_message(cmd_name, name, 'range_error', ex=ex)}", "ERROR")
        # return return_state(f" 数字范围解析出现错误，请确定你写的符合格式 (r=范围开始(整数)~范围结束(整数)) 哦 uwu\n{ex}", "ERROR")
    default_times_limit = min(int(math.log2(sum([abs(num) for num in num_range])) + 2), MAX_LIMIT)
    try:
        times_limit = x if (x:=int(settings.get("t", default_times_limit))) > 0 else default_times_limit
    except Exception as ex:
        return return_state(f"{get_message(cmd_name, name, 'times_limit_error', ex=ex)}", "ERROR")
        # return return_state(f" 猜测次数限制解析出现错误，请确定你写的是整数哦 uwu\n{ex}", "ERROR")

    if abs(num_range[0]) > MAX_RANGE or abs(num_range[1]) > MAX_RANGE:
        return return_state(f"{get_message(cmd_name, name, 'range_out_of_range', max_range=format(MAX_RANGE, ','))}", "ERROR")
        # return return_state(f" 数字范围不能大于或小于 {MAX_RANGE} 哦 uwu", "ERROR")
    elif num_range[0] > num_range[1]:
        # 交换一下
        num_range[0], num_range[1] = num_range[1], num_range[0]
        # return return_state(f" 数字范围开始不能比结束大或相同哦 uwu", "ERROR")
    elif num_range[0] == num_range[1]:
        return return_state(f"{get_message(cmd_name, name, 'range_equals')}", "ERROR")
        # return return_state(f" 数字范围不能是相同的哦 uwu", "ERROR")
    if times_limit > MAX_LIMIT:
        return return_state(f"{get_message(cmd_name, name, 'times_out_of_range', max_limit=format(MAX_LIMIT, ','))}", "ERROR")
        # return return_state(f" 猜测次数不能大于 {MAX_LIMIT} 哦 uwu", "ERROR")
    guess = GuessNum(num_range, times_limit)
    # await send_msg(session, guess.start())
    prefix = get_message(cmd_name, name, 'guess_prompt_prefix_default',
        start=get_message(cmd_name, name, 'cost_message', cost=game_meta['cost'], coin_name=coin_name, coin_pronoun=coin_pronoun,) + guess.start(),
    )
    # prefix = f"{guess.start()}\n请"
    ask_to_guess = True
    quit_inputs = ("quit", "退出游戏", "退出", "exit")
    while True:
        user_input = (await session.aget(prompt=f'[CQ:at,qq={session.event.user_id}] ' + get_message(cmd_name, name, 'guess_prompt',
            prefix=prefix,
            quit_input=quit_inputs[0]) if ask_to_guess else "")).strip()
        # user_input = (await session.aget(prompt=f" {prefix}输入你要猜的数字吧~ 或输入 quit 退出" if ask_to_guess else "")).strip()
        if user_input.lower().strip() in quit_inputs:
            await send_cmd_msg(session, get_message(cmd_name, name, 'quit_message') if start_guessing else get_message(cmd_name, name, 'quit_message_not_start', coin_name=coin_name))
            # await send_msg(session, f" 退出游戏啦 ovo")
            if start_guessing:
                return return_state(state="OK", data={
                    "limited": False,
                    "times_left": get_award_times_left,
                })
            return return_state(state="EXITED")
        try:
            num = int(user_input)
            ask_to_guess = True
        except:
            # prefix = f"转换整数出错，请确定你输入的是整数哦 uwu\n"
            # prefix += "请重新"
            print("忽略")
            ask_to_guess = False
            if get_cmd_by_alias(user_input) != False:
                await send_cmd_msg(session, get_message(cmd_name, name, 'cmd_in_game'))
                # await send_msg(session, f" 你还在游戏中哦，不能执行指令 uwu")
            continue
        result = guess.parse_game_step(num)
        start_guessing = True
        if result == 2:
            await send_cmd_msg(session, get_message(cmd_name, name, 'game_over', answer=format(guess.answer_num, ',')))
            # await send_msg(session, f" 你的猜测次数用完啦，正确答案应该是 {guess.answer_num} ovo")
            return return_state(state="OK", data={
                    "limited": False,
                    "times_left": get_award_times_left,
            })
        message = get_message(cmd_name, name, 'guess_result',
            num=format(num, ','),
            result= get_message(cmd_name, name, 'num_too_big_result') if
                    result == 1 else
                    get_message(cmd_name, name, 'num_too_small_result') if
                    result == -1 else
                    get_message(cmd_name, name, 'num_right_result')
        )
        # message = f"{num} {'大啦' if result == 1 else '小啦' if result == -1 else '正确~'}"
        if result == 0:
            await send_cmd_msg(session, message)
            break
        message += f"\n" + get_message(cmd_name, name, 'remaining_times', times=guess.max_guessing_times - guess.guessing_times)
        # message += f"\n你还可以猜 {guess.max_guessing_times - guess.guessing_times} 次数字ovo"
        # await send_msg(session, message)
        prefix = get_message(cmd_name, name, 'guess_prompt_prefix_default',
            start=message,
        )
        # prefix = f"{message}\n请"
    return return_state(data={
        "award": calc_award(BASIC_AWARD, guess),
        "limited": False,
        "times_left": get_award_times_left
    })