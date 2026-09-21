"""调用机台协议工具（独立 Go 项目 mai-arcade）的唯一入口。

只做封装：起进程、经 stdin 传二维码、收 stdout 的 JSON 信封、判退出码。
不产生任何文案——失败文案由命令层按 error.code 或退出码映射。

契约（由工具侧保证，有测试强制）：
    * 二维码走 stdin，位置参数会被拒绝；凭证走 --fish-token
    * stdout 只有一行 JSON：{"ok":bool, "command":str, "data":{}, "error":{}}
    * 日志走 stderr；退出码 0 成功 / 1 业务 / 2 网络或阻断 / 3 参数
"""

import asyncio
import json
from dataclasses import dataclass, field

import config
from nonebot.log import logger

from . import constants

# 工具未能给出结果时的 error.code（与工具自身的 code 区分开）
TOOL_MISSING = 'tool_missing'
TOOL_TIMEOUT = 'timeout'
TOOL_BAD_OUTPUT = 'bad_output'


@dataclass
class ArcadeResult:
    """一次外部调用的结果。

    exit_code 与 ok 要一起看：工具的 --help 之类会 ok=false 但退出码为 0。
    """

    exit_code: int = -1
    ok: bool = False
    data: dict = field(default_factory=dict)
    error: dict = field(default_factory=dict)
    stderr: str = ""

    @property
    def code(self) -> str:
        """失败原因：优先用工具给的 error.code。"""
        return self.error.get('code', '')


async def run(command: str, sgid: str, credential: str = "",
              path: str = "", timeout: int = constants.ARCADE_TIMEOUT) -> ArcadeResult:
    """调用 mai-arcade 的子命令，二维码经 stdin 传入。

    Args:
        command (str): 子命令名，见 constants.ARCADE_SYNC_COMMAND
        sgid (str): 机台二维码内容
        credential (str): 查分器凭证（水鱼为 Import-Token），为空则不传
        path (str): 二进制路径，为空取 config.MAI_ARCADE_PATH
        timeout (int): 墙钟超时秒数

    Returns:
        ArcadeResult: 总是返回结果对象；进程起不来或超时时 error.code 为本模块的 TOOL_* 值
    """
    argv = [path or config.MAI_ARCADE_PATH, command]
    if credential:
        argv += ['--fish-token', credential]

    try:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except OSError as ex:
        logger.warning(f"无法启动 mai-arcade（{argv[0]}）：{ex}")
        return ArcadeResult(error={'code': TOOL_MISSING, 'message': str(ex)})

    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(sgid.encode('utf-8')), timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        logger.warning(f"mai-arcade {command} 超过 {timeout} 秒未完成，已终止")
        return ArcadeResult(error={'code': TOOL_TIMEOUT, 'message': f'超过 {timeout} 秒未完成'})

    result = parse_output(stdout.decode('utf-8', 'replace'), proc.returncode or 0)
    result.stderr = stderr.decode('utf-8', 'replace').strip()
    return result


def parse_output(stdout: str, exit_code: int = 0) -> ArcadeResult:
    """解析工具输出的单行 JSON 信封（纯函数，便于单测）。"""
    text = stdout.strip()
    if not text:
        return ArcadeResult(exit_code=exit_code,
                            error={'code': TOOL_BAD_OUTPUT, 'message': '工具没有输出任何内容'})
    line = text.splitlines()[-1]
    try:
        envelope = json.loads(line)
    except json.JSONDecodeError:
        return ArcadeResult(exit_code=exit_code,
                            error={'code': TOOL_BAD_OUTPUT, 'message': line[:120]})
    if not isinstance(envelope, dict):
        return ArcadeResult(exit_code=exit_code,
                            error={'code': TOOL_BAD_OUTPUT, 'message': line[:120]})
    return ArcadeResult(
        exit_code=exit_code,
        ok=bool(envelope.get('ok')),
        data=envelope.get('data') or {},
        error=envelope.get('error') or {},
    )


def failure_key(result: ArcadeResult) -> str:
    """把失败结果映射到文案键：先按 error.code 精确匹配，再按退出码兜底。"""
    key = constants.ARCADE_CODE_KEYS.get(result.code)
    if key:
        return key
    return constants.ARCADE_EXIT_KEYS.get(result.exit_code, constants.ARCADE_FALLBACK_KEY)
