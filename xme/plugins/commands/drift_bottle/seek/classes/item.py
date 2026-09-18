"""seek 物品的运行时工具：定义转道具、物品条件判定"""
from ..seek_items import ITEMS, get_item


def build_item_tool(item_dict: dict, player):
    """把物品定义转换为局内道具（价格为 0，不会计入结算扣费）

    纯钥匙物品（没有 apply_event 字段）返回 None

    Args:
        item_dict (dict): 物品定义
        player (Player): 绑定的玩家

    Returns:
        Tool | None: 道具实例
    """
    if item_dict.get("apply_event", None) is None:
        return None
    # 函数内导入避免 item -> tool -> event -> item 循环依赖
    from .tool import Tool
    return Tool(
        tool_id=item_dict["id"],
        name=item_dict["name"],
        desc=item_dict["desc"],
        price=0,
        player=player,
        apply_event=item_dict["apply_event"],
        apply_condition=item_dict["apply_condition"],
        apply_times=item_dict.get("apply_times", 1),
    )


def meets_require_items(player, item_ids) -> bool:
    """判断玩家是否携带了所有要求的物品

    Args:
        player (Player): 玩家
        item_ids (list): 要求的物品 id 列表

    Returns:
        bool: 是否全部携带，空列表视为满足
    """
    if not item_ids:
        return True
    return all(player.has_item(item_id) for item_id in item_ids)
