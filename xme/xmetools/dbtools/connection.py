"""数据库连接管理：为 XmeDatabase 的读写方法提供「连接-执行-提交-关闭」包装。

每个被装饰的调用都使用独立的短连接，事务边界即方法边界：
正常返回时提交，异常时回滚并以原异常向上抛出。
"""
import sqlite3
from functools import wraps

from nonebot.log import logger

from xme.xmetools.debugtools import debug_msg


def database_connect(func):
    """装饰器：管理 sqlite3 连接生命周期，并把 cursor 注入被装饰方法的 self 之后。

    Args:
        func (Callable): 首个业务参数为 cursor 的 XmeDatabase 方法

    Returns:
        Callable: 对外不感知 cursor 的包装方法
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # 预置 None，连接建立失败时 except/finally 分支才不会 UnboundLocalError
        connection = None
        try:
            connection = sqlite3.connect(self.db_path)
            cursor = connection.cursor()
            result = func(self, cursor, *args, **kwargs)
            connection.commit()
            return result
        except Exception:
            if connection is not None:
                connection.rollback()
            logger.exception("ERROR: XME 数据库控制出现问题")
            raise
        finally:
            debug_msg("关闭连接")
            if connection is not None:
                try:
                    connection.close()
                except sqlite3.Error:
                    logger.exception("关闭数据库连接失败")
    return wrapper
