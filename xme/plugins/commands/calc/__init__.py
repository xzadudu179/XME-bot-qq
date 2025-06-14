from nonebot import on_command, CommandSession
from xme.xmetools.doctools import CommandDoc
from character import get_message
from xme.xmetools.texttools import contains_blacklisted
from xme.xmetools.functools import run_with_timeout
from xme.xmetools.bottools import permission
from sympy.core.sympify import SympifyError
from .parser import parse_polynomial
from .func import funcs
from xme.xmetools.msgtools import send_session_msg, send_to_superusers
from xme.xmetools.imgtools import image_msg
from xme.xmetools.drawtools import draw_exprs, draw_3d_exprs

alias = ['计算', 'cc']
permissions = ["是 SUPERUSER"]
__plugin_name__ = 'calc'
__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    usage=f'(算式)',
    permissions=permissions,
    alias=alias
))

@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda x: True)
@permission(lambda sender: sender.is_superuser, permission_help=permissions)
async def _(session: CommandSession):
    message = "uwu"
    arg = session.current_arg_text.strip()
    if not arg:
        return await send_session_msg(session, get_message("plugins", __plugin_name__, 'no_arg'))
    if arg == 'funcs':
        message = get_message("plugins", __plugin_name__, 'func_intro') + "\n"
        for k, v in funcs.items():
            message += f'{k}{v["body"]}: {v["info"] if v["info"] else "-"}\n'
        if len(funcs.items()) < 1:
            message += get_message("plugins", __plugin_name__, 'func_nothing') + '\n'
        return await send_session_msg(session, '\n' + message)
    if arg == 'builtins':
        message += get_message("plugins", __plugin_name__, 'func_builtin_intro') + "\n"
        for k, v in func.builtins.items():
            message += f'{k}: {v if v else "-"}\n'
        return await send_session_msg(session, '\n' + message)
    if len(arg) > 100:
        message = get_message("plugins", __plugin_name__, 'too_long')
        return await send_session_msg(session, message)
    if contains_blacklisted(arg):
        message = get_message("plugins", __plugin_name__, 'have_risk')
        await send_to_superusers(session.bot, f"警告：{session.event.user_id} 在 calc 指令里输入了有注入风险的表达式：{arg}")
        return await send_session_msg(session, message)
    try:
        TIMEOUT_SECS = 15
        formula, result, is_image = run_with_timeout(parse_polynomial, TIMEOUT_SECS / 2, f"计算超时 (>{TIMEOUT_SECS / 2}s)", arg)
        if is_image > 0:
            await send_session_msg(session, get_message("plugins", __plugin_name__, 'drawing'))
            if is_image == 1:
                path, _ = run_with_timeout(draw_exprs, TIMEOUT_SECS, f"绘图超时 (>{TIMEOUT_SECS}s)", *result)
                # path, _ = linux_draw_exprs(*result)
            elif is_image == 2:
                path, _ = run_with_timeout(draw_3d_exprs, TIMEOUT_SECS, f"绘图超时 (>{TIMEOUT_SECS}s)", *result)
                # path, _ = linux_draw_3d_exprs(*result)
            # message = get_message("plugins", __plugin_name__, 'success_image', image=f"[CQ:image,file=http://server.xzadudu179.top:17980/temp/{path}]", formula=formula)
            print("正在发送完成消息...")
            # message = get_message("plugins", __plugin_name__, 'success_image', image=str(image_msg(path)), formula=formula)
            message = await image_msg(path)
            # print(message)
            await send_session_msg(session, message)
            print("发送完成")
            return
        else:
            message = get_message("plugins", __plugin_name__, 'success', result=str(result).replace("**", "^"), formula=formula)
        try:
            float_result = str(float(result.doit()))
        except Exception as ex:
            print(ex)
            print(result)
            float_result = None
        if float_result:
            message += '\n' + get_message("plugins", __plugin_name__, 'float_result', float_result=float_result)
    except SyntaxError as ex:
        # return await send_session_msg(session, get_message("plugins", __plugin_name__, 'syntaxerror', ex=traceback.format_exc()))
        return await send_session_msg(session, get_message("plugins", __plugin_name__, 'syntaxerror', ex=ex))
    except SympifyError as ex:
        # return await send_session_msg(session, get_message("plugins", __plugin_name__, 'sympifyerror', ex=traceback.format_exc()))
        return await send_session_msg(session, get_message("plugins", __plugin_name__, 'sympifyerror', ex=ex))
    except Exception as ex:
        # return await send_session_msg(session, get_message("plugins", __plugin_name__, 'error', ex=traceback.format_exc()))
        return await send_session_msg(session, get_message("plugins", __plugin_name__, 'error', ex=ex))
    await send_session_msg(session, message)