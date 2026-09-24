"""mai b50 子命令：解析查分目标 → 查询水鱼 → 组装资源 → 渲染皮肤 → 出图回复。"""

import hashlib
import pathlib
import re

from character import get_message
from nonebot import CommandSession
from nonebot.log import logger
from xme.plugins.commands.maimai import __plugin_name__
from xme.plugins.commands.xme_user.classes.user import (
    User,
    detect_limit,
    limit_count_tick,
    try_load,
)
from xme.xmetools.imgtools import get_html_image_async, get_qq_avatar
from xme.xmetools.msgtools import image_msg
from xme.xmetools.timetools import TimeUnit

from . import api, binding, constants, records, render
from .covers import (
    BADGES,
    COVERS,
    avatar_uri,
    background_uri,
    chart_icon_uri,
    official_ui_assets,
    pic_uri,
    rating_frame_uri,
    star_icons,
    static_asset_uri,
)

cmd_name = constants.CMD_B50
alias = constants.B50_ALIAS
usage = {
    "name": cmd_name,
    "desc": get_message("plugins", __plugin_name__, cmd_name, 'desc'),
    "introduction": get_message("plugins", __plugin_name__, cmd_name, 'introduction'),
    "usage": '<用户名 | @某人> [-s 皮肤名]',
    "permissions": [],
    "alias": alias,
}

# MaimaiAPIError.reason -> 文案键
_ERROR_KEYS = {
    api.REASON_PRIVACY: 'privacy_error',
    api.REASON_NOT_FOUND: 'not_found',
    api.REASON_INVALID_TOKEN: 'token_invalid',
    api.REASON_NETWORK: 'api_error',
}

_SKIN_PATTERN = re.compile(r'(?:^|\s)(?:-s|--skin)\s+(\S+)')


def _split_skin(arg: str) -> tuple[str | None, str]:
    """从参数中拆出 -s/--skin 指定的皮肤名与剩余目标参数。"""
    match = _SKIN_PATTERN.search(arg)
    if not match:
        return None, arg
    rest = (arg[:match.start()] + " " + arg[match.end():]).strip()
    return match.group(1), rest


def _resolve_target(session: CommandSession, user: User, arg: str) -> tuple[str, str, int | None] | None:
    """解析查分目标，Token 优先（Token 只能读到它对应账号的成绩，故可用于代查）。

    优先级：@提及者（其 Token，回退其用户名）→ 指定用户名（公开接口）→
    自己（自己的 Token，回退自己的用户名）。均无绑定时返回 None，由调用方提示绑定。

    Returns:
        tuple[str, str, int | None] | None: (查询方式, Token或用户名, 用于头像的 QQ)；
        查询方式为 "token"（本地算 b50）或 "username"（走公开接口）。
    """
    at_id = get_user_id_from_arg(arg)
    if at_id is not None:
        at_binding = binding.get_binding(try_load(at_id))
        if at_binding[binding.TOKEN_KEY]:
            return "token", at_binding[binding.TOKEN_KEY], at_id
        if at_binding[binding.USERNAME_KEY]:
            return "username", at_binding[binding.USERNAME_KEY], at_id
        return None
    if arg:
        return "username", arg, None
    own = binding.get_binding(user)
    if own[binding.TOKEN_KEY]:
        return "token", own[binding.TOKEN_KEY], session.event.user_id
    if own[binding.USERNAME_KEY]:
        return "username", own[binding.USERNAME_KEY], session.event.user_id
    return None


def _error_text(ex: api.MaimaiAPIError) -> str:
    """按 API 错误类别取对应的回复文案。"""
    key = _ERROR_KEYS.get(ex.reason, 'api_error')
    return get_message("plugins", __plugin_name__, key, ex=ex.message)


def _prune_render_cache() -> None:
    """渲染缓存超过上限时删除最旧的图片。"""
    cache_dir = pathlib.Path(constants.RENDER_CACHE_DIR)
    files = sorted(cache_dir.glob("b50_*.png"), key=lambda p: p.stat().st_mtime)
    for p in files[:max(0, len(files) - constants.RENDER_CACHE_MAX)]:
        p.unlink(missing_ok=True)


async def _build_card_message(session: CommandSession, data, skin: str, known_qq: int | None) -> str:
    """补齐资源（曲绘/徽章/框图/UI 小件）并渲染出图，返回最终消息（不限频、不落库）。"""
    # 渲染前补齐曲绘/徽章/框图：本地缓存优先，缺失才下载（受限并发），失败回退远程 URL
    song_ids = [s.song_id for s in data.dx + data.sd]
    data.covers = await COVERS.get_uris(song_ids)
    badge_uris = await BADGES.get_uris(constants.BADGE_NAMES)
    # 徽章按水鱼缩写做 key，皮肤直接 badges.get(score.fc/fs) 即可
    data.badges = {
        "fc": badge_uris["fc"],
        "fcp": badge_uris["fcp"],
        "ap": badge_uris["ap"],
        "app": badge_uris["app"],
        "fs": badge_uris["fs"],
        "fsp": badge_uris["fsp"],
        "fdx": badge_uris["fsd"],
        "fdxp": badge_uris["fsdp"],
        "sync": badge_uris["sync"],
    }
    data.rating_frame = rating_frame_uri(data.rating) or ""
    data.background_uri = background_uri() or ""
    data.star_icons = star_icons()
    data.chart_icons = {kind: uri for kind in ("dx", "sd") if (uri := chart_icon_uri(kind))}
    rates = {s.rate for s in data.dx + data.sd}
    combos = {s.fc for s in data.dx + data.sd}
    syncs = {s.fs for s in data.dx + data.sd}
    star_counts = {s.stars for s in data.dx + data.sd if s.stars}
    data.ui = official_ui_assets(rates, combos, syncs, star_counts)
    data.pic = pic_uri
    # deon 三件套：姓名牌背景 / 默认头像（无 QQ 头像时）/ deon logo
    data.ui.update({
        "deon_bg": static_asset_uri("img/maimai-pics/deon-bg.webp"),
        "deon_avatar": static_asset_uri("img/maimai-pics/deon_avatar.jpg"),
        "deon_logo": static_asset_uri("img/deon-logo.png"),
    })
    if known_qq:
        try:
            data.avatar_uri = avatar_uri(await get_qq_avatar(known_qq))
        except Exception as ex:
            logger.warning(f"拉取 QQ 头像失败: {ex}")
    skin_name = skin or constants.DEFAULT_SKIN
    skin_tip = ""
    if skin_name not in render.SKINS.names():
        skin_tip = get_message(
            "plugins", __plugin_name__, 'unknown_skin',
            skin=skin_name, skins=", ".join(render.SKINS.names()),
        )
        skin_name = constants.DEFAULT_SKIN
    try:
        card_html = render.render_b50_html(data, skin_name)
        if constants.DEBUG_SAVE_HTML:
            pathlib.Path(constants.DEBUG_HTML_PATH).write_text(card_html, encoding="utf-8")
        # 渲染缓存：HTML 指纹相同直接复用上次出图（含头像/背景等资源状态）
        digest = hashlib.sha1(card_html.encode("utf-8")).hexdigest()
        cache_path = pathlib.Path(constants.RENDER_CACHE_DIR) / f"b50_{digest}.png"
        if cache_path.is_file():
            image = await image_msg(str(cache_path))
        else:
            png = await get_html_image_async(card_html)
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            png.save(cache_path)
            image = await image_msg(str(cache_path))
            _prune_render_cache()
        message = get_message(
            "plugins", __plugin_name__, 'b50_result',
            html_image=image, name=data.username, rating=data.rating,
        )
    except Exception as ex:
        logger.warning(f"b50 查分卡渲染失败: {ex}")
        message = get_message(
            "plugins", __plugin_name__, 'b50_fallback',
            name=data.username, rating=data.rating,
            summary=render.b50_text_summary(data),
        )
    if skin_tip:
        message = skin_tip + "\n" + message
    return message


async def _query_by_token(session: CommandSession, token: str, skin: str, known_qq: int | None = None) -> str:
    """用成绩导入 Token 拉全量成绩并本地算 b50（Token 只能读到对应账号，可安全代查）。"""
    try:
        payload = await api.fetch_records_payload(token)
    except api.MaimaiAPIError as ex:
        return _error_text(ex)
    # 曲目表用于判定新旧曲分组与补齐等级/定数，缺失时无法给出正确 b50
    try:
        music = await api.fetch_music_data()
    except api.MaimaiAPIError as ex:
        logger.warning(f"曲目表拉取失败，无法本地计算 b50: {ex}")
        return get_message("plugins", __plugin_name__, 'api_error', ex=ex.message)
    data = records.b50_from_records(payload, music)
    if not data.dx and not data.sd:
        return get_message("plugins", __plugin_name__, 'no_scores', username=data.username)
    return await _build_card_message(session, data, skin, known_qq)


async def handle(session: CommandSession, user: User, arg: str) -> str:
    """处理 b50 查分：有 Token 时（自己的或 @ 提及者的）本地算 b50，否则走公开接口。"""
    skin, target_arg = _split_skin(arg)
    target = target_arg.strip()
    if detect_limit(
        user=user,
        name=constants.B50_LIMIT_NAME,
        interval=constants.B50_LIMIT_INTERVAL,
        count_limit=constants.B50_LIMIT_COUNT,
        unit=TimeUnit.MINUTE,
    ):
        return get_message("plugins", __plugin_name__, 'limited')

    resolved = _resolve_target(session, user, target)
    if resolved is None:
        # @ 他人时对方没绑，与自己没绑要分开提示
        key = 'at_not_bound' if get_user_id_from_arg(target) is not None else 'not_bound'
        return get_message("plugins", __plugin_name__, key)
    target_type, target_value, known_qq = resolved

    # 已绑 Token（自己的或 @ 提及者的）：拉全量成绩本地算 best50
    if target_type == "token":
        message = await _query_by_token(session, target_value, skin, known_qq)
        limit_count_tick(user, constants.B50_LIMIT_NAME)
        user.save()
        return message

    # 指定用户名 / 老数据里只绑了用户名：走水鱼公开接口
    try:
        raw = await api.query_player_b50(username=target_value)
    except api.MaimaiAPIError as ex:
        return _error_text(ex)
    # 曲目表用于联表物量计算 DX 星级；失败仅影响星星展示
    try:
        music = await api.fetch_music_data()
    except api.MaimaiAPIError as ex:
        logger.warning(f"曲目表拉取失败，跳过 DX 星级计算: {ex}")
        music = None
    data = render.build_b50_card_data(raw, music)
    if not data.dx and not data.sd:
        return get_message("plugins", __plugin_name__, 'no_scores', username=data.username)
    message = await _build_card_message(session, data, skin, known_qq)
    limit_count_tick(user, constants.B50_LIMIT_NAME)
    user.save()
    return message
