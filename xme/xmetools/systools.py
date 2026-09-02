import psutil as pt
import platform
import time
from .timetools import secs_to_ymdh
import socket
import shutil
import subprocess

# 将字节转换为 MiB
def bytes_to_mib(bytes):
    return bytes / (1024 * 1024)

# 将字节转换为 GiB
def bytes_to_gib(bytes):
    return bytes / (1024 * 1024 * 1024)

def get_bot_address():
    try:
        ip_address = socket.gethostbyname('xzadudu179.top')
        return ip_address
    except socket.gaierror as e:
        return f"(获取失败: {e})"

def get_disks():
    result = subprocess.run(
        [
            "lsblk",
            "-J",
            "-o", "NAME,PATH,SIZE,TYPE,FSTYPE,MOUNTPOINT"
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    import json
    data = json.loads(result.stdout)

    disks = []

    def walk(devices):
        for device in devices:
            # 只处理分区
            if device["type"] == "part":
                mountpoint = device.get("mountpoint")

                if mountpoint:
                    total, used, free = shutil.disk_usage(mountpoint)

                    disks.append({
                        "name": device["name"],
                        "path": device["path"],
                        "size": device["size"],
                        "mountpoint": mountpoint,
                        "total": total,
                        "used": used,
                        "free": free,
                        "usage": used / total,
                    })

            # 递归处理子设备
            if "children" in device:
                walk(device["children"])

    walk(data["blockdevices"])

    return disks


def system_info():
    mem = pt.virtual_memory()
    disks = get_disks()
    disk_msg = ""
    for disk in disks:
        disk_msg += f"  - {disk['name']}: {bytes_to_mib(disk['used']):,.2f} / {bytes_to_mib(disk['total']):,.2f} MiB ({(disk['used'] / disk['total']):.2f}%)\n"
    disk_msg = disk_msg.rstrip("\n")
    content = f"""    === 当前系统状态 ===
- 机器名: {platform.node()}
- 系统: {platform.system()} {platform.version()} {platform.machine()}
- CPU 使用率: {pt.cpu_percent(interval=0.1)}%
- 内存消耗: {bytes_to_mib(mem.used):,.2f} / {bytes_to_mib(mem.total):,.2f} MiB ({(mem.used / mem.total):.2f}%)
- 硬盘使用：
{disk_msg}
- 当前开机时长: {secs_to_ymdh(time.time() - pt.boot_time())}
"""
    return content
if __name__ == "__main__":
    # CPU 信息
    print("CPU Count:", pt.cpu_count())
    print("CPU Usage:", pt.cpu_percent(interval=1))

    # 内存信息
    mem = pt.virtual_memory()
    print("Total Memory:", mem.total)
    print("Available Memory:", mem.available)
    print("Used Memory:", mem.used)
    print("Memory Usage:", mem.percent)

    # 磁盘信息
    disk = pt.disk_usage('/')
    print("Total Disk Space:", disk.total)
    print("Used Disk Space:", disk.used)
    print("Free Disk Space:", disk.free)
    print("Disk Usage:", disk.percent)

    # 网络信息
    net = pt.net_io_counters()
    print("Bytes Sent:", net.bytes_sent)
    print("Bytes Received:", net.bytes_recv)

    print()
    print(system_info())
