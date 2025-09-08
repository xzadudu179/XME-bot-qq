from xme.xmetools.randtools import html_messy_string
from xme.xmetools.typetools import use_attribute
from enum import Enum
from xme.plugins.commands.xme_user.classes.user import coin_name

# 寻宝区域
class SeekRegion(Enum):
    SHALLOW_SEA = "浅海"
    DEEP_SEA = "深海"
    SHIPWRECK = "沉船"
    TRENCH = "海沟"
    UNDERSEA_CITY = "深海城市"
    UNDERSEA_CAVE = "海底洞穴"
    ABYSS = "深渊"
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
        print("assign", assign)
        if assign:
            changed_value = set_method(self.value)
            self.value = changed_value
            print("value1", self.value)
            print("return_method1", return_method(self.value))
            return return_method(changed_value)
        else:
            set_method(self)
            print("value2", self)
            print("return_method2", return_method(self))
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
        self.depth = PlayerAttr(f"深度", 0, max_value=2500, detail=False)
        # 是否往回走
        self.back = False
        # 机会
        self.chance = PlayerAttr(f"剩余机会", 10, show=False)

        # 遇到过的事件（存uid）
        self.events_encountered: list[str] = []

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
        text_color = "#E2EBFF"
        card_border_color = "#54D4D8"
        card_background_color = "#181831"
        fail_color = "#FC5959"
        win_color = "#7FFF7F"
        ident_color = "#59CEFC"
        dice_color = "#BBD0FF"
        region_color = "#8DFFCA"
        effect_color = "#8DBEFF"
        event_color = "#ADFFFB"
        attr_color = "#ADFFFB"
        line_color = "#a9b2ff4b"
        match self.region.value:
            # 默认深海
            case SeekRegion.SHALLOW_SEA:
                text_color = "#FFFFFF"
                card_border_color = "#88E2F1"
                card_background_color = "#202D41"
                fail_color = "#FC5959"
                win_color = "#AEFFAE"
                ident_color = "#59CEFC"
                dice_color = "#BBD0FF"
                region_color = "#8DFFCA"
                effect_color = "#75D8FF"
                event_color = "#C5F2FF"
                attr_color = "#C5F2FF"
                line_color = "#a9c7ff4b"
            case SeekRegion.SHIPWRECK:
                text_color = "#FFF3EC"
                card_border_color = "#b67154"
                card_background_color = "#110D0B"
                fail_color = "#FC5959"
                win_color = "#B0FFA0"
                ident_color = "#FFAF63"
                dice_color = "#FFD4CC"
                region_color = "#8DFFCA"
                effect_color = "#FFECAC"
                event_color = "#FFD9BA"
                attr_color = "#FFD9BA"
                line_color = "#ffdda94b"
            case SeekRegion.UNDERSEA_CITY:
                text_color = "#ddefff"
                card_border_color = "#416ab6"
                card_background_color = "#0b0d25"
                fail_color = "#fc5982"
                win_color = "#86ffae"
                ident_color = "#7bffde"
                dice_color = "#abebff"
                region_color = "#8dffff"
                effect_color = "#e7c2ff"
                event_color = "#a2cbff"
                attr_color = "#a2cbff"
                line_color = "#aaa9ff4b"

        return {
            "text_color": text_color,
            "card_border_color": card_border_color,
            "card_background_color": card_background_color,
            "fail_color": fail_color,
            "win_color": win_color,
            "ident_color": ident_color,
            "dice_color": dice_color,
            "region_color": region_color,
            "effect_color": effect_color,
            "event_color": event_color,
            "attr_color": attr_color,
            "line_color": line_color,
        }

    def get_depth_tip(count):
        # 深度改变时 1~5 是 单箭头，5~15 是双箭头 15 以上是三箭头
        arrow_count = 1
        if abs(count) > 5:
            arrow_count = 2
        elif abs(count) > 15:
            arrow_count = 3
        arrow = "↓" if count > 0 else "↑"
        if count == 0:
            arrow = "-"
        return f"{arrow * arrow_count}"

    def get_messy_rate(self):
        # 得到自己的混乱值
        return (100 - (self.san.value / self.san.max_value) * 100) * 0.5


    def change_attr(self, changes: dict, html=True):
        print("changes", changes)
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
                print("getgetget", v.get("assign", True), v)
                result_strs.append(self.custom_change_attr(v["change_func"], v["return_func"], change_value, v.get("return_msg", "{name}: {value}"), assign=v.get("assign", True)))
                continue
            value_diff = new_value - old_value
            # 对于无变化的忽略
            # if (v[0] in ["+", "-"] and value == 0) or (v[0] in ["*", "/"] and value == 1) or (v[0] in ["="] and value == last_change_value):
            if value_diff == 0:
                continue
            # 深度单独计算
            if k == "depth":
                result_strs.append(Player.get_depth_tip(value_diff))
                continue
            result_strs.append(f"{change_value.name} {'+' + str(value_diff) if value_diff >= 0 else str(value_diff)}")
        content = ', '.join(result_strs)
        content = html_messy_string(content, self.get_messy_rate(), html=html)
        # c = f"<div class=\"effect\">({content})</div>" if html else f"({content})"
        c = f"({content})"
        return c if content else ""

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
            # print(f"[DEBUG] type={type(v)}, value={v}")
            if not isinstance(v, PlayerAttr): continue
            if not isinstance(v.value, int) and not isinstance(v.value, SeekRegion): continue
            # if v.name == "上个区域": continue
            if not v.show: continue
            value = v.value
            name = v.name
            maxvalue = v.max_value
            if isinstance(v.value, SeekRegion):
                value = v.value.value
                maxvalue = -1
            if v.name == "深度":
                value = str(value) + " d.n."
            name = html_messy_string(str(name), self.get_messy_rate(), html=html)
            value = html_messy_string(str(value), self.get_messy_rate(), html=html)
            # 星币不显示
            if v.name == f"{coin_name}数":
                continue
            prefix = "<div>"
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
            # print(index)
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

