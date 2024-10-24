import sqlite3
import traceback
from xme.plugins.commands.xme.xme_config import XME_DB_PATH
from nonebot import log
from functools import wraps
import pickle

class Xme_database:
    """XME 数据库相关类
    """
    DB_PATH = XME_DB_PATH
    def __init__(self) -> None:
        """初始化数据库
        """

    def database_connect(func):
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

    def init_faction_info(self):
        """初始化阵营信息
        """
        self.exec_query('''
            CREATE TABLE IF NOT EXISTS factions (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                desc TEXT,
                relations TEXT,
                users TEXT,
                prices TEXT,
                creator INTEGER,
            )
        ''')

    def save_to_db(self, obj, name=''):
        """将类存储至表

        Args:
            name (str): 表名
            obj (Any): 自定义类
        """
        if obj == None: raise ValueError("类不可是 None")
        if not name:
            name = type(obj).__name__.lower()
        # 获取类的字段和值
        fields = [field for field in obj.__dict__.keys() if field != 'database']  # 获取所有字段名 除了 database
        values = [value if isinstance(value, (str, int)) else pickle.dumps(value) for key, value in obj.__dict__.items() if key != 'database' and not callable(value)]
        columns = ', '.join(fields)
        placeholders = ', '.join(['?'] * len(fields))
        sql = f"INSERT OR REPLACE INTO {name} ({columns}) VALUES ({placeholders})"
        self.exec_query(sql, tuple(values))

    @database_connect
    def load_from_db(self, cursor, id, table_name='', type=None) -> dict:
        """通过表名和 id 获取内容

        Args:
            table_name (str): 表名
            id (int): id

        Returns:
            dict: 类型参数数据
        """
        if not table_name and not type:
            raise ValueError("必须指定类型或者表名")
        if not table_name:
            table_name = type.__name__.lower()
        sql = f"SELECT * FROM {table_name} WHERE id = ?"
        print("正在通过语句加载内容:\n", sql, (id,))
        cursor.execute(sql, (id,))
        row = cursor.fetchone()
        if not row: return None
        # 获取列信息
        columns = [column[0] for column in cursor.description]
        data_dict = dict(zip(columns, row))
        # 寻找 BLOB 数据并且反序列化
        for column in columns:
            if isinstance(data_dict[column], bytes):
                print(f"反序列化字段 {column}\n{data_dict[column]}")
                data_dict[column] = pickle.loads(data_dict[column])  # 反序列化
        # print(data_dict)
        data_dict['database'] = self
        return data_dict

    def create_table(self, obj, name=''):
        """通过类创建表

        Args:
            name (str): 表名
            obj (Any): 类
        """
        if obj == None: raise ValueError("类不可是 None")
        if not name:
            name = type(obj).__name__.lower()
        print(f"初始化表 {name} 中...")
        # print(obj.__dict__.items())
        fields = {k: v for k, v in obj.__dict__.items() if k != 'id' and k != 'database'}
        types = ['TEXT' if isinstance(value, str) else 'INTEGER' if isinstance(value, int) else 'BLOB' for value in fields.values()]
        columns = ', '.join([f"{field} {ftype}" for field, ftype in zip(fields.keys(), types)])
        sql = f"CREATE TABLE IF NOT EXISTS {name} (id INTEGER PRIMARY KEY, {columns})"
        self.exec_query(sql)

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

    @database_connect
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
