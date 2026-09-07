"""数据库模型协议：约定一个模型要能存入 XME 数据库需要提供哪些接口。

模型无需显式继承 DbReadWriteable（鸭子类型即可），但需满足：
- `id` 属性：主键，-1 表示尚未入库（入库时跳过该列由 sqlite 自增分配）
- `get_table_name()`：类方法，返回模型对应的表名（通常为类名）
- `to_dict()`：返回「列名 -> 值」的 dict，值需为可入库类型或可被 adapt_value 转换
- `form_dict(data)`：约定通过类直接调用（如 ``User.form_dict(row)``），
  接收一行查询结果 dict，返回模型实例
"""
from typing import Protocol, TypeVar, runtime_checkable

T_DbReadWriteable = TypeVar("T", bound="DbReadWriteable")


@runtime_checkable
class DbReadWriteable(Protocol):
    """可读写数据库的模型协议。"""

    id: int

    def form_dict(data: dict) -> T_DbReadWriteable:
        """由一行查询结果 dict 构建模型实例。

        Args:
            data (dict): 列名 -> 值 的查询结果行

        Returns:
            T_DbReadWriteable: 模型实例
        """
        ...

    @classmethod
    def get_table_name(cls) -> str:
        """返回模型对应的表名。

        Returns:
            str: 表名
        """
        ...

    def to_dict(self) -> dict:
        """返回模型的「列名 -> 值」dict，供入库使用。

        Returns:
            dict: 列名 -> 值
        """
        ...
