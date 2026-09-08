"""沙箱代码执行工具：对文件的副本运行 AI 编写的 Python 分析代码。"""

from pathlib import Path

from xme.xmetools.filetools import bytes_to_file
from xme.xmetools.sandboxexec import run_code_in_workspace
from xme.xmetools.sandboxtools import SandboxError, SandboxTimeoutError
from ..constants import (
    RUN_PYTHON_FSIZE_MB, RUN_PYTHON_MAX_CODE, RUN_PYTHON_MAX_FILE_SIZE,
    RUN_PYTHON_MAX_FILES, RUN_PYTHON_MAX_INPUT_SIZE, RUN_PYTHON_MEM_MB,
    RUN_PYTHON_OUTPUT_LIMIT, RUN_PYTHON_TIMEOUT,
)


async def run_python(code: str, ref: str = "", agent=None):
    """在一次性沙箱工作区内执行 code 分析 ref 文件的副本，回传输出与产出文件。

    原文件只被父进程复制进临时工作区，路径不进沙箱，代码无法改动原文件；
    代码经全局变量 INPUT_FILE 拿到副本文件名，print 输出即分析结果，
    保存到工作区的文件（如图表）会被回收为可发送的引用。
    """
    if not code.strip():
        return {"result": "[执行失败：code 不能为空]", "no_compress": True}
    if len(code) > RUN_PYTHON_MAX_CODE:
        return {"result": f"[执行失败：代码过长（>{RUN_PYTHON_MAX_CODE} 字符）]", "no_compress": True}
    if ref:
        if agent is None:
            return {"result": "[执行失败：缺少会话上下文，无法解析文件引用]", "no_compress": True}
        try:
            input_path = Path(agent.resolve_ref(ref))
        except KeyError:
            return {"result": f"[执行失败：没有找到引用 {ref}]", "no_compress": True}
        if not input_path.is_file():
            return {"result": f"[执行失败：引用 {ref} 指向的不是普通文件]", "no_compress": True}
        if input_path.stat().st_size > RUN_PYTHON_MAX_INPUT_SIZE:
            return {"result": f"[执行失败：输入文件过大（>{RUN_PYTHON_MAX_INPUT_SIZE // 1024 // 1024} MB）]",
                    "no_compress": True}
    else:
        input_path = None
    try:
        outcome = await run_code_in_workspace(
            code, input_path, timeout=RUN_PYTHON_TIMEOUT, mem_mb=RUN_PYTHON_MEM_MB,
            fsize_mb=RUN_PYTHON_FSIZE_MB, output_limit=RUN_PYTHON_OUTPUT_LIMIT,
            max_files=RUN_PYTHON_MAX_FILES, max_file_size=RUN_PYTHON_MAX_FILE_SIZE,
        )
    except SandboxTimeoutError:
        return {"result": f"[执行失败：代码执行超时（>{RUN_PYTHON_TIMEOUT}s）]", "no_compress": True}
    except SandboxError as ex:
        return {"result": f"[执行失败：沙箱异常：{ex}]", "no_compress": True}
    parts = []
    output = outcome["output"].strip()
    error = outcome["error"]
    if output:
        parts.append(f"代码输出：\n{output}")
    if error:
        parts.append(f"代码报错（可修正后重新调用）：\n{error}")
    if not output and not error:
        parts.append("（代码执行完成，没有任何 print 输出）")
    if outcome["files"]:
        if agent is None:
            parts.append(f"产出文件 {len(outcome['files'])} 个（缺少会话上下文，未保存）")
        else:
            saved = []
            for file_name, data in outcome["files"].items():
                try:
                    res = bytes_to_file(data, agent.user_id, Path(file_name).suffix or ".bin", agent)
                    saved.append(f"{file_name}（引用 {res['ref']}，可经 send_file 发送）")
                except FileExistsError:
                    saved.append(f"{file_name}（与已有文件内容相同，未重复保存）")
            parts.append("产出文件：" + "；".join(saved))
    return {"result": "\n".join(parts)}
