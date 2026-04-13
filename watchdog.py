import subprocess
import sys
import time
import signal
import os
import select
import logging
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

    # 控制台输出
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    return logger





def start_process():
    logger.info(f"正在启动子进程 {TARGET_SCRIPT}")

    return subprocess.Popen(
        [sys.executable, "-u", TARGET_SCRIPT],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        cwd=os.getcwd(),
    )


def stop_process():
    global proc
    if proc and proc.poll() is None:
        logger.info("正在终止子进程...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            logger.warning("强制杀死子进程")
            proc.kill()


def handle_sigint(signum, frame):
    global running
    logger.info("检测到用户中断，执行退出...")
    running = False
    stop_process()


# interrupt
signal.signal(signal.SIGINT, handle_sigint)
if os.name == "nt":
    signal.signal(signal.SIGBREAK, handle_sigint)


if __name__ == "__main__":
    logger = setup_logger()
    while running:
        proc = start_process()

        while running and proc.poll() is None:
            rlist, _, _ = select.select([proc.stdout], [], [], 0.5)
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

        RESTART_DELAY = 5
        logger.info(f"{TARGET_SCRIPT} 已退出，将在 {RESTART_DELAY} 秒后重启...\n")
        time.sleep(RESTART_DELAY)

    stop_process()
    logger.info("watchdog 已退出")