"""爱发电 OAuth 回调 API：/afdian/oauth 校验 state、兑换 code 并绑定 afdian_id。

返回 JSON 而非页面，展示层由独立前端项目完成；前端跨域调用时依赖
keys.AFDIAN_OAUTH_FRONTEND_ORIGIN 的 CORS 头。
"""
import nonebot
from nonebot.log import logger
from quart import jsonify, request
from keys import AFDIAN_OAUTH_FRONTEND_ORIGIN
from xme.plugins.commands.xme_user.classes.user import User, try_load
from xme.xmetools.afdiantools import AFDIAN_CLIENT, AfdianApiError
from xme.xmetools.mailtools import send_bot_email

bot = nonebot.get_bot()  # 在此之前必须已经 init


def _json_result(ok: bool, title: str, reason: str):
    """统一的 JSON 结果体，附带 CORS 头供前端项目跨域调用。"""
    resp = jsonify({"success": ok, "title": title, "reason": reason})
    resp.headers["Access-Control-Allow-Origin"] = AFDIAN_OAUTH_FRONTEND_ORIGIN
    return resp


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
    # 在此之前，检查一遍其他用户有没有绑定这个账号
    bind_user = User.load_by_afdian_id(afdian_user_id)
    if bind_user is not None:
        if bind_user.id != user.id:
            return _json_result(False, "绑定失败", f"该账号已经被他人绑定了(qq{bind_user.id})")
        return _json_result(False, "绑定失败", f"你已绑定了爱发电账号，如需更换请使用 /afd unbind 解绑。")
    # users = [u["user_id"] for u in User.get_users() if u.get("afdian_id", "") and u["user_id"] != user.id]
    user.afdian_id = afdian_user_id
    user.update("afdian_id")
    logger.info(f"用户 {qq} 已绑定爱发电账号 {afdian_user_id}")
    return _json_result(True, "绑定成功", f"该账号已绑定至 qq {qq}")
