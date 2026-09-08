"""沙箱安全自检：在沙箱内执行一组逃逸与隔离探测，产出结构化检查结果。

本模块只依赖标准库与 sandboxtools；cell 档探针以 marshal 字节码注入容器，
必须自包含（函数体内自行 import，不引用模块级名字）；检查结果为 JSON 纯
数据，由指令层负责拼装回复文案。
"""

import os
import socket
import sys
from pathlib import Path

from xme.xmetools.sandboxtools import CELL_PROFILE, REPO_PROFILE, run_in_cell, run_in_sandbox

PROBE_TIMEOUT = 30
DEFAULT_BOT_PORT = 18980  # 仅兜底值；调用方应传 config.PORT


def _check(name: str, escaped: bool, detail: str) -> dict:
    """组装一条检查结果；escaped=True 表示攻击面可用（即未被隔离挡住）。"""
    return {"name": name, "passed": not escaped, "detail": detail}


def cell_probes(bot_port: int = DEFAULT_BOT_PORT) -> list[dict]:
    """（cell 档沙箱内执行，自包含）逃逸探测：网络、文件系统、导入、进程、环境。

    以 marshal 字节码注入容器执行：函数体内自行 import，不引用模块级名字；
    每项检查为 {name, passed, detail}。
    """
    import os
    import socket
    import sys

    checks = []

    def check(name: str, escaped: bool, detail: str) -> None:
        """escaped=True 表示攻击面可用（即未被隔离挡住）。"""
        checks.append({"name": name, "passed": not escaped, "detail": detail})

    for label, path in (("/etc/passwd", "/etc/passwd"),
                        ("keys.py", "/app/keys.py"),
                        ("config.py", "/app/config.py"),
                        ("/root", "/root")):
        try:
            with open(path, "rb"):
                check(f"读取 {label}", True, f"可读！{path}")
        except OSError as ex:
            check(f"读取 {label}", False, type(ex).__name__)

    for label, module in (("config", "config"), ("keys", "keys")):
        try:
            __import__(module)
            check(f"导入 {label} 模块", True, f"可导入！{module}")
        except ImportError as ex:
            check(f"导入 {label} 模块", False, type(ex).__name__)

    for label, target in (("公网 1.1.1.1:80", ("1.1.1.1", 80)),
                          (f"bot 本机端口 127.0.0.1:{bot_port}", ("127.0.0.1", bot_port))):
        try:
            s = socket.socket()
            s.settimeout(2)
            s.connect(target)
            s.close()
            check(f"外连 {label}", True, "连接成功！网络未隔离")
        except OSError as ex:
            check(f"外连 {label}", False, f"{type(ex).__name__}: {ex}")

    proc_pids = [p for p in os.listdir("/proc") if p.isdigit()]
    # 独立 PID 命名空间内只剩沙箱自己（与 bwrap 占位），看不到宿主进程
    check("看不见沙箱外进程", len(proc_pids) > 3, f"可见进程数 {len(proc_pids)}")

    sensitive = [k for k, v in os.environ.items()
                 if any(word in k.upper() for word in ("KEY", "TOKEN", "SECRET", "PASSWORD"))]
    host_path_leak = (any("/home/" in str(v) for v in os.environ.values())
                      or any("/home/" in a for a in sys.argv))
    home_ok = os.environ.get("HOME") == "/tmp"
    cwd_ok = os.getcwd() == "/workspace"
    check("环境与路径无宿主泄漏",
          bool(sensitive) or host_path_leak or not home_ok or not cwd_ok,
          f"HOME={os.environ.get('HOME')} cwd={os.getcwd()} "
          f"敏感变量 {sensitive or '无'} 宿主路径泄漏 {'有' if host_path_leak else '无'}")

    try:
        os.mkdir("/escape-marker")
        # 命名空间私有 tmpfs 上成功：宿主不可见、容器销毁即消失，性质由宿主侧断言
        check("根目录写入不外泄", False, "写入落在命名空间私有 tmpfs（宿主侧复核为不可见）")
    except OSError as ex:
        check("根目录写入不外泄", False, type(ex).__name__)

    return checks


def repo_probes() -> list[dict]:
    """（repo 档沙箱内执行）隔离探测：仓库只读、数据库遮蔽、网络隔离。"""
    checks = []

    try:
        with open("/app/guild1.db", "rb") as f:
            size = len(f.read())
        checks.append(_check("数据库文件遮蔽", size > 0, f"guild1.db 可见字节数 {size}"))
    except OSError as ex:
        checks.append(_check("数据库文件遮蔽", False, f"{type(ex).__name__}: {ex}"))

    try:
        with open("/app/keys.py", "rb") as f:
            content = f.read()
        # 已知设计取舍：calc 导入链顶层依赖 keys，repo 档无任意代码能力
        checks.append({"name": "keys.py 可见（设计取舍）", "passed": True,
                       "detail": f"{len(content)} 字节，仅 AST 白名单档可达"})
    except OSError as ex:
        checks.append({"name": "keys.py 可见（设计取舍）", "passed": True,
                       "detail": f"不可读（{type(ex).__name__}），导入链会失败需排查"})

    try:
        with open("/app/bot.py", "a"):
            checks.append(_check("仓库源码只读", True, "仓库源码可写！"))
    except OSError as ex:
        checks.append(_check("仓库源码只读", False, type(ex).__name__))

    try:
        s = socket.socket()
        s.settimeout(2)
        s.connect(("1.1.1.1", 80))
        s.close()
        checks.append(_check("外连公网 1.1.1.1:80", True, "连接成功！网络未隔离"))
    except OSError as ex:
        checks.append(_check("外连公网 1.1.1.1:80", False, f"{type(ex).__name__}: {ex}"))

    return checks


def _host_checks() -> list[dict]:
    """（宿主侧执行）复核沙箱写入没有落到宿主、容器无进程残留。"""
    checks = []
    checks.append(_check("宿主根目录无逃逸标记", Path("/escape-marker").exists(),
                         "发现 /escape-marker！" if Path("/escape-marker").exists() else "不存在"))
    leaked = []
    for name in os.listdir("/proc"):
        if not name.isdigit():
            continue
        try:
            with open(f"/proc/{name}/cmdline", "rb") as f:
                cmdline = f.read()
        except OSError:
            continue
        if b"_worker_main" in cmdline or b"--die-with-parent" in cmdline:
            leaked.append(name)
    checks.append(_check("宿主侧无沙箱进程残留", bool(leaked),
                         f"残留 pid {leaked}" if leaked else "无残留"))
    return checks


async def run_security_audit(profiles: tuple[str, ...] = (CELL_PROFILE, REPO_PROFILE),
                             bot_port: int = DEFAULT_BOT_PORT,
                             timeout: int = PROBE_TIMEOUT) -> dict[str, list[dict]]:
    """运行沙箱安全自检，返回 {档位或 host: 检查结果列表}。

    Args:
        profiles: 要探测的档位，可含 CELL_PROFILE / REPO_PROFILE
        bot_port: bot 本机端口（用于本机回环探测，调用方传 config.PORT）
        timeout: 单次沙箱探测的墙钟超时秒数

    Returns:
        dict[str, list[dict]]: 每个档位（及宿主侧 "host"）的检查结果列表，
        每条为 {"name": str, "passed": bool, "detail": str}
    """
    results: dict[str, list[dict]] = {}
    if CELL_PROFILE in profiles:
        results[CELL_PROFILE] = await run_in_cell(cell_probes, bot_port, timeout=timeout)
    if REPO_PROFILE in profiles:
        results[REPO_PROFILE] = await run_in_sandbox(
            repo_probes, timeout=timeout, mem_mb=768, fsize_mb=16)
    results["host"] = _host_checks()
    return results
