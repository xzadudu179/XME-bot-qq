import config
from nonebot.command import call_command, CommandManager, Command

async def send_cmd(cmd_string, session, check_permission=True):
    name = cmd_string.split(" ")[0]
    if name[0] in config.COMMAND_START:
        name = name[1:]
    alias_cmd: Command = CommandManager._aliases.get(name, False)
    if alias_cmd:
        name = alias_cmd.name
    # print(CommandManager._find_command(self=CommandManager, name=name))
    args = " ".join((cmd_string.split(" ")[1:])) if len(cmd_string.split(" ")) > 1 else ""
    print(f"parse command: {name} | {args}")
    await call_command(
        bot=session.bot,
        event=session.event,
        name=name,
        current_arg=args,
        check_perm=check_permission)