from .classes.player import SeekRegion, Player
from xme.plugins.commands.xme_user.classes.user import coin_name
import random
from .. import get_random_broken_bottle
from ..tools.bottlecard import get_pickedup_bottle_card
from xme.xmetools.msgtools import image_msg

def shark_post(p: Player):
  if p.is_die()[0] and p.region.value == SeekRegion.SHALLOW_SEA:
    p.achieved_achievements.append("你需要一艘更大的船"),

def repair_bottle(data: dict, p: Player):
  bottle = data["bottle"]
  bottle.is_broken = False
  bottle.views //= 2
  bottle.likes //= 2
  bottle.save()
  p.achieved_achievements.append("打捞者"),

async def get_bottle_content(datas):
  return await image_msg(get_pickedup_bottle_card(datas["bottle"], suffix="<div></div>"))

EVENTS = [
  {
    "type": "normal",
    "tags": [],
    "prob": 20,
    "post_func": None,
    "descs": ["你收集到了一些资源", f"你找到了一些散落的{coin_name}", "你发现了一些资源", "你抓到了几只小鱼", "你发现了一些零件", "你找到了一些被遗弃的物品"],
    "regions": [SeekRegion.DEEP_SEA, SeekRegion.SHIPWRECK, SeekRegion.UNDERSEA_CITY, SeekRegion.TRENCH, SeekRegion.SHALLOW_SEA],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: depth.value > 30 and depth.value < 300,
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
    "tags": [],
    "prob": 10,
    "post_func": None,
    "descs": ["你收集到了一些珍珠", "你发现了一些漂亮的石头", "你抓到了几只深海鱼类", "你发现了一些发光的物品", "你找到了一些挂饰"],
    "regions": [SeekRegion.DEEP_SEA, SeekRegion.SHIPWRECK, SeekRegion.UNDERSEA_CITY, SeekRegion.TRENCH, SeekRegion.SHALLOW_SEA, SeekRegion.FOREST],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: depth.value > 300,
    "changes": {
      "coins": {
        "change": lambda: random.randint(20, 50),
        "type": "+",
        "custom": False,
      }
    }
  },
  {
    "type": "normal",
    "tags": [],
    "prob": 3,
    "post_func": None,
    "descs": ["你收集到了一些神秘的发光物体...", "你发现了几个发着光的球体...", "你捕捉到了一些黑影..."],
    "regions": [SeekRegion.ABYSS, SeekRegion.DEEPEST, SeekRegion.VOID],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: depth.value > 900,
    "changes": {
      "coins": {
        "change": lambda: random.randint(80, 110),
        "type": "+",
        "custom": False,
      }
    }
  },
  {
    "type": "normal",
    "tags": [],
    "prob": 3,
    "post_func": None,
    "descs": ["你收集到了一些神秘的发光物体...他们似乎能治疗你", "你发现了几个发着光的球体...它们好像可以疗愈你的伤口", "你捕捉到了一些黑影...它们似乎能治疗你"],
    "regions": [SeekRegion.ABYSS, SeekRegion.DEEPEST, SeekRegion.VOID, SeekRegion.SHADOWRECK],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: depth.value > 900,
    "changes": {
      "health": {
        "change": lambda: random.randint(6, 15),
        "type": "+",
        "custom": False,
      }
    }
  },
  {
    "type": "normal",
    "tags": [],
    "prob": 3,
    "post_func": None,
    "descs": ["你收集到了一些神秘的发光物体...", "你发现了几个发着光的球体...", "你捕捉到了一些黑影..."],
    "regions": [SeekRegion.SHADOWRECK],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: depth.value > 900,
    "changes": {
      "coins": {
        "change": lambda: random.randint(50, 90),
        "type": "+",
        "custom": False,
      }
    }
  },
  {
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": -1,
    "post_func": None,
    "descs": ["什么都没有发生...", "你没发现任何东西...", "周围空空如也...", "这里什么都没有...", "好像没有任何东西..."],
    "regions": [],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, events_encountered, *args: san.value >= 80,
    "changes": {
      "oxygen": {
        "change": lambda: random.randint(0, 1),
        "type": "-",
        "custom": False,
      }
    }
  },
  {
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 10,
    "post_func": None,
    "descs": ["什么都没有发生...", "你没发现任何东西...", "周围空空如也...", "这里什么都没有...", "好像没有任何东西..."],
    "regions": [],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, events_encountered, *args: san.value >= 80,
    "changes": {
      "oxygen": {
        "change": lambda: random.randint(0, 1),
        "type": "-",
        "custom": False,
      }
    }
  },
  {
    # 下潜事件
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": -1,
    "post_func": None,
    "descs": ["岸边离你越来越远了...", "太阳的光线逐渐变暗了...", "海平面越来越模糊了...", "你下潜得越来越深了...", "你感觉到水压越来越大..."],
    "regions": [SeekRegion.SHALLOW_SEA],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: not back and depth.value < 150,
    "changes": {
      "depth": {
        "change": lambda: random.randint(2, 10),
        "type": "+",
        "custom": False,
      },
      "oxygen": {
         "change": lambda: random.randint(0, 2),
        "type": "-",
        "custom": False,
      },
    }
  },
  {
    # 下潜事件
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 25,
    "top": True,
    "post_func": None,
    "descs": ["岸边离你越来越远了...", "太阳的光线逐渐变暗了...", "海平面越来越模糊了...", "你下潜得越来越深了...", "你感觉到水压越来越大..."],
    "regions": [SeekRegion.SHALLOW_SEA],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: not back and depth.value < 150,
    "changes": {
      "depth": {
        "change": lambda: random.randint(2, 10),
        "type": "+",
        "custom": False,
      },
      "oxygen": {
         "change": lambda: random.randint(0, 2),
        "type": "-",
        "custom": False,
      },
    }
  },
  {
    # 下潜事件
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 5,
    "post_func": None,
    "descs": ["你徘徊了一阵子...", "你想要回头看看有没有东西错过。", "你觉得你下潜的有点太快了。"],
    "regions": [SeekRegion.SHALLOW_SEA, SeekRegion.DEEP_SEA, SeekRegion.TRENCH],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: not back and depth.value > 70,
    "changes": {
      "depth": {
        "change": lambda: random.randint(1, 7),
        "type": "-",
        "custom": False,
      },
      "oxygen": {
         "change": lambda: random.randint(0, 1),
        "type": "-",
        "custom": False,
      },
    }
  },
  {
    # 下潜事件
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": -1,
    "post_func": None,
    "descs": ["你继续前往更深的地方...", "你尝试探索更深处...", "你下潜得越来越深了...", "你感觉到水压越来越大..."],
    "regions": [SeekRegion.DEEP_SEA, SeekRegion.TRENCH, SeekRegion.ABYSS],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: not back,
    "changes": {
      "depth": {
        "change": lambda: random.randint(2, 14),
        "type": "+",
        "custom": False,
      },
      "oxygen": {
        "change": lambda: random.randint(0, 2),
        "type": "-",
        "custom": False,
      }
    }
  },
  {
    # 下潜事件
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 20,
    "top": True,
    "post_func": None,
    "descs": ["你继续前往更深的地方...", "你尝试探索更深处...", "你下潜得越来越深了...", "你感觉到水压越来越大..."],
    "regions": [SeekRegion.DEEP_SEA, SeekRegion.TRENCH, SeekRegion.ABYSS],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: not back,
    "changes": {
      "depth": {
        "change": lambda: random.randint(2, 14),
        "type": "+",
        "custom": False,
      },
      "oxygen": {
        "change": lambda: random.randint(0, 2),
        "type": "-",
        "custom": False,
      }
    }
  },
  {
    # 下潜事件
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": -1,
    "post_func": None,
    "descs": ["你继续前往更深的地方...", "你尝试探索更深处...", "你下潜得越来越深了...", "你反而感觉到水压越来越小..."],
    "regions": [SeekRegion.DEEPEST, SeekRegion.VOID],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: not back,
    "changes": {
      "depth": {
        "change": lambda: random.randint(5, 28),
        "type": "+",
        "custom": False,
      },
      "oxygen": {
        "change": lambda: random.randint(0, 3),
        "type": "-",
        "custom": False,
      }
    }
  },
  {
    # 返回事件
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 50,
    "top": True,
    "post_func": None,
    "descs": ["你奋力地往上游...", "你尽全力往上游去...", "你尽力地往上游...", "你感觉到水压越来越小..."],
    "regions": [SeekRegion.SHALLOW_SEA, SeekRegion.ABYSS, SeekRegion.DEEP_SEA, SeekRegion.TRENCH, SeekRegion.UNDERSEA_CAVE, SeekRegion.UNDERSEA_CITY],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: back and oxygen.value >= 30,
    "changes": {
      "depth": {
        "change": lambda: random.randint(7, 20),
        "type": "-",
        "custom": False,
      },
      "oxygen": {
        "change": lambda: random.randint(0, 3),
        "type": "-",
        "custom": False,
      }
    }
  },
  {
    # 返回事件
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 27,
    "top": True,
    "post_func": None,
    "descs": ["你奋力地往上游...但是你快没氧气了...", "你尽全力往上游去...但是你快没有氧气了...", "你尝试尽力地往上游..."],
    "regions": [SeekRegion.SHALLOW_SEA, SeekRegion.ABYSS, SeekRegion.DEEP_SEA, SeekRegion.TRENCH, SeekRegion.UNDERSEA_CAVE, SeekRegion.UNDERSEA_CITY, SeekRegion.VOID, SeekRegion.DEEPEST],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: back and oxygen.value < 30,
    "changes": {
      "depth": {
        "change": lambda: random.randint(3, 12),
        "type": "-",
        "custom": False,
      },
      "oxygen": {
        "change": lambda: random.randint(0, 1),
        "type": "-",
        "custom": False,
      }
    }
  },
  {
    # 返回事件
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 50,
    "top": True,
    "post_func": None,
    "descs": ["你奋力地往上游...", "你尽全力往上游去...", "你尽力地往上游...", "你虽然在往上游，但是感觉到水压越来越大..."],
    "regions": [SeekRegion.VOID, SeekRegion.DEEPEST],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: back and oxygen.value >= 30,
    "changes": {
      "depth": {
        "change": lambda: random.randint(10, 38),
        "type": "-",
        "custom": False,
      },
      "oxygen": {
        "change": lambda: random.randint(0, 4),
        "type": "-",
        "custom": False,
      }
    }
  },
  # 漂流瓶决策
  {
    "type": "decision",
    "tags": [],
    "datas": {"bottle": get_random_broken_bottle},
    "formats": {
      "bottle_content": get_bottle_content,
    },
    "prob": 0.184,
    "post_func": None,
    "descs": ["你发现一个破碎的漂流瓶...{bottle_content}你打算如何处理它？", "你找到了一个已经被打碎的漂流瓶...{bottle_content}要把它装到新的瓶子里吗？", "你发现了一个碎掉的漂流瓶...{bottle_content}要把它装进新的瓶子吗？"],
    "regions": [SeekRegion.SHALLOW_SEA, SeekRegion.DEEP_SEA, SeekRegion.FOREST, SeekRegion.SHIPWRECK, SeekRegion.UNDERSEA_CITY, SeekRegion.UNDERSEA_CAVE, SeekRegion.TRENCH],
    "can_quit": True,
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, events, is_sim, *args: not back and not is_sim,
    "decisions": [
      {
        "type": "normal",
        "tags": [],
        "names": ["使用少许星币修复瓶子", "用少许星币修好瓶子"],
        "descs": ["你修复了这个瓶子，向远处抛去...", "你修复了这个瓶子，并抛去...", "你修复并抛走了这个瓶子..."],
        "event_func": repair_bottle,
        "tip": "[特殊+][星币-]",
        "changes": {
          "san": {
            "change": lambda: random.randint(0, 5),
            "type": "+",
            "custom": False,
          },
          "coins": {
            "change": lambda: random.randint(5, 15),
            "type": "-",
            "custom": False,
          },
        },
      },
      {
        "type": "normal",
        "tags": [],
        "tip": "",
        "names": ["无视", "不管"],
        "descs": ["你不打算管这个瓶子", "你觉得没必要修复这个瓶子", "你不打算修复这个瓶子"],
        "changes": {
        }
      },
    ]
  },
  # {
  #   # 返回事件
  #   "type": "normal",
  #   "tags": [],
  #   # 概率 -1 为默认事件
  #   "prob": 100,
  #   "post_func": None,
  #   "top": True,
  #   "descs": ["你回到了海面", "你回到了海上"],
  #   "regions": [SeekRegion.SHALLOW_SEA],
  #   "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: back and depth.value <= 0,
  #   "changes": {
  #     "oxygen": {
  #       "change": lambda: 10000,
  #       "type": "+",
  #       "custom": False,
  #     },
  #     "san": {
  #       "change": lambda: 3,
  #       "type": "*",
  #       "custom": False,
  #     }
  #   }
  # },
  {
    # 返回事件
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": -1,
    "post_func": None,
    "descs": ["你需要往回走。", "你觉得你应该先回去了。", "你不觉得你还有时间继续探索这艘船了。"],
    "regions": [SeekRegion.SHIPWRECK, SeekRegion.SHADOWRECK],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: back,
    "changes": {
    },
    "region_change": lambda last: last,
  },
  {
    # 切换深渊事件
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 100,
    "top": True,
    "post_func": None,
    "descs": ["你似乎感受到了一阵热量...但你知道，这绝对不是来自太阳的热量...", "你大概是来到了一片没有尽头的无底深渊..."],
    "regions": [SeekRegion.TRENCH],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: depth.value > 1000,
    "changes": {
      "depth": {
        "change": lambda: random.randint(10, 20),
        "type": "+",
        "custom": False,
      }
    },
    "region_change": lambda last: SeekRegion.ABYSS,
  },
  {
    # ↑切换海沟事件
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 100,
    "top": True,
    "post_func": None,
    "descs": ["你感到四周变寒冷了，但是你知道太阳光离你更近了...", "你终于离开了无底的深渊..."],
    "regions": [SeekRegion.ABYSS],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: depth.value <= 900,
    "changes": {
      "depth": {
        "change": lambda: random.randint(10, 20),
        "type": "-",
        "custom": False,
      }
    },
    "region_change": lambda last: SeekRegion.TRENCH,
  },
  {
    # ↓切换溟渊事件
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 100,
    "top": True,
    "post_func": None,
    "descs": ["水的感觉渐渐减弱了...周围似乎冒出了一些奇怪的光点...", "你来到了深渊之下...这是一个理论上不可能出现的区域..."],
    "regions": [SeekRegion.ABYSS],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: depth.value > 2000,
    "changes": {
      "depth": {
        "change": lambda: random.randint(10, 20),
        "type": "+",
        "custom": False,
      }
    },
    "region_change": lambda last: SeekRegion.DEEPEST,
  },
  {
    # ↑切换深渊事件
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 100,
    "top": True,
    "post_func": None,
    "descs": ["你回到了...深渊", "你回到了有点\"温暖\"的深渊..."],
    "regions": [SeekRegion.DEEPEST],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: depth.value < 1900,
    "changes": {
      "depth": {
        "change": lambda: random.randint(10, 20),
        "type": "-",
        "custom": False,
      }
    },
    "region_change": lambda last: SeekRegion.ABYSS,
  },
  {
    # ↓切换虚境事件
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 100,
    "top": True,
    "post_func": None,
    "descs": ["你感到身体轻飘飘的...下方...似乎有光...", "光点逐渐消散...你感到自己的身体变得很轻盈...下方似乎有光..."],
    "regions": [SeekRegion.DEEPEST],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: depth.value > 3500,
    "changes": {
      "depth": {
        "change": lambda: random.randint(10, 20),
        "type": "+",
        "custom": False,
      }
    },
    "region_change": lambda last: SeekRegion.VOID,
  },
  {
    # ↑切换溟渊事件
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 100,
    "top": True,
    "post_func": None,
    "descs": ["周围的光点逐渐变多，你也不再感到身体那么轻盈了...", "水的感觉变明显了...你离开了这片虚空..."],
    "regions": [SeekRegion.VOID],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: depth.value <= 3400,
    "changes": {
      "depth": {
        "change": lambda: random.randint(10, 20),
        "type": "-",
        "custom": False,
      }
    },
    "region_change": lambda last: SeekRegion.DEEPEST,
  },
  {
    # 深度过高受到伤害
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": -1,
    # "top": True,
    "post_func": None,
    "descs": ["周围嘈杂的声响正在撕裂你的身体...与心智...", "你的心灵无法承受如此多的...侵蚀...", "你快要被虚空融化了..."],
    "regions": [SeekRegion.VOID],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: depth.value > 5000,
    "changes": {
      "health": {
        "change": lambda: random.randint(10, 20),
        "type": "-",
        "custom": False,
      },
      "san": {
        "change": lambda: random.randint(10, 20),
        "type": "-",
        "custom": False,
      }
    },
  },
  {
    # ↓切换海沟事件
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 100,
    "top": True,
    "post_func": None,
    "descs": ["即便是探照灯也完全无法看清现在的环境了...", "太阳已经完全消失了...", ],
    "regions": [SeekRegion.DEEP_SEA],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: depth.value > 500,
    "changes": {
      "depth": {
        "change": lambda: random.randint(10, 20),
        "type": "+",
        "custom": False,
      }
    },
    "region_change": lambda last: SeekRegion.TRENCH,
  },
  {
    # 切换深海事件
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 100,
    "top": True,
    "post_func": None,
    "descs": ["四周的小生物渐渐多了起来..", "海水总算有了颜色...和亮度", "四周不再是黑乎乎的一片了..."],
    "regions": [SeekRegion.TRENCH],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: depth.value <= 480,
    "changes": {
      "depth": {
        "change": lambda: random.randint(10, 20),
        "type": "-",
        "custom": False,
      }
    },
    "region_change": lambda last: SeekRegion.DEEP_SEA,
  },
  {
    # 切换深海事件
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 100,
    "top": True,
    "post_func": None,
    "descs": ["周围一片寂静...与漆黑", "太阳的光芒要消失了...", ],
    "regions": [SeekRegion.SHALLOW_SEA],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: depth.value > 130,
    "changes": {
      "depth": {
        "change": lambda: random.randint(10, 20),
        "type": "+",
        "custom": False,
      }
    },
    "region_change": lambda last: SeekRegion.DEEP_SEA,
  },
  {
    # 切换浅海事件
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 100,
    "top": True,
    "post_func": None,
    "descs": ["你逐渐看到了太阳的光芒...", "海水总算有了颜色...和亮度", "四周不再是黑乎乎的一片了..."],
    "regions": [SeekRegion.DEEP_SEA],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: depth.value <= 110,
    "changes": {
      "depth": {
        "change": lambda: random.randint(10, 20),
        "type": "-",
        "custom": False,
      }
    },
    "region_change": lambda last: SeekRegion.SHALLOW_SEA,
  },
  {
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 1.3,
    "post_func": None,
    "descs": ["你似乎充满了力量", "你现在精神勃发", "你现在充满决心", "你现在精神亢奋"],
    "regions": [SeekRegion.DEEP_SEA, SeekRegion.SHALLOW_SEA, SeekRegion.TRENCH, SeekRegion.ABYSS],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: health.value >= health.max_value * 0.9 and (oxygen.value >= oxygen.max_value * 0.85 or oxygen.value >= 110) and san.value >= san.max_value * 0.85 and depth.value > 155 and coins.value > 200,
    "changes": {
      "chance": {
        "change": lambda: random.randint(1, 2),
        "type": "+",
        "custom": False,
      }
    },
  },
  {
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 5,
    "post_func": None,
    "descs": ["你觉得这一切还不应该结束", "你觉得你还有精力继续探险", "你下定了探索的决心", "你知道你这次探险一定能成功"],
    "regions": [SeekRegion.DEEP_SEA, SeekRegion.SHALLOW_SEA, SeekRegion.TRENCH],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: health.value >= health.max_value * 0.95 and oxygen.value >= oxygen.max_value * 0.9 and san.value >= san.max_value * 0.9 and depth.value > 250 and coins.value > 440 and chance.value <= 3,
    "changes": {
      "chance": {
        "change": lambda: random.randint(2, 5),
        "type": "+",
        "custom": False,
      },
      "oxygen": {
        "change": lambda: random.randint(15, 25),
        "type": "-",
        "custom": False,
      }
    },
  },
  {
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": -1,
    "post_func": None,
    "descs": ["你没有发现任何\"活物\"...", "你没发现任何东西...", "周围空空如也...", "这里什么都没有...", "好像没有任何东西..."],
    "regions": [],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: san.value <= 50,
    "changes": {
      "oxygen": {
        "change": lambda: random.randint(0, 3),
        "type": "-",
        "custom": False,
      }
    }
  },
  {
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": -1,
    "post_func": None,
    "descs": ["什么都没有发生...你长舒一口气", "还好...你没发现任何东西...", "安静...或许是一种好事", "这里什么都没有...那就足够了", "还好没有任何东西..."],
    "regions": [],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: san.value < 80 and san.value >= 50,
    "changes": {
      "san": {
        "change": lambda: random.randint(0, 3),
        "type": "+",
        "custom": False,
      },
      "oxygen": {
        "change": lambda: random.randint(0, 2),
        "type": "-",
      }
    }
  },
  {
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 20,
    "post_func": None,
    "descs": ["太阳的光辉让你心情愉悦...", "看到太阳的光芒，你感到很放松...", "温暖的海水与鱼群让你感到心情舒畅..."],
    "regions": [SeekRegion.SHALLOW_SEA],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: san.value < san.max_value,
    "changes": {
      "san": {
        "change": lambda: random.randint(0, 6),
        "type": "+",
        "custom": False,
      },
    }
  },
  {
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 12,
    "post_func": None,
    "descs": ["请忽略那些长着触手的事物...", "你听到了不详的低语...", "是谁在说话？", "不要回头看...", "到处都是眼睛..."],
    "regions": [],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: san.value < 60,
    "changes": {
      "san": {
        "change": lambda: random.randint(1, 6),
        "type": "-",
        "custom": False,
      }
    }
  },
  {
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 10,
    "post_func": None,
    "descs": ["你因精神不稳定在大口喘气...", "你绝望地哭喊...", "你不觉得你能活下来..."],
    "regions": [],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: san.value < 60,
    "changes": {
      "oxygen": {
        "change": lambda: random.randint(3, 7),
        "type": "-",
        "custom": False,
      }
    }
  },
  {
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 15,
    "post_func": None,
    "descs": ["你听到了祂的声音...", "你看到了面前的...???", "祂!^&在...这里...", "你已然...全身心投入于祂...", "...供奉自己吧", "你?看到了不存在?的东西...???", "你听到了神的呼唤...祂的声音...", "海洋...?你已与祂融为一体...", "啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊", "...你所看到的一切都在蠕动", "聆听祂的声音吧......"],
    "regions": [],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: san.value < 40,
    "changes": {
      "san": {
        "change": lambda: random.randint(2, 8),
        "type": "-",
        "custom": False,
      }
    }
  },
  {
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 4,
    "post_func": None,
    "descs": ["你回想起了曾经的时光...", "你想到了美好的事物...", "你觉得你有信心完成这次探险"],
    "regions": [SeekRegion.DEEP_SEA, SeekRegion.SHALLOW_SEA, SeekRegion.UNDERSEA_CITY, SeekRegion.UNDERSEA_CAVE],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: san.value > 80 and health.value > 50 and san.value < san.max_value,
    "changes": {
      "san": {
        "change": lambda: random.randint(2, 5),
        "type": "+",
        "custom": False,
      }
    }
  },
  {
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 5,
    "post_func": None,
    "descs": ["出现了一只海豚，助你前往了更深的地方...", "你发现了一只海豚，跟着它，你前往了更深的水域...", "有一群小鱼带着你游到了更深的水域...", "出现了一片鱼群，它们对水流的扰动使你更快地下潜..."],
    "regions": [SeekRegion.DEEP_SEA, SeekRegion.SHALLOW_SEA],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: san.value > 80 and not back,
    "changes": {
      "depth": {
        "change": lambda: random.randint(9, 20),
        "type": "+",
        "custom": False,
      },
      "san": {
        "change": lambda: random.randint(0, 5),
        "type": "+",
        "custom": False,
      }
    }
  },
  {
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 4,
    "post_func": None,
    "descs": ["一阵乱流让你下潜地更深了...", "忽然出现了一阵乱流，把你带到了更深的地方"],
    "regions": [SeekRegion.DEEP_SEA, SeekRegion.TRENCH, SeekRegion.ABYSS],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: True,
    "changes": {
      "depth": {
        "change": lambda: random.randint(10, 30),
        "type": "+",
        "custom": False,
      },
    }
  },
  {
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 15,
    "post_func": None,
    "descs": ["周围的墙面似乎正在收缩...这让你感到不安...", "你好像听到了一阵低语...", "楼房在移动吗？", "你似乎知道...你不应该来这里", "你被迷雾包围了...", "你好像听到了什么声音...", "你似乎听到了不属于这个世界的声音...", "你似乎看到了不应该看到的东西..."],
    "regions": [SeekRegion.UNDERSEA_CITY],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: True,
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
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 5,
    "post_func": None,
    "descs": ["你似乎听到了诡异的声音...", "你好像听到了一阵低语...", "这里的环境让你感到不安...", "这里的黑暗让你感到害怕...", "你是不是被什么东西包围了...", "周围一片死寂...你感到不安", "你似乎听到了不属于这个世界的声音...", "你似乎看到了不应该看到的东西..."],
    "regions": [SeekRegion.UNDERSEA_CITY, SeekRegion.DEEP_SEA, SeekRegion.TRENCH, SeekRegion.ABYSS, SeekRegion.FOREST, SeekRegion.UNDERSEA_CAVE, SeekRegion.VOID, SeekRegion.DEEPEST, SeekRegion.SHADOWRECK],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: True,
    "changes": {
      "san": {
        "change": lambda: random.randint(1, 3),
        "type": "-",
        "custom": False,
      },
    }
  },
  {
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 3,
    "post_func": None,
    "descs": ["沉船里没有任何东西了...", "这个沉船已经没有可以探索的了。", "这个沉船里没什么东西了。", "这个沉船已经被探索完了"],
    "regions": [SeekRegion.SHIPWRECK, SeekRegion.SHADOWRECK],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: True,
    "changes": {
    },
    "region_change": lambda last: last,
  },
  {
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 0.3,
    "post_func": None,
    "descs": ["你觉得你对这个城市的搜刮差不多就到这了。", "这块城区已经没什么东西了。", "这里差不多被探索完了。", "这个城市里没什么东西了。"],
    "regions": [SeekRegion.UNDERSEA_CITY],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: True,
    "changes": {
    },
    "region_change": lambda last: last,
  },
  {
    # 返回事件
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": -1,
    "post_func": None,
    "descs": ["你需要往回走。", "你觉得你应该先回去了。", "你不觉得你还有时间继续探索城市了。"],
    "regions": [SeekRegion.UNDERSEA_CITY],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: back,
    "changes": {
    },
    "region_change": lambda last: last,
  },
  {
    "type": "dice",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 1.7,
    "post_func": None,
    "event_messages": [
      {
        # 什么都没有是所有地区都可
        "regions": [],
        "descs": ["出现了一只巨大的远古生物！", "你发现了一只巨大的远古生物...", "你看到了一只神秘的巨兽..."],
        "ok_msgs": ["你的脑袋感受到了剧烈的疼痛，你奋力反抗，夺走了巨兽尝试对你的控制...", "你的思绪被一股强大且混乱的力量侵蚀，你奋力尝试保持专注...", "你忽然感觉到一阵无形的力量从四周侵入，你奋力反抗，最终击退了那股力量..."],
        "bigwin_msgs": ["你的思绪被巨兽强大的力量侵蚀，但你趁着它集中精神的时刻朝着它的眼睛攻击！巨兽被击退了，留下了许多奇怪的珍品...", "你成功抵抗了巨兽对你的精神攻击，并趁机攻击巨兽的弱点！巨兽痛苦地嚎叫，散落出闪烁着诡光的宝物离开...", "你忽然感到剧烈的疼痛，你集中全部精神反抗，并且找准时机攻击了巨兽的弱点！巨兽发出痛苦的嘶鸣，留下了许多闪闪发光的宝物消散..."],
        "fail_msgs": ["巨兽的眼睛散发光芒，你在剧烈的疼痛中被它控制，献上了鲜血以交换自由...", "你的意识被巨兽强大的力量击碎，你被迫献上了鲜血以换取自由...", "你的思绪忽然受到了强烈的侵蚀，你感到意识逐渐模糊...血液从身体中抽离..."],
        "bigfail_msgs": ["你的精神因巨兽的注视下而崩溃...它夺走了你身上的财宝与鲜血作为对你精神力的惩罚...", "你忽然被无形的力量控制，无论如何也无法反抗...你眼睁睁看着这只巨兽愤怒地夺走了你身上的财宝与鲜血...", "巨兽在一瞬间下压制了你的思绪，粉碎了你的精神...它夺走了你身上的财宝与鲜血...作为你弱小精神力的惩罚"],
      },
    ],
    "regions": [SeekRegion.FOREST, SeekRegion.ABYSS, SeekRegion.DEEPEST],
    "dice_faces": lambda: random.randint(10, 30),
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: depth.value > 200,
    "determine_attr": "mental",
    "ok": {
      "changes": {
        "coins": {
          "change": lambda: random.randint(20, 80),
          "type": "+",
          "custom": False,
        },
        "oxygen": {
          "change": lambda: random.randint(0, 5),
          "type": "-",
          "custom": False,
        },
        "san": {
          "change": lambda: random.randint(0, 5),
          "type": "-",
          "custom": False,
        },
      },
    },
    "big_win": {
      "changes": {
        "coins": {
          "change": lambda: random.randint(180, 320),
          "type": "+",
          "custom": False,
        },
        "combat": {
          "change": lambda: random.randint(0, 1),
          "type": "+",
          "custom": False,
        },
        "mental": {
          "change": lambda: random.randint(1, 3),
          "type": "+",
          "custom": False,
        },
        "san": {
          "change": lambda: random.randint(10, 15),
          "type": "+",
          "custom": False,
        }
      },
    },
    "fail": {
      "changes": {
        "health": {
          "change": lambda: random.randint(10, 20),
          "type": "-",
          "custom": False,
        },
        "oxygen": {
          "change": lambda: random.randint(0, 5),
          "type": "-",
          "custom": False,
        },
        "san": {
          "change": lambda: random.randint(7, 15),
          "type": "-",
          "custom": False,
        },
      },
    },
    "big_fail": {
      "changes": {
        "coins": {
          "change": lambda: random.randint(100, 200),
          "type": "-",
          "custom": False,
        },
        "oxygen": {
          "change": lambda: random.randint(5, 12),
          "type": "-",
          "custom": False,
        },
        "health": {
          "change": lambda: random.randint(25, 45),
          "type": "-",
          "custom": False,
        },
        "san": {
          "change": lambda: random.randint(10, 20),
          "type": "-",
          "custom": False,
        },
      },
    },
  },
  {
    # 返回事件
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": -1,
    "post_func": None,
    "descs": ["你奋力地试图往外游...", "你尝试往外游...", "你尽力地尝试往外游去...", "虽然感知不到方向，但你觉得你应该在往外游..."],
    "regions": [SeekRegion.FOREST],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: back,
    "changes": {
      "depth": {
        "change": lambda: random.randint(-15, 20),
        "type": "-",
        "custom": False,
      },
      "oxygen": {
        "change": lambda: random.randint(0, 3),
        "type": "-",
        "custom": False,
      }
    }
  },
  {
    "type": "normal",
    "tags": [],
    "prob": 5,
    "post_func": None,
    "descs": ["你发现了一些发光的珍珠", "扭曲的藤蔓上出现了散发光芒的球体...", "你发现了一些藤蔓的嫩芽", "你找到了一些奇特的小生物"],
    "regions": [SeekRegion.FOREST],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: True,
    "changes": {
      "coins": {
        "change": lambda: random.randint(50, 100),
        "type": "+",
        "custom": False,
      }
    }
  },
  {
    "type": "normal",
    "tags": [],
    "prob": 8,
    "post_func": None,
    "descs": ["你找到了一些漂流的物资残骸...", "你发现了一些沉船的碎块...", "你找到了一些残破的物资箱..."],
    "regions": [SeekRegion.FOREST, SeekRegion.TRENCH, SeekRegion.UNDERSEA_CITY],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: True,
    "changes": {
      "health": {
        "change": lambda: random.randint(5, 20),
        "type": "+",
        "custom": False,
      },
      "coins": {
        "change": lambda: random.randint(10, 30),
        "type": "+",
        "custom": False,
      }
    }
  },
  {
    "type": "normal",
    "tags": [],
    "prob": 8,
    "post_func": None,
    "descs": ["你找到了一些漂流的物资残骸...", "你发现了一些沉船的碎块...", "你找到了一些残破的物资箱..."],
    "regions": [SeekRegion.SHALLOW_SEA, SeekRegion.DEEP_SEA, SeekRegion.TRENCH],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: True,
    "changes": {
      "health": {
        "change": lambda: random.randint(5, 12),
        "type": "+",
        "custom": False,
      }
    }
  },
  {
    "type": "normal",
    "tags": [],
    "prob": 18,
    "post_func": None,
    "descs": ["你正在流血...", "你需要赶快寻找治疗...", "你感觉你快要失血过多了..."],
    "regions": [],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: health.value < 30,
    "changes": {
      "health": {
        "change": lambda: random.randint(1, 4),
        "type": "-",
        "custom": False,
      }
    }
  },
  {
    "type": "normal",
    "tags": [],
    "prob": 5,
    "post_func": None,
    "descs": ["你触碰到了蠕动植物的荆棘，它似乎很不高兴...", "你似乎招惹到了这些植物，它们对你发动了攻击..."],
    "regions": [SeekRegion.FOREST],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: True,
    "changes": {
      "health": {
        "change": lambda: random.randint(2, 7),
        "type": "-",
        "custom": False,
      }
    }
  },
  {
    "type": "normal",
    "tags": [],
    "prob": 5.5,
    "post_func": None,
    "descs": ["你返回的途中碰到了蠕动植物的荆棘，它似乎很不高兴...", "你似乎在返回的路上招惹到了这些植物，它们对你发动了攻击...", "你撞到了荆棘上，它们毫不犹豫地向你发动了攻击..."],
    "regions": [SeekRegion.FOREST],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: back,
    "changes": {
      "health": {
        "change": lambda: random.randint(4, 12),
        "type": "-",
        "custom": False,
      }
    }
  },
  {
    # 返回事件
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 15,
    "regions": [SeekRegion.FOREST],
    "post_func": None,
    "descs": ["幽绿色的藤蔓形植物似乎正在低语...", "四周非常的空，且包裹着雾气...你感到很害怕", "那些扭曲的植物似乎在主动朝你靠近...", "你似乎听到了远古生物的低鸣..."],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: back,
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
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 0.3,
    "post_func": None,
    "descs": ["你一阵恍惚，这片森林忽然消失了...就好像它从来没存在过", "你突然感到一阵晕眩，随后发现整片森林消失不见了...", "你忽然感到了眩晕...随后发现整片森林完全消失了..."],
    "regions": [SeekRegion.FOREST],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: True,
    "changes": {
      "san": {
        "change": lambda: random.randint(5, 20),
        "type": "-",
        "custom": False,
      }
    },
    "region_change": lambda last: last,
  },
  {
    "type": "decision",
    "tags": [],
    "prob": 0.7,
    "post_func": None,
    "descs": ["一抹幽绿色的光芒引起了你的注意...前方似乎是一片森林？", "前方出现了一片神秘的...海底森林？", "你的视野似乎被蒙上了一层雾，前方出现了一片奇怪的海底森林..."],
    "regions": [SeekRegion.DEEP_SEA, SeekRegion.TRENCH],
    "can_quit": True,
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: not back and depth.value > 250 and depth.value < 600,
    "decisions": [
      {
        "type": "normal",
        "tags": [],
        "names": ["进入此地", "探索森林"],
        "descs": ["你游进了这片神秘的区域...", "你尝试探索这片奇怪的区域...", "你尝试探索这片海底森林...", "你尝试深入此地探索..."],
        "tip": "[区域→]",
        "changes": {
        },
        "region_change": lambda last: SeekRegion.FOREST
      },
      {
        "type": "normal",
        "tags": [],
        "tip": "",
        "names": ["离开", "放弃", "放弃探索"],
        "descs": ["你觉得你可能进去这里后就出不来了...", "你觉得自己还不适合来这里探索", "你觉得你在这里无法判断深度，很可能出问题..."],
        "changes": {
        }
      },
    ]
  },
  # {
  #   "type": "decision",
  #   "tags": [],
  #   "prob": 0.7,
  #   "post_func": None,
  #   "descs": ["一些华丽的鱼群吸引了你的注意...前方是一片错综复杂的海底洞穴...", "你忽然发现了一片绚丽的海底洞穴...", "这里出现了一片生态丰富的海底洞穴..."],
  #   "regions": [SeekRegion.DEEP_SEA],
  #   "can_quit": True,
  #   "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: not back and depth.value < 450,
  #   "decisions": [
  #     {
  #       "type": "normal",
  #       "tags": [],
  #       "names": ["探索此地", "探索洞穴"],
  #       "descs": ["你尝试进入这片洞穴搜刮...", "你觉得进去这里能找到好东西...", "你打算探索这片美丽的洞穴...", "你尝试游入洞穴探索..."],
  #       "tip": "[区域→]",
  #       "changes": {
  #       },
  #       "region_change": lambda last: SeekRegion.FOREST
  #     },
  #     {
  #       "type": "normal",
  #       "tags": [],
  #       "tip": "",
  #       "names": ["离开", "放弃", "放弃探索"],
  #       "descs": ["你觉得你可能进去这里后就出不来了...", "你觉得自己还不适合来这里探索", "你觉得你在这里无法判断深度，很可能出问题..."],
  #       "changes": {
  #       }
  #     },
  #   ]
  # },
  {
    # 返回事件
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": -1,
    "post_func": None,
    "descs": ["你总算离开了这个神秘的森林...", "在你的努力下，总算找到了森林的出口...", "你找到了森林的出口..."],
    "regions": [SeekRegion.FOREST],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: back and depth.value < 180,
    "changes": {
    },
    "region_change": lambda last: SeekRegion.DEEP_SEA,
  },
  {
    # 下潜事件
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": -1,
    "post_func": None,
    "descs": ["你尝试往前探索...", "你尝试探索更深处...", "你希望能通过探索找到点什么..."],
    "regions": [SeekRegion.FOREST],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: not back,
    "changes": {
      "depth": {
        "change": lambda: random.randint(-10, 32),
        "type": "+",
        "custom": False,
      },
      "oxygen": {
        "change": lambda: random.randint(0, 2),
        "type": "-",
        "custom": False,
      }
    }
  },
  {
    "type": "decision",
    "tags": [],
    "prob": 0.75,
    "post_func": None,
    "descs": ["你发现一个海底城市...要不要探索一下？", "你发现一片神秘的海底城市...要不要去探索一下？", "黑暗中出现了一片城市的轮廓...要去探索吗？"],
    "regions": [SeekRegion.SHALLOW_SEA, SeekRegion.DEEP_SEA, SeekRegion.TRENCH],
    "can_quit": True,
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: not back and depth.value > 230,
    "decisions": [
      {
        "type": "normal",
        "tags": [],
        "names": ["进入城市", "探索城市"],
        "descs": ["你进入了这座城市...", "你来到了这座城市...", "你开始对这座城市进行探险...", "你进入了这个城市..."],
        "tip": "[区域→]",
        "changes": {
        },
        "region_change": lambda last: SeekRegion.UNDERSEA_CITY
      },
      {
        "type": "normal",
        "tags": [],
        "tip": "",
        "names": ["离开", "放弃", "放弃探索"],
        "descs": ["你觉得探索这座城市太危险了", "你觉得自己还不适合来这里探索", "你觉得城市太危险了"],
        "changes": {
        }
      },
    ]
  },
  {
    "type": "decision",
    "tags": [],
    "prob": 0.5,
    "post_func": None,
    "descs": ["城市旁出现了一道峡谷，要不要离开城市去往更深处探险？", "你发现了一块悬崖，要不要离开城市去探索？", "这里有一块悬崖，要不要离开城市往更深处探索？"],
    "regions": [SeekRegion.UNDERSEA_CITY],
    "can_quit": True,
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: not back and depth.value > 230,
    "decisions": [
      {
        "type": "normal",
        "tags": [],
        "names": ["离开城市", "放弃城市"],
        "descs": ["你离开了这座城市，并往更深处下潜...", "你离开了这座城市...", "你离开城市以探索更深处...", "你离开了这个城市..."],
        "tip": "[深度++][区域-]",
        "changes": {
          "depth": {
            "change": lambda: random.randint(80, 200),
            "type": "+",
            "custom": False,
          }
        },
        "region_change": lambda last: last,
      },
      {
        "type": "normal",
        "tags": [],
        "tip": "",
        "names": ["留在城市", "继续探索城市"],
        "descs": ["你觉得这座城市还有东西没被发现", "你觉得这座城市还适合继续探索", "你觉得这座城市应该多探索一下"],
        "changes": {
        }
      },
    ]
  },
  {
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 5,
    "post_func": None,
    "descs": ["沉船里是不是冒出了一个触手...？", "沉船的结构突然发出了断裂声...", "你听到了结构断裂的响声...", "你好像看到了一只眼睛..."],
    "regions": [SeekRegion.SHIPWRECK],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: depth.value > 50,
    "changes": {
      "san": {
        "change": lambda: random.randint(1, 3),
        "type": "-",
        "custom": False,
      },
    },
  },
  {
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 5,
    "post_func": None,
    "descs": ["你感觉身边围着很多...人？", "你的身边出现了奇怪的声响...", "你似乎听到了\"船员\"的谈话...", "旁边似乎有什么东西消失了..."],
    "regions": [SeekRegion.SHADOWRECK],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: depth.value > 550,
    "changes": {
      "san": {
        "change": lambda: random.randint(3, 8),
        "type": "-",
        "custom": False,
      },
    },
  },
  {
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 2,
    "post_func": None,
    "descs": ["你找到了一些镇定剂", "你发现了一些祈愿好运的挂饰", "你拿到了一些镇定剂...", "你发现了此前的探险队遗留下来的痕迹..."],
    "regions": [SeekRegion.SHADOWRECK, SeekRegion.SHIPWRECK, SeekRegion.UNDERSEA_CITY],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: depth.value > 150,
    "changes": {
      "san": {
        "change": lambda: random.randint(4, 10),
        "type": "+",
        "custom": False,
      },
    },
  },
  {
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 3,
    "post_func": None,
    "descs": ["四周的光点整齐地排列，似乎对你的到来感到好奇...", "四周的光点围着你，似乎在打量着什么", "周围的光点排列成一种规则的几何图案，让你感到了一阵平静"],
    "regions": [SeekRegion.SHADOWRECK, SeekRegion.ABYSS, SeekRegion.VOID, SeekRegion.DEEPEST],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: depth.value > 900,
    "changes": {
      "san": {
        "change": lambda: random.randint(1, 7),
        "type": "+",
        "custom": False,
      },
    },
  },
  {
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 10.3,
    "top": True,
    "post_func": None,
    "descs": ["你发现了一些喷气孔", "你发现这里有一些气泡", "有一些气泡正在上浮...", "你发现了一些气泡", "你发现了一根气泡柱..."],
    "regions": [SeekRegion.DEEP_SEA, SeekRegion.UNDERSEA_CITY, SeekRegion.TRENCH, SeekRegion.ABYSS, SeekRegion.FOREST, SeekRegion.DEEPEST, SeekRegion.VOID],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: depth.value > 100,
    "changes": {
      "oxygen": {
        "change": lambda: random.randint(3, 12),
        "type": "+",
        "custom": False,
      }
    }
  },
  {
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 15,
    "post_func": None,
    "descs": ["你发现了一些密封的食物罐头", "你发现了一些保存妥善的零食", "你发现了一些密封的罐头", "你找到了一些吃的，看起来还能吃", "你发现了一些急救用品"],
    "regions": [SeekRegion.SHIPWRECK, SeekRegion.UNDERSEA_CITY],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: health.value < health.max_value,
    "changes": {
      "health": {
        "change": lambda: random.randint(1, 7),
        "type": "+",
        "custom": False,
      }
    }
  },
  {
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 15,
    "post_func": None,
    "descs": ["你发现了一些密封的食物罐头", "你发现了一些保存妥善的零食", "你发现了一些密封的罐头", "你找到了一些吃的，看起来还能吃", "你发现了一些急救用品"],
    "regions": [SeekRegion.SHIPWRECK, SeekRegion.UNDERSEA_CITY],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: health.value >= health.max_value,
    "changes": {
      "coins": {
        "change": lambda: random.randint(3, 10),
        "type": "+",
        "custom": False,
      }
    }
  },
  {
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 8,
    "post_func": None,
    "descs": ["你找到了一些物资", "你发现了一些他人遗留的资源", "你找到了一些物资箱子", "你发现了别人曾丢弃的物品", "你发现了一些物资"],
    "regions": [SeekRegion.UNDERSEA_CITY],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: True,
    "changes": {
      "coins": {
        "change": lambda: random.randint(10, 80),
        "type": "+",
        "custom": False,
      }
    }
  },
  {
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 7,
    "post_func": None,
    "descs": ["你找到了一些物资？", "物资箱里是许多奇怪的光点...", "你找到了一些物资箱子...里面是阴影", "你发现了别人曾丢弃的物品...的暗影", "你发现了一些蠕动的生物..."],
    "regions": [SeekRegion.SHADOWRECK],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: True,
    "changes": {
      "coins": {
        "change": lambda: random.randint(10, 80),
        "type": "+",
        "custom": False,
      }
    }
  },
  {
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 10,
    "post_func": None,
    "descs": ["你发现了一些氧气瓶", "你发现了一些氧气罐", "这里有些氧气瓶", "你找到了一些应急气罐"],
    "regions": [SeekRegion.SHIPWRECK, SeekRegion.UNDERSEA_CITY],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: True,
    "changes": {
      "oxygen": {
        "change": lambda: random.randint(3, 20),
        "type": "+",
        "custom": False,
      }
    }
  },
  {
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 10,
    "post_func": None,
    "descs": ["你发现了一些...氧气瓶？", "你发现了一个被阴影覆盖的氧气瓶...", "你找到一个黑暗的氧气瓶..."],
    "regions": [SeekRegion.SHADOWRECK],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: True,
    "changes": {
      "oxygen": {
        "change": lambda: random.randint(6, 30),
        "type": "+",
        "custom": False,
      }
    }
  },
  {
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    # "prob": 0.1,
    "prob": 0.065,
    "post_func": None,
    "descs": ["你忽然晕了过去...随后醒来在了一个奇怪的地方...", "你好像感觉到了一阵温暖...但你知道...你很快就要死了。", "你晕了过去...但是你一定不会想知道发生了什么的..."],
    "regions": [SeekRegion.SHALLOW_SEA],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: True,
    "changes": {
      "oxygen": {
        "change": lambda: random.randint(1, 25),
        "type": "-",
        "custom": False,
      },
      "san": {
        "change": lambda: random.randint(20, 50),
        "type": "-",
        "custom": False,
      },
      "depth": {
        "change": lambda: random.randint(1100, 1300),
        "type": "+",
        "custom": False,
      },
      "coins": {
        "change": lambda: 666,
        "type": "+",
        "custom": False,
      },
    },
    "region_change": lambda last: SeekRegion.ABYSS,
  },
  {
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    # "prob": 0.1,
    "prob": 0.03,
    "post_func": None,
    "descs": ["\"我很喜欢看你们不知所措的样子\"...你好像听到了什么？", "你忽然感到一阵强烈的头疼，随后晕了过去...醒来在了一个奇怪的地方", "你晕了过去...或许你根本无法理解刚刚发生了什么..."],
    "regions": [SeekRegion.SHALLOW_SEA],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: True,
    "changes": {
      "san": {
        "change": lambda: random.randint(15, 32),
        "type": "-",
        "custom": False,
      },
      "chance": {
        "change": lambda: random.randint(7, 9),
        "type": "+",
        "custom": False,
      },
      "depth": {
        "change": lambda: random.randint(2000, 2300),
        "type": "+",
        "custom": False,
      },
      "oxygen": [{
        "change": lambda v: v.change_max(lambda x: random.randint(190, 210)),
        "return": lambda v: v.max_value,
        "return_msg": "最大{name} = {value}",
        "custom": True,
        "assign": False,
      }, {
        "change": lambda: random.randint(90, 110),
        "type": "+",
        "custom": False,
      }],
    },
    "region_change": lambda last: SeekRegion.DEEPEST,
  },
  # {
  #   "type": "normal",
  #   "tags": [],
  #   # 概率 -1 为默认事件
  #   # "prob": 0.1,
  #   "prob": 100,
  #   "top": True,
  #   "post_func": None,
  #   "descs": ["（测试）我很好奇你会怎么做..."],
  #   "regions": [SeekRegion.SHALLOW_SEA],
  #   "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, events, is_sim, *args: not back and is_sim,
  #   "changes": {
  #     "depth": {
  #       "change": lambda: random.randint(3600, 3800),
  #       "type": "+",
  #       "custom": False,
  #     },
  #   },
  #   "region_change": lambda last: SeekRegion.VOID,
  # },
  {
    "type": "normal",
    "tags": ["oxy_full"],
    # 概率 -1 为默认事件
    "prob": 100,
    "top": True,
    "post_func": None,
    "descs": ["氧气充足的状态让你感到精神充沛", "有了这么多的氧气，你觉得你可以继续你的探险", "获得了如此充足的氧气让你下定了决心"],
    "regions": [],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, events_encountered, *args: not events_encountered.get("oxy_full", False) and oxygen.value >= 160,
    "changes": {
      "chance": {
        "change": lambda: random.randint(4, 5),
        "type": "+",
        "custom": False,
      }
    }
  },
  {
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 5,
    "post_func": None,
    "descs": ["你发现了一些空的氧气瓶", "你发现了一些小气罐", "你找到了一些能被你使用的应急气罐", "你找到了完好的空氧气罐"],
    "regions": [SeekRegion.SHIPWRECK, SeekRegion.UNDERSEA_CITY],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: True,
    "changes": {
      "oxygen": {
        "change": lambda v: v.change_max(lambda x: x + random.randint(1, 15)),
        "return": lambda v: v.max_value,
        "return_msg": "最大{name} = {value}",
        "custom": True,
        "assign": False,
      },
    }
  },
  {
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 5,
    "post_func": None,
    "descs": ["你发现了一些氧气瓶", "你发现了一些小气罐", "你找到了一些能被你使用的应急气罐", "你找到了完好的氧气罐"],
    "regions": [SeekRegion.SHIPWRECK, SeekRegion.UNDERSEA_CITY],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: True,
    "changes": {
      "oxygen": {
        "change": lambda: random.randint(9, 19),
        "type": "+",
        "custom": False,
      },
    }
  },
  {
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 5,
    "post_func": None,
    "descs": ["你发现了一些氧气瓶...应该是吧", "你发现了一些...或许是氧气瓶的东西", "这些黑暗的罐体曾经可能是应急气罐..."],
    "regions": [SeekRegion.SHADOWRECK],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: True,
    "changes": {
      "oxygen": [{
        "change": lambda: random.randint(1, 25),
        "type": "+",
        "custom": False,
      }, {
        "change": lambda v: v.change_max(lambda x: x + random.randint(5, 20)),
        "return": lambda v: v.max_value,
        "return_msg": "最大{name} = {value}",
        "custom": True,
        "assign": False,
      }],
    }
  },
  {
    "type": "decision",
    "tags": [],
    "prob": 2,
    "post_func": None,
    "descs": ["你发现了一艘沉船...要不要探索一下？", "出现了一艘沉船...要不要去探索一下？", "你看到了一艘沉船...要去探索吗？"],
    "regions": [SeekRegion.SHALLOW_SEA, SeekRegion.DEEP_SEA],
    "can_quit": True,
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: not back and depth.value > 60,
    "decisions": [
      {
        "type": "normal",
        "tags": [],
        "names": ["进入沉船", "探索沉船"],
        "descs": ["你进入了沉船...", "你来到了沉船的内部...", "你游入了沉船...", "你游入了这艘沉船..."],
        "tip": "[区域→]",
        "changes": {
        },
        "region_change": lambda last: SeekRegion.SHIPWRECK
      },
      {
        "type": "normal",
        "tags": [],
        "tip": "",
        "names": ["离开", "放弃", "放弃探索"],
        "descs": ["你不打算探索这艘沉船。", "你放弃了对沉船的探索。", "你没有尝试探索这艘沉船。"],
        "changes": {
        }
      },
    ]
  },
  {
    "type": "decision",
    "tags": [],
    "prob": 1.6,
    "post_func": None,
    "descs": ["出现了一艘被阴影包裹着的沉船...你看不清它的具体样貌，但是或许可以进入搜刮？", "你发现了一艘包裹着阴影的沉船...是否要进去探险？"],
    "regions": [SeekRegion.TRENCH, SeekRegion.ABYSS, SeekRegion.DEEPEST, SeekRegion.VOID],
    "can_quit": True,
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: not back and depth.value > 60,
    "decisions": [
      {
        "type": "normal",
        "tags": [],
        "names": ["进入沉船", "探索沉船"],
        "descs": ["你进入了阴影中的沉船...", "你游进了黑暗的沉船..."],
        "tip": "[区域→]",
        "changes": {
        },
        "region_change": lambda last: SeekRegion.SHADOWRECK
      },
      {
        "type": "normal",
        "tags": [],
        "tip": "",
        "names": ["离开", "放弃", "放弃探索"],
        "descs": ["你感觉这艘奇怪的沉船有点危险。", "你放弃了对沉船的探索。", "你没有尝试探索这艘奇怪的沉船。"],
        "changes": {
        }
      },
    ]
  },
  {
    "type": "dice",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 4,
    "post_func": shark_post,
    "event_messages": [
      {
        # 什么都没有是所有地区都可
        "regions": [SeekRegion.SHALLOW_SEA, SeekRegion.DEEP_SEA, SeekRegion.UNDERSEA_CITY, SeekRegion.UNDERSEA_CAVE],
        "descs": ["出现了一只鲨鱼！", "突然有一只鲨鱼朝你冲来！", "有一只鲨鱼冲来！"],
        "ok_msgs": ["你奋力反击，打败了鲨鱼。", "在你的努力下，鲨鱼被击败了。", "你成功招架住了鲨鱼的攻击，随后趁着机会逃离了。", "你奋力反击，赶跑了鲨鱼。", "在你不懈的努力下，成功打败了鲨鱼。"],
        "bigwin_msgs": ["你察觉到了鲨鱼的姿态，瞬间命中要害打败了鲨鱼！", "你在一瞬间击中了鲨鱼的要害，鲨鱼被你击败了！", "你反应过来，成功攻击到鲨鱼的眼睛！趁着眩晕，你迅速离开了。", "你反应过来，瞬间躲避开，并且趁机打晕了鲨鱼逃跑。"],
        "fail_msgs": ["你招架不住鲨鱼的攻击，受了一些伤。", "你被鲨鱼撞得不知所措。", "鲨鱼冲上来咬了你一口，你根本没反应过来。", "你想挡住鲨鱼的攻击，可惜它的力量太大了。", "鲨鱼冲到了你的面前，在你反应过来之前咬了你一口..."],
        "bigfail_msgs": ["你完全没反应过来，被鲨鱼狠狠咬了一口！", "你尝试招架它，但是后面还有一只鲨鱼！", "鲨鱼的攻击被拦下了...不对，有两只鲨鱼！", "你尝试攻击鲨鱼，却打空了，随后被鲨鱼狠狠地咬了一口！", "鲨鱼的力量实在太大，你根本阻挡不住攻击..."],
      },
      {
        # 什么都没有是所有地区都可
        "regions": [SeekRegion.DEEP_SEA, SeekRegion.UNDERSEA_CITY, SeekRegion.UNDERSEA_CAVE],
        "descs": ["出现了一只大章鱼！", "突然有一只章鱼朝你发起攻击！", "有一只大章鱼冒了出来！"],
        "ok_msgs": ["你奋力反击，打败了章鱼。", "在你的努力下，章鱼被打跑了。", "你成功招架住了章鱼的攻击，随后趁着机会逃离了。", "你奋力反击，赶跑了章鱼。", "在你不懈的努力下，成功打败了章鱼。"],
        "bigwin_msgs": ["章鱼的触手被你一一截断，这只章鱼根本不是你的对手。", "你在一瞬间击中了章鱼的要害，章鱼被你打败了！", "你反应过来，成功截断了章鱼的触手！趁着章鱼受伤，你迅速离开了。", "你反应过来，瞬间躲避开，并且利落地砍断了它的触手。"],
        "fail_msgs": ["你招架不住章鱼的攻击，受了一些伤。", "你被章鱼撞得不知所措。", "章鱼冲上来把你死死捆住，你花了半天才挣脱开。", "你想挡住章鱼的攻击，可惜它的触手太多了。", "章鱼冲到了你的面前，用触手把你团团包围了..."],
        "bigfail_msgs": ["你完全没反应过来，被章鱼死死的捆住了！", "你完全拦不住它的攻击...！", "章鱼太大了，你根本防不住它..."],
      },
      {
        # 什么都没有是所有地区都可
        "regions": [SeekRegion.UNDERSEA_CITY, SeekRegion.TRENCH, SeekRegion.ABYSS, SeekRegion.FOREST, SeekRegion.VOID, SeekRegion.DEEPEST],
        "descs": ["一个黑影逼近...", "你看到了一道黑影...", "你发现了一个不寻常的黑影...", "忽然闪过一团黑影..."],
        "ok_msgs": ["黑影突然冲了过来！但是你反应过来，干掉了它。", "黑影忽然把你包围了！但是在你的反击下，黑影逐渐消失了...", "黑影将你团团包围...但是被你反击开了。"],
        "bigwin_msgs": [f"你顺势攻击，黑影忽然消散了，变成了一堆{coin_name}...？", "你似乎察觉到了什么，瞬间朝黑影攻击！它即刻飘散了...", "黑影消失了...但是你的身边似乎多了一点东西...", "黑影突然冲来！但是你早有准备，一击挡住了它！它忽然消散了。"],
        "fail_msgs": ["黑影将你团团包围！你突然两眼一黑，随后在一块石头旁醒来..."," 黑影突然冲了过来！你没反应过来，遭到了一阵强烈的撞击...",],
        "bigfail_msgs": ["你被黑影包围，随后失去了知觉...", "黑影忽然冲向了你！你完全没有反应过来，被强烈的冲击撞晕了..."],
      },
    ],
    "regions": [SeekRegion.DEEP_SEA, SeekRegion.UNDERSEA_CITY, SeekRegion.UNDERSEA_CAVE, SeekRegion.TRENCH, SeekRegion.FOREST, SeekRegion.SHALLOW_SEA, SeekRegion.ABYSS, SeekRegion.DEEPEST, SeekRegion.VOID],
    "dice_faces": lambda: random.randint(5, 29),
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: depth.value > 40,
    "determine_attr": "combat",
    "ok": {
      "changes": {
        "coins": {
          "change": lambda: random.randint(5, 28),
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
          "change": lambda: random.randint(10, 50),
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
          "change": lambda: random.randint(10, 20),
          "type": "-",
          "custom": False,
        },
        "coins": {
          "change": lambda: random.randint(0, 30),
          "type": "-",
          "custom": False,
        }
      },
    },
    "big_fail": {
      "changes": {
        "oxygen": {
          "change": lambda: random.randint(12, 30),
          "type": "-",
          "custom": False,
        },
        "health": {
          "change": lambda: random.randint(15, 35),
          "type": "-",
          "custom": False,
        },
        "coins": {
          "change": lambda: random.randint(10, 50),
          "type": "-",
          "custom": False,
        }
      },
    },
  },
  {
    "type": "dice",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 4,
    "post_func": None,
    "event_messages": [
      {
        # 什么都没有是所有地区都可
        "regions": [],
        "descs": ["你似乎看到了一个柜子？", "你好像在墙角看到了什么？", "你好像看到了什么有趣的东西...",],
        "ok_msgs": ["原来是一个物资箱...还好你看到了它", "你走上前，发现是一个物资储备箱...", "原来是一个箱子...", "原来是一个很不起眼的物资储备箱..."],
        "bigwin_msgs": ["原来是隐蔽的宝藏箱！看看里面究竟有什么好东西...", "原来是大型物资柜！这下有得搜刮了。", "看来是一个被遗弃已久的宝箱！"],
        "fail_msgs": ["看来你只是看错了...那里什么都没有", "光线太暗，你大概是看错了...", "好吧，刚刚只是错觉...", "看来只是错觉...什么也没有。"],
        "bigfail_msgs": ["不对，那是...什么？它扑上来了！", "不对，它向你冲过来了...！", "不对...这个东西突然扑过来了！", "这不是什么有趣的东西...这就是一只怪物！"],
      },
    ],
    "regions": [SeekRegion.SHIPWRECK, SeekRegion.UNDERSEA_CITY, SeekRegion.SHADOWRECK],
    "dice_faces": lambda: random.randint(8, 25),
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: depth.value > 100,
    "determine_attr": "insight",
    "ok": {
      "changes": {
        "coins": {
          "change": lambda: random.randint(15, 70),
          "type": "+",
          "custom": False,
        },
        "oxygen": {
          "change": lambda: random.randint(0, 8),
          "type": "+",
          "custom": False,
        },
      },
    },
    "big_win": {
      "changes": {
        "coins": {
          "change": lambda: random.randint(100, 150),
          "type": "+",
          "custom": False,
        },
        "combat": {
          "change": lambda: random.randint(0, 1),
          "type": "+",
          "custom": False,
        },
        "insight": {
          "change": lambda: random.randint(1, 3),
          "type": "+",
          "custom": False,
        },
        "oxygen": {
          "change": lambda: random.randint(5, 20),
          "type": "+",
          "custom": False,
        }
      },
    },
    "fail": {
      "changes": {
      },
    },
    "big_fail": {
      "changes": {
        "oxygen": {
          "change": lambda: random.randint(5, 12),
          "type": "-",
          "custom": False,
        },
        "health": {
          "change": lambda: random.randint(5, 30),
          "type": "-",
          "custom": False,
        },
        "san": {
          "change": lambda: random.randint(3, 10),
          "type": "-",
          "custom": False,
        },
      },
    },
  },
  {
    "type": "dice",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 2,
    "post_func": None,
    "event_messages": [
      {
        # 什么都没有是所有地区都可
        "regions": [],
        "descs": ["沉船的结构突然断裂了！", "沉船突然塌陷了下去！", "这艘船的结构忽然断裂了！", "沉船忽然断开了！"],
        "ok_msgs": ["你敏捷地躲过了塌陷的结构，但是这艘船已经彻底没有价值了...", "所幸你没有因此受到一点伤，但是这艘船也没有什么探索的必要了。", "你灵敏地躲开了这些结构，但是这艘船也彻底损坏了..."],
        "bigwin_msgs": ["你敏捷地躲过了塌陷的结构，随后发现坍塌的地方居然还藏着一堆救生用品。", "所幸你没有被断裂的结构砸中，而且你还看到一个隐蔽的物资箱...", "坍塌的结构并没有砸到你，而且还让你发现了一块隐藏的物资存放点。"],
        "fail_msgs": ["你没反应过来，被坍塌的结构砸中了...", "坍塌的结构太多了，你根本躲不过去...", "你没有躲过，被坍塌的船体砸中了..."],
        "bigfail_msgs": ["坍塌的结构把你完全压住了...你废了好大劲才脱身", "坍塌的结构实在太大，你根本躲不过去，被压住了...", "结构坍塌后把你压倒在了地上...你花了好久才脱身"],
      },
    ],
    "regions": [SeekRegion.SHIPWRECK, SeekRegion.SHADOWRECK],
    "dice_faces": lambda: random.randint(8, 25),
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: depth.value > 100,
    "determine_attr": "insight",
    "ok": {
      "changes": {
      },
      "region_change": lambda last: last,
    },
    "big_win": {
      "region_change": lambda last: last,
      "changes": {
        "coins": {
          "change": lambda: random.randint(70, 120),
          "type": "+",
          "custom": False,
        },
        "health": {
          "change": lambda: random.randint(5, 10),
          "type": "+",
          "custom": False,
        },
        "oxygen": {
          "change": lambda: random.randint(5, 20),
          "type": "+",
          "custom": False,
        }
      },
    },
    "fail": {
      "region_change": lambda last: last,
      "changes": {
        "health": {
          "change": lambda: random.randint(5, 14),
          "type": "-",
          "custom": False,
        },
      },
    },
    "big_fail": {
      "region_change": lambda last: last,
      "changes": {
        "oxygen": {
          "change": lambda: random.randint(5, 12),
          "type": "-",
          "custom": False,
        },
        "health": {
          "change": lambda: random.randint(10, 30),
          "type": "-",
          "custom": False,
        }
      },
    },
  },
  {
    "type": "decision",
    "tags": [],
    "prob": 2,
    "post_func": None,
    "descs": ["这里似乎有一些日志...要不要看看？", "你发现了一些笔记...或许可以查看一下？", "你发现了一些保存完好的手稿...要打开看看吗？"],
    "regions": [SeekRegion.SHIPWRECK, SeekRegion.UNDERSEA_CITY, SeekRegion.SHADOWRECK],
    "can_quit": True,
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: not back and depth.value > 150,
    "decisions": [
      {
        "type": "dice",
        "tags": [],
        "names": ["阅读", "翻阅", "查看"],
        "tip": "[???]",
        "event_messages": [
          {
            # 什么都没有是所有地区都可
            "regions": [],
            "descs": ["让我看看它究竟写了些什么...", "既然都来了，还是打开看看吧..."],
            "ok_msgs": ["有意思的内容...或许能给我一些启发。", "通过里面的内容，你获得了一些启发。", "有了前车之鉴，你觉得你会更不容易陷入灾难中...", "你多了些许对这个世界的了解...", "你了解了一些有关海底文明的东西。"],
            "bigwin_msgs": ["你好像知道了些什么，顿时充满了探险的决心。", "翻阅完后，你感觉自己充满了力量", "你从里面获得了极大的启发...", "你对这个世界的理解忽然地加深了"],
            "fail_msgs": ["你不应该翻阅它的...", "翻阅...什么？它怎么在我眼前消失了...", "你看到了一些不该看到的东西...", "它们根本就不是什么笔记日志之类的东西..."],
            "bigfail_msgs": ["你翻阅了它，随后再也不想看第二次了...", "你觉得你阅读它是你此生最大的错误...", "你似乎没有信心再探险下去了..."],
          },
        ],
        # "regions": [SeekRegion.SHIPWRECK, SeekRegion.UNDERSEA_CITY],
        "dice_faces": lambda: random.randint(6, 25),
        "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: True,
        "determine_attr": "mental",
        "ok": {
          "changes": {
            "san": {
              "change": lambda: random.randint(3, 12),
              "type": "+",
              "custom": False,
            },
            "insight": {
              "change": lambda: random.randint(0, 1),
              "type": "+",
              "custom": False,
            },
          },
        },
        "big_win": {
          "changes": {
            "chance": {
              "change": lambda: random.randint(1, 5),
              "type": "+",
              "custom": False,
            },
            "insight": [{
              "change": lambda: random.randint(2, 4),
              "type": "+",
              "custom": False,
            }, {
              "change": lambda v: v.change_max(lambda x: x + random.randint(1, 3)),
              "return": lambda v: v.max_value,
              "return_msg": "最大{name} = {value}",
              "custom": True,
              "assign": False,
            },],
          },
        },
        "fail": {
          "changes": {
            "san": {
              "change": lambda: random.randint(5, 15),
              "type": "-",
              "custom": False,
            },
          },
        },
        "big_fail": {
          "changes": {
            "chance": {
              "change": lambda: random.randint(1, 2),
              "type": "-",
              "custom": False,
            },
            "san": {
              "change": lambda: random.randint(10, 20),
              "type": "-",
              "custom": False,
            },
          },
        },
      },

      {
        "type": "normal",
        "tags": [],
        "tip": "",
        "names": ["算了", "放弃", "无视", "离开"],
        "descs": ["你不打算翻阅这些没用的文件。", "你觉得这些文件没必要翻阅。", "你觉得这些手稿没什么帮助。", "你觉得对于这些东西还是不要太过于好奇。"],
        "changes": {
        }
      },
    ]
  },
]
