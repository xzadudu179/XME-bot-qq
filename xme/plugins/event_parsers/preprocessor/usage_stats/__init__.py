from xme.xmetools.dbtools import DATABASE
from xme.xmetools.timetools import get_time_now, get_time_period

class CmdUsage:
    def __init__(self, cmd_name: str, from_user: int, call_time: str):
        pass

    @classmethod
    def from_dict(data: dict):
        ...

    @classmethod
    def get_table_name(cls):
        return CmdUsage.__name__

    def to_dict(self):
        ...