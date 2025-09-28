from xme.plugins.commands.drift_bottle import __plugin_name__
from .player import Player, PlayerAttr, SeekRegion
from xme.xmetools.randtools import random_percent
import random
from typing import Any
from xme.xmetools.typetools import use_attribute
from nonebot import CommandSession
from xme.xmetools.randtools import html_messy_string
from character import get_message
from xme.xmetools.msgtools import send_session_msg

# 探险事件
class Event:
    def __init__(self, player: Player):
        self.player = player

    def gen_event(self, event_list: list[dict], current_region: SeekRegion) -> str | dict:
        region_events = Event.get_region_event_list(event_list, self.player.region.value)
        # 符合条件的事件
        # print("region_events", region_events)
        eligible_events = [e for e in region_events if e["condition"](self.player.health, self.player.san, self.player.oxygen, self.player.combat, self.player.insight, self.player.mental, self.player.coins, self.player.tools, self.player.depth, self.player.back, self.player.chance, self.player.events_encountered)]
        # print("eligible_events", eligible_events)
        chosen_event = Event.choose_event(eligible_events)
        result = self.build_event(
            event_dict=chosen_event,
            current_region=current_region
        )
        # print("event", chosen_event)
        # 事件标签，用来保存发生了哪类事件，用于特殊事件链
        ev_tags: list = chosen_event.get("tags", None)
        if ev_tags is not None:
            for t in ev_tags:
                self.player.events_encountered[t] = True
        self.player.post_process(chosen_event.get("post_func", None))
        return result

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
            # 空列表就是都可以
            if current_region not in e["regions"] and len(e["regions"]) >= 1:
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
        random_events = [e for e in event_list if e["prob"] != -1 and not e.get("top", False)]
        top_events = [e for e in event_list if e.get("top", False)]
        # events = normal_events
        # default_events = normal_default_events
        # if random_percent(9):
            # default_events = dice_default_events
            # events = dice_events
        random.shuffle(random_events)
        random_events = top_events + random_events
        # random_events.sort(key=lambda x: x["prob"])
        # random_events.reverse()
        # print(random_events)
        for e in random_events:
            if not random_percent(e["prob"]):
                continue
            return e
        event = random.choice(default_events)
        return event


    def can_trigger_event(self, event_dict: dict) -> bool:
        # 是否可以触发事件
        return event_dict["condition"](self.player.health, self.player.san, self.player.oxygen, self.player.combat, self.player.insight, self.player.mental, self.player.coins, self.player.tools, self.player.depth, self.player.back, self.player.chance)


    def build_changes(event_changes):
        build_changes = {}
        for k, v in event_changes.items():
            if v.get("custom", False):
                build_changes[k] = {
                    "change_func": v['change'],
                    "return_func": v['return'],
                    "assign": v.get("assign", True),
                    "return_msg": v.get("return_msg", "{name}: {value}"),
                }
            else:
                build_changes[k] = f"{v['type']}{v['change']()}" # 这里需要调用一次，因为是 Lambda
        return build_changes

    def build_normal_event(self, event_dict: dict, html=True) -> str:
        event_changes: dict = event_dict["changes"]
        region_change = event_dict.get("region_change", None)
        build_changes = Event.build_changes(event_changes)
        # for k, v in event_changes:
            # build_changes[k] = f"{v['type']}{v['change']()}"
        event_desc: str = random.choice(event_dict["descs"])
        return self.normal_event(event_desc, build_changes, region_change, html=html)

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
        bigwin = {
            "changes": bigwin_changes,
            "msg": bigwin_msg,
            "region_change": event_dict["big_win"].get("region_change", None),
        }
        win = {
            "changes": ok_changes,
            "msg": ok_msg,
            "region_change": event_dict["ok"].get("region_change", None),
        }
        fail = {
            "changes": fail_changes,
            "msg": fail_msg,
            "region_change": event_dict["fail"].get("region_change", None),
        }
        big_fail = {
            "changes": bigfail_changes,
            "msg": bigfail_msg,
            "region_change": event_dict["big_fail"].get("region_change", None),
        }
        return self.dice_event(
            event_desc=desc,
            dice_faces=dice_faces,
            determine_attr=determine_attr,
            big_win=bigwin,
            win=win,
            fail=fail,
            big_fail=big_fail,
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
        from .. import is_stepping, command_name
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
                await send_session_msg(session, get_message("plugins", __plugin_name__, command_name, 'in_decision'))
                continue
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
        from .. import command_name
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
        win: dict,
        big_win: dict,
        fail: dict,
        big_fail: dict,
        html: bool = True,
        # TODO region change
        ) -> str:
        from .. import command_name
        """掷骰判定事件

        Args:
            event_desc (str): 事件介绍（开头）
            dice_faces (int): 掷骰面数
            determine_attr (str): 鉴定属性名
            win (dict): 成功结果
            big_win (dict): 大成功结果
            fail (dict): 失败结果
            big_fail (dict): 大失败结果
        """
        attr: PlayerAttr = use_attribute(self.player, determine_attr)
        random.seed()
        attr_value = attr.value
        attr_name = attr.name
        rd = random.randint(1, dice_faces)
        # magnification = 1
        state = ""
        msg = ""
        region_change = None
        if rd == 1 and attr_value >= 1:
            # 大成功
            state = "<span class=\"win\">大成功</span>"
            if not html:
                state = "大成功"
            # win = True
            result = big_win["changes"]
            msg = big_win["msg"]
            region_change = big_win["region_change"]
        elif rd <= attr_value:
            # 成功
            state = "<span class=\"win\">成功</span>"
            if not html:
                state = "成功"
            # win = True
            result = win["changes"]
            msg = win["msg"]
            region_change = win["region_change"]
        elif rd == dice_faces and dice_faces > attr_value + 2:
            # 大失败
            state = "<span class=\"failed\">大失败</span>"
            if not html:
                state = "大失败"
            # win = False
            result = big_fail["changes"]
            msg = big_fail["msg"]
            region_change = big_fail["region_change"]
        else:
            # 失败
            state = "<span class=\"failed\">失败</span>"
            if not html:
                state = "失败"
            # win = False
            result = fail["changes"]
            msg = fail["msg"]
            region_change = big_fail["region_change"]
        # if win:
        #     # attr_change = self.player.change_attr(ok_result, magnification)
        #     # await send_session_msg(session, get_message("plugins", __plugin_name__, command_name, 'limited'))
        # else:
        region_ch = ""
        if region_change is not None:
            region_ch = self.player.change_region(region_change, html=html)
        attr_change = self.player.change_attr(result, html=html)
        event_desc = html_messy_string(event_desc, self.player.get_messy_rate(), html=html)
        attr_name = html_messy_string(attr_name, self.player.get_messy_rate(), html=html)
        dice_faces_str = html_messy_string(str(dice_faces), self.player.get_messy_rate(), html=html)
        rd_str = html_messy_string(str(rd), self.player.get_messy_rate(), html=html)
        attr_value_str = html_messy_string(str(attr_value), self.player.get_messy_rate(), html=html)
        msg = html_messy_string(msg, self.player.get_messy_rate(), html=html)
        if not html:
            return get_message("plugins", __plugin_name__, command_name, 'dice_event_no_html', attr_change=attr_change, event_desc=event_desc, attr_name=attr_name, dice_faces=dice_faces_str, dice_result=rd_str, attr_value=attr_value_str, state=state, result_message=msg, region_ch=region_ch)
        return get_message("plugins", __plugin_name__, command_name, 'dice_event', attr_change=attr_change, event_desc=event_desc, attr_name=attr_name, dice_faces=dice_faces_str, dice_result=rd_str, attr_value=attr_value_str, state=state, result_message=msg, region_ch=region_ch)

