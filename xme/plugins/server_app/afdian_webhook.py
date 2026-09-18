"""爱发电 Webhook 路由：/afdian/webhook/<token> 接收订单实时推送并通知 SUPERUSER。

官方 webhook 不携带 sign 字段、无法验签，鉴权与防伪分三层：
- URL 密钥段：token 须与 keys.AFDIAN_WEBHOOK_TOKEN 一致，爱发电后台的通知地址
  需配置为 .../afdian/webhook/<该值>；
- 订单反查：经签名 API query-order 按 out_trade_no 核验订单真实存在且金额一致，
  通知文案以反查结果为准（官方建议幂等，重复推送只通知一次）；
- 频控：60s 窗口最多 10 条通知，超出仅 ack。
爱发电要求响应体为 {"ec":200,"em":""}；任何失败都只记日志并照常 ack。
"""
import hmac
import time
from collections import deque

import nonebot
from nonebot.log import logger
from quart import jsonify, request

from keys import AFDIAN_WEBHOOK_TOKEN
from xme.xmetools.afdiantools import AFDIAN_CLIENT, AfdianApiError
from xme.xmetools.texttools import escape_cq
from xme.plugins.commands.xme_user.classes.user import User
from xme.xmetools.msgtools import send_to_superusers

bot = nonebot.get_bot()  # 在此之前必须已经 init


class _NotifyGuard:
    """webhook 通知的频控与订单号幂等去重（仅事件循环内访问，无锁）。"""

    def __init__(self, window: float = 60.0, max_notifies: int = 10, seen_cap: int = 200):
        self._window = window
        self._max_notifies = max_notifies
        self._notify_times: deque[float] = deque()
        self._seen: deque[str] = deque(maxlen=seen_cap)

    def allow_notify(self) -> bool:
        """本次通知是否放行（滑动窗口内未超上限）；放行即占用一个名额。"""
        now = time.time()
        while self._notify_times and now - self._notify_times[0] > self._window:
            self._notify_times.popleft()
        if len(self._notify_times) >= self._max_notifies:
            return False
        self._notify_times.append(now)
        return True

    def mark_seen(self, out_trade_no: str) -> bool:
        """记录订单号；重复推送（已通知过）返回 False。"""
        if out_trade_no in self._seen:
            return False
        self._seen.append(out_trade_no)
        return True


_guard = _NotifyGuard()


def _format_order_message(order: dict, bound_qq: int | None) -> str:
    """把（已核验的）订单格式化为通知文案，动态字段一律 CQ 转义；绑定用户附带 @。"""
    plan_title = escape_cq(str(order.get("plan_title") or "") or "无偿赞助")
    remark = escape_cq(str(order.get("remark") or "") or "无")
    amount = str(order.get("show_amount") or order.get("total_amount") or "0")
    user_name = escape_cq(str(order.get("user_name") or order.get("user_id") or "神秘发电用户"))
    lines = [
        "收到了新的发电支持！",
        f"用户：{user_name}",
        f"金额：¥{amount}",
        f"方案：{plan_title}",
        f"备注：{remark}",
    ]
    if bound_qq:
        lines.append(f"[CQ:at,qq={bound_qq}] 感谢发电！")
    return "\n".join(lines)


def _to_float(value) -> float | None:
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


async def _verify_order(order: dict) -> dict | None:
    """经签名 API 反查订单真伪：存在、status==2 且金额一致时返回 API 侧订单。

    反查失败（网络异常等）按可疑丢弃：通知非关键路径，订单仍可经 /afdian
    stat 查询，宁漏报不误报。
    """
    out_trade_no = str(order.get("out_trade_no") or "")
    if not out_trade_no:
        return None
    try:
        api_orders = await AFDIAN_CLIENT.get_orders_by_no([out_trade_no])
    except AfdianApiError as ex:
        logger.warning(f"afdian webhook 订单反查失败，按可疑丢弃: {ex}")
        return None
    for api_order in api_orders:
        if str(api_order.get("out_trade_no")) != out_trade_no:
            continue
        if api_order.get("status") != 2:
            return None
        webhook_amount = _to_float(order.get("total_amount"))
        api_amount = _to_float(api_order.get("total_amount"))
        if webhook_amount is not None and api_amount is not None \
                and abs(webhook_amount - api_amount) > 0.005:
            logger.warning(f"afdian webhook 订单金额与反查不一致，丢弃: {out_trade_no}")
            return None
        return api_order
    return None


@bot.server_app.route('/afdian/webhook/<token>', methods=['POST'])
async def afdian_webhook(token: str):
    """接收爱发电订单推送：URL 密钥鉴权 + API 反查核验后通知 SUPERUSER。"""
    if not hmac.compare_digest(token, AFDIAN_WEBHOOK_TOKEN):
        logger.warning("afdian webhook 收到密钥错误的回调，已忽略")
        return jsonify({"ec": 200, "em": ""})
    data = await request.get_json(silent=True) or {}
    order = ((data.get("data") or {}).get("order")) or {}
    try:
        if not (isinstance(order, dict) and order.get("status") == 2):
            return jsonify({"ec": 200, "em": ""})
        if not _guard.allow_notify():
            logger.warning("afdian webhook 通知超出频控窗口，本次仅 ack")
            return jsonify({"ec": 200, "em": ""})
        verified = await _verify_order(order)
        if verified is None:
            logger.warning(f"afdian webhook 订单未能通过反查核验，已丢弃: {order.get('out_trade_no')}")
            return jsonify({"ec": 200, "em": ""})
        if not _guard.mark_seen(str(verified.get("out_trade_no") or "")):
            return jsonify({"ec": 200, "em": ""})  # 重复推送：幂等，只通知一次
        user = User.load_by_afdian_id(str(verified.get("user_id") or ""))
        bound_qq = user.id if user else None
        await send_to_superusers(bot, _format_order_message(verified, bound_qq))
    except Exception as e:
        logger.warning(f"afdian webhook 通知失败: {e}")
    return jsonify({"ec": 200, "em": ""})
