# some are made by Deepseek-v4-flash-vison-exp at Deepseek Harness
"""Provider 注册表 / 模型目录 / 能力配置（多 Provider 升级的配置单点）。

- **密钥与端点**：`keys.py` 的 `LLM_PROVIDERS`（该文件不提交）。缺配置时自动回落
  GLM 官方兼容端点（保持升级前的行为，老部署零改动即可运行）。
- **模型目录与能力**：`constants.py` 的 `LLM_MODELS` / `LLM_CAPABILITIES`（可提交，
  不含敏感信息），用户直接改常量即可切换模型、倍率、上下文上限与各能力归属。
"""
from .openai_client import OpenAICompatProvider
from .types import ChatResult, LLMError, LLMErrorKind, ToolCall, Usage  # noqa: F401 (对外导出)

# GLM 官方 OpenAI 兼容端点（实测支持 tools / thinking / stream / usage.cached_tokens）
_GLM_DEFAULT_BASE = "https://open.bigmodel.cn/api/paas/v4"

_providers: dict[str, object] = {}


def _load_provider_configs() -> dict:
    """读取 keys.LLM_PROVIDERS；文件里没有该配置时返回空（触发 GLM 回落）。"""
    try:
        from keys import LLM_PROVIDERS  # type: ignore
        if isinstance(LLM_PROVIDERS, dict):
            return {str(k): dict(v or {}) for k, v in LLM_PROVIDERS.items()}
    except Exception:
        pass
    return {}


def _glm_fallback() -> dict:
    """升级前的等价配置：GLM 官方端点 + keys.GLM_API_KEY。"""
    try:
        from keys import GLM_API_KEY
    except Exception:
        GLM_API_KEY = ""
    return {"base_url": _GLM_DEFAULT_BASE, "api_key": GLM_API_KEY}


def _delta_logger(provider_name: str):
    """流式增量 → 调试日志（半流式：只写日志，不影响用户可见回复）。"""
    def on_delta(kind: str, text: str) -> None:
        if not text:
            return
        try:
            from ..constants import LLM_STREAM_LOG
            if not LLM_STREAM_LOG:
                return
            from ..agent import ai_logger  # 延迟导入避免循环依赖
            label = {"reasoning": "流式思考", "content": "流式回复",
                     "tool_call": "流式工具", "note": "提示"}.get(kind, kind)
            ai_logger.info(f"[{provider_name} {label}] {text}")
        except Exception:
            pass
    return on_delta


def provider_configured(name: str) -> bool:
    """该 provider 是否真的可用（配置齐全：有 base_url 与 api_key）。

    glm 没有显式配置时也能走官方兼容端点回落，但同样要求 keys.GLM_API_KEY 存在；
    配置项缺 api_key 视为不可用（避免回退到一个必然失败的模型）。
    """
    if not name:
        return False
    cfg = _load_provider_configs().get(name)
    if cfg is None and name == "glm":
        cfg = _glm_fallback()
    if not cfg:
        return False
    return bool(cfg.get("api_key")) and bool(cfg.get("base_url") or name == "glm")


def get_provider(name: str):
    """按名取 provider（惰性构造并缓存）；无该配置时回落 GLM。返回 None 表示不可用。"""
    if name in _providers:
        return _providers[name]
    from .. import constants
    timeout = float(getattr(constants, "LLM_TIMEOUT", 300.0))
    cfgs = _load_provider_configs()
    cfg = dict(cfgs.get(name) or {})
    if not cfg and name == "glm":
        cfg = _glm_fallback()
    if not cfg:
        return None
    transport = str(cfg.get("transport") or "openai_http")
    if transport != "openai_http":
        # 其他传输实现（如 zai SDK 轮询）尚未接入：明确报错而不是静默失败
        raise LLMError(LLMErrorKind.BAD_REQUEST,
                       f"provider {name} 配置的 transport={transport} 尚未实现",
                       provider=name)
    provider = OpenAICompatProvider(
        name, cfg.get("base_url") or _GLM_DEFAULT_BASE, cfg.get("api_key") or "",
        timeout=float(cfg.get("timeout") or timeout),
        stream=bool(cfg.get("stream", True)),
        temperature=cfg.get("temperature"),
        extra_headers=cfg.get("extra_headers"),
        on_delta=_delta_logger(name),
        transport=transport,
        stream_fallback=bool(cfg.get("stream_fallback", True)),
    )
    _providers[name] = provider
    return provider


async def close_all() -> None:
    """释放所有已建 provider 的连接（进程退出/重载时调用）。"""
    for p in list(_providers.values()):
        try:
            await p.close()
        except Exception:
            pass
    _providers.clear()


# ---------- 模型目录 ----------

def _model_table() -> dict:
    from .. import constants
    return getattr(constants, "LLM_MODELS", {}) or {}


def default_alias() -> str:
    """默认模型别名（配置缺失时回落 flash）。"""
    from .. import constants
    alias = getattr(constants, "LLM_DEFAULT_MODEL", "flash")
    return alias if alias in _model_table() else next(iter(_model_table()), "flash")


def resolve_model(spec: str) -> dict:
    """把"模型别名"或"provider/model"解析为目录项。

    别名（如 flash / pro）→ 目录里的完整描述；"provider/model" 形式 → 现造一项
    （provider 与模型名直接取自输入，能力/上限走默认值），便于临时指定第三方模型。
    """
    table = _model_table()
    spec = (spec or "").strip()
    if spec in table:
        entry = dict(table[spec])
        entry.setdefault("alias", spec)
        return entry
    if "/" in spec:
        provider, _, model = spec.partition("/")
        from .. import constants
        return {"alias": spec, "provider": provider.strip(), "model": model.strip(),
                "vision": True, "context_limit": getattr(constants, "CONTEXT_LIMIT_DEFAULT", 1_000_000),
                "credit_multiplier": 1}
    raise LLMError(LLMErrorKind.BAD_REQUEST, f"未知模型 {spec}（可用：{'、'.join(table)}）")


def list_model_aliases() -> list[str]:
    """所有可用的模型别名（供 /ai -m 校验与帮助文案）。"""
    return list(_model_table().keys())


def is_valid_model(spec: str) -> bool:
    """判断模型规格（别名或 "provider/model"）是否可用。"""
    try:
        resolve_model(spec)
        return True
    except LLMError:
        return False


def model_by_name(name: str) -> dict | None:
    """按真实模型名反查目录项（旧快照恢复 / 计费反查用）。"""
    for alias, entry in _model_table().items():
        if entry.get("model") == name:
            found = dict(entry)
            found.setdefault("alias", alias)
            return found
    return None


def vision_entry() -> dict:
    """取"视觉模型"目录项：能力配置 vision 优先，否则目录里第一个 vision=True 的项。

    用于带图轮切换模型（替代原先硬编码的 FLASH_MODEL 判据）。
    """
    cap = get_capability("vision")
    if cap.get("provider") and cap.get("model"):
        entry = model_by_name(cap["model"])
        if entry is not None:
            return entry
        return {"alias": f"{cap['provider']}/{cap['model']}", "provider": cap["provider"],
                "model": cap["model"], "vision": True,
                "context_limit": _default_context_limit(), "credit_multiplier": 1}
    for alias, entry in _model_table().items():
        if entry.get("vision"):
            found = dict(entry)
            found.setdefault("alias", alias)
            return found
    raise LLMError(LLMErrorKind.BAD_REQUEST, "模型目录里没有可用的视觉模型（LLM_MODELS / LLM_CAPABILITIES）")


def _default_context_limit() -> int:
    from .. import constants
    return getattr(constants, "CONTEXT_LIMIT_DEFAULT", 1_000_000)


def cache_credit_ratio(entry: dict | None) -> float:
    """模型目录项的缓存计费倍率（LLM_MODELS 的 cache_credit_ratio；缺省 0.25）。"""
    from .. import constants
    default = getattr(constants, "DEFAULT_CACHE_CREDIT_RATIO", 0.25)
    if not entry:
        return default
    value = entry.get("cache_credit_ratio")
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def get_capability(name: str) -> dict:
    """取某项能力（vision / ocr / image_gen / web_reader / moderation）的配置。"""
    from .. import constants
    caps = getattr(constants, "LLM_CAPABILITIES", {}) or {}
    return dict(caps.get(name) or {})
