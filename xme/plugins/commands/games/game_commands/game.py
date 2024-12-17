from abc import ABC, abstractmethod

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