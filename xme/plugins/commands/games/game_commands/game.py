from abc import ABC, abstractmethod
from nonebot import CommandSession
from xme.plugins.commands.xme_user.classes import user


def return_state(message: str = "", state: str = "OK", data: dict = {}) -> dict:
    """构造 play_game 的标准返回值

    Args:
        message (str): 结束时附带的消息
        state (str): 游戏状态 OK / ERROR / EXITED
        data (dict): 结算数据，如 award / limited / times_left
    """
    return {
        "state": state,
        "message": message,
        "data": data
    }


async def limited(func, session: CommandSession, user: user.User, *args, **kwargs):
    """达到每日奖励次数上限后仍可游玩，把结果标记为 limited 让结算跳过发奖"""
    result = await func(session, user, *args, **kwargs)
    if result['state'] == 'OK':
        result['data']['limited'] = True
    return result


# xme 的游戏
class Game(ABC):
    def __init__(self, **kwargs) -> None:
        self.starting = False
        self.before_starting(**kwargs)

    @abstractmethod
    def start(self) -> ...:
        """游戏开始的方法
        """
        ...

    @abstractmethod
    def before_starting(self) -> ...:
        """游戏开始前的方法
        """
        ...

    @abstractmethod
    def parse_game_step(self) -> ...:
        """处理游戏的每一步的方法
        """
        if not self.starting:
            return
        ...

    @abstractmethod
    def calc_award(self, basic: int) -> int:
        """根据本局游戏数据与基础奖励计算应得的星币数
        """
        ...
