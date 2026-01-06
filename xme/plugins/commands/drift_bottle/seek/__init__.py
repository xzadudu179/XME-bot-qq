from xme.xmetools.timetools import *
from xme.plugins.commands.drift_bottle import __plugin_name__
from xme.xmetools.cmdtools import is_command
from .classes.player import SeekRegion
from xme.xmetools.bottools import get_group_name
from xme.xmetools.filetools import b64_encode_file
from xme.xmetools.timetools import TimeUnit
from config import BOT_SETTINGS_PATH
from html2image import Html2Image
from xme.xmetools.randtools import html_messy_string, messy_image
from character import get_message
from xme.xmetools.imgtools import crop_transparent_area, image_msg
from xme.xmetools.jsontools import change_json, read_from_path
from nonebot import SenderRoles
import time
import asyncio
import os
from xme.plugins.commands.xme_user.classes import user
import random
import traceback
from .classes.player import Player
from .classes.event import Event, SPECIAL_EVENTS
random.seed()
from .. import DriftBottle, get_random_bottle
from nonebot import CommandSession, MessageSegment
from xme.xmetools.plugintools import on_command
from xme.xmetools.msgtools import send_session_msg, aget_session_msg
from uuid import uuid4
hti = Html2Image()


class Seek:
    def __init__(self, player: Player, events: list[dict]):
        self.player = player
        self.event = Event(self.player)
        self.events = events
        self.status = "stop"
        self.total_steps = 0

    async def parse_steps(self, step_count, total_steps: int, is_sim) -> dict:
        msgs = []
        count = 0
        self.status = "start"
        # isover = 0
        for _ in range(step_count):
            count += 1
            for tool in self.player.tools:
                if tool.can_apply():
                    msgs.append(tool.apply_event(self.event))
            msg = SeekStep(self.event).gen_step(self.events, self.player, is_sim=is_sim)
            is_die, die_reason = self.player.is_die()
            if (self.player.back and self.player.depth.value <= 0) or is_die:
                # 回到海面，新增一步回到海面的计算
                if not is_die:
                    msgs.append(msg)
                    msgs.append(SeekStep(self.event).gen_event_step(SPECIAL_EVENTS["on_sea"], self.player))
                return {
                    "msgs": "\n".join([f"<li><div class=\"text\">{i + 1 + total_steps}. {m}</li>" for i, m in enumerate(msgs)]),
                    "count": count,
                    "is_die": is_die,
                    "die_reason": die_reason,
                    "decision": None,
                    "over": self.player.back and self.player.depth.value <= 0,
                }
            # 处理决策事件，决策事件会直接返回字典
            if isinstance(msg, dict) and msg["type"] == "decision":
                # if len(msgs) < 1:
                    # msgs.append()
                return {
                    "msgs": "\n".join([f"<li><div class=\"text\">{i + 1 + total_steps}. {m}</li>" for i, m in enumerate(msgs)]),
                    "count": count,
                    "is_die": is_die,
                    "die_reason": die_reason,
                    "decision": msg,
                    "over": self.player.back and self.player.depth.value <= 0,
                }
            # 因为决策事件不在卡片里，所以并不会被添加到 msgs
            msgs.append(msg)
        # if self.player.depth.value <= 0 and self.player.oxygen.value < self.player.oxygen.max_value:
        #     self.player.oxygen.change(lambda v: v + 100000)

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

    @staticmethod
    def special_message(content: str, html_class="tip"):
        return f"<li><span class=\"{html_class}\">{content}</span></li>"

    # 阶段消息
    async def make_steps_message(self, session, steps_result: dict, prefix: str = "<h2>----------阶段总结----------</h2>\n<hr/>", suffix: str = "", send=True):
        prefix = prefix.format(chance=self.player.chance.value)
        msgs = steps_result['msgs']
        if len(steps_result['msgs']) < 1:
            msgs = Seek.special_message("暂时没有任何事件...")
        steps = f"{prefix}<ul>{msgs}"

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
            steps += Seek.special_message(f"你已被迫结束探险。原因：{steps_result['die_reason']}", html_class="die")
            # steps += f"<li><span class=\"die\">你已被迫结束探险。原因：{steps_result['die_reason']}</span></li></ul>"
            # self.player.coins = 0
            self.status = "stop"
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
                font-family: "Helvetica Neue", "Noto Sans CJK SC", sans-serif;
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
                font-weight: normal;
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

            .tip {
                color: var(--attr-color);
            }

            .ident {
                color: var(--ident-color);
            }
            .other-lines {
                text-indent: 2em;
                max-width: 415px;
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
                width: 600px;
                flex-wrap: wrap;
                justify-content: center;
            }
            .fl div {
                padding: 10px 20px;
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

    def gen_step(self, events, player: Player, is_sim) -> str | dict:
        # print(player.region)
        return self.event.gen_event(events, player.region.value, is_sim=is_sim)

    def gen_event_step(self, event_dict: dict, player: Player):
        """生成单独事件的寻宝步数

        Args:
            event_dict (dict): 事件字典
            player (Player): 当前玩家
        """
        return self.event.create_event(event_dict, player.region.value)


def is_stepping(reply, step_name="s"):
    return reply.startswith(step_name) and len(reply.split(step_name)) > 1 and reply.split(step_name)[1].strip().isdigit()

seek_alias = ["寻宝", 'sk']
command_name = "seek"

TIMES_LIMIT = 2

seeking_groups = [

]
seeking_players = {
    # xxx: time
}


async def limited(func, session: CommandSession, user: user.User, *args, **kwargs):
    # print(args, kwargs)
    result = await func(session, user, *args, **kwargs)
    # print(result)
    if result['state'] == 'OK':
        result['data']['limited'] = True
    return result

def validate_group(session: CommandSession, sender):
    if sender.is_groupchat and session.event.group_id in seeking_groups:
        return False
    return True

def validate_player(session: CommandSession) -> bool:
    """
    验证玩家是否可探险
    """
    global seeking_players
    if session.event.user_id not in seeking_players.keys():
        return True
    if time.time() - seeking_players[session.event.user_id]["time"] > 1800:
        del seeking_players[session.event.user_id]
        return True
    return False

@on_command(command_name, aliases=seek_alias, only_to_me=False, permission=lambda _: True)
@user.using_user(save_data=True)
# @permission(lambda sender: sender.from_group(727949269) or sender.is_superuser, permission_help="在 179 的主群使用 或 是 SUPERUSER")
@user.custom_limit(command_name, 1, TIMES_LIMIT, TimeUnit.DAY)
async def _(session: CommandSession, u: user.User, validate, count_tick):
    try:
        global seeking_groups
        global seeking_players
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
                reply = (await aget_session_msg(session, prompt=get_message("plugins", __plugin_name__, command_name, 'enable_warning'))).strip()
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
        # # 验证该群是否有人在探险
        if not validate_group(session, sender):
            return await send_session_msg(session, get_message("plugins", __plugin_name__, command_name, 'group_seeking'))
        # # 验证正在探险的玩家防止多开
        if not validate_player(session):
            return await send_session_msg(session, get_message("plugins", __plugin_name__, command_name, 'seek_on_seeking', place=seeking_players[session.event.user_id]["place"]))
        from .seek_events import EVENTS
        player = Player()
        seek = Seek(player, EVENTS)
        total_results = []
        # total_messages: list[MessageSegment] = []
        seek.status = "start"
        # seek_operate_time = time.time()
        seeking_players[session.event.user_id] = {
            "time": time.time(),
            "place": f"{await get_group_name(session.event.group_id)}" if session.event.group_id is not None else "私聊"
        }
        if sender.is_groupchat:
            seeking_groups.append(session.event.group_id)
            # 处理 每一次机会（？）
        async def parse_event_steps(total_steps, expected_steps, prefix='', msg_prefix="", prefix_onlyonce=False):
            # seek_operate_time = time.time()
            msgs = ""
            step_results = []
            last_event = ''
            while expected_steps > 0 and seek.status == "start":
                result = await seek.parse_steps(expected_steps, total_steps, is_sim=is_sim)
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
                    msg = msg_prefix + (await image_msg(messy_image(get_img_msg(md_msg, player), (100 - player.san.value) / 3.5, rand_color=False))) + (continue_message if result["decision"] is None else "")
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
            afk = False
            while not valid_reply:
                try:
                    reply: str = await asyncio.wait_for(aget_session_msg(session), timeout=300)
                except asyncio.TimeoutError:
                    # 5 分钟没有操作
                    if afk:
                        seek.status = 'exit'
                        break
                    msg_name = "seeking_tip"
                    if player.depth.value <= 0:
                        msg_name = "seeking_tip_onsea"
                    await send_session_msg(session, get_message("plugins", __plugin_name__, command_name, msg_name))
                    afk = True
                    continue
                reply = reply.strip()
                if reply == "quit":
                    seek.status = "exit"
                    if player.depth.value <= 0:
                        # 正常结束
                        seek.status = "stop"
                    valid_reply = True
                    # await send_session_msg(session, get_message("plugins", __plugin_name__, command_name, 'introduction'))
                elif is_command(reply):
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
            if seek.status != "exit" and afk:
                afk = False
            if afk:
                break
            prefix = "----------阶段总结[剩余 {chance} 次机会]----------"
            player.chance.change(lambda v: v - 1)
            total_steps = await parse_event_steps(total_steps, expected_steps, prefix=f'<h2>{prefix}</h2>\n<hr/>\n')
            # print(player.chance.value, seek.status)
    except TimeoutError as ex:
        seek.status = "exit"
    except Exception as ex:
        if sender.is_groupchat:
            try:
                seeking_groups.remove(session.event.group_id)
            except:
                print(f"无法移除群 id {session.event.group_id} 因为不存在。")
        try:
            del seeking_players[session.event.user_id]
        except:
            print(f"无法移除用户 id {session.event.user_id} 因为不存在。")
        traceback.print_exc()
        return await send_session_msg(session, get_message("plugins", __plugin_name__, command_name, 'error_msg', ex=traceback.format_exc()))
    # await sleep(10)
    # 结算
    # 最后统计的值
    result_value = player.coins.value
    if player.depth.value > 20 and seek.status == "exit":
        result_value = 0 if result_value > 0 else result_value

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
    # 去除放弃惩罚
    exit_punish = 1
    # if seek.status == "exit":
        # exit_punish = 0
    no_exit_result = int(result_value * gain_ratio)
    result_value = no_exit_result * exit_punish
    coins_str = f"{player.coins.name}: {player.coins.value} - {player.coins.value - no_exit_result}(深度惩罚)  结算:{result_value}"
    if not is_sim and player.coins.value > 1000 and result_value == 0:
        await u.achieve_achievement(session, "满载无归")
    try:
        del seeking_players[session.event.user_id]
    except:
        print(f"无法移除用户 {session.event.user_id} 因为不存在。")
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