import psutil as pt
import platform
import time

def secs_to_ymdh(secs):
    days = secs / 86400
    # 计算年数
    years = days // 365
    # 计算剩余天数
    remaining_days = days % 365
    # 计算月数
    months = remaining_days // 30
    # 计算剩余天数
    remaining_days = remaining_days % 30
    # 计算小时数
    hours = 24 * (remaining_days % 1)

    mins = 24 * 60 * (remaining_days % 1) % 60

    remaining_secs = secs % 60 % 60

    # 返回格式化后的字符串z
    formatted_string = "" if years < 1 else str(int(years)) + "年"
    formatted_string += "" if months < 1 else str(int(months)) + "个月"
    formatted_string += "" if remaining_days < 1 else str(int(remaining_days)) + "天"
    formatted_string += str(int(hours)) + "小时"
    formatted_string += str(int(mins)) + "分钟"
    formatted_string += str(int(remaining_secs)) + "秒"
    return formatted_string

# 将字节转换为 MiB
def bytes_to_mib(bytes):
    return bytes / (1024 * 1024)

# 将字节转换为 GiB
def bytes_to_gib(bytes):
    return bytes / (1024 * 1024 * 1024)

def system_info():
    mem = pt.virtual_memory()
    content = f"""    === 当前系统状态 ===
- 机器名: {platform.node()}
- 系统: {platform.system()} {platform.version()} {platform.machine()}
- CPU 数量: {pt.cpu_count()}
- CPU 使用率: {pt.cpu_percent(interval=0.1)}%
- 内存总量: {bytes_to_mib(mem.total):.2f} MiB
- 内存使用率: {mem.percent}%
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
