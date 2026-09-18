"""seek 持久数据模块

数据存储于 user.plugin_datas["漂流瓶"]["seek"]，结构：
{
    "inventory": ["ghost_lantern", "pearl"],  # 物品栏，元素为 seek_items.ITEMS 的 id，
                                              # 长度不超过 INVENTORY_MAX_SLOTS，可重复（各占一格）
}
统计（stats）、尸体（corpses）等其余键由对应功能自行定义写入。
"""
from xme.xmetools.dicttools import get_value, set_value
from xme.plugins.commands.drift_bottle import __plugin_name__
from .constants import SEEK_DATAS_KEY, INVENTORY_KEY, INVENTORY_MAX_SLOTS, ITEM_SAVE_PUNISH_RATE
from .seek_items import get_item


def get_seek_datas(user) -> dict:
    """获取用户的 seek 持久数据

    Args:
        user (User): 用户

    Returns:
        dict: seek 持久数据，不存在时返回空 dict
    """
    datas = get_value(__plugin_name__, SEEK_DATAS_KEY, search_dict=user.plugin_datas, default=None)
    return datas if isinstance(datas, dict) else {}


def get_inventory(user) -> list:
    """获取用户物品栏

    Args:
        user (User): 用户

    Returns:
        list: 物品 id 列表，不存在时返回空列表
    """
    inventory = get_value(__plugin_name__, SEEK_DATAS_KEY, INVENTORY_KEY, search_dict=user.plugin_datas, default=None)
    return inventory if isinstance(inventory, list) else []


def save_inventory(user, items) -> bool:
    """保存用户物品栏，物品非法或超出容量时拒绝写入

    Args:
        user (User): 用户
        items (list): 物品 id 列表

    Returns:
        bool: 是否保存成功
    """
    if not isinstance(items, list) or len(items) > INVENTORY_MAX_SLOTS:
        return False
    if any(not isinstance(item_id, str) or get_item(item_id) is None for item_id in items):
        return False
    set_value(__plugin_name__, SEEK_DATAS_KEY, INVENTORY_KEY, search_dict=user.plugin_datas, set_method=lambda _: list(items))
    user.update("plugin_datas")
    return True


def drop_inventory_items(user, index: int, count: int = 1) -> tuple[int, str]:
    """按序号从物品栏丢弃物品

    同种物品每个各占一格，丢弃时按物品 id 移除至多 count 个

    Args:
        user (User): 用户
        index (int): 物品栏序号（从 1 开始）
        count (int): 丢弃数量. Defaults to 1.

    Returns:
        tuple[int, str]: (实际丢弃数量, 物品名)，序号无效时丢弃数量为 0
    """
    inventory = get_inventory(user)
    if not 1 <= index <= len(inventory):
        return (0, "")
    item = get_item(inventory[index - 1])
    if item is None:
        return (0, "")
    removed = 0
    remaining: list = []
    for item_id in inventory:
        if item_id == item["id"] and removed < count:
            removed += 1
            continue
        remaining.append(item_id)
    if removed > 0:
        set_value(__plugin_name__, SEEK_DATAS_KEY, INVENTORY_KEY, search_dict=user.plugin_datas, set_method=lambda _: remaining)
        user.update("plugin_datas")
    return (removed, item["name"])


def get_gain_ratio(depth: float) -> float:
    """根据深度获取结算收益比例（与结算的深度惩罚档位一致）

    Args:
        depth (float): 探险深度

    Returns:
        float: 收益比例
    """
    if depth > 300:
        return 0
    if depth > 200:
        return 0.1
    if depth > 100:
        return 0.2
    if depth > 50:
        return 0.5
    if depth > 20:
        return 0.7
    return 1


def calc_depth_punish_rate(depth: float, depth_gain_ratio: float) -> float:
    """计算深度惩罚比例

    Args:
        depth (float): 探险深度
        depth_gain_ratio (float): 深度惩罚倍率（百分比）

    Returns:
        float: 深度惩罚比例
    """
    return (1 - get_gain_ratio(depth)) * depth_gain_ratio / 100.0


def can_save_items(depth: float, depth_gain_ratio: float) -> bool:
    """判断当前深度惩罚比例是否满足物品保存条件

    Args:
        depth (float): 探险深度
        depth_gain_ratio (float): 深度惩罚倍率（百分比）

    Returns:
        bool: 深度惩罚比例是否小于保存阈值
    """
    return calc_depth_punish_rate(depth, depth_gain_ratio) < ITEM_SAVE_PUNISH_RATE
