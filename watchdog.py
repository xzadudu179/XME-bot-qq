import subprocess
import sys
import time
import signal
import os

TARGET_SCRIPT = "bot.py"

running = True
proc = None


def start_process():
    print(f"正在启动子进程 {TARGET_SCRIPT}")

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
        print("正在终止子进程...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            print("强制杀死子进程")
            proc.kill()


def handle_sigint(signum, frame):
    global running
    print("\n检测到用户中断，执行退出...")
    running = False
    stop_process()


# interrupt
signal.signal(signal.SIGINT, handle_sigint)
if os.name == "nt":
    signal.signal(signal.SIGBREAK, handle_sigint)


if __name__ == "__main__":
    while running:
        proc = start_process()
        while running and proc.poll() is None:
            line = proc.stdout.readline()
            if line:
                print(line.strip())
            else:
                time.sleep(0.0001)

        if not running:
            break

        RESTART_DELAY = 5
        print(f"{TARGET_SCRIPT} 已退出，将在 {RESTART_DELAY} 秒后重启...\n")
        time.sleep(RESTART_DELAY)

    stop_process()