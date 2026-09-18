# flock 单实例：误跑两份会双 bot 同时连 QQ、并发写同一 sqlite
exec 9>./.watchdog.lock
if ! flock -n 9; then
    echo "watchdog 已在运行（./.watchdog.lock 被占用），拒绝重复启动"
    exit 1
fi
source ./venv/bin/activate
python3.11 watchdog.py
