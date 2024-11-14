from nonebot import CommandSession
from .game import Game
from xme.xmetools.command_tools import find_command_by_args
import random

game_meta = {
    "name": "guess",
    "desc": "猜数字游戏",
    "introduction": "指定一个数字范围并且生成一个随机数字，然后不断猜测直到猜中随机的数字。\n每次猜测时会说目标数字比猜测的数字大还是小",
    "args": {
        "r": "数字范围 (r=范围开始~范围结束)",
        "t": "猜测次数限制 (t=次数限制)"
    }
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
        return f"游戏开始~ 你需要在 {self.max_guessing_times} 次尝试内猜出一个范围 {self.number_range[0]} ~ {self.number_range[1]} 的整数！"

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

async def play_game(session: CommandSession, args: dict):
    settings: dict = args
    try:
        times_limit = x if (x:=int(settings.get("t", 7))) > 0 else 7
    except Exception as ex:
        # await session.send(f"转换整数出错，请确定你输入的是正确的整数哦 uwu\n")
        return return_state(f"[CQ:at,qq={session.event.user_id}] 猜测次数限制解析出现错误，请确定你写的是整数哦 uwu\n{ex}", "ERROR")
    try:
        num_range = (int(settings.get("r", "0~100").split("~")[0]), int(settings.get("r", "0~100").split("~")[1]))
    except Exception as ex:
        # await session.send(f"转换整数出错，请确定你输入的是正确的整数哦 uwu\n")
        return return_state(f"[CQ:at,qq={session.event.user_id}] 数字范围解析出现错误，请确定你写的符合格式 (r=范围开始(整数)~范围结束(整数)) 哦 uwu\n{ex}", "ERROR")

    if num_range[0] >= 1000000000 or num_range[0] >= 1000000000:
        return return_state(f"[CQ:at,qq={session.event.user_id}] 数字范围不能大于 1000000000 哦 uwu", "ERROR")
    elif num_range[0] >= num_range[1]:
        # await session.send(f"[CQ:at,qq={session.event.user_id}] 数字范围不能是")
        return return_state(f"[CQ:at,qq={session.event.user_id}] 数字范围开始不能比结束大或相同哦 uwu", "ERROR")
    if times_limit > 1000:
        return return_state(f"[CQ:at,qq={session.event.user_id}] 猜测次数不能大于 1000 哦 uwu", "ERROR")
    guess = GuessNum(num_range, times_limit)
    # await session.send(guess.start())
    prefix = f"{guess.start()}\n请"
    ask_to_guess = True
    while True:
        user_input = (await session.aget(prompt=f"[CQ:at,qq={session.event.user_id}] {prefix}输入你要猜的数字吧~ 或输入 quit 退出" if ask_to_guess else "")).strip()
        if user_input.lower() in ("quit", "退出游戏", "退出", "exit"):
            await session.send(f"[CQ:at,qq={session.event.user_id}] 退出游戏啦 ovo")
            break
        try:
            num = int(user_input)
            ask_to_guess = True
        except:
            # prefix = f"转换整数出错，请确定你输入的是整数哦 uwu\n"
            # prefix += "请重新"
            ask_to_guess = False
            if find_command_by_args(user_input) != False:
                await session.send(f"[CQ:at,qq={session.event.user_id}] 你还在游戏中哦，不能执行指令 uwu")
            continue
        result = guess.parse_game_step(num)
        if result == 2:
            await session.send(f"[CQ:at,qq={session.event.user_id}] 你的猜测次数用完啦，正确答案应该是 {guess.answer_num} ovo")
            break
        message = f"{num} {'大啦' if result == 1 else '小啦' if result == -1 else '正确~'}"
        if result == 0:
            await session.send(message)
            break
        message += f"\n你还可以猜 {guess.max_guessing_times - guess.guessing_times} 次数字ovo"
        # await session.send(message)
        prefix = f"{message}\n请"
    return return_state()