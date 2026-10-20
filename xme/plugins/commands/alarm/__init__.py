"""快捷定时：定时句式预处理 + /alarm 指令，共用 timers 登记与 timetools 时间解析。

时间支持相对时长（5分/3天）与自然语句时间（明天9点/周三8点）两种格式；群聊里要叫
bot 的名字（@ 或名字开头）才会触发句式，私聊直接说「5分钟后提醒我…」即可；
到点后私聊提醒设置者，可用「/alm list」查看、「/alm del 编号」删除、「/alm del ALL」清空、
「/alm pause 编号」暂停或继续循环计时器。
"""
from character import get_message
from xme.xmetools.doctools import CommandDoc

from .constants import MAX_ACTIVE_PER_USER

__plugin_name__ = 'alarm'
alias = ['定时', '闹钟', '提醒', 'alm']
__plugin_usage__ = CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    introduction=get_message("plugins", __plugin_name__, 'introduction', max_active=MAX_ACTIVE_PER_USER),
    usage='<时间/操作> <名字>（list / del 编号 / pause 编号）',
    permissions=["无"],
    alias=alias
)

from . import commands  # noqa: E402,F401
from . import schedule  # noqa: E402,F401
from .preprocessor import * # noqa: E402,F401
