# some are made by Deepseek-v4-flash-vison-exp at Deepseek Harness
"""单轮 AI 调用工具：给程序用的"一次提问、拿回解析好的回复"入口。

与 agent 的完整会话无关——不落历史、不挂工具、不做计费快照，只做
「提示词 → 模型 → 回复」，调用方零配置（provider/密钥/温度/超时全走现有配置）：

    result = await ask("总结这段话：...", model="flash", json_output=True)
    if result is not None:
        data = result.data   # 解析好的 JSON（解析不出为 None，原文仍在 result.text）

- model 支持：别名（flash）/ 自由形式（provider/model）/ 候选链列表 / None（默认模型）；
  候选链按序尝试，超时/异常/未配置自动换下一个，全失败返回 None（不抛异常）；
- temperature：显式参数 > 模型目录项 temperature > LLM_DEFAULT_TEMPERATURE；
- json_output：提示词强制 JSON 输出并稳健解析（多数端点对 response_format
  支持参差，用提示词约束 + 本地解析最通用）；是否计费由调用方拿 usage 自行决定。
"""
import asyncio
import json
import re
from dataclasses import dataclass

from nonebot.log import logger

from . import registry
from .types import Usage

# 要求 JSON 输出时追加到 system 的硬性约束
_JSON_INSTRUCTION = "只输出一个合法的 JSON：不要 markdown 代码块，不要任何解释或多余文字。"

_FENCE_END_RE = re.compile(r"```\s*$")


@dataclass
class AskResult:
    """一次单轮调用的结果（所有候选模型都失败时 ask 返回 None 而不是本类型）。"""

    text: str      # 模型回复原文（已 strip）
    data: object   # json_output=True 时解析出的 JSON；解析失败或未要求时为 None
    usage: Usage   # 本次调用用量（是否计费由调用方决定）
    model: str     # 实际使用的真实模型名
    provider: str  # 实际使用的 provider 名


def extract_json(raw: str):
    """从模型输出里稳健地提取 JSON，失败返回 None。

    覆盖三种常见形态：裸 JSON、markdown 代码围栏（可带语言标注）、
    前后带解释文字的 JSON（截取第一段括号平衡的部分，字符串内的括号/引号不干扰）。
    """
    s = (raw or "").strip()
    if not s:
        return None
    if s.startswith("```"):
        nl = s.find("\n")
        if nl != -1:
            s = s[nl + 1:]
        s = _FENCE_END_RE.sub("", s).strip()
    try:
        return json.loads(s)
    except Exception:
        pass
    for opener, closer in (("{", "}"), ("[", "]")):
        start = s.find(opener)
        if start < 0:
            continue
        depth = 0
        in_str = False
        escaped = False
        for i in range(start, len(s)):
            ch = s[i]
            if in_str:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == opener:
                depth += 1
            elif ch == closer:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(s[start:i + 1])
                    except Exception:
                        break   # 该段不是合法 JSON，换下一种括号再试
    return None


def _model_specs(model) -> list[str]:
    """把 model 参数归一成候选链：None/空 → 默认模型；str → 单候选；list/tuple → 按序候选。"""
    if model is None or (isinstance(model, str) and not model.strip()):
        return registry.free_models()
    if isinstance(model, str):
        return [model.strip()]
    return [str(m).strip() for m in model if str(m).strip()]

def _resolve_temperature(entry: dict, temperature: float | None) -> float:
    """采样温度取值顺序：显式参数 > 模型目录项 temperature > 全局默认。"""
    if temperature is not None:
        return float(temperature)
    value = entry.get("temperature")
    if value is not None:
        return float(value)
    from .. import constants
    return float(getattr(constants, "LLM_DEFAULT_TEMPERATURE", 0.5))


async def ask(prompt: str, *, system: str = "", model=None,
              temperature: float | None = None, timeout: float = 30.0,
              json_output: bool = False, silent: bool = True,
              label: str = "AI 调用") -> AskResult | None:
    """单轮对话：发一段提示词，拿回解析好的回复；所有候选模型都失败返回 None。

    model：别名 / "provider/model" / 候选链列表 / None（默认模型）。
    json_output：True 时提示词强制 JSON 输出并稳健解析到 result.data。
    silent：静默调用（不写流式日志）；label：仅用作日志前缀，方便定位是哪个功能在调用。
    """
    if not (prompt or "").strip():
        logger.warning(f"{label}：提示词为空，跳过调用")
        return None
    if json_output:
        system = f"{(system or '').strip()}\n{_JSON_INSTRUCTION}".strip()
    messages = []
    if system.strip():
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    for spec in _model_specs(model):
        try:
            entry = registry.resolve_model(spec)
        except Exception as ex:
            logger.info(f"{label}：模型 {spec} 无效（{ex}），尝试下一个候选")
            continue
        provider = registry.get_provider(entry.get("provider", ""))
        if provider is None:
            logger.info(f"{label}：provider {entry.get('provider')} 未配置，跳过 {entry.get('model')}")
            continue
        try:
            result = await asyncio.wait_for(
                provider.chat(messages, model=entry["model"],
                              temperature=_resolve_temperature(entry, temperature),
                              silent=silent),
                timeout=timeout)
        except asyncio.TimeoutError:
            logger.info(f"{label}：{entry.get('model')} 超时（>{timeout:g}s），尝试下一个候选")
            continue
        except Exception as ex:
            flag = "限流" if getattr(ex, "kind", "") == "rate_limit" else type(ex).__name__
            logger.info(f"{label}：{entry.get('model')} 调用失败（{flag}: {ex}），尝试下一个候选")
            continue
        text = (result.text or "").strip()
        data = extract_json(text) if json_output else None
        if json_output and data is None:
            logger.warning(f"{label}：要求 JSON 输出但解析失败，原文：{text[:120]!r}")
        return AskResult(text=text, data=data, usage=result.usage,
                         model=result.model, provider=result.provider)
    logger.warning(f"{label}：所有候选模型都失败")
    return None
