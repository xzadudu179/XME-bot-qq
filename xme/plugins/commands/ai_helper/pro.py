"""高级模型白名单：只有白名单用户能选择受控模型。

名单分两处（各归其位）：
- 受控（高级）模型别名 → `constants.LLM_PRO_MODELS`（可提交的代码侧配置，
  与 LLM_MODELS 同级；格式即 LLM_MODELS 的 key）；
- 可用高级模型的用户 qq → `data/_botsettings.json` 的 `ai_pro_users`
  （运行时数据，与 blacklist_users 同一惯例）。

模型名单为空即视为**未启用该功能**——不配就能照常运行。
`config.SUPERUSERS` 恒放行（管理名单的人不该被自己锁住）。

本模块只做判定与名单读写，不含任何回复文案（文案由调用方按返回的键去取）。
"""
from config import BOT_SETTINGS_PATH, SUPERUSERS
from xme.xmetools import jsontools

from . import constants
from .llm import registry

PRO_USERS_KEY = "ai_pro_users"


def pro_models() -> list[str]:
    """受控（高级）模型别名列表（constants.LLM_PRO_MODELS）；未配置时返回空（= 不限制）。"""
    value = getattr(constants, "LLM_PRO_MODELS", []) or []
    return [str(i) for i in value] if isinstance(value, (list, tuple, set)) else []


def pro_users() -> list[str]:
    """可用高级模型的用户 qq 列表（字符串）。"""
    value = jsontools.get_json_value(BOT_SETTINGS_PATH, PRO_USERS_KEY, default=[]) or []
    return [str(i) for i in value] if isinstance(value, list) else []


def is_pro_model(spec: str) -> bool:
    """该模型规格是否受控（别名落在高级模型名单里）。"""
    return bool(spec) and str(spec) in pro_models()


def can_use(user_id) -> bool:
    """该用户能否使用高级模型：超管或名单内用户。"""
    if int(user_id) in SUPERUSERS:
        return True
    return str(user_id) in pro_users()


def check_spec(user_id, spec: str) -> str | None:
    """校验用户能否使用该模型规格；可用返回 None，不可用返回拒绝理由的文案键。

    规则：
    - 模型规格本身必须合法（别名或 "provider/model"，见 registry.is_valid_model）；
    - 受控别名（高级模型名单里的）只有白名单/超管能用；
    - "provider/model" 自由形式同样只有白名单/超管能用——否则随便写个第三方模型
      就能绕过名单拿到高级模型的能力，名单形同虚设。
    """
    if not registry.is_valid_model(spec):
        return "error_model"
    if can_use(user_id):
        return None
    if "/" in spec:
        return "pro_freeform_denied"
    if is_pro_model(spec):
        return "pro_denied"
    return None


def allowed_aliases(user_id) -> list[str]:
    """该用户可用的模型别名（供"请选择模型"之类的提示列出）。"""
    if can_use(user_id):
        return registry.list_model_aliases()
    return [a for a in registry.list_model_aliases() if a not in pro_models()]


def toggle_user(user_id) -> bool:
    """切换用户的高级模型权限，返回切换后是否在白名单（写入 _botsettings.json）。"""
    target = str(int(user_id))
    users = set(pro_users())
    if target in users:
        users.discard(target)
        enabled = False
    else:
        users.add(target)
        enabled = True
    jsontools.change_json(BOT_SETTINGS_PATH, PRO_USERS_KEY, set_method=lambda _: sorted(users))
    return enabled


def spec_restricted(user_id, spec: str) -> bool:
    """该模型规格对这名用户是否受限（高级别名，或自由指定的 provider/model 形式）。

    用于"已存下的/快照里的模型"是否要拦的场景——与 check_spec 的区别是不判合法性，
    只管权限维度（模型本身失效由调用方按自己的方式回退）。
    """
    if can_use(user_id):
        return False
    return "/" in (spec or "") or is_pro_model(spec)
