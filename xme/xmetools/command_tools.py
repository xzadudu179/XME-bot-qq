import config
from nonebot.command import call_command, CommandManager, Command
from nonebot import CommandSession
from character import get_message

async def send_cmd(cmd_string, session, check_permission=True):
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
        await send_msg(session, get_message('other', 'wife_error'))
        # await send_msg(session, "注意：你在一个可回复的指令后面执行了 wife 指令，会默认显示我的老婆 uwu")
    print(f"parse command: {name} | {args}")
    await call_command(
        bot=session.bot,
        event=session.event,
        name=name,
        current_arg=args,
        check_perm=check_permission)

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

async def send_msg(session: CommandSession, message, at=True, **kwargs):
    await session.send(str(message), at_sender=at, **kwargs)