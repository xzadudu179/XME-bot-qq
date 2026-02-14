from .event import Event
from typing import Callable
# import random

# 道具
class Tool:
    from .player import Player
    def __init__(
            self,
            name: str,
            desc: str,
            player: Player,
            changes: dict,
            apply_event : dict,
            apply_condition: Callable,
            apply_times: int = -1,
            region_change: Callable | None = None,
        ):
        self.name = name
        self.desc = desc
        # self.apply_message = apply_message
        self.cost
        self.player = player
        self.changes = changes
        self.region_change = region_change
        # 激活条件
        self.apply_condition = apply_condition
        self.apply_event = apply_event
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


    def apply(self, e: Event) -> str:
        if self.apply_times > 0:
            self.apply_times -= 1
        event_type = self.apply_event.get("type", "normal")
        match event_type:
            case "normal":
                return e.build_normal_event(self.apply_event, html=True)
            case "dice":
                return e.build_dice_event(self.apply_event, self.player.region.value, html=True)
            case _:
                raise ValueError(f"道具不支持 normal 和 dice 之外的事件: {event_type}")

    def build_tool(tool_dict: dict):
        return Tool(
            name=tool_dict["name"],
            desc=tool_dict["desc"],
            apply_condition=tool_dict["apply_condition"],
            apply_times=tool_dict["apply_times"],
            region_change=tool_dict.get("region_change", None)
        )