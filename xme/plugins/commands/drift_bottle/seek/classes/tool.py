from .event import Event
from typing import Callable
# import random

# 道具
class Tool:
    from .player import Player
    def __init__(self, name: str, desc: str, apply_message: str, player: Player, changes: dict, apply_condition: Callable, apply_times: int = -1, region_change: Callable | None = None):
        self.name = name
        self.desc = desc
        self.apply_message = apply_message
        self.cost
        self.player = player
        self.changes = changes
        self.region_change = region_change
        # 激活条件
        self.apply_condition = apply_condition
        # 可用次数，-1 为无限
        self.apply_times = apply_times

    def __str__(self):
        return f"{self.name}: {self.desc}"

    def can_apply(self) -> bool:
        if self.apply_times < 1 and self.apply_times != -1:
            return False
        # 验证条件
        if self.apply_condition(self.player):
            return True
        return False


    def apply_event(self, e: Event) -> str:
        if self.apply_times > 0:
            self.apply_times -= 1
            # f"道具 [{self.name}] 激活：{self.apply_message}", self.changes, self.region_change
        return e.build_normal_event({
            "descs": [self.apply_message],
            "changes": {
                "coins": {
                    "change": lambda: 100,
                    "type": "+",
                    "custom": False,
                }
            }
        }, html=True)

    def build_tool(tool_dict: dict):
        return Tool(
            name=tool_dict["name"],
            desc=tool_dict["desc"],
            apply_message=tool_dict["desc"],
            apply_condition=tool_dict["apply_condition"],
            apply_times=tool_dict["apply_times"],
            region_change=tool_dict.get("region_change", None)
        )