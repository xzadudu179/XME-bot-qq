from concurrent.futures import TimeoutError, ThreadPoolExecutor
import multiprocessing
from functools import wraps
from xme.xmetools.jsontools import read_from_path, change_json
import config
import signal
import asyncio
import copy
multiprocessing.set_start_method('spawn', force=True)

def thread_set_timeout(seconds=10, timeout_message="函数执行超时", callback=None):
    """设置超时装饰器（非大量计算）

    Args:
        seconds (int, optional): 超时秒数. Defaults to 10.
        timeout_message (str, optional): 若未填写回调函数时超时的报错消息. Defaults to "函数执行超时".
        callback (function, optional): 回调函数，参数是被装饰的函数的参数. Defaults to None.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = thread_run_with_timeout(func, seconds, *args, **kwargs)
            except TimeoutError:
                if callback:
                    result = callback(*args, **kwargs)
                else:
                    raise TimeoutError(timeout_message)
            return result
        return wrapper
    return decorator

class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutException("函数执行超时")

def linux_set_timeout(seconds=10, timeout_message="函数执行超时", callback=None):
    """设置 linux 超时装饰器

    Args:
        seconds (int, optional): 超时秒数. Defaults to 10.
        timeout_message (str, optional): 若未填写回调函数时超时的报错消息. Defaults to "函数执行超时".
        callback (function, optional): 回调函数，参数是被装饰的函数的参数. Defaults to None.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(seconds)
                result = func(*args, **kwargs)
            except TimeoutException:
                if callback:
                    result = callback(*args, **kwargs)
                else:
                    raise TimeoutException(timeout_message)
            finally:
                signal.alarm(0)
            return result
        return wrapper
    return decorator

def run_with_timeout(func, timeout_seconds, error_message="函数执行超时", *args, **kwargs):
    """设置函数执行超时

    Args:
        func (function): 需要执行的函数
        timeout_seconds (float): 超时秒数
        error_message (str): 超时报错消息

    Raises:
        TimeoutError: 超时

    Returns:
        Any: 函数结果
    """
    # 使用 multiprocessing.Pool 来执行长时间计算
    print("running....")
    with multiprocessing.Pool(1) as pool:
        result = pool.apply_async(func, args=args, kwds=kwargs)
        try:
            return result.get(timeout=timeout_seconds)  # 获取计算结果，设定超时
        except multiprocessing.TimeoutError:
            pool.terminate()  # 超时后终止进程池
            raise TimeoutError(error_message)

def thread_run_with_timeout(func, timeout_seconds=2, *args, **kwargs):
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func, *args, **kwargs)
        try:
            result = future.result(timeout=timeout_seconds)  # 获取计算结果，设定超时
            return result
        except TimeoutError:
            future.cancel()  # 超时后取消任务
            raise TimeoutError("函数执行超时")