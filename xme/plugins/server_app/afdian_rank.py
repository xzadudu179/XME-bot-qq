"""爱发电发电排行 API：GET /afdian/rank 返回全部发电用户的排行数据。

按真实付款金额（订单 total_amount，兑换码计 0）降序，仅供前端展示；
累计收入总额不在本接口暴露（收入统计仅 SUPERUSER 可见）。
数据经 get_ranking 的客户端缓存，5 分钟内重复请求不额外调用爱发电 API。
跨域头由 server_app/cors.py 的全局策略按来源白名单统一附加。
"""
import nonebot
from nonebot.log import logger
from quart import jsonify, request

from xme.plugins.server_app.client_info import log_visit
from xme.xmetools.afdiantools import AFDIAN_CLIENT, AfdianApiError, RankEntry, get_ranking

bot = nonebot.get_bot()  # 在此之前必须已经 init


def _entry_to_dict(entry: RankEntry) -> dict:
    """把排行条目转为前端可直接消费的 dict（时间为 unix 秒）。"""
    return {
        "rank": entry.rank,
        "user_id": entry.user_id,
        "name": entry.name,
        "avatar": entry.avatar,
        "amount": entry.amount,
        "order_count": entry.order_count,
        "last_pay_time": entry.last_pay_time,
    }


def _json(data: list[dict], ok: bool, message: str = ""):
    """构造排行响应：统一结构、中文不转义、允许前端缓存 60 秒。"""
    resp = jsonify({"success": ok, "message": message, "total": len(data), "data": data})
    resp.json_module.ensure_ascii = False
    resp.headers["Cache-Control"] = "public, max-age=60"
    return resp


@bot.server_app.route('/afdian/rank')
async def afdian_rank():
    """返回全部发电用户排行（含昵称、头像、金额、次数、最近发电时间）。"""
    log_visit("爱发电排行", request)
    try:
        entries = await get_ranking(AFDIAN_CLIENT)
    except AfdianApiError as e:
        logger.warning(f"afdian rank 接口获取排行失败: {e}")
        return _json([], False, "爱发电接口请求失败，请稍后再试")
    return _json([_entry_to_dict(entry) for entry in entries], True)
