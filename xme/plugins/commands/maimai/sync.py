"""maimai 资源自动同步：启动延迟补齐 + 每日定时补齐曲绘与徽章缓存。

只下载缺失文件（增量），已有缓存跳过；失败仅记日志，不影响 bot 其他功能。
"""

import asyncio
import datetime
import pathlib
import shutil

import nonebot
from nonebot import scheduler
from nonebot.log import logger

from . import api
from .constants import BADGE_NAMES, RESOURCE_DIR, RESOURCE_PACK_URL, SYNC_ON_STARTUP
from .covers import BADGES, COVERS

STARTUP_SYNC_DELAY = 60  # 启动后延迟秒数，避免和 bot 连接抢资源
RESOURCE_MARKER = ".resource_complete"


async def sync_resource_pack() -> bool:
    """下载并解压 maimaiDX(Hoshino) 官方静态资源包中的 pic 子集。

    完成后写入 RESOURCE_DIR/.resource_complete 标记，已完成的启动直接跳过；
    资源包约 467MB（下载 + 解压耗时数分钟），失败仅记日志。
    """
    resource_dir = pathlib.Path(RESOURCE_DIR)
    if (resource_dir / RESOURCE_MARKER).exists():
        return True
    try:
        import py7zr
    except ImportError:
        logger.warning("maimai 资源包同步需要 py7zr（requirements 已含），请先安装")
        return False
    tmp_archive = pathlib.Path(RESOURCE_DIR) / "pack.7z"
    tmp_archive.parent.mkdir(parents=True, exist_ok=True)
    try:
        proc = await asyncio.create_subprocess_exec(
            "curl", "-sL", "--max-time", "580", RESOURCE_PACK_URL,
            "-o", str(tmp_archive),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        if await proc.wait() != 0:
            raise RuntimeError(f"curl 退出码 {proc.returncode}")
        with py7zr.SevenZipFile(tmp_archive) as z:
            targets = [n for n in z.getnames() if "/mai/pic/" in n]
            z.extract(targets=targets, path=str(tmp_archive.parent / "extract"))
        extracted = tmp_archive.parent / "extract"
        pic_src = next(extracted.rglob("static/mai/pic"))
        pic_dir = resource_dir / "pic"
        if pic_dir.exists():
            shutil.rmtree(pic_dir)
        shutil.copytree(pic_src, pic_dir)
        (resource_dir / RESOURCE_MARKER).write_text("ok", encoding="utf-8")
        logger.info(f"maimai 官方资源包同步完成（{len(targets)} 个文件 → {pic_dir}）")
        return True
    except Exception as ex:
        logger.warning(f"maimai 官方资源包同步失败: {ex}")
        return False
    finally:
        shutil.rmtree(tmp_archive.parent / "extract", ignore_errors=True)
        tmp_archive.unlink(missing_ok=True)


async def sync_resources() -> None:
    """同步官方资源包并补齐徽章/曲绘缓存，失败仅记日志。"""
    try:
        await sync_resource_pack()
        badge_ok, badge_fail = await BADGES.sync_missing(BADGE_NAMES)
        music = await api.fetch_music_data()
        song_ids = [m["id"] for m in music if isinstance(m.get("id"), int)]
        cover_ok, cover_fail = await COVERS.sync_missing(song_ids)
        logger.info(
            f"maimai 资源同步完成：徽章补齐 {badge_ok}（失败 {badge_fail}），"
            f"曲绘补齐 {cover_ok}/{len(song_ids)}（失败 {cover_fail}）"
        )
    except Exception as ex:
        logger.warning(f"maimai 资源同步失败: {ex}")


@scheduler.scheduled_job('cron', hour=4, minute=30)
async def _daily_sync():
    """每日 4:30 增量同步曲绘缓存（新曲目自动补齐）。"""
    await sync_resources()


if SYNC_ON_STARTUP:
    @scheduler.scheduled_job('date', run_date=datetime.datetime.now() + datetime.timedelta(seconds=STARTUP_SYNC_DELAY))
    async def _startup_sync():
        """启动后延迟触发一次全量补齐（首次部署约需数分钟，之后为增量、秒级）。"""
        logger.info("maimai 启动同步：开始补齐曲绘缓存")
        await sync_resources()
