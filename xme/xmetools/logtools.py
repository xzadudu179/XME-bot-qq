"""日志控制台颜色格式化工具

提供 ColoredFormatter，在不改变日志字段与文本内容的前提下，给控制台
输出的日期、等级、logger 名、消息正文按字段上色；文件日志继续使用普通
Formatter 即可保持纯文本。
"""
import logging
import re

from xme.xmetools import colortools as c

# 控制台各字段颜色（hex），调整配色只需改这里
TIME_COLOR = "#8a97a8"
NAME_COLOR = "#66c7ff"
MESSAGE_COLOR = "#e8eef4"
LEVEL_COLORS = {
    "DEBUG": "#9aa7b8",
    "INFO": "#a8ffc5",
    "WARNING": "#ffd666",
    "ERROR": "#ff7a7a",
    "CRITICAL": "#ff5555",
}

# aiocqhttp 事件行（"received event: <event>"）里各事件的紧凑显示颜色
EVENT_COLORS = {
    "message": "#a8ffc5",
    "message_sent": "#66c7ff",
    "notice": "#ffd666",
    "request": "#ff7a7a",
    "meta": "#9aa7b8",
}
EVENT_LINE_RE = re.compile(r"^received event: (.+)$")


def _colored(text: str, hex_color: str) -> str:
    """给文本上十六进制前景色"""
    return c.rgb_text(text, f=c.hex_to_rgb(hex_color))


class ColoredFormatter(logging.Formatter):
    """在传入 fmt 基础上按字段上色的 Formatter，渲染结果去色后与原格式一致

    等级颜色查 LEVEL_COLORS，未登记等级用 MESSAGE_COLOR；消息内已含
    ANSI 转义（自带颜色）时不再包裹，避免嵌套转义错乱。渲染中对 record
    字段的修改用 try/finally 恢复，不影响共享同一 record 的文件 handler。
    """

    def formatTime(self, record, datefmt=None):
        return _colored(super().formatTime(record, datefmt), TIME_COLOR)

    def format(self, record):
        original_levelname, original_name = record.levelname, record.name
        record.levelname = _colored(
            record.levelname, LEVEL_COLORS.get(record.levelname, MESSAGE_COLOR))
        record.name = _colored(record.name, NAME_COLOR)
        try:
            return super().format(record)
        finally:
            record.levelname, record.name = original_levelname, original_name

    def formatMessage(self, record):
        message = record.message
        if "\x1b" in message:
            return super().formatMessage(record)
        record.message = _colored(message, MESSAGE_COLOR)
        result = super().formatMessage(record)
        record.message = message
        return result


class MetaEventDemoteFilter(logging.Filter):
    """把 aiocqhttp 的心跳/生命周期事件行降级为 DEBUG

    必须挂在 logger 上而不是 handler 上：logger 级 filter 在各 handler
    的级别判断之前生效，控制台（INFO）不再显示心跳，文件 handler（DEBUG）
    仍完整记录。
    """

    def filter(self, record):
        if record.levelno <= logging.INFO and \
                "received event: meta event" in record.getMessage():
            record.levelno = logging.DEBUG
            record.levelname = "DEBUG"
        return True


class EventLogFormatter(ColoredFormatter):
    """库日志控制台 Formatter：aiocqhttp 事件行渲染为紧凑摘要，其余按原格式上色

    事件行 `[2026-09-21 16:05:21] INFO in __init__: received event: message`
    渲染为 `16:05:21 ↳ message`，事件名按 EVENT_COLORS 区分颜色。
    """

    def format(self, record):
        match = EVENT_LINE_RE.match(record.getMessage())
        if match:
            event = match.group(1)
            color = EVENT_COLORS.get(event.split()[0], MESSAGE_COLOR)
            # 绕过父类已带色的 formatTime，用短时间格式重新上色
            plain_time = logging.Formatter.formatTime(self, record, "%H:%M:%S")
            time_part = _colored(plain_time, TIME_COLOR)
            return f"{time_part} {_colored('↳', color)} {_colored(event, color)}"
        return super().format(record)
