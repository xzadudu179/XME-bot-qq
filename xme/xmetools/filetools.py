from nonebot import log
import os
import base64
from pathlib import Path
from datetime import datetime
import shutil

def cleanup_old_backups(
        backup_root: Path,
        keep: int = 100
    ):
    if not backup_root.exists():
        return
    backups = sorted(
        (p for p in backup_root.iterdir() if p.is_dir()),
        key=lambda p: p.name
    )
    excess = len(backups) - keep
    if excess <= 0:
        return
    for old in backups[:excess]:
        shutil.rmtree(old)

def backup_data_dir(
        data_dir: Path = Path("data"),
        backup_root: Path = Path(".backup"),
        max_backups: int = 100
    ) -> Path:
    """
    将 data 目录备份到 .backup/datas-YYYY-MM-DD_HH-MM-SS

    返回：备份目录路径
    """
    data_dir.mkdir(parents=True, exist_ok=True)
    backup_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_dir = backup_root / ("datas-" + timestamp)
    shutil.copytree(data_dir, backup_dir)
    cleanup_old_backups(backup_root, keep=max_backups)
    return backup_dir


def b64_encode_file(file_path):
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def delete_files_in_folder(folder_path):
    """删除文件夹内的所有文件

    Args:
        folder_path (str): 文件夹路径
    """
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if not os.path.isfile(file_path):
            continue
        os.remove(file_path)
        log.logger.info(f"删除文件: {file_path}")

def has_file(path) -> bool:
    """判断是否有文件存在

    Args:
        path (str): 路径

    Returns:
        bool: 是否存在
    """
    if os.path.exists(path) and os.path.isfile(path):
        return True
    return False

def clear_temp(folder="./data/images/temp"):
    """
    清除缓存"""
    log.logger.info("正在删除缓存文件")
    files = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
    for f in files:
        log.logger.info(f"正在删除 \"{f}\"...")
        os.remove(folder + '/' + f)

def clear_temps(folders=["./data/images/temp", "./data/temp"]):
    for f in folders:
        clear_temp(f)