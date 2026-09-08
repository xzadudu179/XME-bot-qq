"""受限子进程沙箱：把不可信输入驱动的重计算隔离到 bubblewrap 容器中执行。

两个入口对应两个档位：
- run_in_sandbox：repo 档（calc 求值/绘图；输入经 AST 白名单、无任意代码能力）。
  目标函数按模块路径在容器内导入，仓库根只读映射为 /app，data/ 与 logs/ 可写，
  返回相对路径主进程可读。
- run_in_cell：cell 档（run_python 等任意 AI 生成代码，严格空白盒）。容器内
  不存在任何仓库代码——任务函数以 marshal 字节码注入（须自包含），仅工作区
  映射为 /workspace；config/keys/nonebot/仓库全部不可见。

安全模型（纵深防御的最后一层，上层应先做输入语法校验）：
- 强隔离由 bubblewrap 提供，失败关闭：找不到 bwrap 或 userns 不可用时抛
  SandboxError 拒绝执行，绝不静默降级到弱隔离模式。
- 完全没有网络：--unshare-net，独立网络命名空间内只有未配置的孤立 loopback。
- 看不见沙箱外进程、发不出信号：--unshare-pid 独立 PID 命名空间，/proc 里只有
  沙箱内进程；--die-with-parent 保证 bwrap 死则整树原子消失（reparent 孤儿
  清扫仅作 bwrap 失效时的兜底保留）。
- 读不到沙箱外文件：文件系统白名单。只有 /usr 运行时、venv 与档位指定目录以
  只读方式进入沙箱；数据库文件在 repo 档被空文件覆盖绑定遮蔽；家目录、/etc、
  日志完全不进沙箱；cell 档连仓库都不进。
- 写不了沙箱外文件：/usr、venv 与仓库源码全部只读，可写点仅限 repo 档的
  data/ 与 logs/ 运行目录、cell 档的工作区，以及各沙箱私有的 tmpfs（/tmp、
  /run、/home）；沙箱内的落盘副作用随容器销毁。
- 低权限：非特权 user namespace + 新会话 + no_new_privs；沙箱内资源仍受
  resource.setrlimit 约束（内存 RLIMIT_AS、CPU 时间、落盘 RLIMIT_FSIZE、
  打开文件数 RLIMIT_NOFILE，hard 一并压低）。
- 主进程防卡死：墙钟超时强杀 bwrap 进程组；主流程永远能在 timeout 内拿到
  结果或异常；并发名额 sandbox_slot 限量且排队有时限。
- 回传协议不对称：父进程经 stdin 发「8 字节大端长度 + pickle 任务」（该方向
  受信任，载荷由本模块构造；cell 档的 marshal 字节码随载荷注入）；子进程回
  「8 字节大端长度 + JSON」。父进程绝不 unpickle 回传数据，异常按白名单从主
  进程已加载模块（sys.modules）按名还原，绝不 import 回传的模块名（防
  「种模块 + raise」反打主进程）。
- 残余风险：内核 user-namespace 0-day 可逃逸；/usr 与 venv 的只读内容（公共
  库）沙箱内可见；repo 档仓库源码与 keys.py 可见（该档没有任意代码能力，与
  旧行为持平且严格更优）；新部署机器需预装 bubblewrap（apt install
  bubblewrap），否则沙箱拒绝工作。

返回值约定：JSON 可序列化的纯数据。repo 档 dataclass 自动转 dict、tuple/set
转 list、Path 转 str；不可序列化时整个调用以 SandboxExecutionError 失败。

仅支持 Linux（依赖 bubblewrap / resource / start_new_session）。
"""

import asyncio
import ctypes
import importlib
import json
import logging
import marshal
import os
import pickle
import shutil
import signal
import struct
import sys
import traceback
import weakref
from contextlib import asynccontextmanager
from dataclasses import asdict, is_dataclass
from pathlib import Path
from resource import getrlimit, setrlimit, RLIMIT_AS, RLIMIT_CPU, RLIMIT_FSIZE, RLIMIT_NOFILE

DEFAULT_TIMEOUT = 15.0
MAX_TIMEOUT = 60.0
DEFAULT_MEM_MB = 512
MAX_MEM_MB = 2048
DEFAULT_FSIZE_MB = 0
DEFAULT_RESULT_LIMIT = 64 * 1024
MAX_CONCURRENT_SANDBOXES = 4
QUEUE_WAIT_TIMEOUT = 30.0
_PAYLOAD_LIMIT = 1024 * 1024
_STDERR_LIMIT = 4096
_STDERR_GRACE = 2.0
_TRACEBACK_LIMIT = 2000
_SPAWN_TIMEOUT_CAP = 10.0
# 孤儿清扫预算：轮数 × 轮间隔。正常路径首轮即空扫返回，只有存在幸存派生进程时才消耗预算
_SWEEP_ROUNDS = 5
_SWEEP_INTERVAL = 0.2

REPO_PROFILE = "repo"  # calc 求值/绘图档：仓库只读 + data/、logs/ 可写
CELL_PROFILE = "cell"  # 任意代码档：严格空白盒（无仓库代码，任务以 marshal 字节码注入）
PROFILES = (REPO_PROFILE, CELL_PROFILE)

# 沙箱内固定布局：仓库根 /app、venv /opt/venv、工作区 /workspace
_SANDBOX_APP = "/app"
_SANDBOX_VENV = "/opt/venv"
_SANDBOX_WORKSPACE = "/workspace"
_PYTHON_VERSION = f"python{sys.version_info.major}.{sys.version_info.minor}"
_IN_VENV = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
# 宿主侧 venv 根（bot 经 start.sh 在 venv 内启动）；系统解释器部署时为 None
_HOST_VENV_ROOT = Path(sys.prefix) if _IN_VENV else None
_SANDBOX_PYTHON = f"{_SANDBOX_VENV}/bin/{_PYTHON_VERSION}" if _HOST_VENV_ROOT else f"/usr/bin/{_PYTHON_VERSION}"
# repo 档在 /app 内用空文件覆盖绑定遮蔽数据库（导入链无任何模块读它们）。
# keys.py 不能遮蔽：filetools 顶层 `from keys import ...` 在 calc 导入链上，
# 而 repo 档无任意代码能力（AST 白名单），keys 的值不可被表达式读取。
_REPO_SHADOWED_FILES = ("guild1.db", "guild1.db-shm", "guild1.db-wal")

_REPO_ROOT = str(Path(__file__).resolve().parents[2])
_HEADER = struct.Struct(">Q")
_logger = logging.getLogger(__name__)

# repo 档引导脚本：-I 模式不会把任何目录加进 sys.path，仓库根由父进程经 argv
# 传入。先设 no_new_privs：其派生进程 exec setuid 二进制不再提权（不支持的平台
# 静默放过）。仅 repo 档使用——cell 档容器内没有仓库，走 _CELL_BOOTSTRAP。
_WORKER_BOOTSTRAP = (
    "import ctypes, sys\n"
    "try:\n"
    "    ctypes.CDLL(None, use_errno=True).prctl(38, 1, 0, 0, 0)  # PR_SET_NO_NEW_PRIVS\n"
    "except Exception:\n"
    "    pass\n"
    "sys.path.insert(0, sys.argv[1])\n"
    "from xme.xmetools.sandboxtools import _worker_main\n"
    "sys.exit(_worker_main())\n"
)

# cell 档引导脚本：完全自包含，不 import 任何仓库代码。任务函数以 marshal
# 字节码随载荷注入，重建后调用；约束见 run_in_cell。
_CELL_BOOTSTRAP = (
    "import ctypes, json, marshal, os, pickle, resource, sys, traceback, types\n"
    "try:\n"
    "    ctypes.CDLL(None, use_errno=True).prctl(38, 1, 0, 0, 0)  # PR_SET_NO_NEW_PRIVS\n"
    "except Exception:\n"
    "    pass\n"
    "def _read_frame(stream):\n"
    "    header = stream.read(8)\n"
    "    if len(header) < 8:\n"
    "        raise EOFError('帧头不完整')\n"
    "    length = int.from_bytes(header, 'big')\n"
    "    data = b''\n"
    "    while len(data) < length:\n"
    "        chunk = stream.read(length - len(data))\n"
    "        if not chunk:\n"
    "            raise EOFError('帧体不完整')\n"
    "        data += chunk\n"
    "    return data\n"
    "def _write_frame(fd, data):\n"
    "    view = memoryview(len(data).to_bytes(8, 'big') + data)\n"
    "    while view:\n"
    "        view = view[os.write(fd, view):]\n"
    "payload = pickle.loads(_read_frame(sys.stdin.buffer))\n"
    "limits = payload['limits']\n"
    "resource.setrlimit(resource.RLIMIT_AS, (limits['mem_mb'] * 1024 * 1024,) * 2)\n"
    "cpu = max(1, int(limits['timeout']) + 5)\n"
    "resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))\n"
    "fsize = limits['fsize_mb'] * 1024 * 1024\n"
    "resource.setrlimit(resource.RLIMIT_FSIZE, (fsize, fsize))\n"
    "nofile = min(32, resource.getrlimit(resource.RLIMIT_NOFILE)[1])\n"
    "resource.setrlimit(resource.RLIMIT_NOFILE, (nofile, nofile))\n"
    "result_fd = os.dup(1)\n"
    "os.dup2(2, 1)\n"
    "try:\n"
    "    try:\n"
    "        func = types.FunctionType(marshal.loads(payload['code']),\n"
    "                                  {'__builtins__': __builtins__}, 'cell_task')\n"
    "        value = func(*payload['args'], **payload['kwargs'])\n"
    "        result = {'ok': True, 'value': value}\n"
    "    except Exception as ex:\n"
    "        result = {'ok': False, 'exc_module': type(ex).__module__,\n"
    "                  'exc_name': type(ex).__qualname__, 'message': str(ex),\n"
    "                  'traceback': ''.join(traceback.format_exception(type(ex), ex, ex.__traceback__))[-2000:]}\n"
    "    try:\n"
    "        data = json.dumps(result, ensure_ascii=False).encode('utf-8')\n"
    "    except Exception:\n"
    "        data = json.dumps({'ok': False, 'exc_module': 'builtins', 'exc_name': 'TypeError',\n"
    "                           'message': 'cell 任务返回值不可 JSON 序列化', 'traceback': ''},\n"
    "                          ensure_ascii=True).encode('utf-8')\n"
    "    if len(data) > limits['result_limit']:\n"
    "        data = json.dumps({'ok': False, 'exc_module': 'xme.xmetools.sandboxtools',\n"
    "                           'exc_name': 'SandboxCrashedError',\n"
    "                           'message': '沙箱结果超过长度上限，已拒绝返回', 'traceback': ''},\n"
    "                          ensure_ascii=True).encode('utf-8')\n"
    "    _write_frame(result_fd, data)\n"
    "finally:\n"
    "    os.close(result_fd)\n"
)


class SandboxError(Exception):
    """沙箱相关错误的基类，调用方只需捕获本类。"""


class SandboxTimeoutError(SandboxError):
    """目标函数超出墙钟时限，子进程已被强杀。"""


class SandboxCrashedError(SandboxError):
    """子进程异常退出：被资源限制击杀、崩溃、通信失败或结果超限。"""


class SandboxExecutionError(SandboxError):
    """目标函数抛出的异常无法按原类型还原时的兜底包装。"""


def _read_frame(reader) -> bytes:
    """读取一帧「8 字节长度 + 数据」，超长或提前断流即抛错。"""
    header = reader.read(_HEADER.size)
    if len(header) < _HEADER.size:
        raise EOFError("帧头不完整")
    (length,) = _HEADER.unpack(header)
    if length > _PAYLOAD_LIMIT:
        raise ValueError(f"帧长超限 ({length})")
    data = b""
    while len(data) < length:
        chunk = reader.read(length - len(data))
        if not chunk:
            raise EOFError("帧体不完整")
        data += chunk
    return data


def _write_frame(fd: int, data: bytes) -> None:
    """向原始 fd 写出「8 字节长度 + 数据」单帧；循环写满，防部分写截断帧。"""
    view = memoryview(_HEADER.pack(len(data)) + data)
    while view:
        view = view[os.write(fd, view):]


def _apply_rlimits(limits: dict) -> None:
    """按任务限制设置当前（子）进程的资源上限。"""
    mem_bytes = limits["mem_mb"] * 1024 * 1024
    cpu_seconds = max(1, int(limits["timeout"]) + 5)
    fsize_bytes = limits["fsize_mb"] * 1024 * 1024
    nofile_limit = min(32, getrlimit(RLIMIT_NOFILE)[1])
    setrlimit(RLIMIT_AS, (mem_bytes, mem_bytes))
    setrlimit(RLIMIT_CPU, (cpu_seconds, cpu_seconds))
    setrlimit(RLIMIT_FSIZE, (fsize_bytes, fsize_bytes))
    # hard 一并压低：只压 soft 时子进程可自行 setrlimit 调回，限制形同虚设
    setrlimit(RLIMIT_NOFILE, (nofile_limit, nofile_limit))


def _settle_repo_imports() -> None:
    """预先导入仓库 config，规避 config/character 的模块级循环引用。

    config 在模块级调用 character.get_message，必须先完成 config 的导入
    （bot 主进程即靠导入顺序规避）；失败时静默放过，让后续目标模块导入
    暴露真实错误。仅 repo 档调用：cell 档的空白盒里没有 config。
    """
    try:
        import config  # noqa: F401
    except Exception:
        pass


def _json_default(obj):
    """json.dumps 的兜底转换：把常见「纯数据」对象降级为 JSON 类型。"""
    if is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj)
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, (set, frozenset)):
        return list(obj)
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    raise TypeError(f"沙箱返回值不可 JSON 序列化: {type(obj).__qualname__}")


def _error_frame(exc_module: str, exc_name: str, message: str) -> bytes:
    """编码一帧错误结果；ensure_ascii 让 message 含代理字符时也永不编码失败。"""
    return json.dumps({
        "ok": False,
        "exc_module": exc_module,
        "exc_name": exc_name,
        "message": message,
        "traceback": "",
    }, ensure_ascii=True).encode("ascii", "backslashreplace")


def _encode_result(result: dict, result_limit: int) -> bytes:
    """把结果 dict 编码为 JSON 帧；编码失败或超限时降级为错误帧。"""
    try:
        data = json.dumps(result, ensure_ascii=False, default=_json_default).encode("utf-8")
    except Exception as ex:
        data = _error_frame("builtins", "TypeError", f"沙箱返回值不可 JSON 序列化: {ex}")
    if len(data) > result_limit:
        data = _error_frame("xme.xmetools.sandboxtools", "SandboxCrashedError",
                            f"沙箱结果超过长度上限 ({result_limit} 字节)，已拒绝返回")
    return data


def _worker_main() -> int:
    """repo 档子进程入口：读任务帧 → 设资源上限 → 导入并执行目标函数 → 回写。

    任何失败都以非零退出码结束，父进程会将其归为 SandboxCrashedError。
    cell 档不走本函数：容器内没有仓库，由 _CELL_BOOTSTRAP 自包含完成。
    """
    try:
        payload = pickle.loads(_read_frame(sys.stdin.buffer))
    except Exception as ex:
        print(f"沙箱任务读取失败: {ex!r}", file=sys.stderr)
        return 2
    limits = payload["limits"]
    try:
        _apply_rlimits(limits)
    except Exception as ex:
        print(f"沙箱资源限制设置失败: {ex!r}", file=sys.stderr)
        return 3
    # 执行目标函数前把 fd 1 整体改道 stderr：print、C 层输出与派生进程继承的
    # fd 1 都无法再污染或伪造回传帧；真正的结果帧走保存下来的 result_fd。
    result_fd = os.dup(1)
    os.dup2(2, 1)
    try:
        try:
            _settle_repo_imports()
            module = importlib.import_module(payload["module"])
            func = module
            for attr in payload["qualname"].split("."):
                func = getattr(func, attr)
            value = func(*payload["args"], **payload["kwargs"])
            result = {"ok": True, "value": value}
        except Exception as ex:
            result = {
                "ok": False,
                "exc_module": type(ex).__module__,
                "exc_name": type(ex).__qualname__,
                "message": str(ex),
                "traceback": "".join(traceback.format_exception(type(ex), ex, ex.__traceback__))[-_TRACEBACK_LIMIT:],
            }
        _write_frame(result_fd, _encode_result(result, limits["result_limit"]))
    finally:
        os.close(result_fd)
    return 0


def _kill_process_group(proc: asyncio.subprocess.Process) -> None:
    """SIGKILL 杀掉子进程整组（bwrap 死则其 PID 命名空间整树原子消失）。"""
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            proc.kill()
        except (ProcessLookupError, OSError):
            pass


def _enable_subreaper() -> None:
    """把主进程设为 child subreaper（仅父进程调用，子进程绝不能走到这里）。

    bwrap 失效时逃出 killpg 的派生进程被孤儿化后会 reparent 到最近的
    subreaper（而非 init），清扫时才能按 ppid 找到并杀掉它们。
    """
    try:
        ctypes.CDLL(None, use_errno=True).prctl(36, 1, 0, 0, 0)  # PR_SET_CHILD_SUBREAPER
    except Exception as ex:
        _logger.debug("设置 child subreaper 失败（孤儿清扫将不可用）: %r", ex)


def _stat_pid_fields(pid: int) -> tuple[int, bytes, int, int] | None:
    """读 /proc/<pid>/stat 返回 (ppid, state, sid, starttime)；消失或解析失败返回 None。

    comm 字段可能含空格与括号，取最后一个 ')' 之后的部分再分段解析；
    sid 为会话 id，starttime 为开机起的时钟滴答数（用于圈定清扫时间窗）。
    """
    try:
        with open(f"/proc/{pid}/stat", "rb") as stat_file:
            data = stat_file.read()
    except OSError:
        return None
    fields = data.rpartition(b")")[2].split()
    try:
        return int(fields[1]), fields[0], int(fields[3]), int(fields[19])
    except (IndexError, ValueError):
        return None


# 存活中的沙箱容器进程 pid。孤儿清扫凭「ppid 是本进程」找人，必须排除仍在存活
# 期的沙箱容器（并发运行的别次沙箱、本次尚待 wait 的进程），否则互相误杀。
# 只在事件循环线程内读写，无锁。
_active_sandbox_pids: set[int] = set()


def _kill_leaked_spawns() -> None:
    """spawn 超时后击杀可能已启动的半启动沙箱容器（bwrap 及其内的引导进程）。

    此刻拿不到容器 pid 也无启动时间窗可用，改按本模块特有的命令行特征精确
    匹配（引导脚本的 _worker_main / bwrap 的 die-with-parent 旗标），不会
    误伤 bot 的其他子进程。
    """
    mine = os.getpid()
    for name in os.listdir("/proc"):
        if not name.isdigit():
            continue
        pid = int(name)
        info = _stat_pid_fields(pid)
        if info is None or info[0] != mine or pid in _active_sandbox_pids:
            continue
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as cmdline_file:
                cmdline = cmdline_file.read()
        except OSError:
            continue
        if b"_worker_main" in cmdline or b"--die-with-parent" in cmdline:
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass


def _sweep_pass(killed_sids: set[int], min_starttime: int) -> bool:
    """清扫一轮 reparent 到本进程的沙箱派生孤儿，返回本轮是否杀过活体。

    判据（同时满足）：父进程是本进程、启动时间不早于沙箱容器（缩小误伤
    窗口）、属于已确认的沙箱会话（自身是会话 leader，或 sid 已随其会话
    leader 被杀而入集）、且不在存活沙箱名单里。僵尸 WNOHANG 收尸（绝不阻塞
    事件循环），活体 SIGKILL 并把其 sid 记入集合，下一轮逮住它死后 reparent
    过来的子女。
    """
    mine = os.getpid()
    killed = False
    for name in os.listdir("/proc"):
        if not name.isdigit():
            continue
        pid = int(name)
        if pid == mine or pid in _active_sandbox_pids:
            continue
        info = _stat_pid_fields(pid)
        if info is None or info[0] != mine or info[3] < min_starttime:
            continue
        _, state, sid, _ = info
        if sid != pid and sid not in killed_sids:
            continue
        if state == b"Z":
            try:
                os.waitpid(pid, os.WNOHANG)
            except OSError:
                pass
            continue
        try:
            os.kill(pid, signal.SIGKILL)
            killed_sids.add(sid)
            killed = True
        except OSError:
            pass
    return killed


async def _sweep_reparented_orphans(root_sid: int, min_starttime: int) -> None:
    """清场沙箱派生的 reparent 孤儿（bwrap 万一失效时逃出 killpg 的幸存者）。

    带轮次预算防无限 fork 拖死清场；预算用尽仍有残留时记 warning 放弃。
    """
    killed_sids = {root_sid}
    for _ in range(_SWEEP_ROUNDS):
        if not _sweep_pass(killed_sids, min_starttime):
            return
        await asyncio.sleep(_SWEEP_INTERVAL)
    if _sweep_pass(killed_sids, min_starttime):
        _logger.warning("沙箱派生孤儿进程清扫预算用尽仍未清完，可能存在残留进程")


async def _reap(proc: asyncio.subprocess.Process, *, with_stderr: bool = False) -> bytes:
    """清场一个沙箱容器：杀组 → 收尸 → 孤儿清扫，可选限时收回 stderr。

    所有结束路径（成功/超时/崩溃/通信失败/兜底）统一走这里，保证孤儿清扫
    不被任何一条路径遗漏。先 wait 再清扫：派生孤儿 reparent 到本进程发生在
    容器退出时，wait 返回后它们才稳定可见；容器的启动时间则要在 wait 前
    读（收尸后 /proc 条目即消失）。
    """
    _kill_process_group(proc)
    child_info = _stat_pid_fields(proc.pid)
    returncode = await proc.wait()
    await _sweep_reparented_orphans(proc.pid, child_info[3] if child_info else 0)
    stderr = await _read_stderr(proc) if with_stderr else b""
    if with_stderr and stderr:
        _logger.debug("沙箱退出码 %s，stderr: %s", returncode,
                      stderr.decode(errors="replace").strip()[:_STDERR_LIMIT])
    return stderr


# 允许在主进程按名还原异常的模块白名单。回传方向不可信，而主进程的
# import_module 一旦执行回传的模块名就等于运行其顶层代码，因此这里绝不
# import：只允许从主进程【已加载】的模块（sys.modules）解析异常类，沙箱内
# 种下的新模块永远不会出现在 sys.modules 里。白名单须覆盖现有调用方依赖的
# 还原类型：calc 的 SyntaxError/ValueError（builtins）与 SympifyError（sympy.*）。
_TRUSTED_EXC_MODULES = ("xme.", "sympy.")


def _rebuild_exception(result: dict) -> Exception:
    """按白名单从主进程已加载模块还原子进程异常，其余一律包装为 SandboxExecutionError。"""
    exc_module = result.get("exc_module") or "builtins"
    exc_label = f"{exc_module}.{result.get('exc_name', '')}: {result.get('message', '')}"
    sandbox_traceback = result.get("traceback", "")

    def fallback() -> SandboxExecutionError:
        ex = SandboxExecutionError(exc_label)
        ex.sandbox_traceback = sandbox_traceback
        return ex

    if exc_module != "builtins" and not exc_module.startswith(_TRUSTED_EXC_MODULES):
        return fallback()
    try:
        # sys.modules.get 而非 import_module：模块未在主进程加载过时直接兜底，
        # 绝不触发导入
        module = sys.modules.get(exc_module)
        exc_type = getattr(module, result["exc_name"])
        if not (isinstance(exc_type, type) and issubclass(exc_type, Exception)):
            raise TypeError("不是异常类型")
        rebuilt = exc_type(result.get("message", ""))
        rebuilt.sandbox_traceback = sandbox_traceback
        return rebuilt
    except Exception:
        return fallback()


async def _read_stderr(proc: asyncio.subprocess.Process) -> bytes:
    """限量限时读取 stderr；管道被残留派生进程吊住时按宽限期放弃。"""
    try:
        return await asyncio.wait_for(proc.stderr.read(_STDERR_LIMIT), timeout=_STDERR_GRACE)
    except asyncio.TimeoutError:
        return b""


def _loop_semaphore() -> asyncio.Semaphore:
    """按事件循环取并发信号量，限制同时存活的沙箱容器数量。

    run_in_sandbox_sync 每次 asyncio.run 都新建 loop，全局单例信号量会跨 loop
    报错，故按 loop 弱引用缓存；这是运行时资源控制而非业务状态。
    """
    loop = asyncio.get_running_loop()
    sem = _semaphore_by_loop.get(loop)
    if sem is None:
        sem = asyncio.Semaphore(MAX_CONCURRENT_SANDBOXES)
        _semaphore_by_loop[loop] = sem
    return sem


_semaphore_by_loop: "weakref.WeakKeyDictionary" = weakref.WeakKeyDictionary()


@asynccontextmanager
async def _null_slot():
    """不占名额的空占位，供 hold_slot=False 分支复用语法。"""
    yield


@asynccontextmanager
async def sandbox_slot(wait_timeout: float = QUEUE_WAIT_TIMEOUT):
    """占用一个沙箱并发名额，超出排队等待时限抛 SandboxError。

    需要把工作区等资源生命周期整个放进名额内的调用方（如 sandboxexec 先建
    工作区再执行）直接使用本上下文管理器，并让内层执行函数以 hold_slot=False
    复用名额，避免排队期间持有临时目录或双重占额。
    """
    sem = _loop_semaphore()
    try:
        await asyncio.wait_for(sem.acquire(), timeout=wait_timeout)
    except asyncio.TimeoutError:
        raise SandboxError(f"沙箱排队超时 (>{wait_timeout:g}s)，请稍后再试") from None
    try:
        yield
    finally:
        sem.release()


async def _exchange(proc: asyncio.subprocess.Process, payload: bytes, result_limit: int) -> dict:
    """发送任务帧并接收结果帧，结果超限或帧非法时抛 SandboxCrashedError。"""
    proc.stdin.write(_HEADER.pack(len(payload)))
    proc.stdin.write(payload)
    await proc.stdin.drain()
    proc.stdin.close()
    header = await proc.stdout.readexactly(_HEADER.size)
    (length,) = _HEADER.unpack(header)
    if length > result_limit:
        raise SandboxCrashedError(f"沙箱结果超过长度上限 ({length} > {result_limit} 字节)")
    # 回传帧只做 JSON 解析：子进程方向不可信，绝不能在此 unpickle，
    # 否则子进程内执行的任意代码可伪造帧反打主进程。
    try:
        frame = json.loads(await proc.stdout.readexactly(length))
    except (json.JSONDecodeError, UnicodeDecodeError) as ex:
        raise SandboxCrashedError(f"沙箱结果帧不是合法 JSON: {ex}") from None
    if not isinstance(frame, dict) or "ok" not in frame:
        raise SandboxCrashedError("沙箱结果帧格式非法")
    if frame["ok"] and "value" not in frame:
        # 帧方向不可信，schema 一并校验，防伪造/残缺帧以 KeyError 形式漏出
        raise SandboxCrashedError("沙箱结果帧缺少 value 字段")
    return frame


def _bwrap_args(profile: str, work_dir: str | None) -> list[str]:
    """构造 bubblewrap 包裹参数（含 --chdir），返回完整参数表。

    隔离基线：user/pid/net/ipc/uts/cgroup 全隔离、die-with-parent、虚拟
    /dev /proc、私有 /tmp /run /home、/usr 与 venv 只读。档位追加：
    repo = 仓库根只读 + Chrome 运行时 + data/、logs/ 可写 + 数据库遮蔽，
    chdir /app；cell = 容器内无任何仓库代码，工作区（缺省为私有 tmpfs）
    映射为 /workspace，chdir /workspace。
    """
    if profile not in PROFILES:
        raise ValueError(f"未知沙箱档位: {profile!r}，可选 {PROFILES}")
    args = [
        "--unshare-user", "--unshare-pid", "--unshare-net", "--unshare-ipc",
        "--unshare-uts", "--unshare-cgroup-try",
        "--die-with-parent", "--new-session",
        "--dev", "/dev", "--tmpfs", "/dev/shm", "--proc", "/proc",
        "--tmpfs", "/tmp", "--tmpfs", "/run", "--tmpfs", "/home",
        "--ro-bind", "/usr", "/usr",
        "--symlink", "usr/lib64", "/lib64",
        "--symlink", "usr/lib", "/lib",
        "--symlink", "usr/bin", "/bin",
        "--symlink", "usr/sbin", "/sbin",
    ]
    # ldconfig 的库缓存：ctypes.util.find_library / pyenchant 等依赖它定位系统
    # 库；公共库映射表，非敏感物。缺了它 enchant 导入会退化为 gcc 探测并失败
    if Path("/etc/ld.so.cache").is_file():
        args += ["--ro-bind", "/etc/ld.so.cache", "/etc/ld.so.cache"]
    if _HOST_VENV_ROOT:
        args += ["--ro-bind", str(_HOST_VENV_ROOT), _SANDBOX_VENV]
    # matplotlib 字体缓存持久化到仓库 data/，否则沙箱私有 tmpfs 会让每次绘图
    # 重建缓存（首次可达数十秒）
    mpl_cache = Path(_REPO_ROOT, "data/mplcache")
    mpl_cache.mkdir(parents=True, exist_ok=True)
    args += ["--bind", str(mpl_cache), "/tmp/mplconfig"]
    if profile == REPO_PROFILE:
        args += ["--ro-bind", _REPO_ROOT, _SANDBOX_APP]
        # 仓库依赖的宿主运行时：html2image 在导入期定位 Chrome（经 alternatives
        # 软链指向 /opt/google/chrome），缺了会让 calc 导入链直接失败
        for host_path in ("/etc/alternatives", "/opt/google/chrome"):
            if Path(host_path).exists():
                args += ["--ro-bind", host_path, host_path]
        # 仓库运行期可写目录：绘图落盘（data/images/temp）与 bot 日志（部分
        # 模块在导入期即打开日志文件）；repo 档代码无任意能力，与旧行为持平
        for rel in ("data", "logs"):
            host_dir = Path(_REPO_ROOT, rel)
            host_dir.mkdir(parents=True, exist_ok=True)
            args += ["--bind", str(host_dir), f"{_SANDBOX_APP}/{rel}"]
        for name in _REPO_SHADOWED_FILES:
            if Path(_REPO_ROOT, name).is_file():
                args += ["--ro-bind", "/dev/null", f"{_SANDBOX_APP}/{name}"]
        args += ["--chdir", _SANDBOX_APP]
    else:
        # cell 档：容器内不存在任何仓库代码，任务函数以 marshal 字节码注入
        if work_dir:
            args += ["--bind", work_dir, _SANDBOX_WORKSPACE]
        else:
            args += ["--tmpfs", _SANDBOX_WORKSPACE]
        args += ["--chdir", _SANDBOX_WORKSPACE]
    return args


def _sandbox_env() -> dict:
    """构造沙箱内环境变量：全量重建、不从宿主继承，家目录指到可写 tmpfs。"""
    return {
        "PATH": "/usr/bin:/bin",
        "TMPDIR": "/tmp",
        "HOME": "/tmp",
        "MPLCONFIGDIR": "/tmp/mplconfig",
        "XDG_CACHE_HOME": "/tmp/xdgcache",
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        # BLAS 线程池会按核数预留大量虚拟内存，容易触死 RLIMIT_AS；沙箱内单线程足够
        "OPENBLAS_NUM_THREADS": "1",
        "OMP_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
    }


def _clamp_limits(timeout: float, mem_mb: int, result_limit: int) -> tuple[float, int, int]:
    """把调用方的超时/内存/结果上限收敛到沙箱允许范围内。"""
    return (min(max(float(timeout), 0.1), MAX_TIMEOUT),
            min(max(int(mem_mb), 64), MAX_MEM_MB),
            min(max(int(result_limit), 1024), _PAYLOAD_LIMIT))


async def _run_container(payload: bytes, *, profile: str, work_dir: str | None,
                         timeout: float, mem_mb: int, fsize_mb: int, result_limit: int):
    """持有名额前提下的容器执行实体：spawn → 交换帧 → 清场 → 还原异常。

    payload 已含收敛后的 limits；本函数只负责容器生命周期与通信。
    """
    # 失败关闭：没有 bwrap 就拒绝执行，绝不降级到弱隔离模式
    bwrap_path = shutil.which("bwrap")
    if not bwrap_path:
        raise SandboxError("未找到 bubblewrap（bwrap），沙箱拒绝以弱隔离模式运行；请安装：apt install bubblewrap")
    bwrap_args = _bwrap_args(profile, work_dir)
    # 子进程 import numpy/sympy 可能需要数秒，spawn 超时单独封顶；超时瞬间可能
    # 已启动半截容器，subreaper 已把它收编为直接子进程，清扫即可回收
    _enable_subreaper()
    spawn_timeout = min(timeout, _SPAWN_TIMEOUT_CAP)
    bootstrap = _WORKER_BOOTSTRAP if profile == REPO_PROFILE else _CELL_BOOTSTRAP
    command = [bwrap_path, *bwrap_args,
               _SANDBOX_PYTHON, "-I", "-B", "-c", bootstrap, _SANDBOX_APP]
    try:
        proc = await asyncio.wait_for(
            asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                cwd=work_dir or _REPO_ROOT, env=_sandbox_env(), start_new_session=True,
            ),
            timeout=spawn_timeout)
    except asyncio.TimeoutError:
        _kill_leaked_spawns()
        raise SandboxCrashedError(f"沙箱容器启动超时 (>{spawn_timeout:g}s)") from None
    except OSError as ex:
        # fork 资源不足等启动失败也要落进 SandboxError 家族，调用方只兜底本类
        raise SandboxCrashedError(f"沙箱容器启动失败: {ex}") from ex
    _active_sandbox_pids.add(proc.pid)
    try:
        try:
            result = await asyncio.wait_for(_exchange(proc, payload, result_limit), timeout=timeout)
        except asyncio.TimeoutError:
            await _reap(proc)
            raise SandboxTimeoutError(f"沙箱执行超时 (>{timeout:g}s)") from None
        except SandboxError:
            await _reap(proc)
            raise
        except asyncio.IncompleteReadError:
            # 容器已断流：先清场防派生进程拖住管道，再收 stderr 诊断
            stderr = await _reap(proc, with_stderr=True)
            raise SandboxCrashedError(
                f"沙箱容器异常退出 (code={proc.returncode}): {stderr.decode(errors='replace').strip()}"
            ) from None
        except OSError as ex:
            # 3.11 起 asyncio.TimeoutError 即内建 TimeoutError（OSError 子类），
            # 已被上方分支接住；这里只剩真正的管道/进程通信故障
            await _reap(proc)
            raise SandboxCrashedError(f"与沙箱容器通信失败: {ex}") from None
        # 已拿到结果帧，容器使命结束：立即清场，防止派生进程吊住管道把
        # stderr 读取挂死
        await _reap(proc, with_stderr=True)
    finally:
        if proc.returncode is None:
            await _reap(proc)
        _active_sandbox_pids.discard(proc.pid)
    if not result["ok"]:
        raise _rebuild_exception(result)
    return result["value"]


async def run_in_sandbox(func, *args, func_kwargs: dict | None = None,
                         timeout: float = DEFAULT_TIMEOUT,
                         mem_mb: int = DEFAULT_MEM_MB, fsize_mb: int = DEFAULT_FSIZE_MB,
                         result_limit: int = DEFAULT_RESULT_LIMIT):
    """在 repo 档容器中执行按模块路径导入的顶层函数并返回其返回值。

    仓库根只读映射为 /app，data/ 与 logs/ 可写；func 经容器内 importlib 导入，
    因此仅适用于仓库自身代码（calc 求值/绘图；输入应先经上层校验，如 calc 的
    AST 白名单）。执行不可信的任意代码请改用 run_in_cell。

    Args:
        func: 可按模块路径导入的顶层函数（lambda、闭包、局部函数不支持）
        *args: 传给 func 的位置参数（pickle 传输，须可序列化）
        func_kwargs: 传给 func 的关键字参数（pickle 传输，须可序列化）
        timeout: 墙钟超时秒数，超时强杀容器并抛 SandboxTimeoutError
        mem_mb: 容器内子进程内存上限 (MB)，超限被内核击杀
        fsize_mb: 容器内单文件写入上限 (MB)，0 为不能创建/增长文件
        result_limit: 返回值序列化后的最大字节数

    Returns:
        Any: func 的返回值，JSON 纯数据（dataclass 转 dict、tuple/set 转 list、
        Path 转 str）

    Raises:
        SandboxTimeoutError: 超时
        SandboxCrashedError: 容器崩溃/被资源限制击杀/结果超限/通信失败
        SandboxExecutionError: 异常类型无法还原时的兜底
        SandboxError: 任务载荷超过单帧上限、并发名额排队超时，或 bwrap 不可用
        Exception: 目标函数抛出的异常会尽量按原类型重新抛出
    """
    module_name = getattr(func, "__module__", None)
    qualname = getattr(func, "__qualname__", None)
    if not module_name or not qualname or "<" in qualname or module_name == "__main__":
        raise ValueError("run_in_sandbox 只支持可按模块路径导入的顶层函数")
    timeout, mem_mb, result_limit = _clamp_limits(timeout, mem_mb, result_limit)
    try:
        payload = pickle.dumps({
            "kind": "func",
            "module": module_name,
            "qualname": qualname,
            "args": args,
            "kwargs": func_kwargs or {},
            "limits": {
                "timeout": timeout,
                "mem_mb": mem_mb,
                "fsize_mb": max(int(fsize_mb), 0),
                "result_limit": result_limit,
            },
        })
    except Exception as ex:
        raise SandboxError(f"沙箱任务参数不可 pickle 序列化: {ex}") from ex
    if len(payload) > _PAYLOAD_LIMIT:
        raise SandboxError(f"沙箱任务载荷超过单帧上限 ({len(payload)} > {_PAYLOAD_LIMIT} 字节)")
    async with sandbox_slot():
        return await _run_container(payload, profile=REPO_PROFILE, work_dir=None,
                                    timeout=timeout, mem_mb=mem_mb, fsize_mb=fsize_mb,
                                    result_limit=result_limit)


async def run_in_cell(func, *args, func_kwargs: dict | None = None,
                      timeout: float = DEFAULT_TIMEOUT,
                      mem_mb: int = DEFAULT_MEM_MB, fsize_mb: int = DEFAULT_FSIZE_MB,
                      result_limit: int = DEFAULT_RESULT_LIMIT,
                      work_dir: str | None = None, hold_slot: bool = True):
    """在 cell 空白盒中执行【自包含】函数并返回其返回值。

    cell 容器内不存在任何仓库代码：func 以 marshal 字节码随载荷注入，因此
    func 必须自包含——函数体内自行 import、不引用模块级名字/闭包变量/默认
    参数值，参数由调用方显式传全，返回值须为 JSON 纯数据。marshal 字节码与
    容器内解释器同版本（同一台机器的同一 Python 系列）。

    Args:
        func: 自包含的顶层函数（lambda、闭包、局部函数不支持）
        work_dir: 宿主侧工作目录，映射为沙箱内 /workspace 并作为 cwd；
            缺省为私有 tmpfs
        hold_slot: 调用方已用 sandbox_slot() 自行持有名额时传 False，
            避免双重占额
        其余参数同 run_in_sandbox

    Raises:
        同 run_in_sandbox；func 不满足自包含顶层函数约束时抛 ValueError
    """
    qualname = getattr(func, "__qualname__", None)
    if not qualname or "<" in qualname:
        raise ValueError("run_in_cell 只支持普通顶层函数（不接受 lambda、闭包、局部函数）")
    timeout, mem_mb, result_limit = _clamp_limits(timeout, mem_mb, result_limit)
    try:
        payload = pickle.dumps({
            "kind": "cell",
            "code": marshal.dumps(func.__code__),
            "args": args,
            "kwargs": func_kwargs or {},
            "limits": {
                "timeout": timeout,
                "mem_mb": mem_mb,
                "fsize_mb": max(int(fsize_mb), 0),
                "result_limit": result_limit,
            },
        })
    except Exception as ex:
        raise SandboxError(f"沙箱任务参数不可 pickle 序列化: {ex}") from ex
    if len(payload) > _PAYLOAD_LIMIT:
        raise SandboxError(f"沙箱任务载荷超过单帧上限 ({len(payload)} > {_PAYLOAD_LIMIT} 字节)")
    slot_ctx = sandbox_slot() if hold_slot else _null_slot()
    async with slot_ctx:
        return await _run_container(payload, profile=CELL_PROFILE, work_dir=work_dir,
                                    timeout=timeout, mem_mb=mem_mb, fsize_mb=fsize_mb,
                                    result_limit=result_limit)


def run_in_sandbox_sync(func, *args, **kwargs):
    """run_in_sandbox 的同步版本，仅供非协程环境调用；事件循环内调用直接拒绝。

    注意：每次 asyncio.run 都新建事件循环，并发信号量按 loop 缓存、不跨调用
    累计，故同步路径的并发上限只对单次调用有效，不要用它在多线程里并发狂开
    沙箱。
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(run_in_sandbox(func, *args, **kwargs))
    raise RuntimeError("run_in_sandbox_sync 禁止在事件循环内调用，请改用 await run_in_sandbox(...)")
