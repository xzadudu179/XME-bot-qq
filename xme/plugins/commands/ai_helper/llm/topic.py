# some are made by Deepseek-v4-flash-vison-exp at Deepseek Harness
"""话题分类器：用小模型判断对话属于哪类话题（供动态模型分配使用）。

设计要点：
- 类别清单从 `constants.LLM_TOPIC_ROUTING` 的键派生（单点维护）；
- 分类模型由 `constants.LLM_TOPIC_CLASSIFIERS` 给出**候选链**，按顺序尝试，前一个失败
  就换下一个（免费模型限流严重、个别型号排队久，靠候选链保住可用性）；
- **带上下文**：分类输入包含最近几轮对话 + 本次输入——角色扮演/设定常出现在对话开头，
  只看当前一句会把"嗯嗯"这类短输入判错；
- 调用形态：非流式 + 静默（不写流式日志）；
- 一律兜底：候选链全部失败、超时、输出无法识别 → 返回兜底类别并记日志；连续失败则熔断
  一段时间，期间直接兜底（不再为每次对话白等一次失败请求）。
"""
import asyncio
import time

from nonebot.log import logger

from . import registry

_fail_streak = 0         # 候选链整体连续失败次数
_circuit_until = 0.0     # 熔断截止时间戳


def _routing() -> dict:
    from .. import constants
    return dict(getattr(constants, "LLM_TOPIC_ROUTING", {}) or {})


def _categories() -> list[str]:
    """可用类别（来自路由表的键，顺序即提示词中的展示顺序）。"""
    return list(_routing().keys())


def _fallback_category() -> str:
    """兜底类别：优先"其他"，否则类别表最后一项。"""
    cats = _categories()
    return "其他" if "其他" in cats else (cats[-1] if cats else "其他")


def parse_category(raw: str) -> str:
    """把模型输出解析为类别：去空白/引号/标点后取首个命中的类别；识别不出返回兜底类别。"""
    fallback = _fallback_category()
    text = (raw or "").strip().strip("\"'“”‘’。，,、:：!！?？ \n\t")
    if not text:
        return fallback
    for cat in _categories():
        if cat and cat in text:
            return cat
    return fallback


def build_messages(text: str, context: str = "", max_chars: int = 500) -> list:
    """构造分类提示词：可选带最近对话，再给本次输入，严格要求只输出类别词。"""
    cats = "、".join(_categories())
    system = (
        "你是一个话题分类器。请综合「最近对话」与「本次输入」，判断这次对话属于哪一类，"
        f"只输出一个类别词，不要输出任何解释、标点或多余内容。\n可选类别：{cats}"
    )
    body = ""
    if (context or "").strip():
        body += f"[最近对话]\n{context.strip()}\n\n"
    body += f"[本次输入]\n{(text or '')[:max_chars]}"
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": body},
    ]


def _is_rate_limited(ex: Exception) -> bool:
    return getattr(ex, "kind", "") == "rate_limit"


def _note_failure() -> None:
    """记录一次候选链整体失败；连续失败达阈值则熔断一段时间。"""
    global _fail_streak, _circuit_until
    from .. import constants
    limit = int(getattr(constants, "LLM_TOPIC_FAIL_STREAK", 3))
    cooldown = float(getattr(constants, "LLM_TOPIC_COOLDOWN", 120.0))
    _fail_streak += 1
    if _fail_streak >= limit:
        _circuit_until = time.time() + cooldown
        _fail_streak = 0
        logger.warning(f"话题分类连续失败，暂停分类 {cooldown:g}s（期间使用默认模型）")


def _candidates() -> list[dict]:
    """候选分类模型（新配置为列表；兼容早期的单配置项写法）。"""
    from .. import constants
    cands = getattr(constants, "LLM_TOPIC_CLASSIFIERS", None)
    if isinstance(cands, list) and cands:
        return [dict(c) for c in cands if isinstance(c, dict)]
    single = getattr(constants, "LLM_TOPIC_CLASSIFIER", None)
    if isinstance(single, dict) and single.get("provider") and single.get("model"):
        return [dict(single)]
    return []


async def classify_topic(text: str, context: str = "", agent=None) -> str:
    """判断话题类别，返回类别名（任何失败都返回兜底类别，不抛异常）。

    context：最近对话文本（调用方从历史提取），用于识别"角色扮演在开头定义"这类情况。
    agent：按需计费（LLM_TOPIC_BILLABLE 为真时累加到 other_credits）。
    """
    from .. import constants
    fallback = _fallback_category()
    if not (text or "").strip() and not (context or "").strip():
        return fallback

    global _fail_streak, _circuit_until
    if time.time() < _circuit_until:
        return fallback   # 熔断期内直接兜底，省掉失败等待

    timeout = float(getattr(constants, "LLM_TOPIC_TIMEOUT", 8.0))
    max_chars = int(getattr(constants, "LLM_TOPIC_MAX_CHARS", 500))
    messages = build_messages(text, context, max_chars)
    billable = bool(getattr(constants, "LLM_TOPIC_BILLABLE", False))

    result = None
    for cand in _candidates():
        provider = registry.get_provider(cand.get("provider", ""))
        if provider is None:
            logger.info(f"话题分类：provider {cand.get('provider')} 未配置，跳过 {cand.get('model')}")
            continue
        model = cand.get("model") or ""
        try:
            result = await asyncio.wait_for(
                provider.chat(messages, model=model, temperature=0.0, silent=True),
                timeout=timeout)
        except asyncio.TimeoutError:
            logger.info(f"话题分类：{model} 超时（>{timeout:g}s），尝试下一个候选")
            continue
        except Exception as ex:
            # 限流或其他错误都换下一个候选（免费模型限流很常见）
            flag = "限流" if _is_rate_limited(ex) else type(ex).__name__
            logger.info(f"话题分类：{model} 调用失败（{flag}: {ex}），尝试下一个候选")
            continue
        if agent is not None and billable:
            entry = registry.model_by_name(model) or {}
            agent.other_credits += result.usage.billable_tokens(registry.cache_credit_ratio(entry))
        break

    if result is None:
        _note_failure()
        return fallback

    _fail_streak = 0   # 成功一次即解除熔断计数
    raw = (result.text or "").strip()
    category = parse_category(raw)
    if category == fallback and raw and fallback not in raw:
        logger.warning(f"话题分类输出无法识别：{raw[:80]!r}，本轮按「{fallback}」处理")
    return category
