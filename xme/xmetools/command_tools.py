import config
from xme.xmetools import color_manage as c
from xme.xmetools import dict_tools
from nonebot import NoneBot
from xme.xmetools.message_tools import event_send_msg
import aiocqhttp
from nonebot.command import call_command, CommandManager, Command
from nonebot import CommandSession
from nonebot.session import BaseSession
from character import get_message

async def event_send_cmd(cmd_string, bot, event, check_permission=True):
    name = cmd_string.split(" ")[0]
    if name[0] in config.COMMAND_START:
        name = name[1:]
    else:
        return
    alias_cmd: Command = CommandManager._aliases.get(name, False)
    if alias_cmd:
        name = alias_cmd.name
    # print(CommandManager._find_command(self=CommandManager, name=name))
    args = " ".join((cmd_string.split(" ")[1:])) if len(cmd_string.split(" ")) > 1 else ""
    if name == "wife" and '[CQ:at,qq=' not in args:
        await event_send_msg(bot, event, get_message('other', 'wife_error'))
        # await send_msg(session, "注意：你在一个可回复的指令后面执行了 wife 指令，会默认显示我的老婆 uwu")
    print(f"parse command: {name} | {args}")
    await call_command(
        bot=bot,
        event=event,
        name=name,
        current_arg=args,
        check_perm=check_permission)

async def send_cmd(cmd_string, session, check_permission=True):
    return await event_send_cmd(cmd_string, session.bot, session.event, check_permission)

def get_alias_by_cmd(cmd_name: str):
    cmds = {k.name[0]: v for k, v in dict_tools.reverse_dict(CommandManager._aliases).items()}
    # print(cmds)
    return cmds.get(cmd_name, False)

def get_cmd_by_alias(input_string, need_cmd_start=True):
    """尝试通过别名获得指令

    Args:
        input_string (str): 输入的字符串
        need_cmd_start (bool, optional): 是否判断必须要包含命令开始字符. Defaults to True.

    Returns:
        Command | bool: 返回的结果（指令或False）
    """
    name = input_string.split(" ")[0]
    if name[0] in config.COMMAND_START:
        name = name[1:]
    elif name[0] not in config.COMMAND_START:
        if need_cmd_start:
            return False
    if CommandManager._commands.get((name,), False) == False:
        return CommandManager._aliases.get(name, False)
    else:
        print("有这个指令")
        return CommandManager._commands.get((name,), False)

def get_args(arg_text: str):
    """得到参数列表

    Args:
        arg_text (str): 参数字符串

    Returns:
        tuple[str]: 参数
    """
    return tuple([a for a in arg_text.strip().split(" ") if a])

async def send_session_msg(session: BaseSession, message, at=True, **kwargs):
    message_result = message
    message_result = await msg_preprocesser(session, message)
    if not message_result and message_result != "":
        print(f"bot 要发送的消息 {message} 已被阻止/没东西")
        return
    await session.send(str(message_result), at_sender=at, **kwargs)

# async def event_send_msg(bot: NoneBot, event: aiocqhttp.Event, message, at=True, **kwargs):
#     await bot.send(event, (f"[CQ:at,qq={event.user_id}] " if at and event.user_id else "") + message, **kwargs)

async def msg_preprocesser(session, message):
    funcs = {
        no_8694
    }
    for func in funcs:
        result = await func(message, session)
        if result and type(result) == str:
            message = result
    return message

async def no_8694(text, session: CommandSession, *_):
    replaced = False
    if "8964" in text:
        replaced = True
        text = text.replace("8964", "(8965-1)")
    if replaced:
        c.gradient_text("#FF5287", "#FF5257", "#FF8257", text=f"bot 输出的 \"{text}\" 有违禁词\n原发送者：{session.event.user_id} 在群 {session.event.group_id}")
    return text