import shlex
import warnings
from datetime import timedelta
from typing import Union, Optional, Iterable, Callable, Type
from nonebot import permission as perm
from nonebot.command import Command, CommandManager, CommandSession
from nonebot.typing import CommandName_T, CommandHandler_T, Patterns_T, PermissionPolicy_T
from nonebot.plugin import Plugin
from xme.xmetools.msgtools import send_to_superusers, send_session_msg
from character import get_message
from bot_variables import command_msgs
from traceback import format_exc
from xme.xmetools.dicttools import set_value
from xme.xmetools.cmdtools import clean_cmd_msgs
from nonebot.command import _FinishException
import functools
# from xme.xmetools.debugtools import debug_msg
from nonebot.log import logger
import time
from xme.xmetools.dbtools import DATABASE

class PluginCallData:
    def __init__(
            self,
            name: str,
            call_time: float,
            from_user_id: int,
            call_group: str,
            success: bool,
            time_cost: float,
            db_id: int = -1
        ):
        self.name = name
        self.call_time = call_time
        self.from_user_id = from_user_id
        self.call_group = call_group if call_group is not None else -1
        self.success = success
        self.time_cost = time_cost
        self.id = db_id

    @classmethod
    def get_table_name(cls):
        return PluginCallData.__name__

    @staticmethod
    def get_datas():
        return [PluginCallData.form_dict(d) for d in DATABASE.exec_query(f"SELECT * FROM {PluginCallData.get_table_name()}")]

    def save(self):
        self.id = DATABASE.save_to_db(self)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "call_time": self.call_time,
            "from_user_id": self.from_user_id,
            "call_group": self.call_group,
            "success": self.success,
            "time_cost": self.time_cost,
            "id": self.id
        }

    @staticmethod
    def get(db_id: int) -> 'PluginCallData':
        result = DATABASE.load_class(select_keys=(db_id,), query="SELECT * FROM {table_name} WHERE id = ?", cl=PluginCallData)
        if result is None:
            return None
        return result

    @staticmethod
    def form_dict(data: dict) -> 'PluginCallData':
        return PluginCallData(
            name=data["name"],
            call_time=data["call_time"],
            from_user_id=data["from_user_id"],
            call_group=data["call_group"],
            success=data["success"],
            time_cost=data["time_cost"],
            db_id=data["id"]
        )

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
        @functools.wraps(func)
        async def wrapper(session: CommandSession, *args, **kwargs):
            start = time.monotonic()
            call_time = time.time()
            success = False
            # 清理指令消息绑定
            try:
                clean_cmd_msgs()
            except RuntimeError:
                pass
            if session.event.message_id is not None:
                command_msgs[session.event.message_id] = {
                    "ids": [],
                    "time": call_time,
                    # 私聊为 None 和 userid
                    "open": f"{session.event.group_id}{session.event.user_id}"
                }
            try:
                result = await func(session, *args, **kwargs)
                success = True
                return result
            except _FinishException:
                success = True
                return result
            except TimeoutError:
                pass
            except Exception:
                logger.error(f"Command {cmd_name[0]} failed")
                try:
                    msg = get_message("config", "unknown_error", ex=format_exc())
                    await send_session_msg(session, msg)
                    await send_to_superusers(session.bot, msg + f"\n来自群 {session.event.group_id}，调用者 {session.event.user_id}")
                except Exception:
                    pass
                raise
            finally:
                if cmd_name[0] == "test":
                    return result
                cost = time.monotonic() - start
                data = PluginCallData(
                        cmd_name[0],
                        call_time=call_time,
                        from_user_id=session.event.user_id,
                        call_group=session.event.group_id,
                        success=success,
                        time_cost=cost,
                    )
                logger.info(f"存储指令调用数据：{data.to_dict()}")
                data.save()
                if session.event.message_id is not None:
                    set_value(session.event.message_id, "open", search_dict=command_msgs, set_method=lambda _: False)
                    # command_msgs[session.event.message_id]["open"] = False

        cmd = Command(name=cmd_name,
                      func=wrapper,
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