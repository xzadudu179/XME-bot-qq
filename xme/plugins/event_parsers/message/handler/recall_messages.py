from nonebot.session import BaseSession
from nonebot import NoneBot
from xme.xmetools import json_tools
import config
# import asyncio

async def recall_handler(session: BaseSession, bot: NoneBot):
    recalls = json_tools.read_from_path('./recalls.json')['recalls']
    if session['group_id'] not in config.GROUPS_WHITELIST or session['user_id'] == session.self_id:
        return
    for recall in recalls:
        if type(recall) == list:
            if session['raw_message'].strip() not in recall: continue
        elif recall not in session['raw_message'].strip(): continue
        print(f"{session['raw_message']} 是/有不该出现的词汇: {recall}")
        # asyncio.sleep(0.5)
        await bot.api.delete_msg(message_id=session['message_id'])
        await bot.send_group_msg(message="不要发奇怪的词汇 uwu", group_id=session['group_id'])
        return