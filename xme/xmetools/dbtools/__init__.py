"""数据库工具包：基于 sqlite3 的 XME 数据库读写、按模型建表与自动迁移。

内部结构：
- protocol.py   DbReadWriteable 模型协议（鸭子类型，无需显式继承）
- adapter.py    值适配与 SQL 标识符白名单校验（纯函数）
- connection.py 连接生命周期装饰器（连接-提交-回滚-关闭）
- schema.py     建表、表结构检查与自动迁移
- database.py   XmeDatabase 类与 DATABASE 单例

外部统一从包入口导入（兼容旧单文件 dbtools.py 的用法）：
    from xme.xmetools.dbtools import DATABASE

常用入口：
- DATABASE.exec_query(query, params, dict_data)    执行任意 SQL，返回行列表
- DATABASE.save_to_db(obj)                         存模型实例，返回主键
- DATABASE.update_db(obj, id, **fields)            按主键更新字段，返回受影响行数
- DATABASE.load_class(select_keys, query, cl)      查询单个模型实例
- DATABASE.create_class_table(obj)                 建表/自动迁移，返回表名
- DATABASE.remove(table_name, condition, params)   按条件删除
"""
from xme.xmetools.dbtools.adapter import (
    adapt_value,
    validate_identifier,
    value_to_sql_type,
)
from xme.xmetools.dbtools.connection import database_connect
from xme.xmetools.dbtools.database import DATABASE, XmeDatabase
from xme.xmetools.dbtools.protocol import T_DbReadWriteable, DbReadWriteable
from xme.xmetools.dbtools.schema import ensure_table_schema, get_table_columns, migrate_table

__all__ = [
    "DATABASE",
    "DbReadWriteable",
    "T_DbReadWriteable",
    "XmeDatabase",
    "adapt_value",
    "database_connect",
    "ensure_table_schema",
    "get_table_columns",
    "migrate_table",
    "validate_identifier",
    "value_to_sql_type",
]
