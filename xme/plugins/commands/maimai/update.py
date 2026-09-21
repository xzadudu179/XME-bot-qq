"""mai update 子命令：用机台二维码把成绩同步到水鱼（限私聊）。

前置是已绑定的水鱼 Import-Token；同步本身由外部工具 mai-arcade 完成，
本模块只做「私聊校验 → 限频 → 提取二维码 → 调工具 → 映射文案」。
"""

import asyncio
import re

from character import get_message
from nonebot import CommandSession, SenderRoles
from nonebot.log import logger
from xme.plugins.commands.maimai import __plugin_name__
from xme.plugins.commands.xme_user.classes.user import (
    User,
    detect_limit,
    limit_count_tick,
)
from xme.xmetools.imgtools import detect_qrcode, get_url_image
from xme.xmetools.msgtools import send_session_msg
from xme.xmetools.texttools import get_images_from_message
from xme.xmetools.timetools import TimeUnit

from . import arcade, binding, constants

cmd_name = constants.CMD_UPDATE
alias = constants.UPDATE_ALIAS
usage = {
    "name": cmd_name,
    "desc": get_message("plugins", __plugin_name__, cmd_name, 'desc'),
    "introduction": get_message("plugins", __plugin_name__, cmd_name, 'introduction'),
    "usage": '(机台二维码)',
    "permissions": [],
    "alias": alias,
}

_SGID_IN_TEXT = re.compile(r'SGWCMAID[0-9A-Fa-f]{16,}', re.IGNORECASE)
_LINK_IN_TEXT = re.compile(r'wahlap\.net/qrcode/(?:req|img)/(MAID[^\s?.\]]+)', re.IGNORECASE)


def _extract_from_text(text: str) -> str:
    """从文本里提取二维码：直接给的内容，或公众号链接（补回 SGWC 前缀）。"""
    match = _SGID_IN_TEXT.search(text)
    if match:
        return match.group(0)
    link = _LINK_IN_TEXT.search(text)
    if link:
        return "SGWC" + link.group(1)
    return ""


async def _extract_from_images(session: CommandSession, arg: str) -> str:
    """从消息里的图片识别二维码，取不到返回空串。

    get_images_from_message 给的是协议端 get_image 的返回（dict，含 file/url 字段），
    必须先经 get_url_image 取成 PIL 图片再交给 detect_qrcode（它只接受路径或图片对象）。
    单张图取图/识别失败只跳过这张，不影响整条指令。
    """
    image_objects, _ = await get_images_from_message(session.bot, arg)
    for image in image_objects:
        image_url = image.get("file") if isinstance(image, dict) else image
        if not image_url:
            continue
        try:
            pil_image = await get_url_image(image_url)
        except Exception as ex:
            logger.warning(f"{__plugin_name__} 二维码取图失败：{type(ex).__name__}: {ex}")
            continue
        try:
            # detect_qrcode 是同步的图片解码，放线程以免阻塞事件循环
            found, texts = await asyncio.to_thread(detect_qrcode, pil_image)
        except Exception as ex:
            logger.warning(f"{__plugin_name__} 二维码识别失败：{type(ex).__name__}: {ex}")
            continue
        if not found:
            continue
        for text in texts:
            sgid = _extract_from_text(text)
            if sgid:
                return sgid
    return ""


async def handle(session: CommandSession, user: User, arg: str) -> str:
    """处理扫码同步请求，返回拼好的回复文案。"""
    sender = await SenderRoles.create(session.bot, session.event)
    if not sender.is_privatechat:
        return get_message("plugins", __plugin_name__, 'private_only')

    token = binding.get_binding(user)[binding.TOKEN_KEY]
    if not token:
        return get_message("plugins", __plugin_name__, 'update_no_token')

    sgid = _extract_from_text(arg) or await _extract_from_images(session, arg)
    if not sgid:
        return get_message("plugins", __plugin_name__, 'update_usage')

    if detect_limit(
        user=user,
        name=constants.SYNC_LIMIT_NAME,
        interval=constants.SYNC_LIMIT_INTERVAL,
        count_limit=constants.SYNC_LIMIT_COUNT,
        unit=TimeUnit.MINUTE,
    ):
        return get_message("plugins", __plugin_name__, 'sync_limited')
    # 发起外部调用即计数，避免拿无效二维码反复刷机台接口
    limit_count_tick(user, constants.SYNC_LIMIT_NAME)
    user.save()

    # 同步要拉全曲库加全量成绩，先应一声免得用户以为没反应
    await send_session_msg(session, get_message("plugins", __plugin_name__, 'update_running'), tips=True)

    result = await arcade.run(constants.ARCADE_SYNC_COMMAND, sgid, token)
    if result.ok and result.exit_code == 0:
        count = result.data.get('scoreCount', 0)
        # utage = result.data.get('utageCount', 0)
        return get_message(
            "plugins", __plugin_name__,
            'update_success',
            count=count,
        )

    key = arcade.failure_key(result)
    logger.warning(
        f"mai update 同步失败：exit={result.exit_code} code={result.code} "
        f"message={str(result.error.get('message', ''))[:200]}"
    )
    return get_message("plugins", __plugin_name__, key)
