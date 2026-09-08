from nonebot import CommandSession
from sympy.core.sympify import SympifyError

from character import get_message
from nonebot.log import logger
from xme.xmetools.bottools import permission
from xme.xmetools.debugtools import debug_msg
from xme.xmetools.doctools import CommandDoc
from xme.xmetools.msgtools import image_msg, send_session_msg, send_to_superusers
from xme.xmetools.plugintools import on_command
from xme.xmetools.sandboxtools import SandboxError, SandboxTimeoutError, run_in_sandbox
from xme.xmetools.texttools import contains_blacklisted

from .constants import DRAW_FSIZE_MB, DRAW_MEM_MB, DRAW_TIMEOUT, MAX_ARG_LEN, PARSE_TIMEOUT
from .evaluator import CalcResult, evaluate_formula
from .func import builtins, funcs

alias = ['计算', 'cc']
permissions = ["是 SUPERUSER"]
__plugin_name__ = 'calc'
__plugin_usage__ = CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    usage='(算式)',
    permissions=permissions,
    alias=alias
)

@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda x: True)
@permission(lambda sender: True, permission_help=permissions)
async def _(session: CommandSession):
    arg = session.current_arg_text.strip()
    if not arg:
        return await send_session_msg(session, get_message("plugins", __plugin_name__, 'no_arg'))
    if arg == 'funcs':
        message = get_message("plugins", __plugin_name__, 'func_intro') + "\n"
        for k, v in funcs.items():
            message += f'{k}{v["body"]}: {v["info"] if v["info"] else "-"}\n'
        if len(funcs) < 1:
            message += get_message("plugins", __plugin_name__, 'func_nothing') + '\n'
        return await send_session_msg(session, '\n' + message)
    if arg == 'builtins':
        message = get_message("plugins", __plugin_name__, 'func_builtin_intro') + "\n"
        for k, v in builtins.items():
            message += f'{k}: {v if v else "-"}\n'
        return await send_session_msg(session, '\n' + message)
    if len(arg) > MAX_ARG_LEN:
        return await send_session_msg(session, get_message("plugins", __plugin_name__, 'too_long'))
    if contains_blacklisted(arg):
        await send_to_superusers(session.bot, f"警告：{session.event.user_id} 在 calc 指令里输入了有注入风险的表达式：{arg}")
        return await send_session_msg(session, get_message("plugins", __plugin_name__, 'have_risk'))
    try:
        # 沙箱回传帧是 JSON 纯数据，dataclass 会被自动转成 dict，这里重建
        calc_result = CalcResult(**await run_in_sandbox(evaluate_formula, arg, timeout=PARSE_TIMEOUT))
        if calc_result.draw_mode:
            # 延迟导入：matplotlib 导入内存开销大，求值沙箱子进程不需要它
            from xme.xmetools.drawtools import draw_3d_exprs, draw_exprs
            await send_session_msg(session, get_message("plugins", __plugin_name__, 'drawing'))
            draw_func = draw_exprs if calc_result.draw_mode == 1 else draw_3d_exprs
            try:
                path, _ = await run_in_sandbox(
                    draw_func, *calc_result.draw_exprs,
                    timeout=DRAW_TIMEOUT, mem_mb=DRAW_MEM_MB, fsize_mb=DRAW_FSIZE_MB)
            except SandboxTimeoutError:
                return await send_session_msg(session, get_message("plugins", __plugin_name__, 'error', ex=f"绘图超时 (>{DRAW_TIMEOUT}s)"))
            debug_msg("正在发送完成消息...")
            message = await image_msg(path)
            debug_msg("发送完成")
            return await send_session_msg(session, message)
        message = get_message("plugins", __plugin_name__, 'success', result=calc_result.result_str.replace("**", "^"), formula=calc_result.formula)
        if calc_result.float_str:
            message += '\n' + get_message("plugins", __plugin_name__, 'float_result', float_result=calc_result.float_str)
    except SandboxTimeoutError:
        return await send_session_msg(session, get_message("plugins", __plugin_name__, 'error', ex=f"计算超时 (>{PARSE_TIMEOUT}s)"))
    except SyntaxError as ex:
        return await send_session_msg(session, get_message("plugins", __plugin_name__, 'syntaxerror', ex=ex))
    except SympifyError as ex:
        return await send_session_msg(session, get_message("plugins", __plugin_name__, 'sympifyerror', ex=ex))
    except SandboxError as ex:
        logger.warning(f"calc 沙箱执行失败: {ex}")
        return await send_session_msg(session, get_message("plugins", __plugin_name__, 'error', ex=ex))
    except Exception as ex:
        logger.exception(ex)
        return await send_session_msg(session, get_message("plugins", __plugin_name__, 'error', ex=ex))
    await send_session_msg(session, message)
