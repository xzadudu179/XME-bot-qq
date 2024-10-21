import sqlite3
import traceback
from xme.xmetools import date_tools
from xme.plugins.commands.xme.xme_config import XME_DB_PATH
from .user import User
from nonebot import log
from functools import wraps

class Xme_database:
    """XME 数据库相关类
    """
    DB_PATH = XME_DB_PATH
    def __init__(self) -> None:
        """初始化数据库
        """

    USER_DATAS = (
        "id",
        "name",
        "last_reg_days",
        "coins",
        "permission",
        "bio",
        "inventory",
    )

    def database_control(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            result = False
            try:
                # 初始化局部变量
                # print("初始化")
                connection = sqlite3.connect(self.DB_PATH)
                cursor = connection.cursor()
                # 将变量传递给原始函数
                result = func(self, cursor, *args, **kwargs)
                connection.commit()
            except Exception as ex:
                log.logger.error(f"ERROR: XME 数据库控制出现问题: {ex}\n{traceback.format_exc()}")
                connection.rollback()
                raise type(ex)(ex)
            finally:
                print("关闭连接")
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
                coins INTEGER,
                permission INTEGER DEFAULT 1,
                bio TEXT,
                inventory TEXT
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
        query = query
        print("正在执行语句:\n", query, params)
        cursor.execute(query, params)
        return cursor.fetchall()

    def get_user_info(self, query, search):
        return self.exec_query(f"SELECT * FROM users WHERE {query} = ?", (search,))


    def add_user_info(self, user):
        values = ', '.join(['?' for _ in self.USER_DATAS])
        query_add = ', '.join([data for data in self.USER_DATAS])
        self.exec_query(f'''
                INSERT INTO users ({query_add})
                VALUES ({values})
            ''', (user.id, user.name, user.last_reg_days, user.coins, user.permission, user.bio, str(user.inventory)))


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
            query_add = ''.join([data + " = ?, " for data in self.USER_DATAS[1:]]).strip()[:-1]
            return self.exec_query(f'''
                UPDATE users
                SET {query_add}
                WHERE id = ?
            ''', (user.name, user.last_reg_days, user.coins, user.permission, user.bio, str(user.inventory),
                user.id))
