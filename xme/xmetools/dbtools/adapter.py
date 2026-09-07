"""数据库值适配：Python 值与 SQLite 存储值之间的纯函数转换，以及 SQL 标识符白名单校验。

本模块全部为无状态纯函数，供 XmeDatabase 与 schema 模块复用。
"""
import json
import re
from typing import Any, Callable

from xme.xmetools.dbtools.protocol import DbReadWriteable

# SQL 标识符（表名/列名）白名单：字母或下划线开头，仅含字母、数字、下划线
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def validate_identifier(name: str) -> str:
    """校验 SQL 标识符（表名/列名）是否在白名单内，非法时抛出异常。

    所有需要拼进 SQL 语句的表名/列名都必须经过本函数，
    值则一律走 sqlite3 的 ? 参数化绑定，两者共同防注入。

    Args:
        name (str): 待校验的标识符

    Returns:
        str: 原样返回合法标识符

    Raises:
        ValueError: 标识符为空或含白名单外字符
    """
    if not isinstance(name, str) or not _IDENTIFIER_RE.match(name):
        raise ValueError(f"非法的 SQL 标识符: {name!r}")
    return name


def value_to_sql_type(value: Any) -> str:
    """根据值推导 SQLite 列类型（无副作用，不会递归入库）。

    Args:
        value (Any): 示例值

    Returns:
        str: SQLite 类型名（INTEGER / REAL / BLOB / TEXT）
    """
    if isinstance(value, bool):
        return "INTEGER"
    if value is None:
        return "TEXT"
    if isinstance(value, int):
        return "INTEGER"
    if isinstance(value, float):
        return "REAL"
    if isinstance(value, (bytes, bytearray)):
        return "BLOB"
    if isinstance(value, DbReadWriteable):
        return "INTEGER"
    return "TEXT"


def adapt_value(value: Any, save_nested: Callable[[DbReadWriteable], int] | None = None) -> Any:
    """把 Python 值转换为可直接绑定给 sqlite3 的存储值。

    Args:
        value (Any): 任意 Python 值
        save_nested (Callable, optional): 嵌套 DbReadWriteable 的入库回调，
            需要时由数据库实例注入（如 ``lambda o: db.save_to_db(o)``），
            嵌套模型入库后以其主键作为本列的存储值

    Returns:
        Any: 可直接存入数据库的值（bool 转 int，list/dict 转 JSON 字符串，
            datetime/date 转 ISO 字符串，嵌套 DbReadWriteable 转其主键）

    Raises:
        ValueError: 值类型无法存入，或嵌套模型未提供 save_nested 回调
    """
    if isinstance(value, bool):
        return int(value)
    if value is None or isinstance(value, (str, int, float, bytes, bytearray)):
        return value
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, DbReadWriteable):
        if save_nested is None:
            raise ValueError(f"嵌套模型 {type(value).__name__} 需要数据库实例提供 save_nested 才能入库")
        return save_nested(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    raise ValueError(f"无法解析类型 {type(value).__name__}")
