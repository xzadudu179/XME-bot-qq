"""数据表结构管理：建表、表结构检查与自动迁移。

本模块函数全部以 sqlite3 cursor 作为第一个参数，在调用方当前连接内执行，
因此 save_to_db 等方法可以复用自己的连接完成表检查，不必另开连接。
"""
import time

from nonebot.log import logger

from xme.xmetools.dbtools.adapter import validate_identifier, value_to_sql_type


def get_table_columns(cursor, table_name: str) -> list[tuple[str, str]] | None:
    """获取表的所有列 (列名, 类型)。

    Args:
        cursor: sqlite3 cursor
        table_name (str): 表名

    Returns:
        list[tuple[str, str]] | None: (列名, 类型) 列表，表不存在时为 None
    """
    validate_identifier(table_name)
    rows = cursor.execute(f"PRAGMA table_info({table_name})").fetchall()
    if not rows:
        return None
    return [(row[1], row[2]) for row in rows]


def create_table(cursor, name: str, keys, values) -> None:
    """按列名与示例值建表（id INTEGER PRIMARY KEY 主键，各列类型由示例值推导）。

    Args:
        cursor: sqlite3 cursor
        name (str): 表名
        keys: 列名可迭代对象
        values: 与 keys 一一对应的示例值
    """
    validate_identifier(name)
    validated_keys = [validate_identifier(k) for k in keys]
    types = [value_to_sql_type(v) for v in values]
    column_defs = ", ".join(f"{k} {t}" for k, t in zip(validated_keys, types))
    cursor.execute(f"CREATE TABLE IF NOT EXISTS {name} (id INTEGER PRIMARY KEY, {column_defs})")


def ensure_table_schema(cursor, table_name: str, fields: dict) -> None:
    """检测模型字段与实际表结构是否一致；不一致时自动重建表并迁移数据。

    处理字段减少（如删除的列）、字段增加（新列默认 NULL）两种情况；
    表不存在时直接按模型建表。

    Args:
        cursor: sqlite3 cursor
        table_name (str): 表名
        fields (dict): 模型字段（列名 -> 示例值，不含主键 id）
    """
    existing = get_table_columns(cursor, table_name)
    if existing is None:
        # 表不存在，正常创建
        create_table(cursor, table_name, fields.keys(), fields.values())
        return
    # id 是主键（由模型统一使用，不参与字段比对）
    existing_cols = {name for name, _ in existing} - {"id"}
    wanted = set(fields.keys())
    if existing_cols == wanted:
        return
    logger.warning(
        f"检测到数据表 {table_name} 结构不一致，开始自动迁移。"
        f" 旧列: {sorted(existing_cols)} / 新列: {sorted(wanted)}"
    )
    migrate_table(cursor, table_name, existing, fields)


def migrate_table(cursor, table_name: str, existing_cols_info, fields: dict) -> None:
    """单事务内完成迁移：旧表改名备份 → 建新表 → 拷贝公共列 → 校验行数 → 删除备份表。

    任何一步出错都会整体回滚，旧表原样保留；行数校验不通过同样回滚。
    需在调用方连接的事务内执行（由 database_connect 装饰器保证）。

    Args:
        cursor: sqlite3 cursor
        table_name (str): 表名
        existing_cols_info: 旧表 (列名, 类型) 列表
        fields (dict): 模型字段（列名 -> 示例值，不含主键 id）
    """
    # 纳秒级时间戳避免同一秒内两次迁移撞备份表名
    backup_table = f"{table_name}__backup__{time.time_ns()}"
    validate_identifier(table_name)
    for name in fields.keys():
        validate_identifier(name)
    old_types = dict(existing_cols_info)
    model_cols = set(fields.keys())
    # 拷贝主键 id 与所有公共模型列，保证外键引用与数据不丢
    listed = [c for c, _ in existing_cols_info if c in model_cols]
    common_cols = ["id"] + listed
    column_defs = [
        f"{name} {old_types[name]}" if name in old_types
        else f"{name} {value_to_sql_type(fields[name])}"
        for name in fields.keys()
    ]
    # 1. 旧表改名（数据完整保留）
    cursor.execute(f"ALTER TABLE {table_name} RENAME TO {backup_table}")
    # 2. 按当前模型建新表
    cursor.execute(
        f"CREATE TABLE {table_name} (id INTEGER PRIMARY KEY, {', '.join(column_defs)})"
    )
    # 3. 拷贝公共列数据
    if common_cols:
        cols = ", ".join(common_cols)
        cursor.execute(
            f"INSERT INTO {table_name} ({cols}) SELECT {cols} FROM {backup_table}"
        )
    # 4. 校验行数，不一致则回滚（旧表恢复）
    old_n = cursor.execute(f"SELECT COUNT(*) FROM {backup_table}").fetchone()[0]
    new_n = cursor.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
    if old_n != new_n:
        raise RuntimeError(
            f"表 {table_name} 迁移校验失败：旧表 {old_n} 行 / 新表 {new_n} 行，已回滚"
        )
    # 5. 校验通过，删除备份表（bot 启动前已有 .backup/ 全量备份兜底）
    cursor.execute(f"DROP TABLE {backup_table}")
    logger.info(
        f"数据表 {table_name} 迁移完成：复制公共列 {len(common_cols)} 个，"
        f"共 {new_n} 行，备份表 {backup_table} 已删除"
    )
