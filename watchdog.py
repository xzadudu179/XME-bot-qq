import subprocess
import sys
import time
import signal
import os
import select
import logging
from xme.xmetools.filetools import backup_data_dir
from xme.xmetools.logtools import ColoredFormatter
from logging.handlers import TimedRotatingFileHandler

TARGET_SCRIPT = "bot.py"

running = True
proc = None


def setup_logger():
    log_dir = "./logs/watchdog"
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger("watchdog")
    logger.setLevel(logging.INFO)

    log_file = os.path.join(log_dir, "watchdog_logs.log")

    handler = TimedRotatingFileHandler(
        log_file,
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8"
    )

    handler.suffix = "%Y-%m-%d"

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s"
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)

    # 控制台输出（文件日志保持纯文本）
    console = logging.StreamHandler()
    console.setFormatter(ColoredFormatter(
        "[%(asctime)s] [%(levelname)s] %(message)s"
    ))
    logger.addHandler(console)

    return logger





if os.name != "nt":
    import ctypes

    _LIBC = ctypes.CDLL("libc.so.6", use_errno=True)

    def _set_pdeathsig():
        # PR_SET_PDEATHSIG：父进程死亡时由内核向子进程发 SIGINT。
        # watchdog 被 kill -9 或随终端关闭（SIGHUP）退出时，已脱离终端信号组的
        # bot 仍能收到中断走优雅退出，不会变成无人监管的孤儿进程（否则再次
        # start.sh 会撞端口 / 双实例写同一 sqlite）
        _LIBC.prctl(1, signal.SIGINT, 0, 0, 0)  # PR_SET_PDEATHSIG = 1


def start_process():
    logger.info(f"正在启动子进程 {TARGET_SCRIPT}")

    # 子进程独立成组/会话：终端 Ctrl+C 只会送到 watchdog，由二次确认逻辑决定
    # 是否转发给子进程。否则第一次 Ctrl+C 就直达 bot.py（nonebot 收到 SIGINT
    # 直接退出），确认窗口内的"忽略中断"形同虚设，还触发无谓的崩溃重启
    group_kw = {"start_new_session": True, "preexec_fn": _set_pdeathsig}
    if os.name == "nt":
        # Windows 无 prctl 等价物（Job Object 未实现）；当前部署均在 Linux
        group_kw = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}

    return subprocess.Popen(
        [sys.executable, "-u", TARGET_SCRIPT],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        cwd=os.getcwd(),
        **group_kw,
    )


def stop_process():
    global proc
    if proc and proc.poll() is None:
        logger.info("正在终止子进程...")
        # 子进程已不在终端信号组里，必须显式转发 SIGINT 走 nonebot 的优雅退出
        # （会话快照落盘、连接正常关闭），无响应再逐级升级 terminate/kill
        proc.send_signal(signal.SIGINT if os.name != "nt" else signal.CTRL_BREAK_EVENT)
        try:
            proc.wait(timeout=8)
            return
        except subprocess.TimeoutExpired:
            logger.warning("子进程未响应中断信号，升级为 terminate")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            logger.warning("强制杀死子进程")
            proc.kill()


def _read_active_sessions() -> int:
    """运行中的会话数 = AI 会话数（aistop 落盘）+ 运行中的指令会话数（plugintools 落盘）。

    两个文件都由 bot 进程 best-effort 维护，读不到按 0 处理。
    """
    total = 0
    for name in (".ai_active_turns", ".nb_active_sessions"):
        try:
            with open(os.path.join(os.getcwd(), "data", name), encoding="utf-8") as f:
                total += max(0, int(f.read().strip() or 0))
        except Exception:
            pass
    return total


_CONFIRM_WINDOW_SECS = 10
_confirm_deadline = 0.0


def handle_sigint(signum, frame):
    global running, _confirm_deadline
    active = _read_active_sessions()
    if active > 0 and time.time() >= _confirm_deadline:
        # 有会话运行（AI 对话 / 指令处理）：第一次中断只提示，窗口期内再次中断才真正退出
        # （不阻塞信号处理器：靠"窗口期内二次确认"机制，而非 input/sleep）
        _confirm_deadline = time.time() + _CONFIRM_WINDOW_SECS
        logger.warning(
            f"检测到 {active} 个运行中的会话（AI 对话/指令），现在退出会打断它们"
            f"（AI 对话重启后可 /ai --continue 恢复）。"
            f"{_CONFIRM_WINDOW_SECS} 秒内再按一次 Ctrl+C 确认退出，否则本次中断将被忽略")
        return
    logger.info("检测到用户中断，执行退出...")
    running = False
    stop_process()


# interrupt
signal.signal(signal.SIGINT, handle_sigint)
if os.name == "nt":
    signal.signal(signal.SIGBREAK, handle_sigint)


if __name__ == "__main__":
    logger = setup_logger()
    logger.info(f"BOT 数据已备份至 {backup_data_dir()}")
    # 重启退避：启动阶段连续崩溃（配置错/端口占用等）时固定 5s 重启会形成
    # 重启风暴刷爆日志；连续异常退出按 5→10→…→300s 递增，子进程稳定运行
    # STABLE_SECS 后计数复位
    BASE_DELAY = 5
    MAX_DELAY = 300
    STABLE_SECS = 1800
    consecutive_failures = 0
    while running:
        start_time = time.time()
        proc = start_process()

        while running and proc.poll() is None:
            rlist, *_ = select.select([proc.stdout], [], [], 0.5)
            if not rlist:
                continue

            line = proc.stdout.readline()
            if not line:
                continue

            # 子进程输出
            print(line.strip())

        if not running:
            break

        ret = proc.poll()
        if ret == 0:
            logger.info(f"{TARGET_SCRIPT} 正常退出")
        else:
            logger.error(f"{TARGET_SCRIPT} 异常退出，返回码: {ret}")

        if time.time() - start_time >= STABLE_SECS:
            consecutive_failures = 0
        restart_delay = min(BASE_DELAY * (2 ** consecutive_failures), MAX_DELAY)
        consecutive_failures += 1
        logger.info(f"{TARGET_SCRIPT} 已退出，将在 {restart_delay:.0f} 秒后重启"
                    f"（连续异常 {consecutive_failures} 次）...")
        time.sleep(restart_delay)

    stop_process()
    logger.info("watchdog 已退出")