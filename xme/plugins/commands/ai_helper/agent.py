from pathlib import Path
import re
import shutil
import json
import inspect
from traceback import format_exc

import config
from nonebot import CommandSession, MessageSegment

from nonebot.log import logger
from xme.xmetools.filetools import dict_to_file, text_to_file
from xme.xmetools.texttools import get_images_from_message, hash_text
from xme.xmetools.debugtools import debug_msg
from xme.xmetools.msgtools import send_session_msg, aget_arg_with_timeout, setup_logger
from xme.xmetools.bottools import get_user_name
from xme.xmetools.timetools import get_time_now
from character import get_message
from keys import GLM_API_KEY
from xme.plugins.commands.xme_user.classes import user as u
from zai import ZhipuAiClient

from .constants import (
    __plugin_name__,
    MAX_CHECK_TIMES,
    MAX_TOOL_CALL_TIMES,
    MAX_HISTORY_COUNT,
)
from .functions import (
    get_telia_clock_state,
    gen_image,
    get_skill_md,
    check_file,
    list_temp_files,
    save_to_history,
    clear_history_files,
    inprocess_report,
    ocr_image,
    view_file,
    view_image,
    view_video,
    read_webpage,
    web_search,
    content_search,
    get_webs_partial,
)


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

    def _check_user_path(self):
        Path(f"./data/temp/{self.user_id}").mkdir(parents=True, exist_ok=True)

    def get_history_path(self):
        path = self.get_temp_path() / "history"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def resolve_ref(self, ref: str) -> str:
        """解析 ref 对应的文件名（相对 temp 根目录），支持跨会话的 history 引用。

        history 文件按 history_N.tmp 命名，其引用 history_N 可由此推导，
        因此即使当前会话 ref_map 未注册，也能直接解析。
        """
        file_name = self.ref_map.get(ref, None)
        if file_name is not None:
            return file_name
        if ref.startswith("history_") and ref[len("history_"):].isdigit():
            candidate = f"history/{ref}.tmp"
            if (self.get_temp_path() / candidate).exists():
                self.ref_map[ref] = candidate
                return candidate
        raise KeyError(f"无法找到引用 {ref}")

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
        # 工具使用依赖注入：所有 tool 都是独立函数，需要 agent 的函数声明 agent 形参，
        # 由 execute_tool 在执行时注入，避免工具内部再实例化 agent 造成连环调用。
        self.tool_functions = {
            "get_telia_clock_state": get_telia_clock_state,
            "gen_image": gen_image,
            "get_skill_md": get_skill_md,
            "check_file": check_file,
            "list_temp_files": list_temp_files,
            "save_to_history": save_to_history,
            "clear_history_files": clear_history_files,
            "inprocess_report": inprocess_report,
            "ocr_image": ocr_image,
            "view_file": view_file,
            "view_image": view_image,
            "view_video": view_video,
            "read_webpage": read_webpage,
            "web_search": web_search,
            "content_search": content_search,
            "get_webs_partial": get_webs_partial,
        }
        self.pending_messages = []
        # 工具 schema 从 tools.json 读取
        tools_path = Path(__file__).parent / "tools.json"
        with open(tools_path, "r", encoding="utf-8") as f:
            self.tools = json.load(f)

    async def run_agent(self, session, messages, model):
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
        raise TimeoutError(f"AI 调用超时 (>{MAX_CHECK_TIMES}次)")

    async def user_talk(self, session: CommandSession, role, user, text):
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


async def get_history(user: u.User):
    user_history = user.ai_history
    if not user_history:
        return "", ""
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
    build_str = f"\n当前对话（现在时间为 {get_time_now()}）发送者为{uname}(qq{user.id})："
    return build_list, build_str


def build_history(user: u.User, ask, ans):
    user.ai_history.append({
        "ask": ask,
        "ans": ans,
        "time": get_time_now()
    })
    if len(user.ai_history) > MAX_HISTORY_COUNT:
        # TODO 压缩上下文
        del user.ai_history[-1]
