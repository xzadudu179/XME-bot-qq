"""XME 数据库核心类：模型建表、增删改查与自动迁移，以及模块级 DATABASE 单例。

对外入口统一从包模块导入（``from xme.xmetools.dbtools import DATABASE``）。
"""
from typing import Type

from xme.xmetools.debugtools import debug_msg
from xme.xmetools.dbtools.adapter import adapt_value, validate_identifier
from xme.xmetools.dbtools.connection import database_connect
from xme.xmetools.dbtools.protocol import T_DbReadWriteable
from xme.xmetools.dbtools.schema import ensure_table_schema

# 未入库模型的 id 哨兵值：保存时跳过主键列，由 sqlite 自增分配
UNSAVED_ID = -1


class XmeDatabase:
    """XME 数据库相关类：封装 sqlite3 的建表、存取、查询与自动迁移。"""

    def __init__(self, db_path: str = './data/xme/xme.db') -> None:
        """初始化数据库工具。

        Args:
            db_path (str): sqlite 数据库文件路径
        """
        self.db_path = db_path

    @staticmethod
    def get_dict_data(cursor, datas: tuple) -> dict:
        """把单行查询结果按 cursor 列描述转换为 dict。

        Args:
            cursor: 已 execute 的 sqlite3 cursor
            datas (tuple): 单行结果元组

        Returns:
            dict: 列名 -> 值
        """
        columns = [column[0] for column in cursor.description]
        return dict(zip(columns, datas))

    def remove(self, table_name: str, condition: str, params: tuple = ()) -> None:
        """按条件删除表中内容。

        Args:
            table_name (str): 表名
            condition (str): WHERE 条件，值必须使用 ? 占位，禁止拼接具体值
            params (tuple): 条件占位符对应内容

        Raises:
            ValueError: 表名不合法
        """
        validate_identifier(table_name)
        self.exec_query(query=f"DELETE FROM {table_name} WHERE {condition}", params=params)

    @database_connect
    def create_class_table(self, cursor, obj: T_DbReadWriteable) -> str:
        """确保模型实例对应的表存在且结构与当前模型一致（不一致时自动迁移）。

        Args:
            obj (T_DbReadWriteable): 模型实例

        Returns:
            str: 表名
        """
        table_name = obj.get_table_name()
        validate_identifier(table_name)
        fields = {k: v for k, v in obj.to_dict().items() if k != 'id'}
        ensure_table_schema(cursor, table_name, fields)
        return table_name

    @database_connect
    def update_db(self, cursor, obj: T_DbReadWriteable, id: int, **kwargs) -> int:
        """按主键更新模型对应表的字段。

        Args:
            obj (T_DbReadWriteable): 模型实例（仅用于确定表名）
            id (int): 行主键
            **kwargs: 列名 -> 新值（值需已可入库）

        Returns:
            int: 受影响行数

        Raises:
            ValueError: id 为未入库哨兵值、未提供更新字段，或列名/表名不合法
        """
        if id == UNSAVED_ID:
            raise ValueError("id 不可以是 -1")
        if not kwargs:
            raise ValueError("至少提供一个更新字段")
        table_name = obj.__class__.get_table_name()
        validate_identifier(table_name)
        placeholders = []
        values = []
        for k, v in kwargs.items():
            placeholders.append(f"{validate_identifier(k)} = ?")
            values.append(v)
        placeholders_msg = ", ".join(placeholders)
        values.append(id)
        sql = f"UPDATE {table_name} SET {placeholders_msg} WHERE id = ?"
        cursor.execute(sql, tuple(values))
        return cursor.rowcount

    @database_connect
    def save_to_db(self, cursor, obj: T_DbReadWriteable) -> int | None:
        """将模型实例存储至数据库（已存在同主键行则替换）。

        Args:
            obj (T_DbReadWriteable): 模型实例

        Returns:
            int | None: 实例的主键

        Raises:
            ValueError: 实例为 None，或字段值/表名无法入库
        """
        if obj is None:
            raise ValueError("类不可是 None")
        data = obj.to_dict()
        # id == -1 表示尚未入库，跳过主键列让 sqlite 自增分配
        fields = [k for k in data.keys() if k != 'id' or data[k] != UNSAVED_ID]
        values = [adapt_value(data[k], save_nested=self.save_to_db) for k in fields]
        table_name = obj.get_table_name()
        validate_identifier(table_name)
        for k in fields:
            validate_identifier(k)
        # 复用当前连接检查表结构（不存在则建表、不一致则迁移），避免另开连接
        ensure_table_schema(cursor, table_name, {k: v for k, v in data.items() if k != 'id'})
        columns = ', '.join(fields)
        placeholders = ', '.join(['?'] * len(fields))
        sql = f"INSERT OR REPLACE INTO {table_name} ({columns}) VALUES ({placeholders})"
        cursor.execute(sql, tuple(values))
        return cursor.lastrowid

    def load_class(self, select_keys: tuple, query: str,
                   cl: Type[T_DbReadWriteable]) -> T_DbReadWriteable | None:
        """按查询语句加载单个模型实例。

        Args:
            select_keys (tuple): 查询占位符实际值元组
            query (str): 查询语句，表名用 {table_name} 占位，
                除该占位符外不要在语句中使用花括号
            cl (Type[T_DbReadWriteable]): 模型类

        Returns:
            T_DbReadWriteable | None: 模型实例，查无结果时为 None
        """
        d = self._load_from_db(select_keys=select_keys, table_name=cl.get_table_name(), query=query)
        if d is None:
            return None
        return cl.form_dict(d)

    @database_connect
    def _load_from_db(self, cursor, select_keys: tuple, table_name: str,
                      query: str = "SELECT * FROM {table_name} WHERE id = ?") -> dict | None:
        """通过表名与查询语句获取单行内容并转为 dict。

        Args:
            select_keys (tuple): 查询占位符实际值元组
            table_name (str): 表名
            query (str): 查询语句，表名用 {table_name} 占位

        Returns:
            dict | None: 行数据 dict，查无结果时为 None
        """
        validate_identifier(table_name)
        sql = query.format(table_name=table_name)
        debug_msg("正在通过语句加载内容:\n", sql, select_keys)
        cursor.execute(sql, select_keys)
        row = cursor.fetchone()
        if not row:
            return None
        return self.get_dict_data(cursor, row)

    @database_connect
    def exec_query(self, cursor, query: str, params: tuple = (), dict_data: bool = False) -> list[tuple | dict]:
        """执行任意 SQL 查询语句。

        Args:
            query (str): 查询 sql 语句
            params (tuple, optional): 查询占位符所对应内容. Defaults to ()
            dict_data (bool): 是否返回字典数据而非元组. Defaults to False

        Returns:
            list[tuple | dict]: 查询结果
        """
        debug_msg("正在执行语句:\n", query, params)
        cursor.execute(query, params)
        if not dict_data:
            return cursor.fetchall()
        return [self.get_dict_data(cursor, r) for r in cursor.fetchall()]


DATABASE = XmeDatabase()
