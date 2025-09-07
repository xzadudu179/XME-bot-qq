from .seek import SeekRegion
import random

EVENTS = [
    {
        "type": "normal",
        "prob": 20,
        "descs": ["你收集到了一些资源", "你找到了一些散落的星币", "你发现了一些资源", "你抓到了几只小鱼", "你发现了一些零件", "你找到了一些被遗弃的物品"],
        "regions": [SeekRegion.DEEP_SEA, SeekRegion.SHIPWRECK, SeekRegion.UNDERSEA_CITY, SeekRegion.TRENCH, SeekRegion.SHALLOW_SEA],
        "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools: True,
        "changes": {
            "coins": {
                "change": lambda: random.randint(1, 15),
                "type": "+",
                "custom": False,
            }
        }
    },
    {
        "type": "normal",
        # 概率 -1 为默认事件
        "prob": -1,
        "descs": ["什么都没有发生...", "你没发现任何东西...", "周围空空如也...", "这里什么都没有...", "好像没有任何东西..."],
        "regions": [SeekRegion.DEEP_SEA, SeekRegion.SHIPWRECK, SeekRegion.UNDERSEA_CITY, SeekRegion.TRENCH, SeekRegion.SHALLOW_SEA],
        "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools: True,
        "changes": {
            "oxygen": {
                "change": lambda: random.randint(0, 2),
                "type": "-",
                "custom": False,
            }
        }
    },
    {
        "type": "normal",
        # 概率 -1 为默认事件
        "prob": 12,
        "descs": ["请忽略那些长着触手的事物...", "你听到了不详的低语...", "是谁在说话？", "不要回头看...", "为什么到处都是眼睛..."],
        "regions": [SeekRegion.DEEP_SEA, SeekRegion.SHIPWRECK, SeekRegion.UNDERSEA_CITY, SeekRegion.TRENCH, SeekRegion.SHALLOW_SEA],
        "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools: san.value < 60,
        "changes": {
            "san": {
                "change": lambda: random.randint(1, 10),
                "type": "-",
                "custom": False,
            }
        }
    },
    {
        "type": "normal",
        # 概率 -1 为默认事件
        "prob": 15,
        "descs": ["你听到了祂的声音...", "你看&了面<?前的%.>..??", "???>%祂!^&在.......", "你已然...全身?心>&投入于>*#祂$>..", "供..奉@>?..自己吧", "你?看到了不存在?的东西???", "你听到了神的呼唤...祂的声音...", "海洋...?你已与祂融为一体...", "啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊", "...你所看到的一切都在蠕动", "聆听祂的声音吧......"],
        "regions": [SeekRegion.DEEP_SEA, SeekRegion.SHIPWRECK, SeekRegion.UNDERSEA_CITY, SeekRegion.TRENCH, SeekRegion.SHALLOW_SEA],
        "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools: san.value < 40,
        "changes": {
            "san": {
                "change": lambda: random.randint(5, 10),
                "type": "-",
                "custom": False,
            }
        }
    },
    {
        "type": "normal",
        # 概率 -1 为默认事件
        "prob": 15,
        "descs": ["周围的墙面似乎正在收缩...这让你感到不安...", "你好像听到了一阵低语...", "楼房在移动吗？", "你似乎知道...你不应该来这里", "你被迷雾包围了...", "你好像听到了什么声音...", "你似乎听到了不属于这个世界的声音...", "你似乎看到了不应该看到的东西..."],
        "regions": [SeekRegion.UNDERSEA_CITY],
        "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools: True,
        "changes": {
            "san": {
                "change": lambda: random.randint(1, 5),
                "type": "-",
                "custom": False,
            }
        }
    },
    {
        "type": "normal",
        # 概率 -1 为默认事件
        "prob": 17,
        "descs": ["沉船里没有任何东西了...", "这个沉船已经没有可以探索的了。", "这个沉船里没什么东西了。", "这个沉船已经被探索完了"],
        "regions": [SeekRegion.SHIPWRECK],
        "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools: True,
        "changes": {
            # "region": {
            #     "change": lambda v: v.change_region(v.get_last_region()),
            #     "return": lambda v: v.region.value,
            #     "custom": True,
            #     "assign": True,
            # }
        },
        "region_changes": lambda last: last,
    },
    {
        "type": "normal",
        # 概率 -1 为默认事件
        "prob": 10,
        "descs": ["你发现了一些喷气孔", "你发现这里有一些气泡", "有一些气泡正在上浮...", "你发现了一个气孔", "你发现了一根气泡柱..."],
        "regions": [SeekRegion.DEEP_SEA, SeekRegion.UNDERSEA_CITY, SeekRegion.TRENCH, SeekRegion.SHALLOW_SEA],
        "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools: True,
        "changes": {
            "oxygen": {
                "change": lambda: random.randint(1, 7),
                "type": "+",
                "custom": False,
            }
        }
    },
    {
        "type": "normal",
        # 概率 -1 为默认事件
        "prob": 15,
        "descs": ["你发现了一些密封的食物罐头", "你发现了一些保存妥善的零食", "你发现了一些密封的罐头", "你找到了一些吃的，看起来还能吃"],
        "regions": [SeekRegion.SHIPWRECK, SeekRegion.UNDERSEA_CITY],
        "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools: True,
        "changes": {
            "health": {
                "change": lambda: random.randint(1, 7),
                "type": "+",
                "custom": False,
            }
        }
    },
    {
        "type": "decision",
        "prob": 5,
        "descs": ["你发现了一艘沉船...要不要探索一下？", "出现了一艘沉船...要不要去探索一下？", "你看到了一艘沉船...要去探索吗？"],
        "regions": [SeekRegion.SHALLOW_SEA, SeekRegion.DEEP_SEA, SeekRegion.TRENCH],
        "can_quit": True,
        "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools: True,
        "decisions": [
            {
                "type": "normal",
                "names": ["进入沉船", "探索沉船"],
                "descs": ["你进入了沉船...", "你来到了沉船的内部...", "你走进了沉船...", "你走进了这艘沉船..."],
                "tip": "[区域→]",
                "changes": {
                },
                "region_changes": lambda last: SeekRegion.SHIPWRECK
            },
            {
                "type": "normal",
                "tip": "",
                "names": ["离开", "放弃", "放弃探索"],
                "descs": ["你不打算探索这艘沉船。", "你放弃了对沉船的探索。", "你没有尝试探索这艘沉船。"],
                "changes": {
                }
            },
        ]
    },
    {
        "type": "dice",
        # 概率 -1 为默认事件
        "prob": 5,
        "event_messages": [
            {
                # 什么都没有是所有地区都可
                "regions": [],
                "descs": ["出现了一只鲨鱼！", "突然有一只鲨鱼朝你冲来！", "有一只鲨鱼冲来！"],
                "ok_msgs": ["你奋力反击，打败了鲨鱼。", "在你的努力下，鲨鱼被击败了。", "你成功招架住了鲨鱼的攻击，随后趁着机会逃离了。", "你奋力反击，赶跑了鲨鱼。", "在你不懈的努力下，成功打败了鲨鱼。"],
                "bigwin_msgs": ["你察觉到了鲨鱼的姿态，瞬间命中要害打败了鲨鱼！", "你在一瞬间击中了鲨鱼的要害，鲨鱼被你击败了！", "你反应过来，成功攻击到鲨鱼的眼睛！趁着眩晕，你迅速离开了。", "你反应过来，瞬间躲避开，并且趁机打晕了鲨鱼逃跑。"],
                "fail_msgs": ["你招架不住鲨鱼的攻击，受了一些伤。", "你被鲨鱼撞得不知所措。", "鲨鱼冲上来咬了你一口，你根本没反应过来。", "你想挡住鲨鱼的攻击，可惜它的力量太大了。", "鲨鱼冲到了你的面前，在你反应过来之前咬了你一口..."],
                "bigfail_msgs": ["你完全没反应过来，被鲨鱼狠狠咬了一口！", "你尝试招架它，但是后面还有一只鲨鱼！", "鲨鱼的攻击被拦下了...不对，有两只鲨鱼！", "你尝试攻击鲨鱼，却打空了，随后被鲨鱼狠狠地咬了一口！", "鲨鱼的力量实在太大，你根本阻挡不住攻击..."],
            },
            {
                # 什么都没有是所有地区都可
                "regions": [SeekRegion.UNDERSEA_CITY, SeekRegion.TRENCH],
                "descs": ["一个黑影逼近...", "你看到了一道黑影...", "你发现了一个不寻常的黑影...", "忽然闪过一团黑影..."],
                "ok_msgs": ["黑影突然冲了过来！但是你反应过来，干掉了它。", "黑影忽然把你包围了！但是在你的反击下，黑影逐渐消失了...", "黑影将你团团包围...但是被你反击开了。"],
                "bigwin_msgs": ["黑影忽然消散了，变成了一堆星币...？", "你似乎察觉到了什么，瞬间朝黑影攻击！它即刻飘散了...", "黑影消失了...但是你的身边似乎多了一点东西...", "黑影突然冲来！但是你早有准备，一击挡住了它！它忽然消散了。"],
                "fail_msgs": ["黑影将你团团包围！你突然两眼一黑，随后在一块石头旁醒来..."," 黑影突然冲了过来！你没反应过来，遭到了一阵强烈的撞击...",],
                "bigfail_msgs": ["你被黑影包围，随后失去了知觉...", "黑影忽然冲向了你！你完全没有反应过来，被强烈的冲击撞晕了..."],
            },
        ],
        "regions": [SeekRegion.DEEP_SEA, SeekRegion.UNDERSEA_CITY, SeekRegion.TRENCH, SeekRegion.SHALLOW_SEA],
        "dice_faces": lambda: random.randint(5, 25),
        "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools: True,
        "determine_attr": "combat",
        "ok": {
            "changes": {
                "coins": {
                    "change": lambda: random.randint(15, 50),
                    "type": "+",
                    "custom": False,
                },
                "oxygen": {
                    "change": lambda: random.randint(0, 8),
                    "type": "-",
                    "custom": False,
                },
            },
        },
        "big_win": {
            "changes": {
                "coins": {
                    "change": lambda: random.randint(30, 70),
                    "type": "+",
                    "custom": False,
                },
                "combat": {
                    "change": lambda: random.randint(1, 3),
                    "type": "+",
                    "custom": False,
                }
            },
        },
        "fail": {
            "changes": {
                "oxygen": {
                    "change": lambda: random.randint(5, 10),
                    "type": "-",
                    "custom": False,
                },
                "health": {
                    "change": lambda: random.randint(5, 10),
                    "type": "-",
                    "custom": False,
                }
            },
        },
        "big_fail": {
            "changes": {
                "oxygen": {
                    "change": lambda: random.randint(12, 25),
                    "type": "-",
                    "custom": False,
                },
                "health": {
                    "change": lambda: random.randint(12, 25),
                    "type": "-",
                    "custom": False,
                }
            },
        },
    }
]
