from xme.xmetools.timetools import *
from xme.plugins.commands.drift_bottle import __plugin_name__
from xme.xmetools.cmdtools import send_cmd, get_cmd_by_alias, is_it_command
from aiocqhttp.exceptions import ActionFailed
from xme.xmetools.bottools import permission
from xme.xmetools.timetools import TimeUnit
from html2image import Html2Image
from xme.xmetools.randtools import html_messy_string
from character import get_message
from xme.xmetools.imgtools import crop_transparent_area, image_msg
from asyncio import sleep
import markdown
import os
from xme.plugins.commands.xme_user.classes import user
from xme.xmetools.typetools import use_attribute
from xme.xmetools.randtools import random_percent
from xme.plugins.commands.xme_user.classes.user import coin_name
import random
from typing import Any
random.seed()
from . import DriftBottle, get_random_bottle
from nonebot import on_command, CommandSession, MessageSegment
from xme.xmetools.msgtools import send_session_msg, send_forward_msg, change_group_message_content
from enum import Enum
hti = Html2Image()

seeking_groups = [

]

# 寻宝区域
class SeekRegion(Enum):
    SHALLOW_SEA = "浅海"
    DEEP_SEA = "深海"
    SHIPWRECK = "沉船"
    TRENCH = "海沟"
    UNDERSEA_CITY = "深海城市"

# class PlayerRegion:
#     def __init__(self, region: SeekRegion = SeekRegion.SHALLOW_SEA):
#         self.region: SeekRegion = region
#         self.lastRegion = SeekRegion.SHALLOW_SEA

#     def change_region(self, region: SeekRegion) -> 'PlayerRegion':
#         self.lastRegion = self.region
#         self.region = region
#         return self

#     def get_last_region(self) -> SeekRegion:
#         return self.lastRegion


class PlayerAttr:
    def __init__(self, name, value, max_value=-1):
        self.name = name
        self.value = value
        # 属性最大值，如果是 -1 那就是无上限
        self.max_value = max_value

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
            set_method(self.value)
            print("value2", self.value)
            print("return_method2", return_method(self.value))
            return return_method(self.value)

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
        self.last_region = PlayerAttr(f"上个区域", SeekRegion.SHALLOW_SEA)

        # 探险深度，目前想法是每走一步深度会随机加减
        self.depth = 0

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

    def get_messy_rate(self):
        # 得到自己的混乱值
        return (100 - (self.san.value / self.san.max_value) * 100) * 0.8


    def change_attr(self, changes: dict, html=True):
        print("changes", changes)
        result_strs = []
        for k, v in changes.items():
            change_value: PlayerAttr = use_attribute(self, k)
            last_change_value = change_value
            if isinstance(v, str):
                value = int(v[1:])
            if not isinstance(v, dict) and v[0] == "+":
                change_value.change(lambda v: v + value)
            elif not isinstance(v, dict) and v[0] == "-":
                change_value.change(lambda v: v - value)
            elif not isinstance(v, dict) and v[0] == "=":
                change_value.change(lambda _: value)
            elif not isinstance(v, dict) and v[0] == "*":
                change_value.change(lambda v: v * value)
            elif not isinstance(v, dict) and v[0] == "/":
                change_value.change(lambda v: v // value)
            else:
                # 此时需要保证是字典类型
                if not isinstance(v, dict):
                    raise ValueError(f"自定义修改类型 \"{v}\" 不是字典")
                print("getgetget", v.get("assign", True), v)
                result_strs.append(self.custom_change_attr(v["change_func"], v["return_func"], change_value, v.get("return_msg", "({name}: {value})"), assign=v.get("assign", True)))
                continue
            # 对于无变化的忽略
            if (v[0] in ["+", "-"] and value == 0) or (v[0] in ["*", "/"] and value == 1) or (v[0] in ["="] and value == last_change_value):
                continue
            result_strs.append(f"{change_value.name} {v[0]} {value}")
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

            if not isinstance(v, PlayerAttr): continue
            if not isinstance(v.value, int) and not isinstance(v.value, SeekRegion): continue
            if v.name == "上个区域": continue
            value = v.value
            name = v.name
            maxvalue = v.max_value
            if isinstance(v.value, SeekRegion):
                value = v.value.value
                maxvalue = -1
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
                if detailed:
                    r = f"{prefix}{name}: {value}" + (f" / {maxvalue}" if maxvalue != -1 else "") + suffix
                else:
                    r = f"{prefix}{name}: {value}{suffix}"
                index += 1
                result += r
                continue
            # print(index)
            if index % 2 == 0:
                result += "\n"
            if detailed:
                r = f"{prefix}{name}: {value}" + (f" / {maxvalue}" if maxvalue != -1 else "") + suffix
            else:
                r = f"{prefix}{name}: {value}{suffix}"
            result += r
            index += 1
        return result

    def get_tools_str(self, detailed=False) -> str:
        ...


# 道具
class Tool:
    def __init__(self, player: Player, changes: dict):
        self.player = player
        self.changes = changes

    def apply(self):
        self.player.change_attr(self.changes)

# 探险事件
class Event:
    def __init__(self, player: Player):
        self.player = player

    def gen_event(self, event_list: list[dict], current_region: SeekRegion) -> str | dict:
        region_events = Event.get_region_event_list(event_list, self.player.region.value)
        # 符合条件的事件
        # print("region_events", region_events)
        eligible_events = [e for e in region_events if e["condition"](self.player.health, self.player.san, self.player.oxygen, self.player.combat, self.player.insight, self.player.mental, self.player.coins, self.player.tools)]
        # print("eligible_events", eligible_events)
        chosen_event = Event.choose_event(eligible_events)
        return self.build_event(
            event_dict=chosen_event,
            current_region=current_region
        )

    def get_region_event_list(event_list: list[dict], current_region: SeekRegion) -> list[dict]:
        """得到当前区域事件列表

        Args:
            event_list (list[dict]): 总事件列表
            current_region (SeekRegion): 当前区域

        Returns:
            list[dict]: 当前区域事件列表
        """
        result_list = []
        for e in event_list:
            # print("regions", e["regions"], "curr", current_region, current_region in e["regions"])
            if current_region not in e["regions"]:
                continue
            result_list.append(e)
        return result_list

    def choose_event(event_list: list[dict]) -> dict:
        # 随机选择事件
        # normal_default_events = [e for e in event_list if e["prob"] == -1 and e["type"] == "normal"]
        # dice_default_events = [e for e in event_list if e["prob"] == -1 and e["type"] == "dice"]
        # normal_events = [e for e in event_list if e["prob"] != -1 and e["type"] == "normal"]
        # dice_events = [e for e in event_list if e["prob"] != -1 and e["type"] == "dice"]
        # print("events", event_list)
        default_events = [e for e in event_list if e["prob"] == -1]
        random_events = [e for e in event_list if e["prob"] != -1]
        # events = normal_events
        # default_events = normal_default_events
        # if random_percent(9):
            # default_events = dice_default_events
            # events = dice_events
        random.shuffle(random_events)
        # random_events.sort(key=lambda x: x["prob"])
        # random_events.reverse()
        for e in random_events:
            if not random_percent(e["prob"]):
                continue
            return e
        event = random.choice(default_events)
        return event


    def can_trigger_event(self, event_dict: dict) -> bool:
        # 是否可以触发事件
        return event_dict["condition"](self.player.health, self.player.san, self.player.oxygen, self.player.combat, self.player.insight, self.player.mental, self.player.coins, self.player.tools)


    def build_changes(event_changes):
        build_changes = {}
        for k, v in event_changes.items():
            if v["custom"]:
                build_changes[k] = {
                    "change_func": v['change'],
                    "return_func": v['return'],
                    "assign": v.get("assign", True),
                }
            else:
                build_changes[k] = f"{v['type']}{v['change']()}" # 这里需要调用一次，因为是 Lambda
        return build_changes

    def build_normal_event(self, event_dict: dict, html=True) -> str:
        event_changes: dict = event_dict["changes"]
        region_changes = event_dict.get("region_changes", None)
        build_changes = Event.build_changes(event_changes)
        # for k, v in event_changes:
            # build_changes[k] = f"{v['type']}{v['change']()}"
        event_desc: str = random.choice(event_dict["descs"])
        return self.normal_event(event_desc, build_changes, region_changes, html=html)

    def parse_event_messages(messages, current_region: SeekRegion):
        # 解析事件消息列表
        result_list = []
        for e in messages:
            # 无是默认
            if len(e["regions"]) < 1:
                result_list.append(e)
                continue
            if current_region not in e["regions"]:
                continue
            result_list.append(e)
        return result_list

    def build_dice_event(self, event_dict: dict, current_region, html=True) -> str:
        event_message = random.choice(Event.parse_event_messages(event_dict["event_messages"], current_region))
        # print("evmsg", event_message)
        desc: str = random.choice(event_message["descs"])
        ok_msg: str = random.choice(event_message["ok_msgs"])
        bigwin_msg: str = random.choice(event_message["bigwin_msgs"])
        fail_msg: str = random.choice(event_message["fail_msgs"])
        bigfail_msg: str = random.choice(event_message["bigfail_msgs"])
        dice_faces: int = event_dict["dice_faces"]()
        determine_attr: str = event_dict["determine_attr"]
        ok_changes: dict = Event.build_changes(event_dict["ok"]["changes"])
        bigwin_changes: dict = Event.build_changes(event_dict["big_win"]["changes"])
        fail_changes: dict = Event.build_changes(event_dict["fail"]["changes"])
        bigfail_changes: dict = Event.build_changes(event_dict["big_fail"]["changes"])
        return self.dice_event(
            event_desc=desc,
            dice_faces=dice_faces,
            determine_attr=determine_attr,
            ok_result=ok_changes,
            fail_result=fail_changes,
            win_msg=ok_msg,
            big_win_msg=bigwin_msg,
            big_win_result=bigwin_changes,
            fail_msg=fail_msg,
            big_fail_msg=bigfail_msg,
            big_fail_result=bigfail_changes,
            html=html,
        )

    async def build_decision_event(self, session, event_dict: dict, current_region: SeekRegion, message_prefix: str = "----------决策事件----------\n") -> str:
        """构造决策事件

        Args:
            session (CommandSession): Session
            event_dict (dict): 决策事件字典
            current_region (SeekRegion): 当前区域

        Returns:
            str: 决策事件返回
        """
        can_quit: bool = event_dict["can_quit"]
        desc: str = random.choice(event_dict["descs"])
        return await self.decision_event(session, current_region, can_quit, desc, event_dict["decisions"], message_prefix)

    # 构建事件
    def build_event(self, event_dict: dict, current_region: SeekRegion, html=True) -> str | dict:
        """构造并且执行事件

        Args:
            event_dict (dict): 事件字典

        Returns:
            str: 事件结果
        """
        event_type: str = event_dict["type"]

        match event_type:
            case 'normal':
                return self.build_normal_event(event_dict, html=html)
            case 'dice':
                return self.build_dice_event(event_dict, current_region, html=html)
            # 单独处理决策事件
            case 'decision':
                return event_dict
            #     return await self.build_decision_event(session, event_dict, current_region)

    # 决策事件
    async def decision_event(self, session: CommandSession, current_region: SeekRegion, can_quit: bool, event_desc, decisions = [list[dict]], message_prefix = "") -> str | dict:
        """决策事件

        Args:
            session (CommandSession): Session
            current_region (SeekRegion): 玩家所在区域
            can_quit (bool): 是否可以放弃决策
            event_desc (str): 决策事件介绍
            decisions (list, optional): 决策事件列表，存放普通事件 dict. Defaults to [list[dict]].

        Returns:
            str: 决策事件返回结果
        """
        # 决策事件里的决策是封装的普通事件或者其他事件，当然也可以是决策事件
        decision_strs = [f'{i + 1}. {html_messy_string(random.choice(e["names"]), self.player.get_messy_rate())} {html_messy_string(e.get("tip", ""), self.player.get_messy_rate())}' for i, e in enumerate(decisions)]
        decision_chunks = [decision_strs[i : i + 2] for i in range(0, len(decision_strs), 2)]
        decision_str = "\n".join(["\t".join(a) for a in decision_chunks])
        event_desc = html_messy_string(event_desc, self.player.get_messy_rate(), html=False)
        await send_session_msg(session, message_prefix + get_message("plugins", __plugin_name__, command_name, 'decision_event', event_desc=event_desc, decision_descs=decision_str) + "\n" + get_message("plugins", __plugin_name__, command_name, 'get_decision'))
        reply_valid = False
        while not reply_valid:
            reply: str = (await session.aget()).strip()
            if is_stepping(reply):
                return get_message("plugins", __plugin_name__, command_name, 'in_decision')
            if reply == "stop" and can_quit:
                return get_message("plugins", __plugin_name__, command_name, 'quit_success')
            elif reply == "stop":
                await send_session_msg(session, get_message("plugins", __plugin_name__, command_name, 'quit_fail'))
            if reply.isdigit() and int(reply) <= len(decisions) and int(reply) > 0:
                reply_valid = True
        next_event = decisions[int(reply) - 1]
        return self.build_event(next_event, current_region, html=False)


    # 一般事件，只有结果
    def normal_event(self, event_desc: str, attr_changes: dict[str, Any] | None = None, region_change=None, html=True) -> str:
        """一般事件

        Args:
            event_desc (str): 事件介绍
            attr_changes (dict[str, str] | None, optional): 事件所改变的属性值. Defaults to None.

        Returns:
            str: 事件返回内容
        """
        attr_change = ''
        if attr_changes is not None:
            attr_change = self.player.change_attr(attr_changes, html=html)
        region_ch = ""
        if region_change is not None:
            region_ch = self.player.change_region(region_change, html=html)
        event_desc = html_messy_string(event_desc, self.player.get_messy_rate(), html=html)
        if not html:
            return get_message("plugins", __plugin_name__, command_name, 'normal_event_no_html', event_desc=event_desc, attr_change=attr_change, region_ch=region_ch).strip()
        return get_message("plugins", __plugin_name__, command_name, 'normal_event', event_desc=event_desc, attr_change=attr_change, region_ch=region_ch).strip()


    # 掷骰判定事件
    def dice_event(
        self,
        event_desc: str,
        dice_faces: int,
        determine_attr: str,
        ok_result: dict[str, Any],
        fail_result: dict[str, Any],
        win_msg: str,
        big_win_msg: str,
        big_win_result: dict[str, Any],
        fail_msg: str,
        big_fail_msg: str,
        big_fail_result: dict[str, Any],
        html: bool = True,
        # TODO region change
        ) -> str:
        """掷骰判定事件

        Args:
            event_desc (str): 事件介绍（开头）
            dice_faces (int): 掷骰面数
            determine_attr (str): 鉴定属性名
            ok_result (dict[str, str]): 鉴定成功修改的属性
            fail_result (dict[str, str]): 鉴定失败修改的属性
            win_msg (str): 成功消息
            big_win_msg (str): 大成功消息
            big_win_result dict[str, str]: 大成功修改的属性结果
            fail_msg (str): 失败消息
            big_fail_msg (str): 大失败消息
            big_fail_result dict[str, str]: 大失败修改的属性结果
        """
        attr: PlayerAttr = use_attribute(self.player, determine_attr)
        random.seed()
        attr_value = attr.value
        attr_name = attr.name
        rd = random.randint(1, dice_faces)
        # magnification = 1
        state = ""
        msg = ""
        if rd == 1:
            # 大成功
            state = "<span class=\"win\">大成功</span>"
            # win = True
            result = big_win_result
            msg = big_win_msg
        elif rd <= attr_value:
            # 成功
            state = "<span class=\"win\">成功</span>"
            # win = True
            result = ok_result
            msg = win_msg
        elif rd == dice_faces and dice_faces > attr_value + 2:
            # 大失败
            state = "<span class=\"failed\">大失败</span>"
            # win = False
            result = big_fail_result
            msg = big_fail_msg
        else:
            # 失败
            state = "<span class=\"failed\">失败</span>"
            # win = False
            msg = fail_msg
            result = fail_result
        # if win:
        #     # attr_change = self.player.change_attr(ok_result, magnification)
        #     # await send_session_msg(session, get_message("plugins", __plugin_name__, command_name, 'limited'))
        # else:
        attr_change = self.player.change_attr(result, html=html)
        event_desc = html_messy_string(event_desc, self.player.get_messy_rate(), html=html)
        attr_name = html_messy_string(attr_name, self.player.get_messy_rate(), html=html)
        dice_faces_str = html_messy_string(str(dice_faces), self.player.get_messy_rate(), html=html)
        rd_str = html_messy_string(str(rd), self.player.get_messy_rate(), html=html)
        attr_value_str = html_messy_string(str(attr_value), self.player.get_messy_rate(), html=html)
        msg = html_messy_string(msg, self.player.get_messy_rate(), html=html)
        if not html:
            return get_message("plugins", __plugin_name__, command_name, 'dice_event_no_html', attr_change=attr_change, event_desc=event_desc, attr_name=attr_name, dice_faces=dice_faces_str, dice_result=rd_str, attr_value=attr_value_str, state=state, result_message=msg)
        return get_message("plugins", __plugin_name__, command_name, 'dice_event', attr_change=attr_change, event_desc=event_desc, attr_name=attr_name, dice_faces=dice_faces_str, dice_result=rd_str, attr_value=attr_value_str, state=state, result_message=msg)


class Seek:
    def __init__(self, player: Player, events: list[dict]):
        self.player = player
        self.event = Event(self.player)
        self.events = events
        self.status = "stop"
        self.total_steps = 0

    def parse_steps(self, step_count, total_steps: int) -> dict:
        msgs = []
        count = 0
        self.status = "start"
        for step in range(step_count):
            count += 1
            msg = SeekStep(self.event).gen_step(self.events, self.player)
            is_die, die_reason = self.player.is_die()
            if is_die:
                return {
                    "msgs": "\n".join([f"<li><div class=\"text\">{i + 1 + total_steps}. {m}</li>" for i, m in enumerate(msgs)]),
                    "count": count,
                    "is_die": is_die,
                    "die_reason": die_reason,
                    "decision": None,
                }
            if isinstance(msg, dict) and msg["type"] == "decision":
                return {
                    "msgs": "\n".join([f"<li><div class=\"text\">{i + 1 + total_steps}. {m}</li>" for i, m in enumerate(msgs)]),
                    "count": count,
                    "is_die": is_die,
                    "die_reason": die_reason,
                    "decision": msg,
            }
            msgs.append(msg)
        return {
            "msgs": "\n".join([f"<li><div class=\"text\">{i + 1 + total_steps}. {m}</li>" for i, m in enumerate(msgs)]),
            "count": count,
            "is_die": is_die,
            "die_reason": die_reason,
            "decision": None,
        }

    async def parse_decision_event(self, session, decision, prefix) -> str:
        result = await self.event.build_decision_event(session, decision, self.player.region.value, message_prefix=prefix)
        await send_session_msg(session, result)
        return result

    # 阶段消息
    async def make_steps_message(self, session, steps_result: dict, prefix: str = "<h2>----------阶段总结----------</h2>\n<hr/>", suffix: str = "", send=True):
        steps = f"{prefix}<ul>{steps_result['msgs']}"
        coins = f"{self.player.coins.name}: {self.player.coins.value}"
        coins = html_messy_string(coins, self.player.get_messy_rate())
        attr_header = html_messy_string("----------当前属性----------", self.player.get_messy_rate())
        gain_header = html_messy_string("----------收益统计----------", self.player.get_messy_rate())
        msg = f"<hr/>\n<h2>{attr_header}</h2>\n<div class=\"fl\">{self.player.get_attr_str(detailed=True)}\n</div>\n<h2>{gain_header}</h2>\n<div class=\"fl coin\"><div>{coins}</div></div>"
        # decision = steps_result['decision']
        # msg.replace("\n\n", "\n")
        # if decision is not None and decision_first:
            # result = await self.event.build_decision_event(session, decision, self.player.region.value, msg + decision_prefix)
            # await send_session_msg(session, result)
        self.total_steps += steps_result['count']
        if steps_result['is_die']:
            steps += f"<li><span class=\"die\">你已被迫结束探险，收益已清空。原因：{steps_result['die_reason']}</span></li></ul>"
            self.player.coins = 0
            self.status = "stop"
        else:
            steps += "</ul>"

        # if decision is not None:
        #     result = await self.event.build_decision_event(session, decision, self.player.region.value, message_prefix=msg + decision_prefix)
        #     await send_session_msg(session, result)
        #     return
        if send:
            await send_session_msg(session, steps + msg + suffix)
        return [steps, msg + suffix]

def get_img_msg(md_str):
    html_body = """
<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Document</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
                color: rgb(226, 235, 255);
            }
            body {
                background-color: transparent;
            }
            main li {
                font-size: 1em;
                padding: 5px 0;
                /* padding-right: 100px; */
                display: flex;
                justify-content: space-between;
                list-style: none;
            }

            main h2 {
                text-align: center;
            }

            main {
                width: 700px;
                max-width: 1000px;
                border-radius: 15px;
                background-color: #181831;
                padding: 25px 50px;
                border: 3px solid rgb(66, 187, 131);
            }

            .failed, .die {
                color: rgb(252, 89, 89);
            }

            .win {
                color: rgb(127, 255, 127)
            }

            .ident {
                color: rgb(89, 206, 252);
            }
            .other-lines {
                text-indent: 2em;
            }
            .other-lines span {
                text-indent: 0;
            }
            .dice {
                color: rgb(187, 208, 255);
            }
            .effect {
                color: rgb(141, 190, 255);
            }
            .region {
                color: rgb(141, 255, 202);
            }

            .ev {
                color: rgb(173, 255, 251);
            }
            .fl {
                display: flex;
                margin: auto;
                width: 500px;
                flex-wrap: wrap;
                justify-content: space-around;
            }
            .fl div {
                padding: 10px;
                font-size: 1.2em;
                color: rgb(173, 255, 251);
            }
            main > p {
                text-align: center;
                font-size: 1.2em;
            }
            hr {
                border-color: #a9b2ff4b;
                margin: 5px;
            }

            li {
                width: 100%;
                position: relative;
            }

            strong {
                font-size: 1em;
                font-weight: bold;
                text-align-left;
            }

            .text {
                max-width: 400px;
            }
        </style>
    </head>
    <body>
        <main>
    """
    html_str = md_str
    print(html_str)
    html_content = html_body + html_str + """\n
            </main>
    </body>
</html>
    """
    hti.screenshot(html_str=html_content, save_as="seekcard.png", size=(1920, 10000))
    image = crop_transparent_area("seekcard.png")
    os.remove("seekcard.png")
    return image
    # return markdown.markdown(md_text)

# 寻宝每一步
class SeekStep:
    def __init__(self, event: Event):
        self.event = event
    # def parse_step():

    def gen_step(self, events, player: Player) -> str | dict:
        # print(player.region)
        return self.event.gen_event(events, player.region.value)

def is_stepping(reply):
    return reply.startswith("s") and len(reply.split(" ")) > 1 and reply.split(" ")[1].isdigit()

seek_alias = ["寻宝", 'sk']
command_name = "seek"

TIMES_LIMIT = 1

@on_command(command_name, aliases=seek_alias, only_to_me=False, permission=lambda _: True)
@user.using_user(save_data=True)
@permission(lambda sender: sender.from_group(727949269) or sender.is_superuser, permission_help="在 179 的主群使用 或 是 SUPERUSER")
# @user.limit(command_name, 2, get_message("plugins", __plugin_name__, command_name, 'limited'), TIMES_LIMIT, TimeUnit.HOUR)
async def _(session: CommandSession, u: user.User):
    global seeking_groups
    arg = session.current_arg_text.strip()
    if arg not in ["start", "st"]:
        await send_session_msg(session, get_message("plugins", __plugin_name__, command_name, 'introduction'))
        return False
    from .seek_events import EVENTS
    player = Player()
    seek = Seek(player, EVENTS)
    message = get_message("plugins", __plugin_name__, command_name, 'seek_start', attrs=player.get_attr_str(detailed=True, html=False), tools="无")
    # TODO: get_tools_str   ↑
    msg_dict = {
        "sender": await session.bot.api.get_group_member_info(group_id=session.event.group_id, user_id=session.self_id) if session.event.group_id else await session.bot.api.get_stranger_info(user_id=session.self_id)
    }
    total_results = []
    total_messages: list[MessageSegment] = []
    await send_session_msg(session, message)
    async def parse_event_steps(total_steps, expected_steps, prefix=''):
        msgs = ""
        while expected_steps > 0:
            result = seek.parse_steps(expected_steps, total_steps)
            msgs += result["msgs"] + "\n"
            expected_steps -= result["count"]
            total_steps += result["count"]
            step_results = await seek.make_steps_message(session, result, prefix=prefix, send=False)
            # 什么都没有就不输出空白
            if step_results[0].strip() != prefix:
                md_msg = "\n".join(step_results)
                # new_messages += [change_group_message_content(msg_dict, r) for r in step_results]
                await send_session_msg(session, await image_msg(get_img_msg(md_msg)))

            if result["decision"] is not None:
                decision_result = await seek.parse_decision_event(session, result["decision"], prefix="---------决策事件----------\n")
                step_results.insert(1, decision_result)
            total_results.append("\n".join(step_results))
            msgs = ""
        return total_steps

    total_steps = 0
    expected_steps = 10
    # msgs = ""
    start_prefix = "----------开头总结----------"
    total_steps = await parse_event_steps(total_steps, expected_steps, prefix=f'<h2>{html_messy_string(start_prefix, temperature=player.get_messy_rate())}</h2>\n<hr/>\n')
    chance = 10
    while seek.status == "start" and chance > 0:
        expected_steps = 0
        valid_reply = False
        failed = True
        while failed:
            try:
                await send_session_msg(session, get_message("plugins", __plugin_name__, command_name, 'continue_step_tip'))
                failed = False
            except ActionFailed:
                failed = True
        while not valid_reply:
            reply: str = await session.aget()
            reply = reply.strip()
            if reply == "quit":
                seek.status = "stop"
                valid_reply = True
                # await send_session_msg(session, get_message("plugins", __plugin_name__, command_name, 'introduction'))
            elif is_it_command(reply):
                await send_session_msg(session, get_message("plugins", __plugin_name__, command_name, 'on_seeking'))
            elif is_stepping(reply):
                expected_steps = int(reply.split(" ")[1])
                if expected_steps > 20 or expected_steps < 1:
                    await send_session_msg(session, get_message("plugins", __plugin_name__, command_name, "invalid_step", count=expected_steps))
                    continue
                valid_reply = True
        # result = await seek.parse_steps(step)
        prefix = f"----------阶段总结[剩余 {chance - 1} 次机会]----------"
        total_steps = await parse_event_steps(total_steps, expected_steps, prefix=f'<h2>{html_messy_string(prefix, player.get_messy_rate())}</h2>\n<hr/>\n')
        chance -= 1
        print(chance, seek.status)
    # 结算
    coins = f"{player.coins.name}: {player.coins.value}"
    coins = html_messy_string(coins, player.get_messy_rate(), html=False)
    await send_session_msg(session, get_message("plugins", __plugin_name__, command_name, 'stop_seeking', player_attr=player.get_attr_str(True, html=False), gain=f"{coins}"))
    total_messages += [change_group_message_content(msg_dict, r) for r in total_results]
    # await send_forward_msg(session.bot, session.event, total_messages)
    if player.coins.value > 0:
        await u.get_coins(session, player.coins.value)
    return True

    # await sleep(10)