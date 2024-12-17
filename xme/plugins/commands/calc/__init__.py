from nonebot import on_command, CommandSession
from xme.xmetools.doc_gen import CommandDoc
from character import get_message
from sympy.core.sympify import SympifyError
from .parser import parse_polynomial
from .func import funcs
from xme.xmetools.command_tools import send_msg

alias = ['计算', 'cc']
__plugin_name__ = 'calc'
__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    desc=get_message(__plugin_name__, 'desc'),
    introduction=get_message(__plugin_name__, 'introduction'),
    usage=f'(算式)',
    permissions=[],
    alias=alias
))

@on_command(__plugin_name__, aliases=alias, only_to_me=False)
async def _(session: CommandSession):
    message = ""
    arg = session.current_arg_text.strip()
    if not arg:
        return await send_msg(session, get_message(__plugin_name__, 'no_arg'))
    if arg == 'funcs':
        message = get_message(__plugin_name__, 'func_intro') + "\n"
        for k, v in funcs.items():
            message += f'{k}{v["body"]}: {v["info"] if v["info"] else "-"}\n'
        if len(funcs.items()) < 1:
            message += get_message(__plugin_name__, 'func_nothing') + '\n'
        message += get_message(__plugin_name__, 'func_builtin_intro') + "\n"
        for k, v in func.builtins.items():
            message += f'{k}: {v if v else "-"}\n'
        return await send_msg(session, '\n' + message)
    try:
        formula, result = parse_polynomial(arg)
        message = get_message(__plugin_name__, 'success', result=str(result).replace("**", "^"), formula=formula)
        try:
            float_result = str(float(result.evalf()))
        except Exception as ex:
            print(ex)
            print(result)
            float_result = None
        if float_result:
            message += '\n' + get_message(__plugin_name__, 'float_result', float_result=float_result)
    except SyntaxError as ex:
        return await send_msg(session, get_message(__plugin_name__, 'syntaxerror', ex=ex))
    except SympifyError as ex:
        return await send_msg(session, get_message(__plugin_name__, 'sympifyerror', ex=ex))
    except Exception as ex:
        return await send_msg(session, get_message(__plugin_name__, 'error', ex=ex))
    await send_msg(session, message)