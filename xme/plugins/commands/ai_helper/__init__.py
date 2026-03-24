from nonebot import CommandSession
from xme.xmetools.plugintools import on_command
# from xme.xmetools.cmdtools import use_args
from xme.xmetools.doctools import CommandDoc, shell_like_usage
# from nonebot.argparse import ArgumentParser
from xme.xmetools.bottools import XmeArgumentParser
from .commands import clear_history
import cn2an
from traceback import format_exc
from xme.xmetools.debugtools import debug_msg
from nonebot.log import logger
import httpx
# from xme.xmetools.texttools import dec_to_chinese
from xme.xmetools.jsontools import read_from_path
from xme.xmetools.cmdtools import is_command
from xme.xmetools.msgtools import send_session_msg, aget_arg_with_timeout
from xme.xmetools.bottools import get_user_name
from character import get_message, get_character_item, character_format
from xme.xmetools.timetools import TimeUnit, Timer, get_time_now
from keys import GLM_API_KEY
from xme.plugins.commands.xme_user.classes import user as u
from zhipuai import ZhipuAI
from zhipuai.core._errors import ZhipuAIError
MAX_CHECK_TIMES = 1000

class AIHelper:
    def __init__(self, ai_client: ZhipuAI):
        self.client = ai_client


    async def ai_init(self, messages):
        response = self.client.chat.asyncCompletions.create(
            # model="glm-4-flashx",
            model="glm-5",
            messages=messages,
            tools=[
                {
                    "type": "web_search",
                    "web_search": {
                        "enable": "True",
                        "search_engine": "search_pro",
                        "search_result": "True",
                        "search_prompt": "你可以进行数据汇总，语义理解与矛盾信息清洗处理。参考以下信息，间接、准确地回答搜索结果：{{search_result}}中的关键信息，并且根据实际对话情况整理自己搜到的数据并作出回答。",
                        "search_intent": "True",
                        "count": "7",
                        "search_recency_filter": "oneYear",
                        "content_size": "medium"
                    }
                }
            ],
            # tools=[
            #     {
            #         "type": "retrieval",
            #         "retrieval": {
            #             "knowledge_id": knowledge_id,
            #             "prompt_template": "若用户提出 BOT/漠月/指令 相关问题或其他问题，默认先从文档\n\"\"\"\n{{knowledge}}\n\"\"\"\n中找问题\n\"\"\"\n{{question}}\n\"\"\"\n的答案，找不到答案就用自身知识回答并且告诉用户该信息不是来自文档。\n不要复述问题，直接开始回答。"
            #         }
            #     }
            # ],
            temperature=0.3

        )
        return response

    # async def talk(self, messages):
    #     # ai_helper = AIHelper(client)
    #     response = await self.ai_init(messages)
    #     task_id = response.id
    #     task_status = ''
    #     get_cnt = 0

    #     t = Timer()
    #     t.start()
    #     while task_status != 'SUCCESS' and task_status != 'FAILED' and get_cnt <= MAX_CHECK_TIMES:
    #         reply = await aget_arg_with_timeout(session, 0.5)
    #         if reply is not None and reply.strip() == "aistop":
    #             await send_session_msg(session, get_message("plugins", __plugin_name__, "ai_send_interrupted"))
    #             return False
    #         result_response = self.client.chat.asyncCompletions.retrieve_completion_result(id=task_id)
    #         # print(result_response)
    #         task_status = result_response.task_status
    #         # await asyncio.sleep(0.5)
    #         get_cnt += 1
    #     try:
    #         if get_cnt >= MAX_CHECK_TIMES:
    #             t.stop()
    #             await send_session_msg(session, get_message("plugins", __plugin_name__, "ai_send_timeout", secs=t.get_timer_value()))
    #             return False
    #         ans = result_response.choices[0].message.content
    #         build_history(user=user, ask=text, ans=ans)
    #         logger.info(f"AI 返回了以下 response：{result_response}")
    #         debug_msg("处理结果")
    #         return result_response.choices[0].message.content
    #     except AttributeError as ex:
    #         logger.error("attribute 错误: ", ex)
    #         await send_session_msg(session, get_message("plugins", __plugin_name__, "attribute_error", content=result_response))
    #         return False

    async def user_talk(self, session: CommandSession, role, user, text):
        # ai_helper = AIHelper(client)
        response = await self.ai_init([
            {"role": "system","content": role},
            {"role": "user","content": f"{await get_history(user)}\n{text}"}
        ])
        task_id = response.id
        task_status = ''
        get_cnt = 0

        t = Timer()
        t.start()
        while task_status != 'SUCCESS' and task_status != 'FAILED' and get_cnt <= MAX_CHECK_TIMES:
            debug_msg(f"尝试获取 AI 连接第 {get_cnt} 次")
            reply = await aget_arg_with_timeout(session, 0.5)
            if reply is not None and is_command(reply):
                await send_session_msg(session, get_message("plugins", __plugin_name__, "ai_sending"))
            if reply is not None and reply.strip() == "aistop":
                await send_session_msg(session, get_message("plugins", __plugin_name__, "ai_send_interrupted"))
                return False
            # result_response = None
            result_response = self.client.chat.asyncCompletions.retrieve_completion_result(id=task_id)
            # print(result_response)
            task_status = result_response.task_status
            # await asyncio.sleep(0.5)
            get_cnt += 1
            if get_cnt >= MAX_CHECK_TIMES:
                t.stop()
                await send_session_msg(session, get_message("plugins", __plugin_name__, "ai_send_timeout", secs=t.get_timer_value()))
                return False
        try:
            ans = result_response.choices[0].message.content
            build_history(user=user, ask=text, ans=ans)
            logger.info(f"AI 返回了以下 response：{result_response}")
            debug_msg("处理结果")
            return result_response.choices[0].message.content
        except AttributeError as ex:
            logger.error("attribute 错误:", ex)
            await send_session_msg(session, get_message("plugins", __plugin_name__, "attribute_error", content=result_response))
            return False
        except ZhipuAIError as ex:
            logger.error(f"AI 出现错误: {ex}")
            code = result_response.get("error", {}).get("code", "未知")
            message = result_response.get("error", {}).get("message", "未知")
            await send_session_msg(session, get_message("plugins", __plugin_name__, "ai_error", content=result_response, code=code, message=message))
            return False
cmds = {
        "clear": {
            "content": clear_history,
            "args": "",
            "desc": "清除你的所有对话历史"
        }
    }

def get_command_list():
    cmd_list_str = "当前指令参数列表：\n"
    for k, v in cmds.items():
        cmd_list_str += f"{k} {v['args']}: {v['desc']}\n"
    return cmd_list_str

def parse_control(session: CommandSession, text: str, user: u.User) -> str:
    text, args = text.split(" ")[0], text.split(" ")[1:]
    def parse_func(text, **_):
        return f"没有这个指令 \"{text}\" 哦"
    cmd = cmds.get(text, None)
    if cmd is not None:
        parse_func = cmd["content"]
    return parse_func(session=session, user=user, text=text, args=args)

arg_usage = shell_like_usage("OPTION", [
    {
        "name": "help",
        "abbr": "h",
        "desc": "查看帮助"
    },
    {
        "name": "raw",
        "abbr": "r",
        "desc": "会把之后的文本全都解析为单纯的文本（注：这个参数优先级最大）"
    },
    {
        "name": "ctrl",
        "abbr": "c",
        "desc": f"只需要在任意地方输入 -c 即可将原本输入给 AI 的内容变为指令\n{get_command_list()}"
    }

])

alias = ['ai', 'aih']
__plugin_name__ = 'ai_helper'
__plugin_usage__ = CommandDoc(
    name=__plugin_name__,
    desc=get_message("plugins", __plugin_name__, 'desc'),
    introduction=get_message("plugins", __plugin_name__, 'introduction'),
    usage=f'(对话内容) [OPTION]\n{arg_usage}',
    permissions=[],
    alias=alias
)

# history = read_from_path("./ai_configs.json")[__plugin_name__]["history"]

TIMES_LIMIT = 15
@on_command(__plugin_name__, aliases=alias, only_to_me=False, shell_like=True, permission=lambda _: True)
@u.using_user(save_data=True)
@u.limit(__plugin_name__, 1, get_message("plugins", __plugin_name__, 'limited'), unit=TimeUnit.HOUR, count_limit=TIMES_LIMIT, fails=lambda x: x == 2 or not x)
async def _(session: CommandSession, user: u.User):
    times_left_now = TIMES_LIMIT - u.get_limit_info(user, __plugin_name__)[1] - 1
    MAX_LENGTH = 1000
    intext = ""
    if "-r " in session.current_arg_text:
        intext = "-r"
    elif "--raw " in session.current_arg_text:
        intext = '--raw'
    if intext:
        text = intext.join(session.current_arg_text.split(intext)[1:])
    else:
        parser = XmeArgumentParser(session=session, usage=arg_usage)
        parser.exit_mssage = get_message("config", "shell_error", command_name=__plugin_name__)
        parser.add_argument('-c', '--ctrl', action='store_true', default=False)
        parser.add_argument('text', nargs='*')
        args = parser.parse_args(session.argv)
        # print(session.argv)
        text =  ' '.join(args.text).strip()
        if args.ctrl and text and len(text) <= MAX_LENGTH:
            await send_session_msg(session, parse_control(session, text, user))
            return 2
    if not text:
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'no_arg'))
        return False
    if len(text) > MAX_LENGTH:
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'too_long', count=MAX_LENGTH))
        return False
    await send_session_msg(session, get_message("plugins", __plugin_name__, 'talking_to_ai'))
    try:
        # print("正常")
        t = await talk(session, text, user)
        if not t:
            return False
        await send_session_msg(
            session,
            get_message("plugins", __plugin_name__, 'talk_result', talk=t, times_left_now=cn2an.an2cn(times_left_now)), tips=True
        )
        return True
    except Exception:
        logger.error("错误：", format_exc())
        await send_session_msg(session, get_message("config", "unknown_error", ex=format_exc()))
        return False

async def get_history(user: u.User):
    user_history = user.ai_history
    if not user_history:
        return ""
    build_str = "历史记录：\n"
    uname = await get_user_name(user.id, default='未知用户')
    for i, item in enumerate(user_history):
        build_str += f"{i + 1}. [{item.get('time', '未知时间')}]][{uname}(qq{user.id})]: {item['ask']};\n\t你回答：{item['ans']}\n----------\n"
    build_str += "=" * 15
    build_str += f"\n当前对话（时间为 {get_time_now()}）发送者为{uname}(qq{user.id})："
    return build_str

def build_history(user: u.User, ask, ans):
    # user_history = user.ai_history
    # if user_history is None:
    #     user.ai_history = []
    user.ai_history.append({
        "ask": ask,
        "ans": ans,
        "time": get_time_now()
    })
    if len(user.ai_history) > 20:
        del user.ai_history[-1]
#     save_history()

# def save_history():
#     ai_conf = read_from_path("./ai_configs.json")
#     ai_conf[__plugin_name__]["history"] = history
#     save_to_path("./ai_configs.json", ai_conf, indent=4)

async def talk(session: CommandSession, text, user: u.User):
    httpx_client = httpx.Client(
        proxy=None,
        trust_env=False,
        timeout=60.0
    )
    client = ZhipuAI(api_key=GLM_API_KEY, http_client=httpx_client)
    with open("./static/glossary.md") as gl:
        glossary = gl.read()
    with open("./docs.md") as do:
        docs = do.read()
    tips = get_character_item("bot_info", "tips", default="无提示")
    if isinstance(tips, list):
        tips = [character_format(t) for t in tips]
    else:
        tips = [tips]
    tips_str = [f"{i + 1}. {t}\n" for i, t in enumerate(tips)]
    role = read_from_path("./ai_configs.json")[__plugin_name__]["system"].format(docs=docs, glossary=glossary, tips=tips_str, time=get_time_now())
    ai_helper = AIHelper(client)
    return await ai_helper.user_talk(session, role, user, text)