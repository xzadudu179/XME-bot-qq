import psutil as pt
import platform
import time
from .timetools import secs_to_ymdh
import socket

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

def system_info():
    mem = pt.virtual_memory()
    content = f"""    === 当前系统状态 ===
- 机器名: {platform.node()}
- 系统: {platform.system()} {platform.version()} {platform.machine()}
- CPU 使用率: {pt.cpu_percent(interval=0.1)}%
- 内存总量: {bytes_to_mib(mem.used):.2f} / {bytes_to_mib(mem.total):.2f} MiB
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
