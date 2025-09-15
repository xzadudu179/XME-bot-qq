import config
from xme.xmetools import colortools as c
from xme.xmetools import dicttools
from functools import wraps
from xme.xmetools.msgtools import send_event_msg
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
    # if name == "wife" and '[CQ:at,qq=' not in args:
        # await event_send_msg(bot, event, get_message('other', 'wife_error'))
        # await send_msg(session, "注意：你在一个可回复的指令后面执行了 wife 指令，会默认显示我的老婆 uwu")
    print(f"parse command: {name} | {args}")
    await call_command(
        bot=bot,
        event=event,
        name=name,
        current_arg=args,
        check_perm=check_permission)

def get_command_args(arg_text: str, mim_args_len: int, max_args_len: int, split_str: str = None, default: str = "") -> list[str]:
    """获取指令参数列表

    Args:
        arg_text (str): 需要解析的指令参数部分
        mim_args_len (int): 最小参数列表长度
        split_str (str, optional): 参数列表分割方式，会被用在 split 函数作为参数. Defaults to None.
        default (str, optional): 为了补充至最小参数列表长度所用的默认值. Defaults to "".

    Returns:
        list[str]: 参数列表
    """
    args = [a for a in arg_text.split(split_str) if a]
    if mim_args_len == 0 or max_args_len == 0:
        return args
    elif len(args) < mim_args_len:
        args += [default for _ in range(mim_args_len - len(args))]
    elif len(args) > max_args_len:
        args = args[:max_args_len]
    return args

async def send_cmd(cmd_string, session, check_permission=True):
    return await event_send_cmd(cmd_string, session.bot, session.event, check_permission)

def get_alias_by_cmd(cmd_name: str):
    cmds = {k.name[0]: v for k, v in dicttools.reverse_dict(CommandManager._aliases).items()}
    # print(cmds)
    return cmds.get(cmd_name, False)

def use_args(arg_len: int, split_str: str = None, default: str = ""):
    """解析指令内参数，会添加一个名叫 arg_list 的指定参数

    Args:
        arg_len (int): 参数列表长度
        split_str (str, optional): 分割方法. Defaults to None.
        default (str, optional): 未获取到参数时的默认值. Defaults to "".
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(session: CommandSession, *args, **kwargs):
            arg_list = get_command_args(session.current_arg_text, arg_len, arg_len, split_str, default)
            return await func(session, arg_list=arg_list, *args, **kwargs)

        return wrapper

    return decorator

def get_cmds():
    """得到指令列表
    """
    return CommandManager._commands

def get_cmds_alias_strings():
    """得到指令与别名列表
    """
    cmds =  [k[0] for k in get_cmds().keys()] + [k for k in get_alias().keys()]
    return cmds
    # alias_cmds = []
    # for c in cmds:
    #     alias = get_alias_by_cmd(c)
    #     alias_cmds.append(c)
    #     if alias is not False:
    #         alias_cmds += alias
    # return alias_cmds

def get_alias():
    return CommandManager._aliases

def is_it_command(text):
    """检测一个文本是否属于指令

    Args:
        text (str): 文本

    Returns:
        bool: 是否
    """
    # print("111")
    # print(event)
    # if raw_msg[0] not in config.COMMAND_START or not raw_msg[1:] or not raw_msg.replace(raw_msg[0], ""):
    if len(text) < 1:
        return False
    if not text[0] in config.COMMAND_START[0] or not text[1:] or not text.replace(text[0], ""):
        return False

    if not get_cmd_by_alias(text.split(" ")[0]):
        return False
    return True

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
        # print("有这个指令")
        return CommandManager._commands.get((name,), False)

def get_args(arg_text: str):
    """得到参数列表

    Args:
        arg_text (str): 参数字符串

    Returns:
        tuple[str]: 参数
    """
    return tuple([a for a in arg_text.strip().split(" ") if a])