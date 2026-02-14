# from .classes.player import Player
# import random
# player = Player()
TOOLS = [
    {
        "name": "备用气罐",
        "desc": "首次氧气耗尽时增加 100 氧气",
        # "apply_message": "你的备用气罐激活了！",
        "apply_condition": lambda player: player.depth > 0 and player.oxygen.value <= 0,
        "apply_times": 1,
        "apply_event": {
            "type": "normal",
            "descs": ["你的备用气罐激活了！", "备用气罐激活了！"],
            "changes": {
                "oxygen": {
                    "change": lambda: 100,
                    "type": "+",
                    "custom": False,
                }
            }
        },
        "price": 300,
    }
]