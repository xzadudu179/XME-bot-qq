from abc import ABC, abstractmethod
from nonebot import CommandSession
from xme.plugins.commands.xme_user.classes.user import User

class MachineEvent(ABC):
    def __init__(self, session: CommandSession, user: User):
        self.sesssion = session
        self.user = user
        pass

    @abstractmethod
    def create(self):
        ...


class NormalMachineEvent(MachineEvent):
    def __init__(self):
        super().__init__()

    def create(self):
        return super().create()