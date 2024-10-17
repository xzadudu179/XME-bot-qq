import sqlite3
from xme.xmetools import date_tools
from nonebot import log

class Xme_database:
    """XME 数据库相关类
    """
    def __init__(self, db_path) -> None:
        """初始化数据库
        """
        self.db_path = "./data/xme/xme.db"

    def database_control(self, func):
        def wrapper(*args, **kwargs):
            try:
                # 初始化局部变量
                connection = sqlite3.connect(self.db_path)
                cursor = connection.cursor()
                # 将变量传递给原始函数
                result = func(cursor, *args, **kwargs)
                connection.commit()
            except Exception as ex:
                log.logger.error(f"ERROR: XME 注册/签到出现问题: {ex}\n{ex.with_traceback()}")
                connection.rollback()
            finally:
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
    def save_user_info(self, cursor, user):
        """保存用户数据 (还没写完)

        Args:
            cursor (Cursor): 数据库 cursor
            user (User): 用户数据
        """
        # cursor.execute('''
        #     UPDATE users
        #     SET last_reg_days = ?, coins = ?
        #     WHERE id = ?
        # ''', (date_tools.curr_days(), coins, user_id))