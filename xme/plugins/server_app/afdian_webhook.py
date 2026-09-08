"""爱发电 Webhook 路由：/afdian/webhook 接收订单实时推送并通知 SUPERUSER。

需在爱发电后台（dashboard/dev）把通知地址配置为本路由的公网 URL；
爱发电要求响应体为 {"ec":200,"em":""}。通知放在响应前同步处理，
全程捕获异常以保证 ack 一定返回。
"""
import nonebot
from nonebot.log import logger
from quart import jsonify, request
from xme.plugins.commands.xme_user.classes.user import User
from xme.xmetools.msgtools import send_to_superusers

bot = nonebot.get_bot()  # 在此之前必须已经 init


def _format_order_message(order: dict, bound_qq: int | None) -> str:
    """把订单格式化为通知文案，绑定过爱发电的用户附带 @。"""
    plan_title = str(order.get("plan_title") or "") or "无偿赞助"
    remark = str(order.get("remark") or "") or "无"
    amount = str(order.get("show_amount") or order.get("total_amount") or "0")
    user_name = str(order.get("user_name") or order.get("user_id") or "神秘发电用户")
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


@bot.server_app.route('/afdian/webhook', methods=['POST'])
async def afdian_webhook():
    """接收爱发电订单推送，回复 ack 并把订单信息私聊通知 SUPERUSER。"""
    data = await request.get_json(silent=True) or {}
    order = ((data.get("data") or {}).get("order")) or {}
    try:
        if order and order.get("status") == 2:
            user = User.load_by_afdian_id(str(order.get("user_id") or ""))
            bound_qq = user.id if user else None
            await send_to_superusers(bot, _format_order_message(order, bound_qq))
    except Exception as e:
        logger.warning(f"afdian webhook 通知失败: {e}")
    return jsonify({"ec": 200, "em": ""})
