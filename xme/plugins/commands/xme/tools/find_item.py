from ..classes.items.item import item_table, Item

def find_item_by_id(id: str) -> Item:
    return item_table.get(id, None)