from pathlib import Path
import re
import shutil

import config
from nonebot import CommandSession, MessageSegment
# from xme.xmetools import jsontools
from xme.xmetools.filetools import dict_to_file, text_to_file
from xme.xmetools.plugintools import on_command
# from xme.xmetools.cmdtools import use_args
from xme.xmetools.doctools import CommandDoc, shell_like_usage
# from nonebot.argparse import ArgumentParser
import argparse
from xme.xmetools.bottools import XmeArgumentParser
from xme.xmetools.texttools import get_images_from_message, hash_text, most_similarity_str_diff
from .commands import clear_history
# import asyncio
from traceback import format_exc
from xme.xmetools.debugtools import debug_msg
from nonebot.log import logger
import httpx
# from xme.xmetools.texttools import dec_to_chinese
from xme.xmetools.jsontools import read_from_path
from xme.xmetools.cmdtools import is_command
from xme.xmetools.msgtools import send_session_msg, aget_arg_with_timeout, setup_logger
from xme.xmetools.bottools import get_user_name
from character import get_message, get_character_item, character_format
from xme.xmetools.timetools import TimeUnit, Timer, get_time_now
from xme.xmetools.dicttools import reverse_dict
from keys import GLM_API_KEY
from xme.plugins.commands.xme_user.classes import user as u
from zai import ZhipuAiClient
from .functions import get_telia_clock_state, gen_image, get_skill_md, get_webs_partial, inprocess_report, ocr_image, web_search, content_search
from .functions import read_webpage, view_file, view_image, view_video
# from zhipuai.core._errors import ZhipuAIError
import json
from functools import partial
import inspect
MAX_CHECK_TIMES = 1000
MAX_HISTORY_COUNT = 50
MAX_TOOL_CALL_TIMES = 50

ai_logger = setup_logger("aihelper", "ai_helper_log")

# 用户: stats
curr_sessions = {}

# 用户可用指令
cmds = {
        "clear": {
            "content": clear_history,
            "args": "",
            "desc": "清除你的所有对话历史"
        }
    }


class AIHelper:
    """AIHelper Agent 实例，生命周期仅存在于单个用户会话中
    """
    def get_temp_path(self, string=False):
        self._check_user_path()
        if string:
            return f"./data/temp/{self.user_id}"
        return Path(f"./data/temp/{self.user_id}")

    def delete_temp(self):
        # 清空临时目录，但保留 history 目录（history 仅在 /ai -c clear 时清空）
        for item in self.get_temp_path().iterdir():
            if item.name == "history":
                continue
            if item.is_file() or item.is_symlink():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)

    def _check_user_path(self):
        Path(f"./data/temp/{self.user_id}").mkdir(parents=True, exist_ok=True)

    def list_temp_files(self, folder="temp"):
        """列出指定文件夹（temp / history）下的文件列表。"""
        if folder == "history":
            hist_path = self.get_history_path()
            files = sorted(
                [f for f in hist_path.iterdir() if f.is_file()],
                key=lambda f: f.name,
            )
            lines = []
            for f in files:
                ref = f.stem if f.stem.startswith("history_") else None
                if ref is None:
                    continue
                # 注册引用，便于 check_file 使用
                self.ref_map[ref] = f"history/{f.name}"
                lines.append(f"{ref}: {f.name}")
            return "\n".join(lines)
        reversed_ref_map = reverse_dict(self.ref_map)
        files = [f"{reversed_ref_map.get(f.name, None)}: {f.name}" for f in self.get_temp_path().iterdir() if f.is_file()]
        return "\n".join(files)

    def check_file(self, ref: str, line_start=0, line_end=0):
        file_name = self.ref_map[ref]
        lines = []
        with open(f"{self.get_temp_path(True)}/{file_name}", 'r', encoding='utf-8') as file:
            lines = file.readlines()
        get_lines = lines[line_start:line_end] if line_end != 0 else lines[line_start:]
        return {"result": "\n".join(get_lines), "no_compress": True}

    def get_history_path(self):
        path = self.get_temp_path() / "history"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def save_to_history(self, ref="", content=""):
        """转存内容/文件到 history 文件夹，返回 history 引用信息。

        若传入 ref，则读取 temp 中对应文件的内容转存；否则使用 content 文本。
        history 文件以 history_N.tmp 命名，其引用 history_N 可由文件名推导，
        因此跨会话也能稳定复用。
        """
        if ref:
            file_name = self.ref_map.get(ref, None)
            if file_name is None:
                return {"result": f"[转存失败：没有找到引用 {ref}]", "no_compress": True}
            src_path = self.get_temp_path() / file_name
            with open(src_path, "r", encoding="utf-8") as f:
                text = f.read()
        else:
            text = content or ""
        if not text:
            return {"result": "[转存失败：没有内容可保存]", "no_compress": True}
        hist_path = self.get_history_path()
        used = set()
        for item in hist_path.iterdir():
            if item.is_file() and item.name.endswith(".tmp"):
                stem = item.stem
                if stem.startswith("history_"):
                    try:
                        used.add(int(stem[len("history_"):]))
                    except ValueError:
                        pass
        n = 1
        while n in used:
            n += 1
        ref_id = f"history_{n}"
        file_name = f"{ref_id}.tmp"
        self.ref_map[ref_id] = f"history/{file_name}"
        with open(hist_path / file_name, "w", encoding="utf-8") as f:
            f.write(text)
        return {
            "result": f"已转存至 history，引用 {ref_id}，可通过 check_file 传入 \"{ref_id}\" 查看内容。",
            "ref": ref_id,
            "file_name": f"history/{file_name}",
            "total_len": len(text),
            "preview": text[:200],
            "no_compress": True,
        }

    def clear_history_files(self):
        """清空 history 文件夹里的所有文件，并移除对应引用。"""
        hist_path = self.get_history_path()
        removed = 0
        if hist_path.is_dir():
            for item in hist_path.iterdir():
                if item.is_file() or item.is_symlink():
                    item.unlink()
                    removed += 1
        self.ref_map = {
            k: v for k, v in self.ref_map.items()
            if not str(v).startswith("history/")
        }
        return {"result": f"已清空 history，共删除 {removed} 个文件", "no_compress": True}

    def __init__(self, ai_client: ZhipuAiClient, user_id: int, session, model="flash"):
        self.ref_map = {}
        self.tokens = 0
        self.other_credits = 0
        self.model = "glm-5.3" if model == "pro" else "glm-5.3-flash"
        self.cached_tokens = 0
        self.client = ai_client
        self.session = session
        self.user_id = user_id
        # 上次回应时间
        self.last_response = 0
        self.tool_functions = {
            "get_telia_clock_state": get_telia_clock_state,
            "gen_image": partial(gen_image, agent=self),
            "get_skill_md": get_skill_md,
            "check_file": self.check_file,
            "list_temp_files": self.list_temp_files,
            "save_to_history": self.save_to_history,
            "clear_history_files": self.clear_history_files,
            "inprocess_report": partial(inprocess_report, agent=self),
            "ocr_image": partial(ocr_image, agent=self),
            "view_file": partial(view_file, agent=self),
            "view_image": partial(view_image, agent=self),
            "view_video": partial(view_video, agent=self),
            "read_webpage": read_webpage,
            "web_search": web_search,
            "content_search": partial(content_search, agent=self),
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
                            "ref": {
                                "type": "string",
                                "description": "temp 文件夹下引用名 例如 text_1"
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
                        "required": ["ref"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_temp_files",
                    "description": "获取指定文件夹下的文件列表（temp 或 history），会以 \"索引: 名称\" 的形式显示。history 是跨单会话保留的历史文件",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "folder": {
                                "type": "string",
                                "description": "要列出的文件夹，\"temp\"（默认，临时文件）或 \"history\"（跨单会话保留的历史文件）不填或者其他都会自动变为 temp。"
                            }
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
                    "name": "view_file",
                    "description": "使用 glm-5.3-flash 查看指定 url 里的文件，并按你给的 prompt 解析回答。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "要查看的内容 url"
                            },
                            "prompt": {
                                "type": "string",
                                "description": "你想让模型针对该 url 内容做什么"
                            }
                        },
                        "required": ["url", "prompt"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "view_image",
                    "description": "使用 glm-5.3-flash 查看指定 url 里的图片，并按你给的 prompt 解析回答。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "要查看的内容 url"
                            },
                            "prompt": {
                                "type": "string",
                                "description": "你想让模型针对该 url 内容做什么"
                            }
                        },
                        "required": ["url", "prompt"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "view_video",
                    "description": "使用 glm-5.3-flash 查看指定 url 里的视频，并按你给的 prompt 解析回答。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "要查看的内容 url"
                            },
                            "prompt": {
                                "type": "string",
                                "description": "你想让模型针对该 url 内容做什么"
                            }
                        },
                        "required": ["url", "prompt"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "read_webpage",
                    "description": "读取并解析指定 url 的网页内容，返回网页正文（默认 markdown）。可传入 url 与可选参数。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "要读取的网页 url"
                            },
                            "timeout": {
                                "type": "integer",
                                "description": "请求超时时间（秒），默认 20，最大 100"
                            },
                            "return_format": {
                                "type": "string",
                                "description": "返回格式， markdown / text，默认 markdown"
                            },
                            "no_cache": {
                                "type": "boolean",
                                "description": "是否禁用缓存，默认 false"
                            },
                            "retain_images": {
                                "type": "boolean",
                                "description": "是否保留图片，默认 true"
                            }
                        },
                        "required": ["url"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_webs_partial",
                    "description": "得到联网搜索内容的部分最接近指定搜索规则的结果。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "key": {
                                "type": "string",
                                "description": "要搜索的部分名，有 \"title\" \"url\" 和 \"content\" 可选。"
                            },
                            "file_ref": {
                                "type": "string",
                                "description": "要搜索的内容文件引用名，例如 \"json_1\""
                            },
                            "search_str": {
                                "type": "string",
                                "description": "搜索文本/表达式本身"
                            },
                            "search_method": {
                                "type": "string",
                                "description": "要使用的搜索方法，默认 \"re_search\" 会使用正则表达式 search。还有 \"re_filter\" 正则表达式只保留 fullmatch 内容，输入其他内容会回退至 \"re_search\""
                            },
                        },
                        "required": ["key", "file_ref", "search_str"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "content_search",
                    "description": "使用正则表达式搜索文件内容。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "param": {
                                "type": "string",
                                "description": "正则表达式语句"
                            },
                            "file_ref": {
                                "type": "string",
                                "description": "要搜索的内容文件引用名，例如 \"text_1\""
                            },
                            "search_method": {
                                "type": "string",
                                "description": "要使用的搜索方法，默认 \"re_search\" 会匹配所有正则匹配到的内容。还有 \"re_filter\" 只保留正则没搜索到的内容，输入其他内容会回退至 \"re_search\""
                            },
                        },
                        "required": ["param", "file_ref"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "inprocess_report",
                    "description": "在会话途中跟用户反馈消息，不会被记录到历史记录，通常可用于表示自己在做什么或者将要做什么防止用户等待太久关闭会话。两次发送最小间隔 30s",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "description": "要发送的消息内容"
                            }
                        },
                        "required": ["message"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "save_to_history",
                    "description": "将一个文件/内容转存到跨会话保留的 history 文件夹，并返回该文件的 history 引用。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ref": {
                                "type": "string",
                                "description": "要转存的 temp 文件引用名，例如 text_1；与 content 二选一"
                            },
                            "content": {
                                "type": "string",
                                "description": "要保存到 history 的文本内容；当 ref 为空时备用"
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "clear_history_files",
                    "description": "清空 history 文件夹里的所有文件（跨单会话保留的历史文件）。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                        },
                        "required": []
                    }
                }
            },
        ]

    async def run_agent(self, session, messages, model):
        # for _ in range(MAX_TOOL_CALL_TIMES):  # 最多允许 20 轮工具调用
        curr_tool_call_times = 0
        MAX_RETRY_TIMES = 5
        retry_times = 0
        while True:
            try:
                result = await self.create_and_wait(session, messages, model)
            except RuntimeError:
                if retry_times >= MAX_RETRY_TIMES:
                    raise
                retry_times += 1
                continue
            if result == False:
                return False, 0
            message = result.choices[0].message
            self.tokens += result.usage.total_tokens
            self.cached_tokens += result.usage.prompt_tokens_details.cached_tokens
            if message.reasoning_content:
                ai_logger.info(
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
                    ai_logger.info(
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
                ai_logger.info(
                    f"加入 tool message: {str(result_text)[:500]!r}..."
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
        try:
            arguments = json.loads(tool_call.function.arguments)
            ai_logger.info(get_message("plugins", __plugin_name__, "call_tool", tool_name=name, arguments=tool_call.function.arguments))

            func = self.tool_functions.get(name)

            if func is None:
                return f"工具 {name} 不存在"
            no_compress = False
            if inspect.iscoroutinefunction(func):
                result = await func(**arguments)
            else:
                result = func(**arguments)
            ai_logger.info(
                f"工具调用完毕，名称 {name} 结果类型={type(result)}, str={str(result)[:100]!r}...{str(result)[-100:]!r}"
            )

            if isinstance(result, dict):
                no_compress = result.get("no_compress", False)
                result = result.get("result", result)

            if isinstance(result, MessageSegment) or str(result).startswith("[CQ:"):
                self.pending_messages.append(result)
                return prefix + f"[\"{name}\" 工具调用完毕，Segment 消息已经准备好，会在本轮最终回复时发送给用户。]"

            ####### 压缩 #######

            if (isinstance(result, list) and len(str(result)) > 5000) or (isinstance(result, dict) and result.get("result", None) is None) and len(str(result)) > 5000:
                res = dict_to_file(result, self.user_id, name + "_", agent=self)
                result = prefix + f'[工具调用完毕，返回列表/字典过长已转为 json，可使用其他 tools 查看 数据如下]：{res}'

            if isinstance(result, str) and len(result) > 5000 and not no_compress:
                res = text_to_file(result, self.user_id, self)
                self.ref_map[res["ref"]] = res["file_name"]
                return prefix + f"[工具调用完毕，返回文本过长已传为文件，可使用 \"check_file\" 工具传入 `file_ref` 预览。数据如下]：\n{res}"

            return prefix + result if isinstance(result, str) else result
        except Exception as e:
            ai_logger.exception(f"执行工具 {name} 失败")
            return f"[工具执行失败：{type(e).__name__}: {e}]"


    async def create_and_wait(self, session, messages, model):
        response = self.client.chat.asyncCompletions.create(
            model=model,
            messages=messages,
            tools=self.tools,
            thinking={
                "type": "enabled"
            },
            tool_choice="auto",
            temperature=0.5
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
        raise TimeoutError(f"AI 调用超时 (>{MAX_CHECK_TIMES}次)")

    async def user_talk(self, session: CommandSession, role, user, text):
        # ai_helper = AIHelper(client)
        self.pending_messages.clear()
        history, curr_text = await get_history(user)

        # 提取 text 里的图片
        image_objects = await get_images_from_message(session.bot, text)
        pattern = r"\[CQ:image,(?![^\]]*emoji_id=)[^\]]*file=[^\]]*?\]"
        matches = re.findall(pattern, text)
        for image_cq in matches:
            arg = arg.replace(f"[图片{hash_text(image_cq)}]")
        image_urls = [x["file"] for x in image_objects]
        url_dicts = [{"type": "image_url", "image_url": {"url": v}} for v in image_urls]
        ai_logger.info(f"用户说：{text}")
        ai_logger.info(f"用户附带了以下图片url {url_dicts}")

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
        prefix = ""
        real_model = "glm-5.3-flash" if len(url_dicts) > 0 else self.model
        if real_model != self.model:
            prefix = get_message("plugins", __plugin_name__, "model_change_prefix", model=self.model, vision_model=real_model)
        result, tool_call_times =  await self.run_agent(session, ai_params, model=real_model)
        if result == False:
            return False, {}, {}, 0
        try:
            ans = result.choices[0].message.content
            build_history(
                user=user,
                ask=text,
                ans=ans
            )
            ai_logger.info(
                f"AI 返回了以下 response：{result}"
            )
            # 缓存 tokens 占 1/4
            credits_use = (
                self.tokens
                - self.cached_tokens * 0.75
            )
            multis = 1
            match real_model:
                case "glm-5.3":
                    multis = 10
                case "glm-5.3-flash":
                    multis = 0.5
            credits_use *= multis
            credits_use += self.other_credits
            debug_msg("处理结果")
            logger.info(
                f"缓存tokens "
                f"{self.cached_tokens}, "
                f"减少 {credits_use} 个 tokens"
            )
            # self.pending_messages = self.pending_messages
            return ans, {"credits_use": credits_use, "cached": self.cached_tokens, "total": self.tokens}, {"messages": self.pending_messages, "prefix": prefix}, tool_call_times
        except AttributeError as ex:
            ai_logger.error(f"attribute 错误: {ex}")

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
            return False, {}, {}, 0
        except Exception as ex:
            ai_logger.error(f"AI 出现错误: {ex}")
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
            return False, {}, {}, 0

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
        "desc": "会把之后的文本全都解析为单纯的文本，如果你在发东西给 ai 的时候出现了 \"指令执行的参数有问题哦\" 的问题，可以试试在发送的内容前加上 -r 哦"
    },
    {
        "name": "model",
        "abbr": "m",
        "desc": "切换模型，可使用 \"pro\" 或 \"flash\" 两种，默认 \"flash\"。"
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

TOKENS_LIMIT = 6000000
@on_command(__plugin_name__, aliases=alias, only_to_me=False, shell_like=True, permission=lambda _: True)
@u.using_user(save_data=True)
@u.custom_limit(__plugin_name__, 1, unit=TimeUnit.DAY, count_limit=TOKENS_LIMIT)
async def _(session: CommandSession, user: u.User, validate, count_tick):
    global curr_sessions
    superuser_mode = False
    # 先去掉
    # if user.id in config.SUPERUSERS:
        # superuser_mode = True
    if validate() and user.id not in config.SUPERUSERS:
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'limited'))
        return False
    # 如果有 session 在运行
    if curr_sessions.get(user.id):
        await send_session_msg(session, get_message("plugins", __plugin_name__, "ai_session_on"))
        return False
    MAX_LENGTH = 3000
    # intext = ""
    # if "-r " in session.current_arg_text:
    #     intext = "-r"
    # elif "--raw " in session.current_arg_text:
    #     intext = '--raw'
    # if intext:
        # text = intext.join(session.current_arg_text.split(intext)[1:])
    # else:
    parser = XmeArgumentParser(session=session, usage=arg_usage)
    parser.exit_mssage = get_message("config", "shell_error", command_name=__plugin_name__)
    parser.add_argument('-c', '--ctrl', action='store_true', default=False)
    parser.add_argument('-m', '--model', type=str)
    parser.add_argument("-r", nargs=argparse.REMAINDER)
    parser.add_argument('text', nargs='*')
    args = parser.parse_args(session.argv)
    text = ' '.join(args.r or args.text).strip()
    if args.ctrl and text and len(text) <= MAX_LENGTH:
        await send_session_msg(session, parse_control(session, text, user))
        return 2
    if not text:
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'no_arg'))
        return False
    if len(text) > MAX_LENGTH:
        await send_session_msg(session, get_message("plugins", __plugin_name__, 'too_long', count=MAX_LENGTH))
        return False

    available_models = ["flash", "pro"]
    model = args.model if args.model else "flash"
    if model not in available_models:
        return await send_session_msg(session, get_message("plugins", __plugin_name__, 'error_model', model=model, models="、".join([f'"{i}"' for i in available_models])))

    await send_session_msg(session, get_message("plugins", __plugin_name__, 'talking_to_ai', model=model, models = ""))
    try:
        # print("正常")
        t, tokens_use_dict, messages_dict, tool_call_times = await talk(session, text, user, model)
        if not t:
            return False
        pending_messages = messages_dict["messages"]
        prefix = messages_dict["prefix"]
        credits_use = tokens_use_dict["credits_use"]
        cached = tokens_use_dict["cached"]
        total = tokens_use_dict["total"]
        if not superuser_mode:
            count_tick(credits_use)
        credits_left_now = TOKENS_LIMIT - u.get_limit_info(user, __plugin_name__)[1]
        message = "\n".join([str(s) for s in pending_messages])
        ai_logger.info(f"msg {message}")
        t = t.replace("[", "&#91;").replace("]","&#93;")
        message += t
        send_msg = get_message(
            "plugins",
            __plugin_name__,
            'talk_result',
            talk=message,
            tokens_left_now=f"{credits_left_now:,.2f}".rstrip('0').rstrip('.')
            if not superuser_mode
            else "∞",
            tool_call_times=tool_call_times,
            cached=f"{cached:,.2f}".rstrip('0').rstrip('.'),
            tokens=f"{total:,.2f}".rstrip('0').rstrip('.'),
            credits=f"{credits_use:,.2f}".rstrip('0').rstrip('.'),
            prefix=prefix
        )
        ai_logger.info(f"send msg {send_msg}")
        await send_session_msg(
            session,
            send_msg, tips=True
        )
        return True
    except Exception:
        ai_logger.error("错误：", format_exc())
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
    if len(user.ai_history) > MAX_HISTORY_COUNT:
        # TODO 压缩上下文
        del user.ai_history[-1]
#     save_history()

# def save_history():
#     ai_conf = read_from_path("./ai_configs.json")
#     ai_conf[__plugin_name__]["history"] = history
#     save_to_path("./ai_configs.json", ai_conf, indent=4)

async def talk(session: CommandSession, text, user: u.User, model: str):
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
    ai_helper = AIHelper(client, user.id, session=session, model=model)
    # 开始前先清空放置上轮会话强制结束之类的问题
    ai_helper.delete_temp()
    result = await ai_helper.user_talk(session, role, user, text)
    ai_helper.delete_temp()
    return result