"""水鱼成绩记录（Import-Token 拉取）→ b50 卡片数据（本地计算 best50）。

水鱼官方的 b50 定义：新版本单曲 rating 最高的 15 张 + 旧版本单曲 rating 最高的 35 张。
新旧曲用曲目表 basic_info.is_new 判定（"歌曲是否为当前版本的新歌"），ra 取自记录本身。
宴谱（song_id >= UTAGE_SONG_ID_BASE）有成绩但不参与定数，直接排除。
本模块为纯逻辑：依赖全部由参数传入，可脱离 bot 单独测试。
"""

from nonebot.log import logger

from .constants import UTAGE_SONG_ID_BASE
from .render import B50CardData, B50SongScore, dx_star_count

# 难度名：水鱼成绩记录与曲目表都不含难度名，按 level_index 固定映射
LEVEL_LABELS = ["Basic", "Advanced", "Expert", "Master", "Re:Master"]
# b50 组成：新曲取前 NEW_SONG_COUNT 张、旧曲取前 OLD_SONG_COUNT 张
NEW_SONG_COUNT = 15
OLD_SONG_COUNT = 35


def _to_score(record: dict, music: dict | None) -> B50SongScore:
    """把一条成绩记录（联表曲目表）转成 B50SongScore。"""
    song_id = int(record.get("song_id", 0))
    level_index = int(record.get("level_index", 0))
    dx_score = int(record.get("dxScore") or 0)

    # 曲目表提供等级/定数/物量；缺失时留空，不影响达成率等记录自带字段
    level = ""
    ds = 0.0
    max_dx = 0
    if music:
        levels = music.get("level") or []
        ds_list = music.get("ds") or []
        if 0 <= level_index < len(levels):
            level = str(levels[level_index])
        if 0 <= level_index < len(ds_list):
            ds = float(ds_list[level_index])
        charts = music.get("charts") or []
        if 0 <= level_index < len(charts):
            notes = (charts[level_index] or {}).get("notes")
            if isinstance(notes, list) and notes:
                max_dx = sum(n for n in notes if isinstance(n, (int, float))) * 3

    return B50SongScore(
        song_id=song_id,
        title=str(record.get("title") or (music or {}).get("title") or f"Unknown-{song_id}"),
        type=str(record.get("type", "")).lower(),
        level=level,
        level_index=level_index,
        level_label=LEVEL_LABELS[level_index] if 0 <= level_index < len(LEVEL_LABELS) else "",
        ds=ds,
        achievements=float(record.get("achievements") or 0.0),
        ra=int(record.get("ra") or 0),
        rate=str(record.get("rate", "")),
        dx_score=dx_score,
        max_dx_score=max_dx,
        stars=dx_star_count(dx_score, max_dx) if max_dx else None,
        fc=str(record.get("fc") or ""),
        fs=str(record.get("fs") or ""),
    )


def b50_from_records(payload: dict, music_list: list[dict]) -> B50CardData:
    """把 /player/records 的响应组装成 B50CardData（纯函数）。

    Args:
        payload (dict): 水鱼 /player/records 原始响应（含 records）
        music_list (list[dict]): 水鱼曲目表，用于判定新旧曲与补齐等级/定数/物量

    Returns:
        B50CardData: 可直接交给皮肤渲染的数据（rating 由 b50 的 ra 之和算出）

    Raises:
        ValueError: 曲目表为空（无法判定新旧曲，宁可不给结果也不给错的分组）
    """
    if not music_list:
        raise ValueError("缺少曲目表，无法判定新旧曲分组")
    music_map = {str(m.get("id")): m for m in music_list}

    new_pool: list[B50SongScore] = []
    old_pool: list[B50SongScore] = []
    missing_ra = 0
    for record in payload.get("records") or []:
        music = music_map.get(str(record.get("song_id")))
        score = _to_score(record, music)
        # 宴谱成绩存在但不参与定数，不能进 b50
        if score.song_id >= UTAGE_SONG_ID_BASE:
            continue
        if not score.ra:
            missing_ra += 1
        is_new = bool((music or {}).get("basic_info", {}).get("is_new"))
        (new_pool if is_new else old_pool).append(score)
    if missing_ra:
        logger.warning(f"有 {missing_ra} 条成绩记录缺少 ra 字段，排序结果可能不准")

    new_pool.sort(key=lambda s: (s.ra, s.achievements), reverse=True)
    old_pool.sort(key=lambda s: (s.ra, s.achievements), reverse=True)
    dx = new_pool[:NEW_SONG_COUNT]
    sd = old_pool[:OLD_SONG_COUNT]

    username = payload.get("username") or payload.get("nickname") or "我"
    return B50CardData(
        username=str(username),
        rating=sum(s.ra for s in dx) + sum(s.ra for s in sd),
        nickname=None,
        plate=None,
        dx=dx,
        sd=sd,
    )
