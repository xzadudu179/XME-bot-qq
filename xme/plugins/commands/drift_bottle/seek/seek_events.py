from .classes.player import SeekRegion, Player
from xme.plugins.commands.xme_user.classes.user import coin_name, coin_pronoun
import random
import uuid

def shark_post(p: Player):
  if p.is_die()[0] and p.region.value == SeekRegion.SHALLOW_SEA:
    p.achieved_achievements.append("你需要一艘更大的船"),

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
    "regions": [SeekRegion.DEEP_SEA, SeekRegion.SHIPWRECK, SeekRegion.UNDERSEA_CITY, SeekRegion.TRENCH, SeekRegion.SHALLOW_SEA],
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
    "prob": 4,
    "post_func": None,
    "descs": ["你收集到了一些神秘的发光物体...", "你发现了几个发着光的球体...", "你捕捉到了一些黑影..."],
    "regions": [SeekRegion.ABYSS],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: depth.value > 900,
    "changes": {
      "coins": {
        "change": lambda: random.randint(50, 120),
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
    "regions": [SeekRegion.ABYSS, SeekRegion.FOREST, SeekRegion.SHIPWRECK, SeekRegion.TRENCH, SeekRegion.UNDERSEA_CITY, SeekRegion.UNDERSEA_CAVE],
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
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: back == False and depth.value < 150,
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
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: back == False and depth.value > 70,
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
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: back == False,
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
    # 返回事件
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": -1,
    "post_func": None,
    "descs": ["你奋力地往上游...", "你尽全力往上游去...", "你尽力地往上游...", "你感觉到水压越来越小..."],
    "regions": [],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: back == True,
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
    "prob": 100,
    "post_func": None,
    "top": True,
    "descs": ["你回到了海面", "你回到了海上"],
    "regions": [SeekRegion.SHALLOW_SEA],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: back and depth.value <= 0,
    "changes": {
      "oxygen": {
        "change": lambda: 10000,
        "type": "+",
        "custom": False,
      },
      "san": {
        "change": lambda: 3,
        "type": "*",
        "custom": False,
      }
    }
  },
  {
    # 返回事件
    "type": "normal",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": -1,
    "post_func": None,
    "descs": ["你需要往回走。", "你觉得你应该先回去了。", "你不觉得你还有时间继续探索这艘船了。"],
    "regions": [SeekRegion.SHIPWRECK],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: back == True,
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
    "regions": [SeekRegion.TRENCH, SeekRegion.FOREST],
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
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: depth.value > 120,
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
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: depth.value <= 100,
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
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: health.value >= health.max_value * 0.85 and (oxygen.value >= oxygen.max_value * 0.85 or oxygen.value >= 110) and san.value >= san.max_value * 0.85 and depth.value > 105 and coins.value > 200,
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
    "prob": 6,
    "post_func": None,
    "descs": ["你觉得这一切还不应该结束", "你觉得你还有精力继续探险", "你下定了探索的决心", "你知道你这次探险一定能成功"],
    "regions": [SeekRegion.DEEP_SEA, SeekRegion.SHALLOW_SEA, SeekRegion.TRENCH],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: health.value >= health.max_value * 0.9 and oxygen.value >= oxygen.max_value * 0.9 and san.value >= san.max_value * 0.9 and depth.value > 150 and coins.value > 240 and chance.value <= 3,
    "changes": {
      "chance": {
        "change": lambda: random.randint(2, 5),
        "type": "+",
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
    "regions": [SeekRegion.DEEP_SEA, SeekRegion.SHIPWRECK, SeekRegion.UNDERSEA_CITY, SeekRegion.TRENCH, SeekRegion.SHALLOW_SEA],
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
    "regions": [SeekRegion.DEEP_SEA, SeekRegion.SHIPWRECK, SeekRegion.UNDERSEA_CITY, SeekRegion.TRENCH, SeekRegion.SHALLOW_SEA],
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
    "regions": [SeekRegion.DEEP_SEA, SeekRegion.SHIPWRECK, SeekRegion.UNDERSEA_CITY, SeekRegion.TRENCH, SeekRegion.SHALLOW_SEA],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: san.value < 60,
    "changes": {
      "oxygen": {
        "change": lambda: random.randint(5, 8),
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
    "regions": [SeekRegion.DEEP_SEA, SeekRegion.SHIPWRECK, SeekRegion.UNDERSEA_CITY, SeekRegion.TRENCH, SeekRegion.SHALLOW_SEA],
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
        "change": lambda: random.randint(0, 3),
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
        "change": lambda: random.randint(1, 4),
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
    "regions": [SeekRegion.UNDERSEA_CITY, SeekRegion.DEEP_SEA, SeekRegion.TRENCH, SeekRegion.ABYSS, SeekRegion.FOREST, SeekRegion.UNDERSEA_CAVE],
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
    "regions": [SeekRegion.SHIPWRECK],
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
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: back == True,
    "changes": {
    },
    "region_change": lambda last: last,
  },
  {
    "type": "decision",
    "tags": [],
    "prob": 0.5,
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
        "tip": "[深度+][区域-]",
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
    "prob": 10,
    "post_func": None,
    "descs": ["你发现了一些喷气孔", "你发现这里有一些气泡", "有一些气泡正在上浮...", "你发现了一个气孔", "你发现了一根气泡柱..."],
    "regions": [SeekRegion.DEEP_SEA, SeekRegion.UNDERSEA_CITY, SeekRegion.TRENCH, SeekRegion.ABYSS, SeekRegion.FOREST],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: depth.value > 100,
    "changes": {
      "oxygen": {
        "change": lambda: random.randint(3, 15),
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
    "prob": 10,
    "post_func": None,
    "descs": ["你发现了一些氧气瓶", "你发现了一些氧气罐", "这里有些氧气瓶", "你找到了一些应急气罐"],
    "regions": [SeekRegion.SHIPWRECK, SeekRegion.UNDERSEA_CITY],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: True,
    "changes": {
      "oxygen": {
        "change": lambda: random.randint(3, 15),
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
    "prob": 0.085,
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
    "prob": 5,
    "post_func": None,
    "descs": ["你发现了一些空的氧气瓶", "你发现了一些小气罐", "你找到了一些能被你使用的应急气罐", "你找到了完好的空氧气罐"],
    "regions": [SeekRegion.SHIPWRECK, SeekRegion.UNDERSEA_CITY],
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: True,
    "changes": {
      "oxygen": {
        "change": lambda: random.randint(1, 15),
        "type": "+",
        "custom": False,
      },
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
        "descs": ["你进入了沉船...", "你来到了沉船的内部...", "你走进了沉船...", "你走进了这艘沉船..."],
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
    "type": "dice",
    "tags": [],
    # 概率 -1 为默认事件
    "prob": 5,
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
        "regions": [SeekRegion.UNDERSEA_CITY, SeekRegion.TRENCH, SeekRegion.ABYSS, SeekRegion.FOREST],
        "descs": ["一个黑影逼近...", "你看到了一道黑影...", "你发现了一个不寻常的黑影...", "忽然闪过一团黑影..."],
        "ok_msgs": ["黑影突然冲了过来！但是你反应过来，干掉了它。", "黑影忽然把你包围了！但是在你的反击下，黑影逐渐消失了...", "黑影将你团团包围...但是被你反击开了。"],
        "bigwin_msgs": [f"你顺势攻击，黑影忽然消散了，变成了一堆{coin_name}...？", "你似乎察觉到了什么，瞬间朝黑影攻击！它即刻飘散了...", "黑影消失了...但是你的身边似乎多了一点东西...", "黑影突然冲来！但是你早有准备，一击挡住了它！它忽然消散了。"],
        "fail_msgs": ["黑影将你团团包围！你突然两眼一黑，随后在一块石头旁醒来..."," 黑影突然冲了过来！你没反应过来，遭到了一阵强烈的撞击...",],
        "bigfail_msgs": ["你被黑影包围，随后失去了知觉...", "黑影忽然冲向了你！你完全没有反应过来，被强烈的冲击撞晕了..."],
      },
    ],
    "regions": [SeekRegion.DEEP_SEA, SeekRegion.UNDERSEA_CITY, SeekRegion.UNDERSEA_CAVE, SeekRegion.TRENCH, SeekRegion.FOREST, SeekRegion.SHALLOW_SEA, SeekRegion.ABYSS],
    "dice_faces": lambda: random.randint(5, 25),
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
          "change": lambda: random.randint(5, 10),
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
          "change": lambda: random.randint(12, 25),
          "type": "-",
          "custom": False,
        },
        "health": {
          "change": lambda: random.randint(12, 25),
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
    "regions": [SeekRegion.SHIPWRECK, SeekRegion.UNDERSEA_CITY],
    "dice_faces": lambda: random.randint(8, 25),
    "condition": lambda health, san, oxygen, combat, insight, mental, coins, tools, depth, back, chance, *args: depth.value > 100,
    "determine_attr": "insight",
    "ok": {
      "changes": {
        "coins": {
          "change": lambda: random.randint(15, 60),
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
          "change": lambda: random.randint(70, 120),
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
    "regions": [SeekRegion.SHIPWRECK],
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
    "regions": [SeekRegion.SHIPWRECK, SeekRegion.UNDERSEA_CITY],
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
            "insight": {
              "change": lambda: random.randint(0, 1),
              "type": "+",
              "custom": False,
            },
            "san": {
              "change": lambda: random.randint(3, 12),
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
            "insight": {
              "change": lambda: random.randint(2, 4),
              "type": "+",
              "custom": False,
            },
            "insight": {
              "change": lambda v: v.change_max(lambda x: x + random.randint(1, 3)),
              "return": lambda v: v.max_value,
              "return_msg": "最大{name} = {value}",
              "custom": True,
              "assign": False,
            },
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
