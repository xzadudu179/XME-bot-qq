
from .classes.player import SeekRegion
# import random
# player = Player()
TOOLS = [
    {
        "name": "无依无靠",
        "desc": "失去了外部信息的帮助，你只能靠自己了...（收益 *1.6）",
        "apply_condition": lambda player: True,
        "apply_times": 1,
        "apply_event": {
            "type": "normal",
            "descs": ["我们开始吧...", "可以开始了..."],
            "changes": {
                "hardcore": {
                    "change": lambda: 1,
                    "type": "=",
                    "custom": False,
                },
                "depth": {
                    "change": lambda: 100,
                    "type": "=",
                    "custom": False,
                },
            }
        },
        "price": 100,
    },
    {
        "name": "备用气罐",
        "desc": "增加 100 点氧气上限",
        "apply_condition": lambda player: True,
        "apply_times": 1,
        "apply_event": {
            "type": "normal",
            "descs": ["你装备上了备用的氧气罐。", "你戴上了备用的氧气罐"],
            "changes": {
                "oxygen": {
                        "change": lambda v: v.change_max(lambda x: x + 100),
                        "return": lambda v: v.max_value,
                        "return_msg": "最大{name} = {value}",
                        "custom": True,
                        "assign": False,
                    },
            }
        },
        "price": 150,
    },
    {
        "name": "星币回收机",
        "desc": "减少 40% 深度惩罚",
        "apply_condition": lambda player: True,
        "apply_times": 1,
        "apply_event": {
            "type": "normal",
            "descs": ["星币回收机启动了！"],
            "changes": {
                "depth_gain_ratio": {
                    "change": lambda: 40,
                    "type": "-",
                    "custom": False,
                },
            },
        },
        "price": 280,
    },
    {
        "name": "次元传送器",
        "desc": "减少 90% 深度惩罚",
        "apply_condition": lambda player: True,
        "apply_times": 1,
        "apply_event": {
            "type": "normal",
            "descs": ["传送器启动了！你现在基本可以放心探险了"],
            "changes": {
                "depth_gain_ratio": {
                    "change": lambda: 90,
                    "type": "-",
                    "custom": False,
                },
            },
        },
        "price": 960,
    },
    {
        "name": "深潜装甲",
        "desc": "战斗力增加5、最大战斗力增加7、生命值增加50",
        "apply_condition": lambda player: True,
        "apply_times": 1,
        "apply_event": {
            "type": "normal",
            "descs": ["你穿戴上了深潜装甲..."],
            "changes": {
                "combat": [{
                    "change": lambda: 5,
                    "type": "+",
                    "custom": False,
                    }, {
                    "change": lambda v: v.change_max(lambda x: x + 7),
                    "return": lambda v: v.max_value,
                    "return_msg": "最大{name} = {value}",
                    "custom": True,
                    "assign": False,
                    },
                ],
                "health": [{
                        "change": lambda v: v.change_max(lambda x: x + 50),
                        "return": lambda v: v.max_value,
                        "return_msg": "最大{name} = {value}",
                        "custom": True,
                        "assign": False,
                    },
                    {
                        "change": lambda: 50,
                        "type": "+",
                        "custom": False,
                    },
                ],
            },
        },
        "price": 300,
    },
    {
        "name": "心灵控制器",
        "desc": "精神力+5、最大精神力+5、san 值+50",
        "apply_condition": lambda player: True,
        "apply_times": 1,
        "apply_event": {
            "type": "normal",
            "descs": ["你携带了心灵控制器出发..."],
            "changes": {
                "mental": [{
                    "change": lambda: 5,
                    "type": "+",
                    "custom": False,
                    }, {
                    "change": lambda v: v.change_max(lambda x: x + 5),
                    "return": lambda v: v.max_value,
                    "return_msg": "最大{name} = {value}",
                    "custom": True,
                    "assign": False,
                    },
                ],
                "san": [{
                        "change": lambda v: v.change_max(lambda x: x + 50),
                        "return": lambda v: v.max_value,
                        "return_msg": "最大{name} = {value}",
                        "custom": True,
                        "assign": False,
                    },
                    {
                        "change": lambda: 50,
                        "type": "+",
                        "custom": False,
                    },
                ],
            },
        },
        "price": 300,
    },
    {
        "name": "物品扫描仪",
        "desc": "洞察力+5、最大洞察力+5",
        "apply_condition": lambda player: True,
        "apply_times": 1,
        "apply_event": {
            "type": "normal",
            "descs": ["你带上了物品扫描仪..."],
            "changes": {
                "insight": [{
                    "change": lambda: 5,
                    "type": "+",
                    "custom": False,
                    }, {
                    "change": lambda v: v.change_max(lambda x: x + 5),
                    "return": lambda v: v.max_value,
                    "return_msg": "最大{name} = {value}",
                    "custom": True,
                    "assign": False,
                    },
                ],
            },
        },
        "price": 500,
    },
    {
        "name": "应急维生装置",
        "desc": "在水下首次耗尽行动机会时增加 3 次行动机会",
        "apply_condition": lambda player: player.depth > 0 and player.chance <= 0,
        "apply_times": 1,
        "apply_event": {
            "type": "normal",
            "descs": ["应急维生装置启动了！你多出了三次机会"],
            "changes": {
                "chance": {
                    "change": lambda: 3,
                    "type": "+",
                    "custom": False,
                },
            },
        },
        "price": 350,
    },
    {
        "name": "探险精神",
        "desc": "增加 10 次初始行动机会",
        "apply_condition": lambda player: True,
        "apply_times": 1,
        "apply_event": {
            "type": "normal",
            "descs": ["你充满了探险的决心...?", "你下定了决心探险。"],
            "changes": {
                "chance": {
                    "change": lambda: 10,
                    "type": "+",
                    "custom": False,
                },
            },
        },
        "price": 780,
    },
    {
        "name": "快速探险",
        "desc": "前进与返回最高步数 + 10",
        "apply_condition": lambda player: True,
        "apply_times": 1,
        "apply_event": {
            "type": "normal",
            "descs": ["你知道这趟旅途需要速战速决。"],
            "changes": {
                "seek_max_steps": {
                    "change": lambda: 10,
                    "type": "+",
                    "custom": False,
                },
                "back_max_steps": {
                    "change": lambda: 10,
                    "type": "+",
                    "custom": False,
                },
            },
        },
        "price": 550,
    },
    {
        "name": "深渊传送器",
        "desc": "你将从 1000 d.n. 处开始下潜...",
        "apply_condition": lambda player: True,
        "apply_times": 1,
        "apply_event": {
            "type": "normal",
            "descs": ["深渊传送器启动了...", "你来到了一个神秘的地方..."],
            "changes": {
                "depth": {
                    "change": lambda: 1000,
                    "type": "=",
                    "custom": False,
                },
            },
            "region_change": lambda last: SeekRegion.ABYSS,
        },
        "price": 600,
    },
]