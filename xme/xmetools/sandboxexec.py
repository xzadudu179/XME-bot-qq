"""一次性工作区里的任意 Python 代码执行：文件以副本进沙箱，原文件零接触。

安全模型（建立在 sandboxtools 之上的应用层封装）：
- 原文件不进沙箱：父进程把输入文件复制进一次性临时工作区后，只把「工作区内的
  副本文件名」交给沙箱代码，原路径对子进程不可见；执行结束整个工作区删除，
  即使代码覆写副本也不影响原文件。
- 本模块走 cell 严格空白盒（bubblewrap）：容器内不存在任何仓库代码——任务
  函数 _code_task 以 marshal 字节码注入（须自包含），除运行时外仅工作区可
  写，无网络、独立 PID 命名空间（看不见沙箱外进程、发不出信号）、config/
  keys/nonebot/仓库/家目录完全不可见、不预导 config；执行结束容器销毁，落盘
  副作用不外泄。
- 主进程防护由 sandboxtools 保障：回传帧为 JSON（无执行语义，子进程内执行的
  任意代码无法伪造帧反打主进程）、执行期 fd 1 改道 stderr、墙钟强杀容器 +
  孤儿清扫兜底、内存/CPU/落盘 rlimit、并发名额先占位后建工作区（排队期间不
  持有临时目录与输入副本）。
- 产出回收防置换：收集走 O_NOFOLLOW + fd 级 fstat + 限额读取，容器内幸存的
  派生进程把产出文件置换成指向工作区外的符号链接、或在读取时撑大文件，都
  只会被跳过，不会泄密或打爆主进程内存。
- 残余风险（继承 sandboxtools）：内核 userns 0-day 可逃逸；/usr 与 venv 的
  只读内容（公共库）沙箱内可见。使用方应据此选择暴露面与权限。

本模块只在父进程使用，仅依赖标准库与 sandboxtools；沙箱内执行逻辑收敛在
自包含的任务函数 _code_task 里（以 marshal 字节码注入），不引入 filetools
（其模块级导入 nonebot）。
"""

import asyncio
import os
import shutil
import stat
import tempfile
from pathlib import Path

from xme.xmetools.sandboxtools import run_in_cell, sandbox_slot

DEFAULT_OUTPUT_LIMIT = 8000
DEFAULT_MAX_FILES = 10
DEFAULT_MAX_FILE_SIZE = 10 * 1024 * 1024


def _workspace_input_name(original: str) -> str:
    """从原文件名得到工作区内的安全副本名（含路径分隔符等不安全字符时回退）。"""
    name = Path(original).name
    # 与 filetools.is_safe_file_name 同语义的最小实现：任务函数须保持零额外依赖
    if name and name not in (".", "..") and "/" not in name and "\\" not in name:
        return name
    return f"input{Path(original).suffix}"


def _code_task(code: str, input_name: str | None, output_limit: int) -> dict:
    """（cell 档沙箱内执行的自包含任务）exec 用户代码，捕获 stdout，异常转文本。

    以 marshal 字节码注入容器执行，必须自包含：函数体内自行 import，不引用
    模块级名字。用户代码经全局变量 INPUT_FILE 获得输入副本的文件名（无输入
    时为 None）。

    Returns:
        {"output": str, "error": str | None}，均为 JSON 纯数据
    """
    import os
    import sys
    import traceback
    from io import StringIO

    def sanitize(text: str) -> str:
        """清洗字符串中的代理字符（surrogate），防下游 JSON 编码崩溃。"""
        return text.encode("utf-8", "replace").decode("utf-8")

    os.environ.setdefault("MPLBACKEND", "Agg")  # 无显示环境下让 matplotlib 正常出图
    buf = StringIO()
    error = None
    original_stdout = sys.stdout
    sys.stdout = buf
    try:
        globs = {
            "__name__": "__main__",
            "__file__": os.path.abspath(input_name) if input_name else "<user_code>",
            "INPUT_FILE": input_name,
        }
        exec(compile(code, "<user_code>", "exec"), globs)
    except BaseException:
        # 捕 BaseException：用户代码里的 exit()/sys.exit() 要变成可回传的报错
        # 文本，而不是让容器无帧退出、上游只能看到「异常退出」
        error = traceback.format_exc()[-4000:]
    finally:
        sys.stdout = original_stdout
    # 超长输出保留末尾（分析结论通常在最后的 print 里）
    return {"output": sanitize(buf.getvalue()[-output_limit:]),
            "error": sanitize(error) if error is not None else None}


def _safe_read_capped(path: Path, max_size: int) -> bytes | None:
    """O_NOFOLLOW 打开并限额读取文件；非普通文件、超限或读取竞态返回 None。

    符号链接直接拒开（ELOOP），目录被 fstat 的 S_ISREG 拒掉；大小与读取都在
    已打开的 fd 上校验，读期间被并发撑大也最多读 max_size+1 字节。
    """
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError:
        return None
    try:
        with os.fdopen(fd, "rb") as f:
            info = os.fstat(f.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > max_size:
                return None
            return f.read(max_size + 1)
    except OSError:
        return None


def _collect_produced_files(workspace: Path, input_name: str | None,
                            max_files: int, max_file_size: int) -> dict:
    """收集工作区内的产出文件为 {文件名: bytes}；阻塞 I/O，须在子线程中调用。

    跳过输入副本与一切拒收条目（符号链接/目录/超限，见 _safe_read_capped，
    防把工作区外文件伪装成产出或无界占内存），单条目故障只跳过不中断；
    沙箱代码可在墙钟内创建任意数量的文件，全部处理必须离开事件循环线程。
    """
    files = {}
    for produced in sorted(workspace.iterdir()):
        if produced.name == input_name or len(files) >= max_files:
            continue
        data = _safe_read_capped(produced, max_file_size)
        if data is None or len(data) > max_file_size:
            continue
        # 沙箱可创建非 UTF-8 文件名（经 surrogateescape 成代理字符），清洗成
        # 合法字符串再当键，防下游 json 编码崩溃
        name = produced.name.encode("utf-8", "surrogateescape").decode("utf-8", "replace")
        files[name] = data
    return files


async def run_code_in_workspace(
        code: str, input_path: str | Path | None = None, *,
        input_name: str | None = None,
        timeout: float = 30.0, mem_mb: int = 768, fsize_mb: int = 16,
        output_limit: int = DEFAULT_OUTPUT_LIMIT,
        max_files: int = DEFAULT_MAX_FILES,
        max_file_size: int = DEFAULT_MAX_FILE_SIZE
    ) -> dict:
    """把输入文件复制进一次性工作区，在沙箱内执行 code 并回收输出与产出文件。

    整个工作区生命周期（建目录→复制→执行→收集→删除）都在一个沙箱并发名额
    内完成，排队超出 sandbox_slot 的等待时限时抛 SandboxError，不会无限占位
    等待，也不会在排队期间持有临时目录与输入副本。

    Args:
        code: 要执行的 Python 代码（cwd 为工作区，print 输出会被捕获回传）
        input_path: 原文件路径；None 为纯代码执行。原文件只被父进程读取复制，
            路径不会进入沙箱，代码能接触到的只有工作区内的副本
        input_name: 副本文件名，缺省用原文件名（不安全时自动回退）
        timeout: 墙钟超时秒数，超时强杀容器并抛 SandboxTimeoutError
        mem_mb: 容器内子进程内存上限 (MB)，matplotlib + numpy 需要放宽
            （同 calc 绘图档）
        fsize_mb: 容器内单文件写入上限 (MB)（RLIMIT_FSIZE 按全路径单文件生效、
            不限工作区），0 会连图表都没法保存
        output_limit: 捕获输出的最大字符数（超出保留末尾）
        max_files / max_file_size: 产出文件数量 / 单文件大小上限，超出的跳过

    Returns:
        {"output": str, "error": str | None, "files": dict[文件名, bytes]}
    """
    if input_path is not None:
        source = Path(input_path)
        if not source.is_file():
            raise FileNotFoundError(f"输入文件不存在: {source}")
        name = input_name or _workspace_input_name(source.name)
    else:
        source = None
        name = None
    async with sandbox_slot():
        workspace = Path(tempfile.mkdtemp(prefix="sandboxexec_"))
        try:
            if source is not None:
                await asyncio.to_thread(shutil.copyfile, source, workspace / name)
            result = await run_in_cell(
                _code_task, code, name, output_limit,
                timeout=timeout, mem_mb=mem_mb, fsize_mb=fsize_mb,
                work_dir=str(workspace), hold_slot=False,
            )
            files = await asyncio.to_thread(
                _collect_produced_files, workspace, name, max_files, max_file_size)
            return {"output": result["output"], "error": result["error"], "files": files}
        finally:
            # 工作区可能被沙箱代码塞入海量文件，删除同样放到子线程，别卡事件循环
            await asyncio.to_thread(shutil.rmtree, workspace, ignore_errors=True)
