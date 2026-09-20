"""兼容 OneBot 11 实现自行扩展的 ``message_sent``（上报自身消息）事件。

NapCat / SnowLuma / LLOneBot 开启 ``reportSelfMessage`` 之后，自身消息的
``post_type`` 是 ``message_sent``，类型字段**沿用** ``message_type``（这些实现都不
提供 ``message_sent_type``，目标方在 ``target_id`` 里）。而 aiocqhttp 是按
``f'{post_type}_type'`` 去取类型字段的（``aiocqhttp/event.py:41``），于是会
``KeyError``，紧接着 ``aiocqhttp/__init__.py:590`` 的 ``if not ev: return`` 把事件
**静默丢弃**。即便解析成功，事件名 ``message_sent.*`` 也只会在总线上逐级截断冒泡
（``aiocqhttp/bus.py:50-66``），永远命中不了只注册了 ``message`` 的 ``on_message``。

所以这里做三件事：

1. 给 ``Event.detail_type`` 加兜底，让 ``message_sent`` 能解析出来；
2. 给 ``Event.from_payload`` 包一层：被丢弃的事件补一条日志（否则出问题时完全无迹可循），
   并把解析成功的 ``message_sent`` 就地归一化成普通 ``message`` 事件；
3. ``normalize_message_sent()``：具体的改写逻辑。

归一化放在解析阶段是刻意的——事件名会随 ``post_type`` 直接变成 ``message.*``，于是既有的
``on_message`` / ``handle_message`` 管线原样工作，总线上不需要任何额外订阅者，也就不存在
"别的订阅者读到未改写事件"的顺序问题。

历史背景：以前的实现（Lagrange 等）自身消息是走服务端回显、以普通 ``message`` 事件
到达的，所以 nonebot1 天然能收到；``preprocessor`` 里那一批 ``event.user_id ==
event.self_id`` 的自身消息判定，以及 ``message_chain.py`` 的接龙打断逻辑，都是为那种
形态写的，归一化后可以直接复用。
"""

from typing import Any, Dict, Optional

from aiocqhttp import Event

from .log import logger

SELF_MESSAGE_POST_TYPE = 'message_sent'

_installed = False
_warned_post_types = set()


def _detail_type(self: Event) -> str:
    key = f'{self.type}_type'
    if key in self:
        return self[key]
    # message_sent 是各实现自行扩展的事件，类型字段沿用 message_type，
    # 只有两者都取不到时才维持上游的 KeyError 行为（让畸形事件照旧被丢弃）
    if self.type == SELF_MESSAGE_POST_TYPE and 'message_type' in self:
        return self['message_type']
    raise KeyError(key)


_original_from_payload = Event.from_payload


def _from_payload(payload: Dict[str, Any]) -> Optional[Event]:
    event = _original_from_payload(payload)
    if event is None:
        if isinstance(payload, dict):
            post_type = payload.get('post_type')
            if post_type not in _warned_post_types:
                # 每个未知的 post_type 只提醒一次，避免刷屏；带上原始内容方便对字段
                _warned_post_types.add(post_type)
                logger.warning(f'丢弃了无法解析的事件（post_type={post_type!r}，缺少 '
                               f'"{post_type}_type" 字段）：{str(payload)[:500]}')
        return None
    if event.type == SELF_MESSAGE_POST_TYPE:
        # 就在解析阶段改写，事件名随之为 message.*，总线上不需要任何特殊订阅者
        normalize_message_sent(event)
    return event


def install_onebot_compat() -> None:
    """给 aiocqhttp 的事件解析打补丁，必须在收到事件之前调用。"""
    global _installed
    if _installed:
        return
    _installed = True
    Event.detail_type = property(_detail_type)
    Event.from_payload = staticmethod(_from_payload)


def normalize_message_sent(event: Event) -> bool:
    """把 ``message_sent`` 事件原地改写成普通 ``message`` 事件。

    ``message_sent`` 的发送者恒为 bot 自己，因此 ``user_id`` 固定为 ``self_id``，
    与原 Lagrange 回显的形态一致，既有 preprocessor 的自身消息判定可直接复用。
    ``user_id == self_id`` 还意味着这条消息的会话上下文是 ``/group/{群}/user/{bot}``，
    与任何真实用户的会话互不干扰。

    原始字段（``post_type`` 除外，还有 ``target_id``、``sender`` 等）一律保留，便于排查。

    :param event: 收到的事件
    :return: 是否成功改写（缺少 ``message_type`` 时无法判定会话，返回 False）
    """
    raw = dict(event)
    message_type = raw.get('message_type') or raw.get('message_sent_type')
    if message_type is None:
        logger.warning(f'message_sent 事件缺少 message_type，无法处理：{str(raw)[:500]}')
        return False

    event['post_type'] = 'message'
    event['message_type'] = message_type
    event['user_id'] = raw.get('self_id')
    if message_type == 'group':
        # 各实现里群号可能在 group_id，也可能只在 target_id
        event['group_id'] = raw.get('group_id') or raw.get('target_id')
        event.setdefault('sub_type', 'normal')
    else:
        event.setdefault('sub_type', 'friend')
    return True


__all__ = [
    'SELF_MESSAGE_POST_TYPE',
    'install_onebot_compat',
    'normalize_message_sent',
]
