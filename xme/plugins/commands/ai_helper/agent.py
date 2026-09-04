# some are made by Deepseek-v4-flash-vison-exp at Deepseek Harness
from pathlib import Path
import re
import shutil
import json
import inspect
import asyncio
from traceback import format_exc
from uuid import uuid4
from xme.xmetools.videotools import extract_video_links, extract_and_download, parse_video
import config
from nonebot import CommandSession, MessageSegment

from nonebot.log import logger
from xme.xmetools.filetools import dict_to_file, get_local_file_url, text_to_file, history_file_name, safe_join
from xme.xmetools.texttools import get_images_from_message, hash_text
from xme.xmetools.debugtools import debug_msg
from xme.xmetools.msgtools import is_text_can_send, send_session_msg, aget_arg_with_timeout, setup_logger
from xme.xmetools.bottools import get_user_name
from xme.xmetools.timetools import get_time_now, Timer
from xme.xmetools.jsontools import read_from_path
from character import get_message
from keys import GLM_API_KEY
from xme.plugins.commands.xme_user.classes import user as u
from zai import ZhipuAiClient

from xme.xmetools.videotools.core import VideoExtractResult, VideoInfo, replace_video_links

from .constants import (
    __plugin_name__,
    MAX_CHECK_TIMES,
    MAX_TOOL_CALL_TIMES,
    MAX_HISTORY_COUNT,
    COMPRESS_TRIGGER,
    CONTEXT_KEEP_RECENT,
    COMPRESS_MAX_LENGTH,
)
from . import functions
from . import history
from .session import AISession

ai_logger = setup_logger("aihelper", "ai_helper_log")


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
        for path in self.temp_file_paths:
            Path(path).unlink(missing_ok=True)

    def _check_user_path(self):
        Path(f"./data/temp/{self.user_id}").mkdir(parents=True, exist_ok=True)

    def get_history_path(self):
        # AI 转存文件默认放到当前 AI 会话的历史文件夹、以会话命名的子文件夹
        # data/ai_historys/<用户id>/<ai_session>/
        path = AISession(self.user_id, self.ai_session).dir_path
        path.mkdir(parents=True, exist_ok=True)
        return path

    def resolve_ref(self, ref: str, use_history=True):
        """解析 ref 对应的文件路径。

        - temp 文件引用：ref_map 里存的是纯文件名，拼上 temp 目录路径；
        - history 引用：ref_map 里存的是完整路径，或按 history_N 推导出会话文件夹内的路径，
          因此即使当前会话 ref_map 未注册，也能直接解析。
        """
        file_name = self.ref_map.get(ref, None)
        if file_name is not None:
            if "/" in file_name or chr(92) in file_name or file_name.startswith("."):
                # 内部生成的完整路径（如会话文件夹下的历史文件），可信
                return Path(file_name)
            # 纯文件名 → 安全拼接到 temp 目录
            return safe_join(self.get_temp_path(), file_name)
        if not use_history:
            raise KeyError(f"无法找到引用 {ref}")
        # 跨会话推导：history_N 或自定义安全文件名
        derived = history_file_name(ref)
        if derived is not None:
            candidate = safe_join(self.get_history_path(), derived)
            if candidate.exists():
                self.ref_map[ref] = str(candidate)
                return candidate
        raise KeyError(f"无法找到引用 {ref}")

    def __init__(self, ai_client: ZhipuAiClient, user_id: int, session, model="flash", ai_session=history.DEFAULT_SESSION):
        # ai_session：用户当前使用的 AI 会话名；session：bot 的 CommandSession
        self.ai_session = ai_session or history.DEFAULT_SESSION
        MODEL_MAP = {
            "pro": "glm-5.3",
        }
        self.ref_map = {}
        self.tokens = 0
        self.other_credits = 0
        self.model_arg = model
        m = MODEL_MAP.get(model, None)
        self.model = m if m is not None else "glm-5.3-flash"
        self.cached_tokens = 0
        self.client = ai_client
        self.session = session
        self.user_id = user_id
        self.temp_file_paths = []
        self.user_input_urls = {}
        self.activate_skills = []

        self.spent_secs = Timer()
        # 上次回应时间
        self.last_response = 0
        # 工具使用依赖注入：所有 tool 都是独立函数，需要 agent 的函数声明 agent 形参，
        # 由 execute_tool 在执行时注入，避免工具内部再实例化 agent 造成连环调用。
        self.tool_functions = {
            name: getattr(functions, name)
            for name in functions.__tools__
        }
        self.pending_messages = []
        # 工具 schema 从 tools.json 读取
        tools_path = Path(__file__).parent / "tools.json"
        with open(tools_path, "r", encoding="utf-8") as f:
            self.tools = json.load(f)

    async def run_agent(self, session, messages, model):
        # self.spent_secs.start()
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
                    f"\n===== GLM Reasoning {session.event.user_id} =====\n"
                    f"{message.reasoning_content}\n"
                    f"========================="
                )

            # 没有工具调用
            if not message.tool_calls:
                return result, curr_tool_call_times
            # 有工具调用
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

    # session 留着以后有用
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
            # 依赖注入：工具声明了 agent 形参则注入当前 agent
            if "agent" in inspect.signature(func).parameters:
                arguments["agent"] = self
            if inspect.iscoroutinefunction(func):
                result = await func(**arguments)
            else:
                result = func(**arguments)
            spent = self.spent_secs.get_timer_value()
            spent_msg = f"本轮对话总计消耗 {spent:,.2f}s"
            ai_logger.info(
                f"[{spent_msg}]工具调用完毕，名称 {name} 结果类型={type(result)}, str={str(result)[:100]!r}...{str(result)[-100:]!r}"
            )

            if isinstance(result, dict):
                no_compress = result.get("no_compress", False)
                result = result.get("result", result)

            if isinstance(result, MessageSegment) or str(result).startswith("[CQ:"):
                self.pending_messages.append(result)
                return prefix + f"[[{spent_msg}] \"{name}\" 工具调用完毕，Segment 消息已经准备好，会在本轮最终回复时发送给用户。]"

            ####### 压缩 ########

            if (isinstance(result, list) and len(str(result)) > 5000) or (isinstance(result, dict) and result.get("result", None) is None) and len(str(result)) > 5000:
                res = dict_to_file(result, self.user_id, name + "_", agent=self)
                result = prefix + f'[{spent_msg}][工具调用完毕，返回列表/字典过长已转为 json，可使用其他 tools 查看 数据如下]：{res}'

            if isinstance(result, str) and len(result) > 5000 and not no_compress:
                res = text_to_file(result, self.user_id, self)
                self.ref_map[res["ref"]] = res["file_name"]
                return prefix + f"[{spent_msg}][工具调用完毕，返回文本过长已传为文件，可使用 \"check_file\" 工具传入 `file_ref` 预览。数据如下]：\n{res}"

            if len(str(result)) > 100000:
                return f"[{spent_msg}][错误：无法返回过大内容 (>100000)]"

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
        raise TimeoutError(f"AI 调用超时 (>{MAX_CHECK_TIMES}次)")

    async def _glm_chat(self, messages, model="glm-5.3-flash"):
        """通用的一次性 chat 完成调用（用于历史压缩等），返回模型文本。"""
        response = self.client.chat.asyncCompletions.create(
            model=model,
            messages=messages,
        )
        task_id = response.id
        while True:
            result = self.client.chat.asyncCompletions.retrieve_completion_result(
                id=task_id
            )
            if result.task_status == "SUCCESS":
                self.other_credits += result.usage.total_tokens - (result.usage.prompt_tokens_details.cached_tokens * 0.75)
                return result.choices[0].message.content
            if result.task_status == "FAIL":
                raise RuntimeError("AI 压缩调用失败")
            await asyncio.sleep(0.5)

    @staticmethod
    def _build_compress_input(summary, to_compress, skills=()) -> str:
        """构造压缩输入：[旧摘要] + [涉及技能] + [待压缩的对话历史]。"""
        history_text = "\n".join([
            f"[{it.get('time', '未知时间')}] 用户: {it.get('ask', '')}\nAI: {it.get('ans', '')}"
            for it in to_compress
        ])
        skills_text = "、".join(skills) if skills else "（无）"
        return (
            f"[旧摘要]\n{summary or '（无）'}\n\n"
            f"[涉及技能]\n{skills_text}\n\n"
            f"[待压缩的对话历史]\n{history_text}"
        )

    async def _compress_context(self, session: CommandSession):
        """历史超过阈值时，把最旧的一部分压缩成摘要，存回 history 文件。

        摘要作为第一条特殊 history（携带 summary 键）存放；
        后续 get_history 会在上下文最前面注入这条摘要，让 AI 知道这是总结。
        """
        session_obj = AISession(self.user_id, self.ai_session)
        user_history = session_obj.load_history()
        summary, summary_skills, normals = history.split(user_history)
        if len(normals) <= COMPRESS_TRIGGER:
            return 0
        await send_session_msg(session, get_message("plugins", __plugin_name__, "compress_context"))
        to_compress = normals[:len(normals) - CONTEXT_KEEP_RECENT]
        keep = normals[len(normals) - CONTEXT_KEEP_RECENT:]
        # 合并旧摘要携带的skills与被压缩记录里用过的skills，压缩后依旧保留
        compressed_skills = sorted(set(summary_skills) | {
            s for it in to_compress for s in (it.get("activate_skills", []) or [])
        })
        try:
            memory_prompt = read_from_path("./ai_configs.json")[__plugin_name__]["memory"]
            if memory_prompt:
                memory_prompt = memory_prompt.format(max_length=COMPRESS_MAX_LENGTH)
            content = await self._glm_chat([
                {"role": "system", "content": memory_prompt},
                {"role": "user", "content": self._build_compress_input(summary, to_compress, compressed_skills)},
            ])
            new_summary = (content or "").strip()
            if new_summary:
                summary = new_summary
                new_history = history.merge(summary, keep, get_time_now(), skills=compressed_skills)
                session_obj.save_history(new_history)
                ai_logger.info(
                    f"上下文已压缩：把 {len(to_compress)} 条历史压成摘要（{len(summary)} 字），保留最近 {len(keep)} 条。"
                )
                await send_session_msg(session, get_message("plugins", __plugin_name__, 'talking_to_ai', model=self.model_arg))
                return len(summary)
        except Exception as ex:
            ai_logger.exception(f"上下文压缩失败: {ex}")
            return 0
        return 0

    async def get_video_url_dicts(self, text):
        links = extract_video_links(text)
        pth = f"./data/videos/temp/"
        pths = []
        if len(links) < 1:
            return text, [], []

        result: VideoExtractResult = await extract_and_download(
            text,
            output_dir=pth
        )
        links = result.links

        video_dicts = []
        new_text = text
        try:
            for link, r in sorted(zip(result.links, result.downloads),
                                key=lambda p: p[0].start, reverse=True):
                if not r.ok:
                    raise ValueError(f"下载视频出现错误：{r.error}")
                video_info = await parse_video(r.url)
                desc = video_info.description if video_info and video_info.description else "无"
                desc = desc[:200] + "..." if len(desc) > 200 else desc
                desc = desc.replace("\r\n", "\n").replace("\r", "\n")
                title = video_info.title if video_info else (r.title or "未知标题")
                platform = f"{video_info.platform_name}-{video_info.video_id}" if video_info else "未知平台信息"
                desc = f"``` Text\n{desc}\n```" if desc.count("\n") > 1 else '"' + desc.strip("\n") + '"'
                info_text = f"[视频:{platform}] 标题：{title} | url:{link.url} | 介绍:{desc} "
                new_text = new_text[:link.start] + info_text + new_text[link.end:]
                for f in r.file_paths:
                    pths.append(f)
                    video_dicts.append({"type": "video_url", "video_url": {"url": get_local_file_url(str(f))}})
            return new_text, video_dicts, pths
        except Exception as ex:
            return f"[解析视频出现异常: {ex}]" + new_text, [], []

    async def user_talk(self, session: CommandSession, role, user, text):
        self.spent_secs.start()
        self.pending_messages.clear()
        compressed = await self._compress_context(session)
        history, curr_text = await get_history(user, self.ai_session)

        # 提取 text 里的图片
        image_objects, matches = await get_images_from_message(session.bot, text)
        # pattern = r"\[CQ:image,(?![^\]]*emoji_id=)[^\]]*file=[^\]]*?\]"
        # matches = re.findall(pattern, text)
        for image_cq in matches:
            text = text.replace(image_cq, f"[图片{hash_text(image_cq)}]")
        image_urls = [x["file"] for x in image_objects]

        text, video_dicts, pths = await self.get_video_url_dicts(text)
        self.temp_file_paths += pths
        self.user_input_urls["images"] = image_urls
        url_dicts = [{"type": "image_url", "image_url": {"url": v}} for v in image_urls]
        url_dicts += video_dicts
        ai_logger.info(f"用户 {user.id} 说：{text}")
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
        prefix = ""
        ai_logger.debug(f"params: {ai_params}")
        real_model = "glm-5.3-flash" if len(url_dicts) > 0 else self.model
        if real_model != self.model:
            prefix = get_message("plugins", __plugin_name__, "model_change_prefix", model=self.model, vision_model=real_model)
        result, tool_call_times =  await self.run_agent(session, ai_params, model=real_model)
        self.spent_secs.stop()
        if result == False:
            return False, {}, {}, 0
        try:
            ans = result.choices[0].message.content

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
            if not (await is_text_can_send(session, ans)):
                return "这个话题好像不是很合适呢...我们换个话题聊吧。", {"credits_use": credits_use, "cached": self.cached_tokens, "total": self.tokens}, {"messages": self.pending_messages, "prefix": prefix, "history_compressed": compressed, "talk_secs": self.spent_secs.get_timer_value()}
            build_history(
                user=user,
                ask=text,
                ans=ans,
                agent=self,
            )
            return ans, {"credits_use": credits_use, "cached": self.cached_tokens, "total": self.tokens}, {"messages": self.pending_messages, "prefix": prefix, "history_compressed": compressed, "talk_secs": self.spent_secs.get_timer_value()}, tool_call_times
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


async def get_history(user: u.User, ai_session=history.DEFAULT_SESSION):
    user_history = AISession(user.id, ai_session).load_history()
    if not user_history:
        return "", ""
    build_list = [{
        "role": "user",
        "content": f"[历史记录-会话 \"{ai_session}\"]",
    }]
    summary = None
    summary_skills: list[str] = []
    uname = await get_user_name(user.id, default='未知用户')
    for _, item in enumerate(user_history):
        if history.is_summary(item):
            summary = item.get("summary")
            summary_skills = list(item.get("skills", []) or [])
            continue
        url_dicts = item.get('urls', {})
        url_str = "|".join([f"{k}: " + "、".join(v) for k, v in url_dicts.items()])
        url_str = f"[附带URLs:{url_str}]" if len(url_str) > 0 else ""
        skills = item.get('activate_skills', [])
        build_dicts = [{
            "role": "user",
            "content": f"[历史记录-{item.get('time', '未知时间')}][{uname}(qq{user.id})]{url_str} {item['ask']}",
        }]
        tool_calls = []
        tool_messages = []
        if skills:
            for s in skills:
                try:
                    with open(f"./static/skills/{s}.md", 'r', encoding="utf-8") as file:
                        skill = file.read()
                except FileNotFoundError:
                    logger.warning(f"无法找到 skill 文件: {s}.md")
                    continue
                except Exception:
                    logger.exception(f"读取 skill 文件 {s}.md 出错")
                    continue
                tool_id = uuid4().hex
                tool_calls.append({
                    "id": tool_id,
                    "type": "function",
                    "function": {
                        "name": "get_skill_md",
                        "arguments": json.dumps({
                            "name": s
                        })
                    }
                })
                tool_messages.append({
                    "role": "tool",
                    "content": skill,
                    "tool_call_id": tool_id
                })
        if tool_calls:
            build_dicts.append({
                "role": "assistant",
                "tool_calls": tool_calls,
            })

            build_dicts.extend(tool_messages)

        build_dicts.append({
            "role": "assistant",
            "content": item["ans"],
        })
        build_list += build_dicts
    if summary:
        # 在上下文最前面注入长期记忆摘要，让 AI 知道这是此前对话的总结（含用过的技能）
        skill_hint = f"；涉及技能：{'、'.join(summary_skills)}" if summary_skills else ""
        build_list.insert(0, {"role": "user", "content": f"[长期记忆摘要（此前对话总结，供你参考{skill_hint}）：\n{summary}\n]"})
    build_str = f"\n当前对话（现在时间为 {get_time_now()}）发送者为{uname}(qq{user.id})："
    return build_list, build_str


def build_history(user: u.User, ask, ans, agent):
    session_obj = AISession(user.id, agent.ai_session)
    user_history = session_obj.load_history()
    summary, summary_skills, normals = history.split(user_history)
    normals.append({
        "ask": ask,
        "ans": ans,
        "time": get_time_now(),
        "urls": agent.user_input_urls,
        "activate_skills":  agent.activate_skills,
    })
    if len(normals) > MAX_HISTORY_COUNT:
        normals = normals[-MAX_HISTORY_COUNT:]
    session_obj.save_history(history.merge(summary, normals, skills=summary_skills))
