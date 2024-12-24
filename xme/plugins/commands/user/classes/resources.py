from enum import Enum

class Resource(Enum):
    """资源种类 含量范围 0 ~ 1
    """
    MINERAL = "矿产资源"
    NATURAL = "自然资源"
    ORGANIC = "生物资源"
    GAS = "气体资源"
    RARE_GAS = "稀有气体资源"
    RARE_MINERAL = "稀有矿产资源"
    SPECIAL = "特殊资源"