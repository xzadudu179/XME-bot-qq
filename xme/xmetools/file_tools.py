from nonebot import log
import os

def delete_files_in_folder(folder_path):
    """删除文件夹内的所有文件

    Args:
        folder_path (str): 文件夹路径
    """
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path):
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