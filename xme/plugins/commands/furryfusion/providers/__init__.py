"""兽聚数据源注册表：CURRENT_PROVIDER 为当前数据源的单点选择。"""
from .base import FurAPIError, FurEvent, FurProvider
from .furrycons import FurryconsProvider

PROVIDERS: dict[str, type[FurProvider]] = {
    "furrycons": FurryconsProvider,
}
CURRENT_PROVIDER = "furrycons"


def get_provider() -> FurProvider:
    """返回当前配置的数据源实例，配置错误直接抛异常。"""
    try:
        return PROVIDERS[CURRENT_PROVIDER]()
    except KeyError as e:
        raise FurAPIError(f"未知兽聚数据源：{CURRENT_PROVIDER}") from e
