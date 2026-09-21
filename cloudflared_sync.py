"""把仓库内的 cloudflared 配置同步到 /etc/cloudflared/config.yml。

deploy/cloudflared/config.yml 是唯一来源：bot 启动时比对两份内容，一致就什么都不做
（连 sudo 都不调用）；有变化时先做 ingress 校验，再安装并重启 cloudflared。写 /etc 与
重启服务需要 root，走一次性的 sudoers 授权（见 deploy/cloudflared/README.md）。

本机没装 cloudflared（例如开发机）时整体跳过，不影响启动。直接执行本文件可手动同步。
"""
import getpass
import subprocess
from enum import Enum
from pathlib import Path
from shutil import which

SOURCE_PATH = Path("deploy/cloudflared/config.yml")
INSTALLED_PATH = Path("/etc/cloudflared/config.yml")
BACKUP_PATH = Path("deploy/cloudflared/config.before-sync.yml")
SERVICE_NAME = "cloudflared"
SUDO = "/usr/bin/sudo"
INSTALL = "/usr/bin/install"
SYSTEMCTL = "/usr/bin/systemctl"
CLOUDFLARED = "cloudflared"
TIMEOUT_SECS = 60
SUDOERS_FILE = "/etc/sudoers.d/xme-cloudflared"


class SyncStatus(Enum):
    """同步结果。"""
    NOT_APPLICABLE = "本机未使用 cloudflared"
    SOURCE_MISSING = "仓库内配置不存在"
    UP_TO_DATE = "与线上一致，无需同步"
    INVALID = "配置校验不通过，未安装"
    NO_PERMISSION = "缺少 sudoers 授权，未安装"
    FAILED = "同步失败"
    SYNCED = "已同步并重启 cloudflared"


# 启动时不算异常的结果：一致、已同步、本机不适用
OK_STATUSES = frozenset({SyncStatus.UP_TO_DATE, SyncStatus.SYNCED, SyncStatus.NOT_APPLICABLE})


def install_command(source: Path = SOURCE_PATH, target: Path = INSTALLED_PATH) -> list[str]:
    """安装 cloudflared 配置的命令（sudoers 授权与实际调用共用同一份参数，避免两处对不上）。"""
    return [INSTALL, "-m", "644", "-o", "root", "-g", "root",
            str(Path(source).resolve()), str(target)]


def sudoers_line(user: str | None = None,
                 source: Path = SOURCE_PATH,
                 target: Path = INSTALLED_PATH) -> str:
    """生成一次性授权所需的 sudoers 内容（只管这两条命令，不放开 root shell）。"""
    user = user or getpass.getuser()
    install = " ".join(install_command(source, target))
    return f"{user} ALL=(root) NOPASSWD: {install}, {SYSTEMCTL} restart {SERVICE_NAME}\n"


def _read_bytes(path: Path) -> bytes | None:
    """读文件内容；不存在或读不了返回 None。"""
    try:
        return Path(path).read_bytes()
    except OSError:
        return None


def _run(command: list[str]) -> tuple[bool, str]:
    """执行命令，返回 (是否成功, 输出)。"""
    try:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=TIMEOUT_SECS)
    except (OSError, subprocess.SubprocessError) as ex:
        return False, str(ex)
    return proc.returncode == 0, (proc.stdout + proc.stderr).strip()


def _validate(source: Path) -> tuple[bool, str]:
    """用 cloudflared 自带校验检查候选配置。"""
    return _run([CLOUDFLARED, "--config", str(Path(source).resolve()),
                 "tunnel", "ingress", "validate"])


def _install(source: Path, target: Path) -> tuple[bool, str]:
    return _run([SUDO, "-n"] + install_command(source, target))


def _restart_service() -> tuple[bool, str]:
    return _run([SUDO, "-n", SYSTEMCTL, "restart", SERVICE_NAME])


def _write_backup(content: bytes, path: Path) -> None:
    """把同步前的线上配置留一份副本，便于出问题时回滚（写不了就跳过）。"""
    try:
        Path(path).write_bytes(content)
    except OSError:
        pass


def sync_cloudflared_config(source: Path = SOURCE_PATH,
                            target: Path = INSTALLED_PATH) -> tuple[SyncStatus, str]:
    """按仓库配置同步 cloudflared 配置，返回 (结果, 说明)。

    内容一致时不产生任何副作用；本机不适用、配置校验不通过时不安装线上配置。
    """
    if which(CLOUDFLARED) is None or not Path(target).parent.is_dir():
        return SyncStatus.NOT_APPLICABLE, "本机未安装 cloudflared，跳过同步"

    source = Path(source)
    wanted = _read_bytes(source)
    if wanted is None:
        return SyncStatus.SOURCE_MISSING, f"读不到仓库内配置 {source}"

    installed = _read_bytes(target)
    if installed == wanted:
        return SyncStatus.UP_TO_DATE, f"与 {source} 一致"

    ok, output = _validate(source)
    if not ok:
        return SyncStatus.INVALID, f"ingress 校验未通过，已保留线上配置：{output}"

    if installed is not None:
        _write_backup(installed, BACKUP_PATH)

    ok, output = _install(source, target)
    if not ok:
        if "password is required" in output or "not allowed" in output:
            return SyncStatus.NO_PERMISSION, f"需要先做一次性授权（{SUDOERS_FILE}，见 deploy/cloudflared/README.md）"
        return SyncStatus.FAILED, f"安装配置失败：{output}"

    ok, output = _restart_service()
    if not ok:
        return SyncStatus.FAILED, f"配置已更新但 cloudflared 重启失败，请手动 systemctl restart {SERVICE_NAME}：{output}"

    return SyncStatus.SYNCED, f"{source} → {target}"


if __name__ == "__main__":
    status, detail = sync_cloudflared_config()
    print(f"[{status.name}] {status.value}（{detail}）")
    raise SystemExit(0 if status in OK_STATUSES else 1)
