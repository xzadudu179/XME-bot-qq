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
            price: int,
            apply_event : dict,
            apply_condition: Callable,
            apply_times: int = -1,
        ):
        self.name = name
        self.desc = desc
        # self.apply_message = apply_message
        self.price = price
        self.player = player
        # 激活条件
        self.apply_condition = apply_condition
        self.apply_event = apply_event
        # 可用次数，-1 为无限
        self.apply_times = apply_times

    def __str__(self):
        return f"(${self.price}) {self.name}: {self.desc}"

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
                return e.build_normal_event(self.apply_event, html=True, is_tool=True)
            case "dice":
                return e.build_dice_event(self.apply_event, self.player.region.value, html=True, is_tool=True)
            case _:
                raise ValueError(f"道具不支持 normal 和 dice 之外的事件: {event_type}")

    def build_tool(tool_dict: dict, player):
        return Tool(
            name=tool_dict["name"],
            desc=tool_dict["desc"],
            price=tool_dict.get("price", 0),
            player=player,
            apply_event=tool_dict["apply_event"],
            apply_condition=tool_dict["apply_condition"],
            apply_times=tool_dict["apply_times"],
        )