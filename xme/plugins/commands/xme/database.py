import sqlite3
from xme.xmetools import date_tools
from nonebot import log
from functools import wraps

class Xme_database:
    """XME 数据库相关类
    """
    def __init__(self, db_path) -> None:
        """初始化数据库
        """
        self.db_path = "./data/xme/xme.db"

    def database_control(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                # 初始化局部变量
                print("初始化")
                connection = sqlite3.connect(self.db_path)
                cursor = connection.cursor()
                # 将变量传递给原始函数
                result = func(self, cursor, *args, **kwargs)
                connection.commit()
            except Exception as ex:
                log.logger.error(f"ERROR: XME 注册/签到出现问题: {ex}\n{ex.with_traceback()}")
                connection.rollback()
            finally:
                print("连接结束，关闭连接")
                connection.close()
                return result
        return wrapper

    @database_control
    def init_user_info(self, cursor):
        """初始化用户信息

        Args:
            cursor (Cursor): 数据库 cursor
        """
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                last_reg_days INTEGER,
                coins INTEGER
            )
        ''')

    @database_control
    def exec_query(self, cursor, query, params=()):
        """查询数据库内容

        Args:
            query (str): 查询sql语句
            params (tuple, optional): 查询占位符所对应内容. Defaults to ().

        Returns:
            list[tuple]: 查询结果
        """
        cursor.execute(query, params)
        return cursor.fetchall()

    def save_user_info(self, user):
        """保存用户数据 (还没写完)

        Args:
            cursor (Cursor): 数据库 cursor
            user (User): 用户数据
        """
        self.exec_query('''
            UPDATE users
            SET last_reg_days = ?, coins = ?
            WHERE id = ?
        ''', (user.last_reg_days, user.coins, user.id))