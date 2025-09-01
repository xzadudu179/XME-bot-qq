import sqlite3
import traceback
from nonebot import log
from functools import wraps
from typing import Protocol, TypeVar, Type, Union
from typing import Any, get_type_hints
from typing import get_origin, get_args
import json

T_DbReadWriteable = TypeVar("T", bound="DbReadWriteable")
class DbReadWriteable(Protocol):
    @classmethod
    def form_dict(data: dict) -> T_DbReadWriteable:
        """由 dict 转换为类

        Args:
            data (dict): 类的 dict 数据
        """
        ...

    def get_table_name():
        ...

    def to_dict(self):
        ...

# class DbTypeParser:

#     @staticmethod

class XmeDatabase:
    """XME 数据库相关类
    """
    db_path = ''
    def __init__(self, db_path='./data/xme/xme.db') -> None:
        """初始化数据库
        """
        self.db_path = db_path

    # def get_class_table_name(cls: type[object]):
    #     return cls.__name__

    # def get_instance_class_table_name(cls_instance: object):
    #     return cls_instance.__class__.__name__

    def get_class_typing_hints(cls: type[T_DbReadWriteable]):
        hints = get_type_hints(cls)
        fields = {name: hints.get(name, Any) for name in vars(cls) if not name.startswith("__")}
        return fields

    def remove(self, table_name, condition):
        self.exec_query(query=f"DELETE FROM {table_name} WHERE {condition}")

    def create_class_table(self, cls: T_DbReadWriteable):
        table_name = cls.__class__.get_table_name()
        fields = {k: v for k, v in cls.to_dict().items() if k != 'id' and k != 'database'}
        # types = ['TEXT' if isinstance(value, str) else 'INTEGER' if isinstance(value, int) else 'BLOB' for value in fields.values()]
        self.create_table_from_values(table_name, fields.keys(),  fields.values())
        # for field, py_type in annotations.items():
        #     sql_type = XmeDatabase.python_type_to_sql(py_type)
        #     columns.append(f"{field} {sql_type}")

        # sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(columns)});"
        # self.exec_query(sql)
        return table_name


    # def save_class(cls_example: T_DbReadWriteable):
    #     table = cls_example.get_table_name()

    def python_type_to_sql(self, py_type):
        """
        把 Python 注解类型转成 SQLite 类型
        """
        if get_origin(py_type) is Union:
            raise TypeError(f"请勿使用联合类型：{py_type}")

        mapping = {
            int: "INTEGER",
            float: "REAL",
            str: "TEXT",
            bytes: "BLOB",
            bytearray: "BLOB",
            list: "TEXT",
            dict: "TEXT",
            T_DbReadWriteable: "INTEGER"
        }

        if py_type == T_DbReadWriteable:
            self.create_class_table(py_type)
        t_result = mapping.get(py_type, None)
        if t_result is None:
            raise TypeError(f"无法解析类型：{py_type}")
        return t_result

    def database_connect(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            result = False
            try:
                # 初始化局部变量
                # print("初始化")
                connection = sqlite3.connect(self.db_path)
                cursor = connection.cursor()
                # 将变量传递给原始函数
                result = func(self, cursor, *args, **kwargs)
                connection.commit()
                return result
            except Exception as ex:
                if connection:
                    connection.rollback()
                log.logger.error(f"ERROR: XME 数据库控制出现问题: {ex}\n{traceback.format_exc()}")
                raise
            finally:
                print("关闭连接")
                connection.close()
        return wrapper

    def create_table_from_values(self, name, keys, values):
        adapt_values = [self.adapt_value(v) for v in values]
        types = []
        for v in adapt_values:
            if v is None:
                t = "TEXT"  # 默认兜底（也可以记成 NULLABLE）
            elif isinstance(v, int):
                t = "INTEGER"
            elif isinstance(v, float):
                t = "REAL"
            elif isinstance(v, (bytes, bytearray)):
                t = "BLOB"
            else:
                t = "TEXT"
            types.append(t)

        column_defs = ', '.join(f"{f} {t}" for f, t in zip(keys, types))
        create_sql = f"CREATE TABLE IF NOT EXISTS {name} (id INTEGER PRIMARY KEY, {column_defs})"
        self.exec_query(create_sql)

    def adapt_value(self, value: Any) -> Any:
        """解析给定的类型是否能存入数据库

        Args:
            value (Any): 类型

        Raises:
            ValueError: 无法存入

        Returns:
            Any: 能够直接存入数据库的类型
        """
        if value is None: return None
        if isinstance(value, (str, int, float, bytes, bytearray)): return value
        if isinstance(value, bool): return int(value)
        if isinstance(value, (list, dict)): return json.dumps(value)
        if isinstance(value, T_DbReadWriteable): return self.save_to_db(value)
        if hasattr(value, "isoformat"): return value.isoformat()
        raise ValueError(f"无法解析类型 {type(value).__name__}")

    @database_connect
    def save_to_db(self, cursor, obj: T_DbReadWriteable) -> int | None:
        """将类实例存储至数据库

        Args:
            obj (Any): 自定义类

        Returns:
            int | None: 实例的主键
        """
        if obj == None: raise ValueError("类不可是 None")
        # if not name:
            # name = XmeDatabase.get_instance_class_table_name(obj)
        # 获取类的字段和值
        print("save to DBDBDBDBDBDBDDBDBDBDBDBDB")
        data = obj.to_dict()
        fields = [field for field in data.keys() if field not in ('id', 'database')]  # 获取所有字段名
        values = [self.adapt_value(data[k]) for k in fields]
        # 顺便新建表（如果没有的话）
        table_name = self.create_class_table(obj)
        columns = ', '.join(fields)
        placeholders = ', '.join(['?'] * len(fields))

        sql = f"""INSERT OR REPLACE INTO {table_name} ({columns}) VALUES ({placeholders}) ON CONFLICT(id) DO UPDATE SET name = excluded.name, value = excluded.value;"""
        cursor.execute(sql, tuple(values))
        return cursor.lastrowid
        # self.exec_query(sql, tuple(values))

    def load_class(self, select_keys, query, table_name='', cl: Type[T_DbReadWriteable]=None) -> T_DbReadWriteable:
        d = self.load_from_db(select_keys=select_keys, table_name=table_name, type=cl, query=query)
        if d is None:
            return None
        return cl.form_dict(d)

    @database_connect
    def load_from_db(self, cursor, select_keys: tuple[str], table_name='', type=None, query="SELECT * FROM {table_name} WHERE id = ?") -> dict | None:
        """通过表名和 id 获取内容

        Args:
            select_keys (tuple[str]): 需要查询的键占位符实际值元组
            table_name (str): 表名
            type (type): 指定的类型
            id (int): id

        Returns:
            dict: 类型参数数据
        """
        if not table_name and not type:
            raise ValueError("必须指定类型或者表名")
        if not table_name:
            table_name = type.__name__.lower()
        # sql = f"SELECT * FROM {table_name} WHERE id = ?"
        sql = query.format(table_name=table_name)
        print("正在通过语句加载内容:\n", sql, select_keys)
        cursor.execute(sql, select_keys)
        row = cursor.fetchone()
        if not row: return None
        # 获取列信息
        # columns = [column[0] for column in cursor.description]
        # data_dict = dict(zip(columns, row))
        data_dict = XmeDatabase.get_dict_data(cursor, row)

        # data_dict['database'] = self
        return data_dict

    def get_dict_data(cursor, datas: tuple):
        columns = [column[0] for column in cursor.description]
        data_dict = dict(zip(columns, datas))

        # data_dict['database'] = self
        return data_dict

    # def create_table(self, obj: T_DbReadWriteable, name=''):
    #     """通过类创建表

    #     Args:
    #         name (str): 表名
    #         obj (Any): 类
    #     """
    #     if obj == None: raise ValueError("类不可是 None")
    #     if not name:
    #         name = XmeDatabase.get_instance_class_table_name(obj)
    #     print(f"初始化表 {name} 中...")
    #     # print(obj.__dict__.items())
    #     fields = {k: v for k, v in obj.to_dict().items() if k != 'id' and k != 'database'}
    #     types = ['TEXT' if isinstance(value, str) else 'INTEGER' if isinstance(value, int) else 'BLOB' for value in fields.values()]
    #     columns = ', '.join([f"{field} {ftype}" for field, ftype in zip(fields.keys(), types)])
    #     sql = f"CREATE TABLE IF NOT EXISTS {name} (id INTEGER PRIMARY KEY, {columns})"
    #     self.exec_query(sql)

    # def init_user_info(self):
    #     """初始化用户信息
    #     """
    #     self.exec_query('''
    #         CREATE TABLE IF NOT EXISTS users (
    #             id INTEGER PRIMARY KEY,
    #             name TEXT NOT NULL,
    #             last_reg_days INTEGER,
    #             coins INTEGER,
    #             permission INTEGER DEFAULT 1,
    #             bio TEXT,
    #             inventory TEXT
    #         )
    #     ''')

    @database_connect
    def exec_query(self, cursor, query, params=(), dict_data=False) -> list[tuple | dict]:
        """查询数据库内容

        Args:
            query (str): 查询sql语句
            params (tuple, optional): 查询占位符所对应内容. Defaults to ().
            dict_data (bool): 是否返回字典数据而非元组. Defaults to False

        Returns:
            list[tuple]: 查询结果
        """
        query = query
        print("正在执行语句:\n", query, params)
        cursor.execute(query, params)
        if not dict_data:
            return cursor.fetchall()
        return [XmeDatabase.get_dict_data(cursor, r) for r in cursor.fetchall()]

    # def get_user_info(self, query, search):
    #     return self.exec_query(f"SELECT * FROM users WHERE {query} = ?", (search,))

DATABASE = XmeDatabase()