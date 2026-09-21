#!/bin/sh
# 构建 mai-arcade（舞萌机台协议工具，独立 Go 项目）并安装到 bot 的 bin/。
#
# 源码位置优先级：$MAI_ARCADE_SRC > 默认 ../mai-arcade；目录不存在时用 $MAI_ARCADE_REPO 克隆。
# 该工具零第三方依赖，构建是秒级的，所以部署时现场构建即可，不需要预编译产物进库。
#
# 用法：
#   ./scripts/build_arcade.sh                        # 用默认路径
#   MAI_ARCADE_SRC=~/src/maimai-arcade ./scripts/build_arcade.sh
#   MAI_ARCADE_REPO=git@github.com:you/maimai-arcade.git ./scripts/build_arcade.sh
set -e

BOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${MAI_ARCADE_SRC:-$(dirname "$BOT_DIR")/mai-arcade}"
REPO="${MAI_ARCADE_REPO:-}"
DEST="$BOT_DIR/bin/mai-arcade"

if [ ! -d "$SRC" ]; then
    if [ -z "$REPO" ]; then
        echo "找不到 Go 源码目录：$SRC" >&2
        echo "设置 MAI_ARCADE_SRC 指向已有源码，或用 MAI_ARCADE_REPO 指定仓库地址自动克隆。" >&2
        exit 1
    fi
    echo "克隆 $REPO → $SRC"
    git clone --depth 1 "$REPO" "$SRC"
fi

if [ -d "$SRC/.git" ]; then
    echo "更新源码：$SRC"
    # 有本地改动或非快进时跳过更新，不阻断部署
    git -C "$SRC" pull --ff-only --quiet || echo "（跳过更新：有本地改动或无法快进）"
fi

echo "构建中（零依赖，秒级）..."
make -C "$SRC" release

mkdir -p "$BOT_DIR/bin"
cp "$SRC/bin/mai-arcade-linux-amd64" "$DEST"
chmod +x "$DEST"
echo "已安装：$DEST"

echo "连通性自检（需要网络）："
"$DEST" probe 2>/dev/null || echo "（自检未通过，部署后可用 mai-arcade probe 单独排查）"
