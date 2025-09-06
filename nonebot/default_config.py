"""
Default configurations.

Any derived configurations must import everything from this module
at the very beginning of their code, and then set their own value
to override the default one.

For example:

>>> from nonebot.default_config import *
>>> PORT = 9090
>>> DEBUG = False
>>> SUPERUSERS.add(123456)
>>> NICKNAME = '小明'
"""

from datetime import timedelta
from typing import Collection, Union, Iterable, Pattern, Optional, Dict, Any

from .typing import Expression_T, PermissionPolicy_T

API_ROOT: str = ''
ACCESS_TOKEN: str = ''
SECRET: str = ''
HOST: str = '127.0.0.1'
PORT: int = 8080
DEBUG: bool = True

SUPERUSERS: Collection[int] = set()
NICKNAME: Union[str, Iterable[str]] = ''

COMMAND_START: Iterable[Union[str, Pattern]] = {'/', '!', '／', '！'}
COMMAND_SEP: Iterable[Union[str, Pattern]] = {'/', '.'}

DEFAULT_COMMAND_PERMISSION: PermissionPolicy_T = lambda _: True  # EVERYBODY
DEFAULT_NLP_PERMISSION: PermissionPolicy_T = lambda _: True  # EVERYBODY

SESSION_EXPIRE_TIMEOUT: Optional[timedelta] = timedelta(minutes=5)
SESSION_RUN_TIMEOUT: Optional[timedelta] = None
SESSION_RUNNING_EXPRESSION: Expression_T = '您有命令正在执行，请稍后再试'

SHORT_MESSAGE_MAX_LENGTH: int = 50

DEFAULT_VALIDATION_FAILURE_EXPRESSION: Expression_T = '您的输入不符合要求，请重新输入'
MAX_VALIDATION_FAILURES: int = 3
TOO_MANY_VALIDATION_FAILURES_EXPRESSION: Expression_T = \
    '您输入错误太多次啦，如需重试，请重新触发本功能'

SESSION_CANCEL_EXPRESSION: Expression_T = '好的'

APSCHEDULER_CONFIG: Dict[str, Any] = {'apscheduler.timezone': 'Asia/Shanghai'}


__all__ = [
    'API_ROOT',
    'ACCESS_TOKEN',
    'SECRET',
    'HOST',
    'PORT',
    'DEBUG',
    'SUPERUSERS',
    'NICKNAME',
    'COMMAND_START',
    'COMMAND_SEP',
    'DEFAULT_COMMAND_PERMISSION',
    'DEFAULT_NLP_PERMISSION',
    'SESSION_EXPIRE_TIMEOUT',
    'SESSION_RUN_TIMEOUT',
    'SESSION_RUNNING_EXPRESSION',
    'SHORT_MESSAGE_MAX_LENGTH',
    'DEFAULT_VALIDATION_FAILURE_EXPRESSION',
    'MAX_VALIDATION_FAILURES',
    'TOO_MANY_VALIDATION_FAILURES_EXPRESSION',
    'SESSION_CANCEL_EXPRESSION',
    'APSCHEDULER_CONFIG',
]
