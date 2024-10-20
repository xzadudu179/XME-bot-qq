import sqlite3
import traceback
from xme.xmetools import date_tools
from .user import User
from nonebot import log
from functools import wraps

class Xme_database:
    """XME 数据库相关类
    """
    def __init__(self, db_path) -> None:
        """初始化数据库
        """
        self.db_path = "./data/xme/xme.db"

    USER_DATAS = (
        "id",
        "name",
        "last_reg_days",
        "coins"
    )

    def database_control(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            result = None
            try:
                # 初始化局部变量
                # print("初始化")
                connection = sqlite3.connect(self.db_path)
                cursor = connection.cursor()
                # 将变量传递给原始函数
                result = func(self, cursor, *args, **kwargs)
                connection.commit()
            except Exception as ex:
                log.logger.error(f"ERROR: XME 数据库控制出现问题: {ex}\n{traceback.format_exc()}")
                connection.rollback()
                raise type(ex)(ex)
            finally:
                print("连接结束，关闭连接")
                connection.close()
                return result
        return wrapper


    def init_user_info(self):
        """初始化用户信息
        """
        self.exec_query('''
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
        print("正在执行语句:\n", query, params)
        cursor.execute(query, params)
        return cursor.fetchall()

    def get_user_info(self, query, search):
        return self.exec_query(f"SELECT * FROM users WHERE {query} = ?", (search,))


    def add_user_info(self, user):
        self.exec_query(f'''
                INSERT INTO users ({self.USER_DATAS[0]}, {self.USER_DATAS[1]}, {self.USER_DATAS[2]}, {self.USER_DATAS[3]})
                VALUES (?, ?, ?, ?)
            ''', (user.id, user.name, user.last_reg_days, user.coins))


    def save_user_info(self, user):
        """保存用户数据

        Args:
            cursor (Cursor): 数据库 cursor
            user (User): 用户数据
        """
        if len(self.get_user_info("id", user.id)) < 1:
            # 没有数据就插入数据
            self.add_user_info(user)
        else:
            self.exec_query(f'''
                UPDATE users
                SET {self.USER_DATAS[2]} = ?, {self.USER_DATAS[3]} = ?
                WHERE id = ?
            ''', (user.last_reg_days, user.coins,
                user.id))
