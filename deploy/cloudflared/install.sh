#!/bin/sh
# 一次性以 root 运行：授权 bot 进程把仓库内的 cloudflared 配置同步到 /etc 并重启 cloudflared。
# 用法：sudo bash deploy/cloudflared/install.sh
set -eu

if [ "$(id -u)" != "0" ]; then
    echo "请用 sudo 运行：sudo bash $0" >&2
    exit 1
fi

REPO=$(cd "$(dirname "$0")/../.." && pwd)
TARGET_USER=${SUDO_USER:-$(id -un)}
DROPIN=/etc/sudoers.d/xme-cloudflared

# 需要 3.10+（模块用了 X | None、list[str] 语法），系统 python3 不一定是；优先用 bot 自己的 venv
PY=$REPO/venv/bin/python3
if [ ! -x "$PY" ]; then
    PY=$(command -v python3.11 || command -v python3.12 || command -v python3 || true)
fi
if [ ! -x "$PY" ]; then
    echo "找不到可用的 python（需要 3.10+）" >&2
    exit 1
fi

# sudoers 内容由 cloudflared_sync 生成，保证与 bot 实际调用的命令参数完全一致
# （-B 不写 pycache，避免 root 在仓库里留下 __pycache__）
LINE=$("$PY" -B -c "import sys; sys.path.insert(0, sys.argv[1]); from cloudflared_sync import sudoers_line; sys.stdout.write(sudoers_line(sys.argv[2]))" "$REPO" "$TARGET_USER")

# 先写到不带点号的临时文件校验，语法不过就不落地（避免写坏 sudoers）
printf '%s\n' "$LINE" > "$DROPIN-new"
chmod 440 "$DROPIN-new"
if ! visudo -c -f "$DROPIN-new" >/dev/null; then
    echo "生成的 sudoers 语法不通过，已放弃（$DROPIN-new）" >&2
    exit 1
fi
mv "$DROPIN-new" "$DROPIN"

echo "已写入 $DROPIN："
printf '%s\n' "$LINE"
echo "下次 bot 启动会自动同步；想立刻生效：$PY -B $REPO/cloudflared_sync.py"
