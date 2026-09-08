"""沙箱安全自检指令：仅限 SUPERUSER，对沙箱执行逃逸与隔离探测并报告结果。"""

import config
from character import get_message
from nonebot import CommandSession
from nonebot.log import logger

from xme.xmetools.bottools import permission
from xme.xmetools.doctools import CommandDoc
from xme.xmetools.msgtools import send_session_msg
from xme.xmetools.plugintools import on_command
from xme.xmetools.sandboxexec import run_code_in_workspace
from xme.xmetools.sandboxtests import CELL_PROFILE, REPO_PROFILE, run_security_audit
from xme.xmetools.sandboxtools import SandboxError, SandboxTimeoutError

from .constants import SANDBOX_TEST_TIMEOUT

RUN_PYTHON_TIMEOUT = 30                  # 沙箱墙钟超时（秒）
RUN_PYTHON_MEM_MB = 768                  # 内存上限（MB），matplotlib + numpy 同 calc 绘图档
RUN_PYTHON_FSIZE_MB = 16                 # 工作区内单文件写入上限（MB），要保存图表
RUN_PYTHON_OUTPUT_LIMIT = 8000           # 捕获 print 输出的最大字符数（超出保留末尾）
RUN_PYTHON_MAX_CODE = 20000              # 代码字符数上限
RUN_PYTHON_MAX_INPUT_SIZE = 20 * 1024 * 1024   # 输入文件大小上限
RUN_PYTHON_MAX_FILES = 10                # 产出文件数量上限
RUN_PYTHON_MAX_FILE_SIZE = 10 * 1024 * 1024    # 产出单文件大小上限

alias = ['沙箱']
__plugin_name__ = 'sandbox'
permissions = ["是 SUPERUSER"]
__plugin_usage__ = CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    usage='[cell|repo]',
    permissions=permissions,
    alias=alias
)

_SECTION_NAMES = {CELL_PROFILE: 'cell 严格空白档', REPO_PROFILE: 'repo 计算档', 'host': '宿主侧复核'}


def _format_report(results: dict[str, list[dict]]) -> str:
    """把自检结果拼成回复文本。"""
    lines = [get_message("plugins", __plugin_name__, 'result_header')]
    total = failed = 0
    for section, checks in results.items():
        if not checks:
            continue
        lines.append(f"\n【{_SECTION_NAMES.get(section, section)}】")
        for check in checks:
            total += 1
            failed += not check["passed"]
            mark = "√" if check["passed"] else "×"
            lines.append(f"{mark} {check['name']}｜{check['detail']}")
    if failed:
        lines.append(get_message("plugins", __plugin_name__, 'has_fail'))
    lines.append(get_message("plugins", __plugin_name__, 'result_footer',
                             total=total, passed=total - failed, failed=failed))
    return "\n".join(lines)


@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda x: True)
@permission(lambda sender: sender.is_superuser, permission_help=permissions)
async def _(session: CommandSession):
    code = session.current_arg_text.strip().lower()
    if not code.strip():
        return send_session_msg(session, "[执行失败：code 不能为空]")
    if len(code) > RUN_PYTHON_MAX_CODE:
        return send_session_msg(session, f"[执行失败：代码过长（>{RUN_PYTHON_MAX_CODE} 字符）]")
    try:
        outcome = await run_code_in_workspace(
            code, None, timeout=RUN_PYTHON_TIMEOUT, mem_mb=RUN_PYTHON_MEM_MB,
            fsize_mb=RUN_PYTHON_FSIZE_MB, output_limit=RUN_PYTHON_OUTPUT_LIMIT,
            max_files=RUN_PYTHON_MAX_FILES, max_file_size=RUN_PYTHON_MAX_FILE_SIZE,
        )
    except SandboxTimeoutError:
        return send_session_msg(session, f"[执行失败：代码执行超时（>{RUN_PYTHON_TIMEOUT}s）]")
    except SandboxError as ex:
        return send_session_msg(session, f"[执行失败：沙箱异常：{ex}]")
    parts = []
    output = outcome["output"].strip()
    error = outcome["error"]
    if output:
        parts.append(f"代码输出：\n{output}")
    if error:
        parts.append(f"代码报错（可修正后重新调用）：\n{error}")
    if not output and not error:
        parts.append("（代码执行完成，没有任何 print 输出）")
    return await send_session_msg(session,"\n".join(parts))
    # await send_session_msg(session, _format_report(results))
