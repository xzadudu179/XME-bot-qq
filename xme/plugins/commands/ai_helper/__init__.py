from pathlib import Path
import shutil

from nonebot import CommandSession, Message, MessageSegment
from xme.xmetools import jsontools
from xme.xmetools.filetools import dict_to_file, text_to_file
from xme.xmetools.plugintools import on_command
# from xme.xmetools.cmdtools import use_args
from xme.xmetools.doctools import CommandDoc, shell_like_usage
# from nonebot.argparse import ArgumentParser
from xme.xmetools.bottools import XmeArgumentParser
from xme.xmetools.texttools import get_images_from_message, most_similarity_str_diff
from .commands import clear_history
# import asyncio
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
from zai import ZhipuAiClient
from .functions import get_telia_clock_state, gen_image, get_skill_md, get_webs_partial, ocr_image, web_search
# from zhipuai.core._errors import ZhipuAIError
import json
from functools import partial
import inspect
MAX_CHECK_TIMES = 1500
MAX_TOOL_CALL_TIMES = 50

# 用户: stats
curr_sessions = {}

class AIHelper:
    def get_temp_path(self, string=False):
        self._check_user_path()
        if string:
            return f"./data/temp/{self.user_id}"
        return Path(f"./data/temp/{self.user_id}")

    def delete_temp(self):
        for item in self.get_temp_path().iterdir():
            if item.is_file() or item.is_symlink():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)

    def _check_user_path(self):
        Path(f"./data/temp/{self.user_id}").mkdir(parents=True, exist_ok=True)

    def list_temp_files(self):
        files = [f for f in self.get_temp_path().iterdir() if f.is_file()]
        return "\n".join(files)

    def check_file(self, file_name: str, line_start=0, line_end=0):
        lines = []
        with open(f"{self.get_temp_path(True)}/{file_name}", 'r', encoding='utf-8') as file:
            lines = file.readlines()
        get_lines = lines[line_start:line_end] if line_end != 0 else lines[line_start:]
        return {"result": "\n".join(get_lines), "no_compress": True}

    def __init__(self, ai_client: ZhipuAiClient, user_id: int):
        self.tokens = 0
        self.cached_tokens = 0
        self.client = ai_client
        self.user_id = user_id
        self.tool_functions = {
            "get_telia_clock_state": get_telia_clock_state,
            "gen_image": partial(gen_image, agent=self),
            # "get_image_msg": get_image_msg,
            "get_skill_md": get_skill_md,
            "check_file": self.check_file,
            "list_temp_files": self.list_temp_files,
            "ocr_image": partial(ocr_image, agent=self),
            "web_search": web_search,
            "get_webs_partial": partial(get_webs_partial, agent=self),
        }
        self.pending_messages = []
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_telia_clock_state",
                    "description": "获取漠月世界观里的忒利亚当前的季节（雨季/旱季）和时期（凌空期/白日期/血日期）",
                    "parameters": {
                        "type": "object",
                        "properties": {
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "gen_image",
                    "description": "通过提示词和指定大小和质量调用 ai 生成图片，图片生成成功会返回 url，失败会返回 \"图片生成失败：原因\"",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "prompt": {
                                "type": "string",
                                "description": "你要生成的图片的提示词"
                            },
                            "size": {
                                "type": "string",
                                "description": "图片大小，格式为 数字x数字（默认1024x1024）"
                            }
                            # "quality": {
                            #     "type": "string",
                            #     "description": "图片质量，分为 standard 和 hd 两个等级"
                            # }
                        },
                        "required": ["prompt"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_skill_md",
                    "description": "获取内部的 skill md文件的内容。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "skill名称，必须完全对应。"
                            }
                        },
                        "required": ["name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "check_file",
                    "description": "获取保存进用户 temp 的文件的内容。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_name": {
                                "type": "string",
                                "description": "temp 文件夹下文件名"
                            },
                            "line_start": {
                                "type": "integer",
                                "description": "要查看的首行索引，填写 0 以下会从行尾往前计算，默认 0。"
                            },
                            "line_end": {
                                "type": "integer",
                                "description": "要查看的尾行索引，填写 0 会直接当作看到结尾，其他和 python 列表索引差不多。默认 0。"
                            },
                        },
                        "required": ["file_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_temp_files",
                    "description": "获取用户 temp 路径下的所有文件列表。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "ocr_image",
                    "description": "对一个图片 url 进行 ocr，并获取识别内容 markdown。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "要识别的图片 url"
                            }
                        },
                        "required": ["url"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "对一个 query 进行联网搜索，并获取识别内容字典列表。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "搜索内容"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "结果数量，默认 10"
                            },
                            "depth": {
                                "type": "string",
                                "description": "搜索深度，分为\"basic\" \"advanced\" \"fast\" \"ultra-fast\" 四个等级，默认 basic"
                            },
                            "time_range": {
                                "type": "string",
                                "description": "时间范围，默认 year"
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_webs_partial",
                    "description": "得到联网搜索内容的部分最接近指定关键词的结果，或指定搜索规则的结果。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "key": {
                                "type": "string",
                                "description": "要搜索的部分名，有 \"title\" \"url\" 和 \"content\" 可选。"
                            },
                            "file_name": {
                                "type": "string",
                                "description": "要搜索的内容文件名，例如 \"xxx.json\""
                            },
                            "search_str": {
                                "type": "string",
                                "description": "搜索文本/表达式本身"
                            },
                            "search_method": {
                                "type": "string",
                                "description": "要使用的搜索方法，默认 \"re_search\" 会模糊匹配关键字。还有 \"re_filter\" 正则表达式只保留 fullmatch 内容，输入其他内容会回退至 \"re_search\""
                            },
                        },
                        "required": ["key", "file_name", "search_str"]
                    }
                }
            },
        ]

    async def run_agent(self, session, messages, model):
        # for _ in range(MAX_TOOL_CALL_TIMES):  # 最多允许 20 轮工具调用
        curr_tool_call_times = 0
        while True:
            result = await self.create_and_wait(session, messages, model)
            if result == False:
                return False, 0
            message = result.choices[0].message
            self.tokens += result.usage.total_tokens
            self.cached_tokens += result.usage.prompt_tokens_details.cached_tokens
            if message.reasoning_content:
                logger.info(
                    f"\n===== GLM Reasoning =====\n"
                    f"{message.reasoning_content}\n"
                    f"========================="
                )


            # 没有工具调用
            if not message.tool_calls:
                return result, curr_tool_call_times
            curr_tool_call_times += 1
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    logger.info(
                        f"[GLM Tool Call] "
                        f"{tool_call.function.name}"
                        f"({tool_call.function.arguments})"
                    )

            # 把 assistant 的原始消息加入历史
            assistant_message = message.model_dump(exclude_none=True)
            # if getattr(message, "reasoning_content", None):
            #     assistant_message["reasoning_content"] = message.reasoning_content

            messages.append(assistant_message)

            # 执行所有工具
            for tool_call in message.tool_calls:

                result_text = str(await self.execute_tool(session, tool_call, curr_tool_call_times))
                logger.info(
                    f"加入 tool message: {str(result_text)[:100]!r}..."
                )
                messages.append({
                    "role": "tool",
                    "content": result_text,
                    "tool_call_id": tool_call.id
                })
        # 改一下 超过限制不允许调用工具
        # raise RuntimeError("Tool Call 次数超过限制")

    async def execute_tool(self, session, tool_call, curr_tool_call_times):
        prefix = ""
        if curr_tool_call_times >= MAX_TOOL_CALL_TIMES:
            return f"[工具执行失败：次数已达到上限，请在下一个会话继续]"
        if curr_tool_call_times >= MAX_TOOL_CALL_TIMES - 7:
            prefix = f"[警告：剩余 {MAX_TOOL_CALL_TIMES - curr_tool_call_times} 次 tools 调用次数]\n"
        name = tool_call.function.name
        debug_msg(get_message("plugins", __plugin_name__, "call_tool", tool_name=name))
        try:
            arguments = json.loads(tool_call.function.arguments)

            func = self.tool_functions.get(name)

            if func is None:
                return f"工具 {name} 不存在"
            no_compress = False
            if inspect.iscoroutinefunction(func):
                result = await func(**arguments)
            else:
                result = func(**arguments)
            logger.info(
                f"Tool {name} result type={type(result)}, "
                f"str={str(result)[:100]!r}...{str(result)[-100:]!r}"
            )
            if isinstance(result, list) or (isinstance(result, dict) and result.get("result", None) is None) and len(str(result)) > 5000:
                result = prefix + f'[工具调用完毕，返回列表/字典过长已转为 json，可使用其他 tools 查看]{dict_to_file(result, self.user_id, name + "_")}'

            if isinstance(result, dict):
                no_compress = result.get("no_compress", False)
                result = result.get("result", result)
            if isinstance(result, MessageSegment) or str(result).startswith("[CQ:"):
                self.pending_messages.append(result)
                return prefix + f"[\"{name}\" 工具调用完毕，Segment 消息已经准备好，会在本轮最终回复时发送给用户。]"
            if isinstance(result, str) and len(result) > 5000 and not no_compress:
                return prefix + f"[工具调用完毕，返回文本过长已传为文件，可使用 \"check_file\" 工具传入 `file_id` 预览。数据如下]：\n{text_to_file(result, self.user_id)}"

            return prefix + result if isinstance(result, str) else result
        except Exception as e:
            logger.exception(f"执行工具 {name} 失败")
            return f"[工具执行失败：{type(e).__name__}: {e}]"


    # async def ai_init(self, messages, model="glm-5.3"):
    #     response = self.client.chat.asyncCompletions.create(
    #         # model="glm-4-flashx",
    #         model=model,
    #         messages=messages,
    #         tools=self.tools,
    #         thinking={
    #             "type": "enabled"
    #         },
    #         tool_choice="auto",
    #         temperature=0.3

    #     )
    #     return response


    async def create_and_wait(self, session, messages, model):
        response = self.client.chat.asyncCompletions.create(
            model=model,
            messages=messages,
            tools=self.tools,
            thinking={
                "type": "enabled"
            },
            tool_choice="auto",
            temperature=0.3
        )
        task_id = response.id
        check_times = 0
        while check_times <= MAX_CHECK_TIMES:
            result = self.client.chat.asyncCompletions.retrieve_completion_result(
                id=task_id
            )

            if result.task_status == "SUCCESS":
                return result

            if result.task_status == "FAIL":
                raise RuntimeError(result)
            check_times += 1
            reply = await aget_arg_with_timeout(session, 1)
            if reply is not None and reply.strip() == "aistop":
                await send_session_msg(session, get_message("plugins", __plugin_name__, "ai_send_interrupted"))
                return False
            # await asyncio.sleep(0.5)
        raise RuntimeError(f"AI 调用超时 (>{MAX_CHECK_TIMES}次)")

    async def user_talk(self, session: CommandSession, role, user, text):
        # ai_helper = AIHelper(client)
        self.pending_messages.clear()
        history, curr_text = await get_history(user)

        # 提取 text 里的图片
        image_objects = await get_images_from_message(session.bot, text)
        image_urls = [x["file"] for x in image_objects]
        url_dicts = [{"type": "image_url", "image_url": {"url": v}} for v in image_urls]
        logger.info(f"用户附带了以下图片url {url_dicts}")

        ai_params = [
            {"role": "system","content": role},
            *history,
            {"role": "user","content": [
                    {"type": "text", "text": f"{curr_text}\n{text}"},
                    *url_dicts
                ]
            },
        ]
        # logger.info(f"params:{ai_params}")
        # response = await self.ai_init(ai_params, "glm-5.3-flash" if len(url_dicts) > 0 else "glm-5.3")
        result, tool_call_times =  await self.run_agent(session, ai_params, model="glm-5.3-flash" if len(url_dicts) > 0 else "glm-5.3")
        if result == False:
            return False, 0, [], 0
        try:
            ans = result.choices[0].message.content
            build_history(
                user=user,
                ask=text,
                ans=ans
            )
            logger.info(
                f"AI 返回了以下 response：{result}"
            )
            tokens_use = (
                self.tokens
                - self.cached_tokens
            )
            debug_msg("处理结果")
            logger.info(
                f"缓存tokens "
                f"{self.cached_tokens}, "
                f"减少 {tokens_use} 个 tokens"
            )
            # pending_message = "\n".join(
            #     str(s) for s in self.pending_messages
            # )
            # logger.info(
            #     f"pending_messages count={len(self.pending_messages)}"
            # )
            # logger.info(
            #     f"pending_messages{repr(pending_message[:500])!r}...{repr(pending_message[-200:])!r}"
            # )
            # logger.info(
            #     f"pending_message length={len(pending_message)}"
            # )
            # logger.info(
            #     f"answer length={len(ans)}"
            # )

            return ans, tokens_use, self.pending_messages, tool_call_times
        except AttributeError as ex:
            logger.error(f"attribute 错误: {ex}")

            await send_session_msg(
                session,
                get_message(
                    "plugins",
                    __plugin_name__,
                    "attribute_error",
                    content=result,
                    replace_cq_str=True
                )
            )
            return False, 0, [], 0
        except Exception as ex:
            logger.error(f"AI 出现错误: {ex}")
            await send_session_msg(
                session,
                get_message(
                    "plugins",
                    __plugin_name__,
                    "ai_error",
                    code="未知",
                    msg=str(ex) + "\n" + format_exc()
                )
            )
            return False, 0, [], 0

        #     # print(result_response)
        #     task_status = result_response.task_status
        #     # await asyncio.sleep(0.5)
        #     get_cnt += 1
        #     if get_cnt >= MAX_CHECK_TIMES:
        #         t.stop()
        #         await send_session_msg(session, get_message("plugins", __plugin_name__, "ai_send_timeout", secs=t.get_timer_value()))
        #         return False, 0
        # try:
        #     ans = result_response.choices[0].message.content
        #     build_history(user=user, ask=text, ans=ans)
        #     logger.info(f"AI 返回了以下 response：{result_response}")
        #     tokens_use = result_response.usage.total_tokens - result_response.usage.prompt_tokens_details['cached_tokens']
        #     debug_msg("处理结果")
        #     logger.info(f"缓存tokens {result_response.usage.prompt_tokens_details['cached_tokens']}, 减少 {tokens_use} 个 tokens")
        #     return result_response.choices[0].message.content, tokens_use
        # except AttributeError as ex:
        #     logger.error("attribute 错误:", ex)
        #     await send_session_msg(session, get_message("plugins", __plugin_name__, "attribute_error", content=result_response, replace_cq_str=True))
        #     return False, 0
        # except Exception as ex:
        #     logger.error(f"AI 出现错误: {ex}")
        #     code = result_response.get("error", {}).get("code", "未知")
        #     message = result_response.get("error", {}).get("message", "未知")
        #     await send_session_msg(session, get_message("plugins", __plugin_name__,"ai_error", replace_cq_str=True, content=result_response, code=code, message=message))
            # return False, 0
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

alias = ['ai']
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

TOKENS_LIMIT = 500000
@on_command(__plugin_name__, aliases=alias, only_to_me=False, shell_like=True, permission=lambda _: True)
@u.using_user(save_data=True)
@u.custom_limit(__plugin_name__, 1, unit=TimeUnit.DAY, count_limit=TOKENS_LIMIT)
async def _(session: CommandSession, user: u.User, validate, count_tick):
    global curr_sessions
    if validate():
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'limited'))
        return False
    # 如果有 session 在运行
    if curr_sessions.get(user.id):
        await send_session_msg(session, get_message("plugins", __plugin_name__, "ai_session_on"))
        return False
    MAX_LENGTH = 3000
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
        t, tokens_use, pending_messages, tool_call_times = await talk(session, text, user)
        if not t:
            return False
        count_tick(tokens_use)
        tokens_left_now = TOKENS_LIMIT - u.get_limit_info(user, __plugin_name__)[1]
        message = "\n".join([str(s) for s in pending_messages])
        logger.info(f"msg {message}")
        t = t.replace("[", "&#91;").replace("]","&#93;")
        message += t
        send_msg = get_message("plugins", __plugin_name__, 'talk_result', talk=message, tokens_left_now=tokens_left_now, tool_call_times=tool_call_times)
        logger.info(f"send msg {send_msg}")
        await send_session_msg(
            session,
            send_msg, tips=True
        )
        return True
    except Exception:
        logger.error("错误：", format_exc())
        await send_session_msg(session, get_message("config", "unknown_error", ex=format_exc()))
        return False
    finally:
        curr_sessions[user.id] = False

async def get_history(user: u.User):
    user_history = user.ai_history
    if not user_history:
        return "", ""
    # build_str = "历史记录：\n"
    build_list = []
    uname = await get_user_name(user.id, default='未知用户')
    for _, item in enumerate(user_history):
        build_dicts = [{
            "role": "user",
            "content": f"[历史记录-{item.get('time', '未知时间')}][{uname}(qq{user.id})] {item['ask']}",
        },
        {
            "role": "assistant",
            "content": f"{item['ans']}"
        }]
        build_list += build_dicts
        # build_str += f"{i + 1}. [{item.get('time', '未知时间')}]][{uname}(qq{user.id})]: {item['ask']};\n\t你回答：{item['ans']}\n----------\n"
    # build_str += "=" * 15
    build_str = f"\n当前对话（现在时间为 {get_time_now()}）发送者为{uname}(qq{user.id})："
    return build_list, build_str

def build_history(user: u.User, ask, ans):
    # user_history = user.ai_history
    # if user_history is None:
    #     user.ai_history = []
    user.ai_history.append({
        "ask": ask,
        "ans": ans,
        "time": get_time_now()
    })
    if len(user.ai_history) > 30:
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
    global curr_sessions
    curr_sessions[user.id] = True
    client = ZhipuAiClient(api_key=GLM_API_KEY, http_client=httpx_client)
    with open("./static/glossary.md") as gl:
        glossary = gl.read()
    with open("./static/telia.txt") as tel:
        telia = tel.read()
    with open("./docs.md") as do:
        docs = do.read()
    tips = get_character_item("bot_info", "tips", default="无提示")
    if isinstance(tips, list):
        tips = [character_format(t) for t in tips]
    else:
        tips = [tips]
    tips_str = [f"- {t}\n" for t in tips]
    skills = {
        "worldview_settings": "漠月、漠星和九九/九镹所在世界观相关的设定合集，在有世界观相关的问题可以调用。"
    }
    skills_text = "\n".join([f"{i + 1}. {k}: {v}" for i, (k, v) in enumerate(skills.items())])
    role = read_from_path("./ai_configs.json")[__plugin_name__]["system"].format(docs=docs, glossary=glossary, tips=tips_str, time=get_time_now(), telia=telia, skills=skills_text, max_tool_call_times=MAX_TOOL_CALL_TIMES)
    ai_helper = AIHelper(client, user.id)
    # 开始前先清空放置上轮会话强制结束之类的问题
    ai_helper.delete_temp()
    result = await ai_helper.user_talk(session, role, user, text)
    ai_helper.delete_temp()
    return result