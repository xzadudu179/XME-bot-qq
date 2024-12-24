from nonebot import on_command, CommandSession, NoneBot, MessageSegment, message_preprocessor, Message
from nonebot.command import call_command
from nonebot.plugin import PluginManager
import aiocqhttp
from xme.xmetools.doc_gen import CommandDoc, shell_like_usage
from xme.xmetools.json_tools import read_from_path
from xme.xmetools.command_tools import get_cmd_by_alias, event_send_msg
from xme.xmetools.message_tools import change_group_message_content, send_forward_msg, get_pure_text_message
from character import get_message
import xme.xmetools.text_tools as t
from keys import GLM_API_KEY
import asyncio
from zhipuai import ZhipuAI

arg_usage = shell_like_usage("OPTION", [
    {
        "name": "help",
        "abbr": "h",
        "desc": "查看帮助"
    },
    {
        "name": "language",
        "abbr": "l",
        "desc": "指定要翻译成的语言"
    }
])

alias = ['trans']
__plugin_name__ = 'translate'
__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    desc=get_message(__plugin_name__, 'desc'),
    introduction=get_message(__plugin_name__, 'introduction'),
    usage=f'<要翻译成的语言> <消息数量>',
    permissions=[],
    alias=alias
))

@message_preprocessor
async def is_it_translate(bot: NoneBot, event: aiocqhttp.Event, plugin_manager: PluginManager):
    # print("running")
    # print(event.raw_message)
    if "[CQ:reply" not in event.raw_message:
        return
    reply_id = int(event.raw_message.split("[CQ:reply,id=")[1].split("]")[0])
    cmd_msg = event.raw_message.split("]")[-1].strip()
    # print(reply_id, event.raw_message, cmd_msg)
    cmd_name = cmd_msg.split(" ")[0].strip()[1:]
    # print(cmd_name, alias + [__plugin_name__])
    if not cmd_name in alias + [__plugin_name__]:
        return
    elif cmd_name in alias:
        cmd_name = get_cmd_by_alias(cmd_name, False).name[0]
    print(f"执行指令: {cmd_name}")
    return await translate_message(bot, event, reply_id, cmd_msg.split(" ")[1:], True)

@on_command(__plugin_name__, aliases=alias, only_to_me=False)
async def _(session: CommandSession):
    await translate_message(session.bot, session.event, session.event.message_id, session.current_arg_text.strip().split(" "))

async def translate_message(bot: NoneBot, event: aiocqhttp.Event, message_id, args, reply=False):
    MAX_MESSAGES_COUNT = 50
    # args = session.current_arg_text.strip().split(" ")
    # print(args)
    lan_arg = args[0] if len(args) >= 1 else ""
    count_arg: str = args[1] if len(args) > 1 else ""
    count = 1
    if lan_arg.isdigit() and not count_arg:
        count_arg = lan_arg
        lan_arg = ""
    elif lan_arg.isdigit() and count_arg and not count_arg.isdigit():
        count_arg, lan_arg = lan_arg, count_arg
        # lan_arg = count_arg
    print(f"count: {count_arg}, lan: {lan_arg}")
    if not count_arg:
        count = 1
    elif not count_arg.isdigit():
        return await event_send_msg(bot, event, get_message(__plugin_name__, 'invalid_count'))
    elif int(count_arg) < 1:
        return await event_send_msg(bot, event, get_message(__plugin_name__, 'count_too_low'))
    elif int(count_arg) > MAX_MESSAGES_COUNT:
        return await event_send_msg(bot, event, get_message(__plugin_name__, 'count_too_many', max_count=MAX_MESSAGES_COUNT))
    else:
        count = int(count_arg)

    if count > 2:
        await event_send_msg(bot, event, get_message(__plugin_name__, 'processing', language=lan_arg if lan_arg else "自动检测语言",  min=f"{(count * 0.3):.2f}", max=f"{(count * 2.5):.2f}"))

    received_messages = (await bot.api.call_action("get_group_msg_history", group_id=event.group_id, message_id=message_id, count=count if reply else count + 1))["messages"]
    if not reply:
        received_messages = received_messages[:-1]

    new_messages: list[MessageSegment] = []
    for msg in received_messages:
        # print(msg)
        msg_dict = msg
        msg = get_pure_text_message(msg_dict)
        lan = "中文"
        if not lan_arg:
            if t.chinese_proportion(msg) >= 0.3:
                lan = "英文"
        else:
            lan = lan_arg
        new_messages.append(change_group_message_content(msg_dict, await translate(msg, lan)))
        # new_messages.append(change_group_message_content(msg, "test"))
    print(lan)
    # print(f"messages: {new_messages}")
    if len(new_messages) > 1:
        return await send_forward_msg(bot, event, new_messages)
    elif len(new_messages) == 1:
        return await event_send_msg(bot, event, get_message(__plugin_name__, 'success_message', name=new_messages[0]["data"]["nickname"], message=new_messages[0]["data"]["content"], language=lan))
    return await event_send_msg(bot, event, get_message(__plugin_name__, 'no_message'))

async def translate(text, language):
    client = ZhipuAI(api_key=GLM_API_KEY)
    role = read_from_path("./ai_configs.json")[__plugin_name__]["system"]
    response = client.chat.asyncCompletions.create(
    # model="glm-4-flashx",
    model="glm-4-plus",
    messages=[
            {"role": "system","content": role},
            {"role": "user","content": f"翻译到{language}: {text}"}
        ], temperature=0.03)
    task_id = response.id
    task_status = ''
    get_cnt = 0
    while task_status != 'SUCCESS' and task_status != 'FAILED' and get_cnt <= 40:
        result_response = client.chat.asyncCompletions.retrieve_completion_result(id=task_id)
        # print(result_response)
        task_status = result_response.task_status
        await asyncio.sleep(0.1)
        get_cnt += 1
    return result_response.choices[0].message.content