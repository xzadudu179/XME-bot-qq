# from nonebot import CommandSession
# from xme.plugins.commands.games.play import cmd_name
# from xme.xmetools.cmdtools import is_command
# from .game import Game
# from xme.xmetools.bottools import permission
# # from xme.xmetools.cmdtools import get_cmd_by_alias
# from xme.plugins.commands.xme_user.classes import user
# # from xme.plugins.commands.xme_user.classes.user import coin_name, coin_pronoun
# from character import get_message
# from xme.xmetools.debugtools import debug_msg
# # from nonebot.log import logger
# import random
# import math
# from xme.xmetools.msgtools import send_session_msg, aget_session_msg
# random.seed()

# TIMES_LIMIT = 10
# name = 'wordle'
# game_meta = {
#     "name": name,
#     "desc": get_message("plugins", cmd_name, name, 'desc'),
#     # "desc": "猜数字游戏",
#     "introduction": get_message("plugins", cmd_name, name, 'introduction',  times_limit=TIMES_LIMIT),
#     # "introduction": "指定一个数字范围并且生成一个随机数字，然后不断猜测直到猜中随机的数字。\n每次猜测时会说目标数字比猜测的数字大还是小",
#     "args": {
#         "c": "单词字数 (c=字数(4 及以上))",
#         # "r": "数字范围 (r=范围开始~范围结束)",
#         "t": "猜测次数限制 (t=次数限制)",
#         # "t": "猜测次数限制 (t=次数限制)"
#     },
#     "cost": 2,
#     "times_left_message": get_message("plugins", cmd_name, name, 'times_left', times_left='{times_left}'),
#     "limited_message": get_message("plugins", cmd_name, name, 'limited'),
#     "award_message": get_message("plugins", cmd_name, name, 'award', award="{award}", coins_left='{coins_left}'),
#     "no_award_message": get_message("plugins", cmd_name, name, 'no_award'),
# }