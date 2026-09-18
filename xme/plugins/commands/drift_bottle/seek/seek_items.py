"""seek 物品目录

物品主要作为「钥匙」存在：事件通过 require_items 判断玩家是否携带、
通过 changes 的 items 字段发放或消耗、通过检测物品事件（type: check）进行分支。
apply_event 为可选的被动效果，携带后像道具一样自动生效，无需手动使用。
"""

ITEMS = [
    {
        "id": "pearl",
        "name": "深海珍珠",
        "desc": "在黑暗中微微发光的珍珠，似乎有什么存在很喜欢它",
    },
]


def get_item(item_id: str, items=None) -> dict | None:
    """根据 id 获取物品定义

    Args:
        item_id (str): 物品 id
        items (list, optional): 物品目录. Defaults to ITEMS.

    Returns:
        dict | None: 物品定义，不存在时返回 None
    """
    if items is None:
        items = ITEMS
    for item in items:
        if item["id"] == item_id:
            return item
    return None
