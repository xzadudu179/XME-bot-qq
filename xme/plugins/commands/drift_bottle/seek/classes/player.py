from xme.xmetools.randtools import html_messy_string
from xme.xmetools.typetools import use_attribute
import random
from enum import Enum
from xme.plugins.commands.xme_user.classes.user import coin_name
from xme.xmetools.colortools import mix_hex_color_lab
from xme.xmetools.debugtools import debug_msg
from nonebot.log import logger

# 寻宝区域
class SeekRegion(Enum):
    SHALLOW_SEA = "浅海"
    DEEP_SEA = "深海"
    SHIPWRECK = "沉船"
    SHADOWRECK = "阴影船骸"
    TRENCH = "海沟"
    UNDERSEA_CITY = "深海城市"
    ABYSS_CITY = "深渊城市"
    UNDERSEA_CAVE = "海底洞穴"
    ABYSS = "深渊"
    DEEPEST = "溟渊"
    VOID = "虚境"
    # 设计于会让人迷路的危险区域
    FOREST = "扭曲森林"

class PlayerAttr:
    def __init__(self, name, value, max_value=-1, show=True, detail=True):
        self.name = name
        self.value = value
        # 属性最大值，如果是 -1 那就是无上限
        self.max_value = max_value
        # 是否显示和是否显示详情
        self.show = show
        self.detail = detail

    def __int__(self):
        if isinstance(self.value, int):
            return self.value
        raise ValueError(f"属性 {self.value} 无法转为 int")

    def custom_change(self, set_method, return_method, assign=True):
        # 自定义修改属性值
        debug_msg("assign", assign)
        if assign:
            changed_value = set_method(self.value)
            self.value = changed_value
            debug_msg("value1", self.value)
            debug_msg("return_method1", return_method(self.value))
            return return_method(changed_value)
        else:
            set_method(self)
            debug_msg("value2", self)
            debug_msg("return_method2", return_method(self))
            return return_method(self)

    def change(self, set_method) -> int:
        """修改属性值，其中属性会被限制在 0 与最大值之间

        Args:
            set_method (Callable): 修改方法，传入参数是属性值

        Returns:
            int: 修改后的属性值
        """
        changed_value = set_method(self.value)
        if changed_value > self.max_value and self.max_value != -1:
            changed_value = self.max_value
        elif changed_value < 0:
            changed_value = 0
        self.value = changed_value
        return changed_value

    def change_max(self, set_method) -> int:
        """修改属性最大值，其中如果最大值比属性当前值小则将属性当前值改为最大值

        Args:
            set_method (Callable): 修改方法，传入参数是属性最大值

        Returns:
            int: 修改后的属性最大值
        """
        change_value = set_method(self.max_value)
        if change_value < 0:
            change_value = 0
        if change_value < self.value:
            self.value = change_value
        self.max_value = change_value
        return change_value


# 玩家
class Player:
    def __init__(self, health=100, oxygen=100, san=100, combat=10, insight=10, mental=10, coins=0, tools=[]):
        from .tool import Tool
        # 基本属性
        self.health = PlayerAttr("生命值", health, 100)
        self.oxygen = PlayerAttr("氧气值", oxygen, 100)
        self.san = PlayerAttr("san 值", san, 100)
        # 战斗力
        self.combat = PlayerAttr("战斗力", combat, 20)
        # 洞察力
        self.insight = PlayerAttr("洞察力", insight, 20)
        # 精神力
        self.mental = PlayerAttr("精神力", mental, 20)
        # 星币
        self.coins = PlayerAttr(f"{coin_name}数", coins)
        # 道具
        self.tools: list[Tool] = tools
        # 区域
        self.region = PlayerAttr(f"区域", SeekRegion.SHALLOW_SEA)
        self.last_region = PlayerAttr(f"上个区域", SeekRegion.SHALLOW_SEA, show=False)

        # 探险深度，目前想法是每走一步深度会随机加减
        self.depth = PlayerAttr(f"深度", 0, max_value=6666, detail=False)
        # 是否往回走
        self.back = False
        # 机会
        self.chance = PlayerAttr(f"剩余机会", 10, show=False)

        # 遇到过的事件（存uid）
        self.events_encountered: dict[bool] = {}

        # 得到的成就
        self.achieved_achievements: list[str] = []

    def post_process(self, custom_func: None):
        # 事件后执行的一些方法
        if custom_func is not None:
            custom_func(self)
        # 其他处理写这里

    def change_region(self, change_func, html=True):
        temp = self.last_region.value
        self.last_region.value = self.region.value
        self.region.value = change_func(temp)
        # self.region = region
        # if (self.last_region == SeekRegion.SHIPWRECK and self.region == SeekRegion.SHIPWRECK):
            # self.last_region = SeekRegion.SHALLOW_SEA
        last = self.last_region.value.value
        curr = self.region.value.value
        last = html_messy_string(last, self.get_messy_rate(), html=html)
        curr = html_messy_string(curr, self.get_messy_rate(), html=html)
        if not html:
            return f"[{last} → {curr}]"
        return f"<div class=\"region\">[{last} &gt;&gt; {curr}]</div>"

    def custom_change_attr(self, change_func, return_func, change_value: PlayerAttr, return_msg: str = "{name}: {value}", assign=True):
        value = change_value.custom_change(change_func, return_method=return_func, assign=assign)
        return return_msg.format(name=change_value.name, value=value)

    def get_card_color(self) -> dict:
        depths = {
            SeekRegion.SHALLOW_SEA: 0,
            SeekRegion.DEEP_SEA: 120,
            SeekRegion.TRENCH: 500,
            SeekRegion.ABYSS: 1000,
            SeekRegion.DEEPEST: 2000,
            SeekRegion.VOID: 3500
        }
        def get_depth_ratio():
            depth: int = self.depth.value
            weight = 1
            # 将区间按深度排序
            if self.region.value not in [SeekRegion.SHALLOW_SEA, SeekRegion.DEEP_SEA, SeekRegion.TRENCH, SeekRegion.ABYSS, SeekRegion.DEEPEST, SeekRegion.VOID]:
                weight = 0.4
            sorted_regions = sorted(depths.items(), key=lambda x: x[1])
            for i in range(len(sorted_regions) - 1):
                region_last, d_last = sorted_regions[i]
                region_next, d_next = sorted_regions[i + 1]

                # 判断深度是否在此区间之间
                if d_last <= depth <= d_next:
                    # 计算相对比值
                    ratio = (depth - d_last) / (d_next - d_last)
                    return region_next, ratio * weight
            # 若未匹配到说明超过最大区间
            last_region, _ = sorted_regions[-1]
            return last_region, 1.0 * weight
        region_colors = {
            SeekRegion.SHALLOW_SEA: {
                "text_color": "#FFFFFF",
                "card_border_color": "#9efcff",
                "card_background_color": "#121c2b",
                "fail_color": "#FC5959",
                "win_color": "#8aff8a",
                "ident_color": "#59CEFC",
                "dice_color": "#BBD0FF",
                "region_color": "#8DFFCA",
                "effect_color": "#75D8FF",
                "event_color": "#C5F2FF",
                "attr_color": "#C5F2FF",
                "line_color": "#a9c7ff4b",
                },SeekRegion.SHIPWRECK: {
                "text_color": "#FFF3EC",
                "card_border_color": "#b67154",
                "card_background_color": "#110D0B",
                "fail_color": "#FC5959",
                "win_color": "#B0FFA0",
                "ident_color": "#FFAF63",
                "dice_color": "#FFD4CC",
                "region_color": "#8DFFCA",
                "effect_color": "#FFECAC",
                "event_color": "#FFD9BA",
                "attr_color": "#FFD9BA",
                "line_color": "#ffdda94b",
                },SeekRegion.UNDERSEA_CITY: {
                "text_color": "#e9edff",
                "card_border_color": "#535368",
                "card_background_color": "#171a22",
                "fail_color": "#ff6161",
                "win_color": "#93dd91",
                "ident_color": "#76ade0",
                "dice_color": "#9bacbd",
                "region_color": "#94c6cc",
                "effect_color": "#decaff",
                "event_color": "#b5bce7",
                "attr_color": "#b5bce7",
                "line_color": "#c2c2c24b",
                }, SeekRegion.ABYSS_CITY: {
                "text_color": "#e9edff",
                "card_border_color": "#d3d3fa",
                "card_background_color": "#040507",
                "fail_color": "#ff6161",
                "win_color": "#87ff83",
                "ident_color": "#59d8ff",
                "dice_color": "#bbc2ff",
                "region_color": "#60ffea",
                "effect_color": "#e196ff",
                "event_color": "#a0f9ff",
                "attr_color": "#a0f9ff",
                "line_color": "#ffffff4b",
                }, SeekRegion.TRENCH: {
                "text_color": "#cfdeff",
                "card_border_color": "#212396",
                "card_background_color": "#020205",
                "fail_color": "#ee516b",
                "win_color": "#72ffbd",
                "ident_color": "#54e5ff",
                "dice_color": "#89bcff",
                "region_color": "#59afff",
                "effect_color": "#c9c3ff",
                "event_color": "#a4b2ff5",
                "attr_color": "#a4b2ff",
                "line_color": "#817eff4b",
                }, SeekRegion.ABYSS: {
                "text_color": "#ffccc8",
                "card_border_color": "#7c1414",
                "card_background_color": "#050202",
                "fail_color": "#ee5151",
                "win_color": "#a5f591",
                "ident_color": "#f7d35e",
                "dice_color": "#ff89a3",
                "region_color": "#ff8045",
                "effect_color": "#ffb17c",
                "event_color": "#ff8884",
                "attr_color": "#ff8884",
                "line_color": "#ff7e7e4b",
                }, SeekRegion.DEEPEST: {
                "text_color": "#cacaec",
                "card_border_color": "#acacac",
                "card_background_color": "#020305",
                "fail_color": "#f3657d",
                "win_color": "#91f5dc",
                "ident_color": "#ffffff",
                "dice_color": "#8a82ff",
                "region_color": "#cac1ff",
                "effect_color": "#ffffff",
                "event_color": "#ffffff",
                "attr_color": "#8b93ff",
                "line_color": "#cec3ff4b",
                }, SeekRegion.VOID: {
                "text_color": "#efe8ff",
                "card_border_color": "#9d79ff",
                "card_background_color": "#020305",
                "fail_color": "#f3657d",
                "win_color": "#7decff",
                "ident_color": "#ffffff",
                "dice_color": "#9992ff",
                "region_color": "#cac1ff",
                "effect_color": "#ffffff",
                "event_color": "#d89dff",
                "attr_color": "#ab8dff",
                "line_color": "#cec3ff4b",
                }, SeekRegion.FOREST: {
                "text_color": "#d4ffe4",
                "card_border_color": "#136e53",
                "card_background_color": "#070e06",
                "fail_color": "#ee7051",
                "win_color": "#6bff58",
                "ident_color": "#52ff78",
                "dice_color": "#d6ff89",
                "region_color": "#bdff41",
                "effect_color": "#84ffe4",
                "event_color": "#95ffa9",
                "attr_color": "#95ffa9",
                "line_color": "#89ff7e4b",
                }, SeekRegion.UNDERSEA_CAVE: {
                "text_color": "#d4eeff",
                "card_border_color": "#4c2b5c",
                "card_background_color": "#091316",
                "fail_color": "#ff5f5f",
                "win_color": "#8dff58",
                "ident_color": "#f36aff",
                "dice_color": "#9ed3ff",
                "region_color": "#928aff",
                "effect_color": "#7ba5ff",
                "event_color": "#95ffa9",
                "attr_color": "#ffb6ef",
                "line_color": "#ffe17e4b",
                }, SeekRegion.SHADOWRECK: {
                "text_color": "#eceeff",
                "card_border_color": "#825fff",
                "card_background_color": "#0c0c1a",
                "fail_color": "#fc597c",
                "win_color": "#a0ffcb",
                "ident_color": "#FFAF63",
                "dice_color": "#daccff",
                "region_color": "#bd9aff",
                "effect_color": "#acb2ff",
                "event_color": "#dabaff",
                "attr_color": "#dabaff",
                "line_color": "#b6a9ff4b",
                }
        }
        default_colors = {
            "text_color": "#E2EBFF",
            "card_border_color": "#3ba3f8",
            "card_background_color": "#141430",
            "fail_color": "#FC5959",
            "win_color": "#7FFF7F",
            "ident_color": "#59CEFC",
            "dice_color": "#BBD0FF",
            "region_color": "#8DFFCA",
            "effect_color": "#8DBEFF",
            "event_color": "#addaff",
            "attr_color": "#addaff",
            "line_color": "#a9b2ff4b",
        }
        color_dict = {}
        next_region, ratio = get_depth_ratio()
        next_region_colors = region_colors.get(next_region, {})
        for k, v in default_colors.items():
            curr_color = region_colors.get(self.region.value, {}).get(k, v)
            color_dict[k] = mix_hex_color_lab(curr_color, next_region_colors.get(k, curr_color), ratio)
        return color_dict

    def get_depth_tip(self, count):
        # 深度改变时 1~5 是 单箭头，5~15 是双箭头 15 以上是三箭头
        arrow_count = 1
        if abs(count) > 3000:
            arrow_count = 11
        elif abs(count) > 2500:
            arrow_count = 10
        elif abs(count) > 2000:
            arrow_count = 9
        elif abs(count) > 1500:
            arrow_count = 8
        elif abs(count) > 1000:
            arrow_count = 7
        elif abs(count) > 800:
            arrow_count = 6
        elif abs(count) > 300:
            arrow_count = 5
        elif abs(count) > 60:
            arrow_count = 4
        elif abs(count) > 20:
            arrow_count = 3
        elif abs(count) > 9:
            arrow_count = 2
        arrow = "↓" if count > 0 else "↑"
        if count == 0:
            arrow = "-"
        return_str = ""
        if self.region.value in [SeekRegion.FOREST]:
            # arrow = random.choice(["↓", "↑"])
            for _ in range(max(arrow_count + random.randint(-1, 1), 1)):
                return_str += random.choice(["↓", "↑"])
            return return_str
        return f"{arrow * arrow_count}"

    def get_messy_rate(self):
        # 得到自己的混乱值
        return (100 - (self.san.value / self.san.max_value) * 100) * 0.5


    def change_attr(self, changes: dict, html=True, blank=True):
        # debug_msg("changes", changes)
        result_strs = []
        for k, v in changes.items():
            change_value: PlayerAttr = use_attribute(self, k)
            last_change_value = change_value
            old_value = change_value.value
            new_value = 0
            if isinstance(v, str):
                value = int(v[1:])
            if not isinstance(v, dict) and v[0] == "+":
                new_value = change_value.change(lambda v: v + value)
                # new_value = change_value.value + value
            elif not isinstance(v, dict) and v[0] == "-":
                new_value = change_value.change(lambda v: v - value)
                # new_value = change_value.value - value
            elif not isinstance(v, dict) and v[0] == "=":
                new_value = change_value.change(lambda _: value)
                # new_value = value
            elif not isinstance(v, dict) and v[0] == "*":
                new_value = change_value.change(lambda v: v * value)
                # new_value = change_value.value * value
            elif not isinstance(v, dict) and v[0] == "/":
                new_value = change_value.change(lambda v: v // value)
                # new_value = change_value.value // value
            else:
                # 此时需要保证是字典类型
                if not isinstance(v, dict):
                    raise ValueError(f"自定义修改类型 \"{v}\" 不是字典")
                # debug_msg("getgetget", v.get("assign", True), v)
                result_strs.append(self.custom_change_attr(v["change_func"], v["return_func"], change_value, v.get("return_msg", "{name}: {value}"), assign=v.get("assign", True)))
                continue
            value_diff = new_value - old_value
            # 对于无变化的忽略
            # if (v[0] in ["+", "-"] and value == 0) or (v[0] in ["*", "/"] and value == 1) or (v[0] in ["="] and value == last_change_value):
            if value_diff == 0:
                continue
            # 深度单独计算
            if k == "depth":
                result_strs.append(self.get_depth_tip(value_diff))
                # if self.depth.value <= 0 and self.oxygen.value < self.oxygen.max_value:
                #     result_strs.append(self.change_attr({
                #         "oxygen": "+100000"
                #     }, blank=False))
                continue
            result_strs.append(f"{change_value.name} {'+' + str(value_diff) if value_diff >= 0 else str(value_diff)}")
        content = ', '.join(result_strs)
        content = html_messy_string(content, self.get_messy_rate(), html=html)
        # c = f"<div class=\"effect\">({content})</div>" if html else f"({content})"
        c = f"({content})"
        return (c if blank else content) if content else ""

    # 玩家是否还活着
    def is_die(self) -> tuple[bool, str]:
        if self.oxygen.value <= 0:
            return (True, html_messy_string("氧气不足", self.get_messy_rate()))
        elif self.health.value <= 0:
            return (True, html_messy_string("生命值过低", self.get_messy_rate()))
        elif self.san.value <= 0:
            return (True, html_messy_string("混乱而死", self.get_messy_rate()))
        return (False, "")

    def get_attr_str(self, detailed=False, html=True) -> str:
        index = 0
        result = ""
        for v in self.__dict__.values():
            # 只显示整数
            # debug_msg(f"[DEBUG] type={type(v)}, value={v}")
            if not isinstance(v, PlayerAttr): continue
            if not isinstance(v.value, int) and not isinstance(v.value, SeekRegion): continue
            # if v.name == "上个区域": continue
            if not v.show: continue
            danger_class = 'style="color: var(--fail-color)"' if v.name in ["氧气值", "生命值", "san 值"] and v.value < 30 else ""
            value = v.value
            name = v.name
            maxvalue = v.max_value
            if isinstance(v.value, SeekRegion):
                value = v.value.value
                maxvalue = -1
            if v.name == "深度":
                value = str(value)
                if self.region.value in [SeekRegion.FOREST]:
                    value = "???"
                value += " d.n."
            name = html_messy_string(str(name), self.get_messy_rate(), html=html)
            value = html_messy_string(str(value), self.get_messy_rate(), html=html)
            # 星币不显示
            if v.name == f"{coin_name}数":
                continue
            prefix = f"<div {danger_class}>"
            suffix = "</div>"
            if not html:
                prefix = ""
                suffix = "; "
            if index == 0:
                r = ""
                if detailed and v.detail:
                    r = f"{prefix}{name}: {value}" + (f" / {maxvalue}" if maxvalue != -1 else "") + suffix
                else:
                    r = f"{prefix}{name}: {value}{suffix}"
                index += 1
                result += r
                continue
            # debug_msg(index)
            if index % 2 == 0:
                result += "\n"
            if detailed and name != "深度" and v.detail:
                r = f"{prefix}{name}: {value}" + (f" / {maxvalue}" if maxvalue != -1 else "") + suffix
            else:
                r = f"{prefix}{name}: {value}{suffix}"
            result += r
            index += 1
        return result

    def get_tools_str(self, detailed=False) -> str:
        ...

