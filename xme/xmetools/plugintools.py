import shlex
import warnings
from datetime import timedelta
from typing import Union, Optional, Iterable, Callable, Type
from nonebot import permission as perm
from nonebot.command import Command, CommandManager, CommandSession
from nonebot.typing import CommandName_T, CommandHandler_T, Patterns_T, PermissionPolicy_T
from nonebot.plugin import Plugin

def on_command(
    name: Union[str, CommandName_T],
    *,
    aliases: Union[Iterable[str], str] = (),
    patterns: Patterns_T = (),
    permission: Union[PermissionPolicy_T, Iterable[PermissionPolicy_T]] = ...,
    only_to_me: bool = True,
    privileged: bool = False,
    shell_like: bool = False,
    expire_timeout: Optional[timedelta] = ...,
    run_timeout: Optional[timedelta] = ...,
    session_class: Optional[Type[CommandSession]] = None
) -> Callable[[CommandHandler_T], CommandHandler_T]:
    """
    Decorator to register a function as a command.

    :param name: command name (e.g. 'echo' or ('random', 'number'))
    :param aliases: aliases of command name, for convenient access
    :param patterns: custom regex pattern for the command.
           Please use this carefully. Abuse may cause performance problem.
           Also, Please notice that if a message is matched by this method,
           it will use the full command as session current_arg.
    :param permission: permission required by the command
    :param only_to_me: only handle messages to me
    :param privileged: can be run even when there is already a session
    :param shell_like: use shell-like syntax to split arguments
    :param expire_timeout: will override SESSION_EXPIRE_TIMEOUT if provided
    :param run_timeout: will override SESSION_RUN_TIMEOUT if provided
    :param session_class: session class
    """
    real_permission = perm.aggregate_policy(permission) \
        if isinstance(permission, Iterable) else permission

    def deco(func: CommandHandler_T) -> CommandHandler_T:
        if not isinstance(name, (str, tuple)):
            raise TypeError('the name of a command must be a str or tuple')
        if not name:
            raise ValueError('the name of a command must not be empty')
        if session_class is not None and not issubclass(session_class,
                                                        CommandSession):
            raise TypeError(
                'session_class must be a subclass of CommandSession')

        cmd_name = (name,) if isinstance(name, str) else name

        cmd = Command(name=cmd_name,
                      func=func,
                      only_to_me=only_to_me,
                      privileged=privileged,
                      permission=real_permission,
                      expire_timeout=expire_timeout,
                      run_timeout=run_timeout,
                      session_class=session_class)

        if shell_like:

            async def shell_like_args_parser(session: CommandSession):
                session.state['argv'] = shlex.split(session.current_arg) if \
                    session.current_arg else []

            cmd.args_parser_func = shell_like_args_parser

        if Plugin.GlobalTemp.now_within_plugin:
            Plugin.GlobalTemp.commands.append((cmd, aliases, patterns))
        else:
            CommandManager.add_command(cmd_name, cmd)
            CommandManager.add_aliases(aliases, cmd)
            CommandManager.add_patterns(patterns, cmd)
            warnings.warn('defining command_handler outside a plugin is deprecated '
                          'and will not be supported in the future')

        func.args_parser = cmd.args_parser

        return func

    return deco
