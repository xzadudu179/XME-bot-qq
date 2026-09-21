"""爱发电 OAuth 回调 API：/afdian/oauth 校验 state、兑换 code 并绑定 afdian_id。

返回 JSON 而非页面，展示层由独立前端项目完成；跨域头由 server_app 的 CORS 策略统一加
（白名单见 cors.py）。
"""
import nonebot
from nonebot.log import logger
from quart import jsonify, request
from xme.plugins.commands.xme_user.classes.user import User, try_load
from xme.xmetools.afdiantools import AFDIAN_CLIENT, AfdianApiError
from xme.xmetools.mailtools import send_bot_email

bot = nonebot.get_bot()  # 在此之前必须已经 init


def _json_result(ok: bool, title: str, reason: str):
    """统一的 JSON 结果体，跨域头由 cors 模块按白名单补上。"""
    return jsonify({"success": ok, "title": title, "reason": reason})


@bot.server_app.route('/afdian/oauth')
async def afdian_oauth():
    """处理爱发电 OAuth 重定向：校验 state -> 兑换 code -> 绑定 -> 返回 JSON。"""
    code = request.args.get('code', '')
    state = request.args.get('state', '')
    qq = AFDIAN_CLIENT.parse_login_state(state)
    if not qq:
        return _json_result(False, "链接无效", "unknown link")
    if not code:
        return _json_result(False, "授权未完成", "no code")
    try:
        data = await AFDIAN_CLIENT.exchange_oauth_code(code)
    except AfdianApiError as e:
        logger.warning(f"afdian oauth code 兑换失败 (qq={qq}): {e}")
        return _json_result(False, "绑定失败", "unknown error")
    afdian_user_id = str(data.get("user_id") or "")
    if not afdian_user_id:
        return _json_result(False, "绑定失败", "no afdian user id")
    user = try_load(int(qq))
    if user is None:
        logger.warning(f"afdian oauth 绑定失败：qq {qq} 不存在用户记录")
        return _json_result(False, "绑定失败", "请先与 bot 私聊使用任意指令注册后再绑定")
    # 在此之前，检查一遍其他用户有没有绑定这个账号
    bind_user = User.load_by_afdian_id(afdian_user_id)
    if bind_user is not None:
        if bind_user.id != user.id:
            # 不回显已绑定者的 QQ 号（避免向请求方泄露他人账号信息）
            return _json_result(False, "绑定失败", "该账号已经被其他用户绑定了")
        return _json_result(False, "绑定失败", f"你已绑定了爱发电账号，如需更换请使用 /afd unbind 解绑。")
    # users = [u["user_id"] for u in User.get_users() if u.get("afdian_id", "") and u["user_id"] != user.id]
    user.afdian_id = afdian_user_id
    user.update("afdian_id")
    logger.info(f"用户 {qq} 已绑定爱发电账号 {afdian_user_id}")
    return _json_result(True, "绑定成功", f"该账号已绑定至 qq {qq}")
