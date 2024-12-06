import psutil as pt
import platform
import time
from .time_tools import secs_to_ymdh
import socket


# 将字节转换为可读格式
def format_datasize(num, suffix="B"):
    for unit in ("", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"):
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"


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
- CPU 数量: {pt.cpu_count()}
- CPU 使用率: {pt.cpu_percent(interval=0.1)}%
- 内存总量: {format_datasize(mem.total)} MiB
- 内存使用率: {mem.percent}%
- 当前开机时长: {secs_to_ymdh(int(time.time() - pt.boot_time()))}
"""
    return content


def _test():
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


if __name__ == '__main__':
    _test()
