"""舞萌绑定数据的读写封装：唯一操作 User.plugin_datas 中舞萌数据入口。

绑定结构：{"username": 水鱼用户名 | None, "import_token": 成绩导入 Token | None}
"""

from xme.plugins.commands.xme_user.classes.user import User

from .constants import TOKEN_MASK_PREFIX

PLUGIN_DATA_KEY = 'maimai'
USERNAME_KEY = 'username'
TOKEN_KEY = 'import_token'


def get_binding(user: User) -> dict:
    """得到用户的舞萌绑定信息，缺失时返回空绑定 dict（不写入用户数据）。

    Args:
        user (User): 目标用户

    Returns:
        dict: {"username": str | None, "import_token": str | None}
    """
    data = user.plugin_datas.get(PLUGIN_DATA_KEY)
    if not isinstance(data, dict):
        return {USERNAME_KEY: None, TOKEN_KEY: None}
    return {
        USERNAME_KEY: data.get(USERNAME_KEY),
        TOKEN_KEY: data.get(TOKEN_KEY),
    }


def set_username(user: User, username: str) -> None:
    """写入用户绑定的水鱼用户名（不落库，落库由命令层调用 user.save()）。"""
    data = user.plugin_datas.setdefault(PLUGIN_DATA_KEY, {})
    data[USERNAME_KEY] = username


def set_token(user: User, token: str) -> None:
    """写入用户绑定的水鱼成绩导入 Token（不落库，落库由命令层调用 user.save()）。"""
    data = user.plugin_datas.setdefault(PLUGIN_DATA_KEY, {})
    data[TOKEN_KEY] = token


def clear_binding(user: User) -> bool:
    """清除用户的全部舞萌绑定信息。

    Args:
        user (User): 目标用户

    Returns:
        bool: 是否存在绑定被清除
    """
    existed = bool(user.plugin_datas.get(PLUGIN_DATA_KEY))
    user.plugin_datas.pop(PLUGIN_DATA_KEY, None)
    return existed


def mask_token(token: str | None) -> str:
    """把导入 Token 打码成"前缀****"形式，用于在回复中展示。"""
    if not token:
        return "未绑定"
    if len(token) <= TOKEN_MASK_PREFIX:
        return "****"
    return f"{token[:TOKEN_MASK_PREFIX]}****"
