from xme.xmetools.timetools import *
from xme.plugins.commands.drift_bottle import __plugin_name__
from xme.xmetools.cmdtools import send_cmd, get_cmd_by_alias, is_it_command
from .classes.player import SeekRegion
from xme.xmetools.bottools import permission
from xme.xmetools.timetools import TimeUnit
from config import BOT_SETTINGS_PATH
from html2image import Html2Image
from xme.xmetools.randtools import html_messy_string
from character import get_message
from xme.xmetools.imgtools import crop_transparent_area, image_msg
from xme.xmetools.jsontools import change_json, read_from_path
from nonebot import SenderRoles
import os
from xme.plugins.commands.xme_user.classes import user
import random
import traceback
from .classes.player import Player
from .classes.event import Event
random.seed()
from .. import DriftBottle, get_random_bottle
from nonebot import on_command, CommandSession, MessageSegment
from xme.xmetools.msgtools import send_session_msg, send_forward_msg, change_group_message_content
from uuid import uuid4
from enum import Enum
hti = Html2Image()



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
        isover = 0
        for step in range(step_count):
            count += 1
            for tool in self.player.tools:
                if tool.can_apply():
                    msgs.append(tool.apply_event(self.event))
            msg = SeekStep(self.event).gen_step(self.events, self.player)
            is_die, die_reason = self.player.is_die()
            if (self.player.back and self.player.depth.value <= 0) or is_die:
                # 到海面上后执行两次步数（问为什么就是第一次是到达事件）
                if isover < 2:
                    isover += 1
                else:
                    return {
                        "msgs": "\n".join([f"<li><div class=\"text\">{i + 1 + total_steps}. {m}</li>" for i, m in enumerate(msgs)]),
                        "count": count,
                        "is_die": is_die,
                        "die_reason": die_reason,
                        "decision": None,
                        "over": self.player.back and self.player.depth.value <= 0,
                    }
            if isinstance(msg, dict) and msg["type"] == "decision":
                return {
                    "msgs": "\n".join([f"<li><div class=\"text\">{i + 1 + total_steps}. {m}</li>" for i, m in enumerate(msgs)]),
                    "count": count,
                    "is_die": is_die,
                    "die_reason": die_reason,
                    "decision": msg,
                    "over": self.player.back and self.player.depth.value <= 0,
            }
            msgs.append(msg)
        if self.player.depth.value <= 0 and self.player.oxygen.value < self.player.oxygen.max_value:
            self.player.oxygen.change(lambda v: v + 100000)
        return {
            "msgs": "\n".join([f"<li><div class=\"text\">{i + 1 + total_steps}. {m}</li>" for i, m in enumerate(msgs)]),
            "count": count,
            "is_die": is_die,
            "die_reason": die_reason,
            "decision": None,
            "over": self.player.back and self.player.depth.value <= 0,
        }

    async def parse_decision_event(self, session, decision, prefix, suffix="") -> str:
        result = await self.event.build_decision_event(session, decision, self.player.region.value, message_prefix=prefix)
        await send_session_msg(session, result + suffix)
        return result

    # 阶段消息
    async def make_steps_message(self, session, steps_result: dict, prefix: str = "<h2>----------阶段总结----------</h2>\n<hr/>", suffix: str = "", send=True):
        prefix = prefix.format(chance=self.player.chance.value)
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
        if steps_result["over"]:
            print("OVER 探险结束")
            # self.status = "stop"
        if steps_result['is_die']:
            steps += f"<li><span class=\"die\">你已被迫结束探险。原因：{steps_result['die_reason']}</span></li></ul>"
            # self.player.coins = 0
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

def get_img_msg(
        md_str,
        player: Player,
    ):
    colors = player.get_card_color()
    text_color = colors["text_color"]
    card_border_color = colors["card_border_color"]
    card_background_color = colors["card_background_color"]
    fail_color = colors["fail_color"]
    win_color = colors["win_color"]
    ident_color = colors["ident_color"]
    dice_color = colors["dice_color"]
    region_color = colors["region_color"]
    effect_color = colors["effect_color"]
    event_color = colors["event_color"]
    attr_color = colors["attr_color"]
    line_color = colors["line_color"]
    color_style = f"""
<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Document</title>
        <style>
    :root {{
        --text-color: {text_color};
        --card-border-color: {card_border_color};
        --card-background-color: {card_background_color};
        --fail-color: {fail_color};
        --win-color: {win_color};
        --ident-color: {ident_color};
        --dice-color: {dice_color};
        --region-color: {region_color};
        --effect-color: {effect_color};
        --event-color: {event_color};
        --attr-color: {attr_color};
        --line-color: {line_color};
    }}

    """
    html_body = color_style + """
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
                color: var(--text-color);
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
                background-color: var(--card-background-color);
                padding: 25px 50px;
                border: 3px solid var(--card-border-color);
            }

            .failed, .die {
                color: var(--fail-color);
            }

            .win {
                color: var(--win-color);
            }

            .ident {
                color: var(--ident-color);
            }
            .other-lines {
                text-indent: 2em;
                max-width: 500px;
            }
            .other-lines span {
                text-indent: 0;
            }
            .dice {
                color: var(--dice-color)
            }
            .effect {
                color: var(--effect-color)
            }
            .region {
                color: var(--region-color)
            }

            .ev {
                color: var(--event-color);
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
                color: var(--attr-color);
            }
            main > p {
                text-align: center;
                font-size: 1.2em;
            }
            hr {
                border-color: var(--line-color);
                margin: 5px;
            }

            li {
                width: 100%;
                position: relative;
            }

            strong {
                font-size: 1em;
                font-weight: bold;
                text-align: left;
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
    # print(html_body)
    html_content = html_body + html_str + """\n
            </main>
    </body>
</html>
    """
    uid = str(uuid4())
    hti.screenshot(html_str=html_content, save_as=f"seekcard{uid}.png", size=(1920, 10000))
    image = crop_transparent_area(f"seekcard{uid}.png")
    os.remove(f"seekcard{uid}.png")
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

def is_stepping(reply, step_name="s"):
    return reply.startswith(step_name) and len(reply.split(step_name)) > 1 and reply.split(step_name)[1].strip().isdigit()

seek_alias = ["寻宝", 'sk']
command_name = "seek"

TIMES_LIMIT = 2

seeking_groups = [

]


async def limited(func, session: CommandSession, user: user.User, *args, **kwargs):
    # print(args, kwargs)
    result = await func(session, user, *args, **kwargs)
    # print(result)
    if result['state'] == 'OK':
        result['data']['limited'] = True
    return result

@on_command(command_name, aliases=seek_alias, only_to_me=False, permission=lambda _: True)
@user.using_user(save_data=True)
# @permission(lambda sender: sender.from_group(727949269) or sender.is_superuser, permission_help="在 179 的主群使用 或 是 SUPERUSER")
@user.custom_limit(command_name, 1, TIMES_LIMIT, TimeUnit.DAY)
async def _(session: CommandSession, u: user.User, validate, count_tick):
    try:
        global seeking_groups
        # TODO 插件管理系统
        enable_groups: list = read_from_path(BOT_SETTINGS_PATH)["seek_enable_groups"]

        arg = session.current_arg_text.strip()
        is_sim = False
        sender = await SenderRoles.create(session.bot, session.event)
        if arg in ["sim", "simulation"]:
            if not sender.is_privatechat:
                return await send_session_msg(session, get_message("plugins", __plugin_name__, command_name, 'not_private'))
            is_sim = True

        if arg in ["swi", "switch"]:
            if not sender.is_groupchat:
                return await send_session_msg(session, get_message("plugins", __plugin_name__, command_name, 'not_group'))
            if not sender.is_admin and not sender.is_superuser and not sender.is_owner:
                return await send_session_msg(session, get_message("plugins", __plugin_name__, command_name, 'not_admin'))
            if str(session.event.group_id) in enable_groups:
                await send_session_msg(session, get_message("plugins", __plugin_name__, command_name, 'disable'))
                enable_groups.remove(str(session.event.group_id))
            else:
                reply = (await session.aget(at=True, prompt=get_message("plugins", __plugin_name__, command_name, 'enable_warning'))).strip()
                if reply != 'y':
                    return await send_session_msg(session, get_message("plugins", __plugin_name__, command_name, 'cancel_enable'))
                enable_groups.append(str(session.event.group_id))
                await send_session_msg(session, get_message("plugins", __plugin_name__, command_name, 'enable'))
            return change_json(BOT_SETTINGS_PATH, "seek_enable_groups", set_method=lambda _: enable_groups)


        if arg not in ["start", "st"] and not is_sim:
            await send_session_msg(session, get_message("plugins", __plugin_name__, command_name, 'introduction'))
            return False

        # ---------- START ---------- #
        if str(session.event.group_id) not in enable_groups and sender.is_groupchat:
            if sender.is_admin or sender.is_owner:
                return await send_session_msg(session, get_message("plugins", __plugin_name__, command_name, 'not_enable_admin'))
            return await send_session_msg(session, get_message("plugins", __plugin_name__, command_name, 'not_enable'))

        if validate() and not is_sim:
            return await send_session_msg(session, get_message("plugins", __plugin_name__, command_name, 'limit'))
        if sender.is_groupchat and session.event.group_id in seeking_groups:
            return await send_session_msg(session, get_message("plugins", __plugin_name__, command_name, 'group_seeking'))

        from .seek_events import EVENTS
        player = Player()
        seek = Seek(player, EVENTS)
        total_results = []
        # total_messages: list[MessageSegment] = []
        seek.status = "start"
        if sender.is_groupchat:
            seeking_groups.append(session.event.group_id)
            # 处理 每一次机会（？）
        async def parse_event_steps(total_steps, expected_steps, prefix='', msg_prefix="", prefix_onlyonce=False):
            msgs = ""
            step_results = []
            last_event = ''
            while expected_steps > 0 and seek.status == "start":
                result = seek.parse_steps(expected_steps, total_steps)
                # --------- 检测成就
                if player.region.value == SeekRegion.ABYSS:
                    await u.achieve_achievement(session, "来自深渊")
                if len(player.achieved_achievements) > 0:
                    for a in player.achieved_achievements:
                        await u.achieve_achievement(session, a)
                        player.achieved_achievements.remove(a)
                # ---------
                msgs += last_event + result["msgs"] + "\n"
                expected_steps -= result["count"]
                total_steps += result["count"]
                if result["over"]:
                    expected_steps = 0
                continue_message = get_message("plugins", __plugin_name__, command_name, 'continue_step_tip') if player.depth.value > 0 else get_message("plugins", __plugin_name__, command_name, 'continue_step_tip_onsea')
                step_results = await seek.make_steps_message(session, result, prefix=prefix, send=False)
                if player.depth.value <= 0:
                    # 回到海面补充一下氧气
                    player.oxygen.change(lambda v: v + 10000)
                # 什么都没有就不输出空白
                msg = ""
                if step_results[0].strip() != prefix:
                    md_msg = "\n".join(step_results)
                    msg = msg_prefix + (await image_msg(get_img_msg(md_msg, player))) + (continue_message if result["decision"] is None else "")
                    if result["decision"] is None:
                    # new_messages += [change_group_message_content(msg_dict, r) for r in step_results]
                        await send_session_msg(session, msg)
                step_results = []
                if result["decision"] is not None:
                    suffix = ''
                    if expected_steps <= 0:
                        suffix = continue_message
                    decision_result = await seek.parse_decision_event(session, result["decision"], prefix=msg + "---------决策事件----------\n", suffix= "\n" + suffix)
                    # step_results.insert(1, decision_result)
                    last_event = decision_result + "\n"
                total_results.append("\n".join(step_results))
                msgs = ""
                if prefix_onlyonce:
                    prefix = ""
                    msg_prefix = ""
            return total_steps


        total_steps = 0
        expected_steps = 20
        # msgs = ""
        if is_sim:
            message = get_message("plugins", __plugin_name__, command_name, 'seek_simulation')
        else:
            message = get_message("plugins", __plugin_name__, command_name, 'seek_start')
        # TODO: get_tools_str↑
        start_prefix = "----------开头总结----------"
        total_steps = await parse_event_steps(total_steps, expected_steps, prefix=f'<h2>----------出发玩家属性----------</h2><div class=\"fl\">{player.get_attr_str(detailed=True, html=True)}</div>\n<p>使用道具：无</p>\n<hr>\n<h2>{html_messy_string(start_prefix, temperature=player.get_messy_rate())}</h2>\n<hr/>\n', msg_prefix=message, prefix_onlyonce=True)
        while seek.status == "start" and player.chance.value > 0:
            expected_steps = 0
            valid_reply = False
            player.back = False
            while not valid_reply:
                reply: str = await session.aget()
                reply = reply.strip()
                if reply == "quit":
                    seek.status = "exit"
                    if player.depth.value <= 0:
                        # 正常结束
                        seek.status = "stop"
                    valid_reply = True
                    # await send_session_msg(session, get_message("plugins", __plugin_name__, command_name, 'introduction'))
                elif is_it_command(reply):
                    await send_session_msg(session, get_message("plugins", __plugin_name__, command_name, 'on_seeking'))
                elif is_stepping(reply, "b") and player.depth.value > 0:
                    expected_steps = int(reply.split("b")[1].strip())
                    if expected_steps > 30 or expected_steps < 1:
                        await send_session_msg(session, get_message("plugins", __plugin_name__, command_name, "invalid_step", count=expected_steps, max=30))
                        continue
                    player.back = True
                    valid_reply = True
                elif is_stepping(reply):
                    expected_steps = int(reply.split("s")[1].strip())
                    if expected_steps > 20 or expected_steps < 1:
                        await send_session_msg(session, get_message("plugins", __plugin_name__, command_name, "invalid_step", count=expected_steps, max=20))
                        continue
                    valid_reply = True
            # result = await seek.parse_steps(step)
            prefix = "----------阶段总结[剩余 {chance} 次机会]----------"
            player.chance.change(lambda v: v - 1)
            total_steps = await parse_event_steps(total_steps, expected_steps, prefix=f'<h2>{prefix}</h2>\n<hr/>\n')
            # print(player.chance.value, seek.status)
        # 结算

        # 最后统计的值
        result_value = player.coins.value
        if player.depth.value > 20 and seek.status == "exit":
            result_value = 0 if result_value > 0 else result_value
            # coins_str = f"{player.coins.name}: {result_value}"
        # if player.depth.value > 20: # 基准深度 20，超过有惩罚
        #     # 深度惩罚
        #     depth_punish = min(player.coins.value * 0.8 / 0.9 / math.log(player.depth.value), player.coins.value)
        #     result_value = player.coins.value - depth_punish
        #     # 对于手动退出的情况，无论如何星币数只能不大于 0
        #     if seek.status == "exit" or player.is_die()[0] == True:
        #         result_value = 0 if result_value > 0 else result_value
        #     coins_str = f"{player.coins.name}: {result_value}"
        gain_ratio = 1
        # 深度惩罚
        if player.depth.value > 300:
            gain_ratio = 0
        elif player.depth.value > 200:
            gain_ratio = 0.1
        elif player.depth.value > 100:
            gain_ratio = 0.2
        elif player.depth.value > 50:
            gain_ratio = 0.5
        elif player.depth.value > 20:
            gain_ratio = 0.7

        #########
        exit_punish = 1
        if seek.status == "exit":
            exit_punish = 0
        no_exit_result = int(result_value * gain_ratio)
        result_value = no_exit_result * exit_punish
        coins_str = f"{player.coins.name}: {player.coins.value} - {player.coins.value - no_exit_result} (深度惩罚){(' * ' + str(exit_punish) + ' (放弃惩罚) ') if exit_punish != 1 else ''}  结算: {result_value}"
        if not is_sim and player.coins.value > 1000 and result_value == 0:
            await u.achieve_achievement(session, "满载无归")
        if sender.is_groupchat:
            try:
                seeking_groups.remove(session.event.group_id)
            except:
                print(f"无法移除群 id {session.event.group_id} 因为不存在。")
        if is_sim:
            await send_session_msg(session, get_message("plugins", __plugin_name__, command_name, 'result_msg_simulation', gain=f"{coins_str}"))
            return
        else:
            count_tick()
        if result_value > 0 and seek.status != "exit":
            await u.get_coins(session, result_value, _get_message = get_message("plugins", __plugin_name__, command_name, 'result_msg_with_coins', gain=f"{coins_str}", coins=result_value))
        else:
            await send_session_msg(session, get_message("plugins", __plugin_name__, command_name, 'result_msg', gain=f"{coins_str}"))
        return True
    except Exception as ex:
        if sender.is_groupchat:
            try:
                seeking_groups.remove(session.event.group_id)
            except:
                print(f"无法移除群 id {session.event.group_id} 因为不存在。")
        traceback.print_exc()
        return await send_session_msg(session, get_message("plugins", __plugin_name__, command_name, 'error_msg', ex=traceback.format_exc()))
    # await sleep(10)