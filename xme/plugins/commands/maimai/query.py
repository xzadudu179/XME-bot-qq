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
from xme.xmetools.texttools import get_at_id
from xme.xmetools.timetools import TimeUnit

from . import api, binding, constants, render
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
    "usage": '[用户名 | @某人] [-s 皮肤名]',
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
    """解析查分目标：参数用户名 → @提及者（需已绑定）→ 自己（需已绑定）。

    未绑定时不回退 QQ 查询，返回 None 由调用方提醒绑定。

    Returns:
        tuple[str, str, int | None] | None: ("username", 用户名, 已知 QQ 或 None)；
        自己/@ 目标未绑定时返回 None。
    """
    if arg.startswith("[CQ:at,qq="):
        at_id = get_at_id(arg)
        at_binding = binding.get_binding(try_load(at_id))
        if at_binding[binding.USERNAME_KEY]:
            return "username", at_binding[binding.USERNAME_KEY], at_id
        return None
    if arg:
        return "username", arg, None
    own = binding.get_binding(user)[binding.USERNAME_KEY]
    if own:
        return "username", own, session.event.user_id
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


async def handle(session: CommandSession, user: User, arg: str) -> str:
    """处理 b50 查分，返回拼好的回复消息（可能含图片消息段）。"""
    skin, target_arg = _split_skin(arg)
    resolved = _resolve_target(session, user, target_arg.strip())
    if resolved is None:
        # 自己没有绑定用户名，也不便通过 QQ 号查询
        return get_message("plugins", __plugin_name__, 'not_bound')
    target_type, target, known_qq = resolved
    if detect_limit(
        user=user,
        name=constants.B50_LIMIT_NAME,
        interval=constants.B50_LIMIT_INTERVAL,
        count_limit=constants.B50_LIMIT_COUNT,
        unit=TimeUnit.MINUTE,
    ):
        return get_message("plugins", __plugin_name__, 'limited')
    try:
        if target_type == "username":
            raw = await api.query_player_b50(username=target)
        else:
            raw = await api.query_player_b50(qq=target)
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
        # 该玩家还没有任何成绩记录，无需渲染卡片
        return get_message("plugins", __plugin_name__, 'no_scores', username=data.username)
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
    limit_count_tick(user, constants.B50_LIMIT_NAME)
    user.save()
    if skin_tip:
        message = skin_tip + "\n" + message
    return message
