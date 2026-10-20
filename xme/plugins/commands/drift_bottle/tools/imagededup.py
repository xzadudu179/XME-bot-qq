"""漂流瓶图片查重：已存图 pHash 的持久化缓存与距离比较。

每次查重都重新解码全部已存图片（数百张）代价过高，这里把每张已存图的
pHash 缓存在图片目录的侧车文件里，命中时只做整数位比较。缓存条目按
「文件名 -> (哈希, mtime_ns, 大小)」校验，文件被覆盖或删除时自动失效；
侧车文件缺失/损坏时按空缓存重建。
"""
import json
import os
import threading

from nonebot.log import logger

from xme.xmetools.imgtools import get_hash

# 侧车缓存文件名（位于图片目录内）
CACHE_FILENAME = ".phash_cache.json"
# pHash 汉明距离阈值：小于等于该值视为重复
MAX_HASH_DISTANCE = 10
# 未落盘的新条目达到该值时自动写入，避免全量补建时反复重写整个缓存
FLUSH_BATCH = 64


def hash_distance(hash_a: int, hash_b: int) -> int:
    """两个 pHash 整数的汉明距离（与 imagehash 相减的语义一致，越小越相似）"""
    return (hash_a ^ hash_b).bit_count()


def is_safe_image_name(filename) -> bool:
    """图片引用必须是图片目录内的纯文件名（不含路径分隔符），防止拼出目录外路径"""
    return (isinstance(filename, str) and bool(filename) and filename not in (".", "..")
            and filename == os.path.basename(filename)
            and "/" not in filename and "\\" not in filename)


class ImagePhashCache:
    """图片目录的 pHash 侧车缓存（懒加载、线程安全、原子写入）。

    条目结构：文件名 -> [哈希 hex, 文件 mtime_ns, 文件大小]；命中要求
    mtime_ns 与大小都与磁盘一致，否则重新计算。文件不存在或解码失败时
    取值为 None（调用方按「无法比较」处理）。
    """

    def __init__(self, folder: str, cache_filename: str = CACHE_FILENAME) -> None:
        self.folder = folder
        self.cache_path = os.path.join(folder, cache_filename)
        # None 表示尚未读取侧车文件，读取后恒为 dict
        self._entries: dict | None = None
        self._pending = 0
        # 查重经 asyncio.to_thread 调用，可能并发读写
        self._lock = threading.RLock()

    def get(self, filename: str) -> int | None:
        """取图片目录内 filename 的 pHash；未命中则计算并记录待落盘。

        文件不存在或解码失败返回 None。
        """
        if not is_safe_image_name(filename):
            logger.warning(f"图片查重跳过非法文件名：{filename!r}")
            return None
        path = os.path.join(self.folder, filename)
        with self._lock:
            entries = self._load()
            try:
                stat = os.stat(path)
            except OSError:
                # 文件已被删除（如被举报瓶子的图片）：丢弃对应缓存条目
                if entries.pop(filename, None) is not None:
                    self._pending += 1
                return None
            entry = entries.get(filename)
            if entry is not None and entry[1] == stat.st_mtime_ns and entry[2] == stat.st_size:
                try:
                    return int(entry[0], 16)
                except (TypeError, ValueError):
                    logger.warning(f"图片查重缓存条目损坏，将重新计算：{filename!r}")
            image_hash = get_hash(path)
            if image_hash is None:
                return None
            image_hash = str(image_hash)
            entries[filename] = [image_hash, stat.st_mtime_ns, stat.st_size]
            self._pending += 1
            if self._pending >= FLUSH_BATCH:
                self.flush()
            return int(image_hash, 16)

    def flush(self) -> None:
        """把待落盘的新条目原子写入侧车文件；顺带清掉文件已不存在的条目。

        无新条目时不写；写入失败时保留待写状态，下次调用重试。
        """
        with self._lock:
            entries = self._load()
            if self._pending <= 0:
                return
            alive = {name: entry for name, entry in entries.items()
                     if os.path.exists(os.path.join(self.folder, name))}
            tmp_path = self.cache_path + ".tmp"
            try:
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(alive, f, ensure_ascii=False)
                os.replace(tmp_path, self.cache_path)
            except OSError as ex:
                logger.warning(f"图片查重缓存写入失败（下次重试）：{ex}")
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
                return
            self._entries = alive
            self._pending = 0
            logger.info(f"图片查重缓存已更新：{len(alive)} 条")

    def _load(self) -> dict:
        """读取侧车缓存；文件不存在/损坏/条目格式不符时按空缓存处理"""
        if self._entries is not None:
            return self._entries
        entries: dict = {}
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                entries = {str(name): entry for name, entry in raw.items()
                           if isinstance(entry, list) and len(entry) == 3
                           and isinstance(entry[0], str)}
        except FileNotFoundError:
            pass
        except (json.JSONDecodeError, OSError) as ex:
            logger.warning(f"图片查重缓存无法读取，将重建：{ex}")
        self._entries = entries
        return entries
