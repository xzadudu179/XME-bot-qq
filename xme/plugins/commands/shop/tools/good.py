from ..static.goods import DECORATIONS
from ..classes.good import Good

def get_good_from_id(id: int) -> Good:
    goods = DECORATIONS
    for g in goods:
        if id != g.id:
            continue
        return g
    return None
