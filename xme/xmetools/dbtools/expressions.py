"""UPDATE 语句的「列值表达式」：让写库表达相对当前行的运算，而不是快照覆盖。

同样一次写库，绝对写（``SET col = ?``）在任何并发写入下都是「后写者覆盖」；
表达式写（``SET col = col + ?``、``json_patch(col, ?)``）由 SQLite 在当前行上求值，
并与同一条语句里的其它列一起原子提交，因此不同来源的改动能正确叠加/互不干扰：

- 数值列 → ``add(delta)``：并发增减各自生效（100 → 别人 +100 到 200 → 本次 +100 = 300）；
- JSON 列 → ``diff_json(old, new)``：把差异收成一份 merge-patch 局部更新，
  不同子键（各插件数据、各计数器）互不覆盖；
- JSON 数组纯追加 → ``append_many(values)``：追加不丢并发写入的其它元素。

JSON 更新一律走 **绑定参数**（merge-patch 文档 / ``$[#]`` 常量路径），SQL 文本里
不拼接任何键名，因此键名含空格、中文、引号、emoji 都安全，也没有路径语法限制。
"""
import json
from dataclasses import dataclass


@dataclass(frozen=True)
class ColumnExpr:
    """列值表达式：模板中的 ``{col}`` 由 update_db 用已校验的列名替换。"""

    template: str
    params: tuple = ()

    def render(self, column: str) -> str:
        """把已校验的列名代入模板，返回可拼进 SET 子句的片段。"""
        return self.template.replace("{col}", column)


def add(delta) -> ColumnExpr:
    """``col = col + delta``（数值列的相对增量）。"""
    return ColumnExpr("{col} + ?", (delta,))


def dump(value) -> str:
    """把要写进 JSON 的值转成 JSON 文本（供绑定参数使用）。"""
    return json.dumps(value, ensure_ascii=False)


def merge_patch(patch: dict) -> ColumnExpr:
    """``json_patch(col, ?)``：按 RFC 7396 merge-patch 局部更新 JSON 列。

    patch 里值为 null 表示删除该键，对象递归合并、其它类型整体替换（数组也整体替换）。
    键名只出现在绑定参数中，不会进入 SQL 文本。
    """
    return ColumnExpr("json_patch({col}, ?)", (dump(patch),))


def append_many(values: list[str]) -> ColumnExpr:
    """在 JSON 数组末尾依次追加（``json_insert(col, '$[#]', json(?))``）。

    路径是常量 ``$[#]``，与元素内容无关，因此不受键名/内容影响。
    """
    template = "{col}"
    params: list = []
    for value_json in values:
        template = f"json_insert({template}, '$[#]', json(?))"
        params.append(value_json)
    return ColumnExpr(template, tuple(params))


def _is_pure_append(loaded: list, current: list) -> bool:
    """current 是否只是在 loaded 尾部追加（前缀完全一致且更长）。"""
    return len(current) > len(loaded) and current[:len(loaded)] == loaded


def _dict_patch(loaded: dict, current: dict) -> dict:
    """把两个 dict 的差异收成一份 merge-patch（值为 None 表示删除该键）。

    只在两侧同为 dict 时继续下钻（交给 merge-patch 递归合并），其余情况整块替换；
    数组只有纯追加时才继续用「整体替换该数组」的写法（顶层数组由 diff_json 用
    json_insert 追加，避免覆盖并发追加的元素）。
    """
    patch: dict = {}
    for key in loaded:
        if key not in current:
            patch[key] = None
    for key, value in current.items():
        if key not in loaded:
            patch[key] = value
            continue
        old = loaded[key]
        if old == value:
            continue
        if isinstance(old, dict) and isinstance(value, dict):
            sub = _dict_patch(old, value)
            if sub:
                patch[key] = sub
        else:
            patch[key] = value
    return patch


def diff_json(loaded, current) -> ColumnExpr | None:
    """比较 JSON 列的新旧结构，返回局部更新表达式。

    loaded / current 为解析后的 Python 结构。顶层数组的纯追加用 json_insert 追加；
    顶层是 dict 时生成 merge-patch；无法局部化（类型变了、一边不是 JSON 结构）
    返回 None，由调用方整列绝对写。
    """
    if isinstance(loaded, list) and isinstance(current, list) and _is_pure_append(loaded, current):
        return append_many([dump(v) for v in current[len(loaded):]])
    if isinstance(loaded, dict) and isinstance(current, dict):
        patch = _dict_patch(loaded, current)
        return merge_patch(patch) if patch else None
    return None

