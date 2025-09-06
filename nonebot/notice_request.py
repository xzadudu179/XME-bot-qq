from typing import List, Optional, Union

from aiocqhttp import Event as CQEvent
from aiocqhttp.bus import EventBus

from . import NoneBot
from .log import logger
from .exceptions import CQHttpError
from .session import BaseSession

from .typing import NoticeHandler_T, RequestHandler_T


class EventHandler:
    """INTERNAL API"""
    __slots__ = ('events', 'func')

    def __init__(self, events: List[str], func: Union[NoticeHandler_T, RequestHandler_T]):
        self.events = events
        self.func = func


class EventManager:
    """INTERNAL API"""
    bus = EventBus()

    @classmethod
    def add_event_handler(cls, handler: EventHandler) -> None:
        for event in handler.events:
            cls.bus.subscribe(event, handler.func)

    @classmethod
    def remove_event_handler(cls, handler: EventHandler) -> None:
        for event in handler.events:
            cls.bus.unsubscribe(event, handler.func)

    @classmethod
    def switch_event_handler_global(cls,
                                    handler: EventHandler,
                                    state: Optional[bool] = None) -> None:
        for event in handler.events:
            if handler.func in cls.bus._subscribers[event] and not state:
                cls.bus.unsubscribe(event, handler.func)
            elif handler.func not in cls.bus._subscribers[
                    event] and state is not False:
                cls.bus.subscribe(event, handler.func)


class NoticeSession(BaseSession):
    __slots__ = ()

    def __init__(self, bot: NoneBot, event: CQEvent):
        super().__init__(bot, event)


class RequestSession(BaseSession):
    __slots__ = ()

    def __init__(self, bot: NoneBot, event: CQEvent):
        super().__init__(bot, event)

    async def approve(self, remark: str = '') -> None:
        """
        Approve the request.

        :param remark: remark of friend (only works in friend request)
        """
        try:
            await self.bot.call_action(action='.handle_quick_operation_async',
                                       self_id=self.event.self_id,
                                       context=self.event,
                                       operation={
                                           'approve': True,
                                           'remark': remark
                                       })
        except CQHttpError:
            pass

    async def reject(self, reason: str = '') -> None:
        """
        Reject the request.

        :param reason: reason to reject (only works in group request)
        """
        try:
            await self.bot.call_action(action='.handle_quick_operation_async',
                                       self_id=self.event.self_id,
                                       context=self.event,
                                       operation={
                                           'approve': False,
                                           'reason': reason
                                       })
        except CQHttpError:
            pass


async def handle_notice_or_request(bot: NoneBot, event: CQEvent) -> None:
    """INTERNAL API"""
    if event.type == 'notice':
        _log_notice(event)
        session = NoticeSession(bot, event)
    else:  # must be 'request'
        _log_request(event)
        session = RequestSession(bot, event)

    ev_name = event.name
    logger.debug(f'Emitting event: {ev_name}')
    try:
        await EventManager.bus.emit(ev_name, session)
    except Exception as e:
        logger.error(f'An exception occurred while handling event {ev_name}:')
        logger.exception(e)


def _log_notice(event: CQEvent) -> None:
    logger.info(f'Notice: {event}')


def _log_request(event: CQEvent) -> None:
    logger.info(f'Request: {event}')


__all__ = [
    'NoticeSession',
    'RequestSession',
]
