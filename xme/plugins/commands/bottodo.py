from nonebot import on_command, CommandSession
from xme.xmetools.doc_tools import CommandDoc
import config
from character import get_message
from xme.xmetools.command_tools import send_session_msg
from xme.xmetools import text_tools

alias = ['bot待办', 'show_bottodo']
REMOVES = ("rm", 'remove', 'delete', 'del', '删除')
__plugin_name__ = 'bottodo'
__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    desc=get_message(__plugin_name__, 'desc'),
    introduction=get_message(__plugin_name__, 'introduction'),
    usage=f'<待办名>',
    permissions=["无"],
    alias=alias
))

@on_command(__plugin_name__, aliases=alias, only_to_me=False, permission=lambda _: True)
async def _(session: CommandSession):
    message = get_message(__plugin_name__, 'todo_prefix') + '\n'
    arg = session.current_arg_text.strip()
    if arg.startswith(REMOVES) and session.event.user_id in config.SUPERUSERS:
        try:
            arg = text_tools.remove_prefix(arg, REMOVES)
            index = int(arg)
        except:
            await send_session_msg(session, get_message(__plugin_name__,'remove_todo_failed', arg=arg))
            return
        removed = remove_todo(index)
        await send_session_msg(session, get_message(__plugin_name__,'remove_todo_success', todo=removed))
        return
    elif arg and session.event.user_id in config.SUPERUSERS:
        add_todo(arg)
        await send_session_msg(session, get_message(__plugin_name__, 'add_todo_success', todo=arg))
        return
    elif arg:
        await send_session_msg(session, get_message(__plugin_name__, 'modify_todo_failed'))
        return
    lines = []
    try:
        with open("TODO.txt", "r", encoding='utf-8') as file:
            for line in file:
                lines.append(line.strip())
    except FileNotFoundError:
        pass
    if len(lines) < 1:
        message += get_message(__plugin_name__, 'no_todo')
    message += '\n'.join([f'{i + 1}. {line}' for i, line in enumerate(lines)])
    await send_session_msg(session, message)

def add_todo(todo_str):
    with open("TODO.txt", "a", encoding='utf-8') as file:
        file.write(todo_str + '\n')

def remove_todo(todo_index):
    removed = ''
    with open("TODO.txt", "r", encoding='utf-8') as file:
        lines = file.readlines()
    with open("TODO.txt", "w", encoding='utf-8') as file:
        for i, line in enumerate(lines):
            if i != todo_index - 1:
                file.write(line)
            else:
                removed = line.strip()
    return removed