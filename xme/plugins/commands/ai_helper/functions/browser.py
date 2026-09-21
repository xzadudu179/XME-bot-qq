# 浏览器工具：元素监听（monitor_element）与页面录制（record_page）。
# 浏览器驱动与宏回放的实现在 xme/xmetools/browsertools.py（一次性 headless chrome CDP 会话）。
"""浏览器类工具：页面元素监听与页面录制（宏回放，录制成视频）。"""
import asyncio
import json
import time
from pathlib import Path
from uuid import uuid4

from nonebot.log import logger
from xme.xmetools.filetools import _create_file_ref, is_safe_custom_name
from xme.xmetools.reqtools import assert_public_http_url
from xme.xmetools import browsertools
from xme.xmetools.browsertools import CDPBrowser, CDPError, run_macro, frames_to_mp4

from ..constants import (BROWSER_NAV_WAIT_MS, MONITOR_MAX_DURATION, MONITOR_MAX_INTERVAL,
                         RECORD_MAX_DURATION, RECORD_DEFAULT_RENDER_WIDTH,
                         RECORD_LAYOUT_MAX_WIDTH, RECORD_QUALITY_PRESETS)
from ._common import exception_detail, ImageToolResult


def _resolve_source(url: str, ref: str, agent) -> tuple[str | None, str | None]:
    """解析录制/监听源：ref（temp/history 里的本地页面，如 AI 刚写的 html）与公网 url 二选一。

    返回 (source, None) 或 (None, 错误文案)。本地文件走 file://（同 screenshot_page，无 SSRF 面），
    网络地址过 assert_public_http_url。
    """
    if bool(url) == bool(ref):
        return None, "[url 与 ref 二选一：本地页面（如你刚写的 html）传 ref，公网页面传 url]"
    if ref:
        try:
            p = Path(agent.resolve_ref(ref))
        except KeyError:
            return None, f"[没有找到引用 {ref}]"
        if not p.is_file():
            return None, f"[引用 {ref} 指向的文件不存在]"
        return p.resolve().as_uri(), None
    url = (url or "").strip()
    if not url.lower().startswith(("http://", "https://")):
        return None, "[url 需要以 http:// 或 https:// 开头]"
    try:
        assert_public_http_url(url)
    except Exception as ex:
        return None, f"[url 被拒绝：{exception_detail(ex)}]"
    return url, None


async def monitor_element(url: str = "", selector: str = "", duration: int = 20,
                          interval: int = 2, attr: str = "", ref: str = "", agent=None):
    """监听页面元素在一段时间内的取值变化，返回变化时间线。

    selector 为 CSS 选择器；attr 留空取元素可见文本（innerText），
    填属性名（如 value/href/class）则取对应属性。url 与 ref 二选一
    （ref 为 temp 里的本地 html/svg 页面引用）。
    """
    duration = max(1, min(int(duration), MONITOR_MAX_DURATION))
    interval = max(1, min(int(interval), MONITOR_MAX_INTERVAL))
    if not (selector or "").strip():
        return {"result": "[监听失败：selector 不能为空]", "no_compress": True}
    source, source_error = _resolve_source(url, ref, agent)
    if source_error:
        return {"result": source_error, "no_compress": True}
    attr_expr = f"el.getAttribute({json.dumps(str(attr))}) ?? el.value" if attr else "el.innerText"
    sample_expr = (f"""(() => {{ const el = document.querySelector({json.dumps(str(selector))});
         if (!el) return null; return String({attr_expr} ?? ""); }})()""")
    samples: list[tuple[float, str | None]] = []
    error = ""
    try:
        async with asyncio.timeout(duration * 2 + 60):
            async with CDPBrowser(1280, 720) as browser:
                await browser.navigate(source, wait_ms=BROWSER_NAV_WAIT_MS)
                start = time.monotonic()
                while time.monotonic() - start < duration:
                    elapsed = time.monotonic() - start
                    try:
                        samples.append((elapsed, await browser.evaluate(sample_expr)))
                    except CDPError as ex:
                        error = str(ex)
                        break
                    await asyncio.sleep(interval)
    except TimeoutError:
        return {"result": "[监听失败：浏览器会话超时]", "no_compress": True}
    except CDPError as ex:
        return {"result": f"[监听失败：{ex}]", "no_compress": True}
    if not samples:
        detail = f"（{error}）" if error else ""
        return {"result": f"[没有采到任何数据{detail}：页面可能加载失败或 selector 一直无法执行]",
                "no_compress": True}
    # 时间线：首条必记，其后只在取值变化时记录
    missing = all(v is None for _, v in samples)
    timeline: list[str] = []
    last = object()
    for elapsed, value in samples:
        if value != last:
            shown = "(元素不存在)" if value is None else value
            timeline.append(f"[+{elapsed:.1f}s] {shown[:200]}")
            last = value
    if missing:
        note = "整个监听期间元素都不存在，请检查 selector 或页面是否需要登录/跳转。"
    else:
        note = f"共采样 {len(samples)} 次（间隔 {interval}s、时长 {duration}s），元素取值变化 {max(0, len(timeline) - 1)} 次。"
    return {"result": "元素监听时间线（selector: " + selector + "）：\n" + "\n".join(timeline) + "\n" + note,
            "no_compress": True}


async def record_page(url: str = "", duration: int = 0, script=None,
                      show_cursor: bool = True,
                      send_to_user: bool = False, new_name: str = "", ref: str = "",
                      quality: str = "medium", render_width: int = 0,
                      agent_prompt="", agent=None, session=None):
    """录制页面一段时间并合成视频：宏回放（可选虚拟光标）→ mp4 → 发给 agent/用户。

    url 与 ref 二选一（ref 为 temp 里的本地页面引用——录自己刚写的 html 动画直接传 ref）。
    输出分辨率由 quality 档位定义（low 640 / medium 1280 / high 1920 宽）。
    duration 可省略：省略时录制在所有宏动作完成后自动结束（此时必须提供 script）；
    指定 duration（3~60）时优先于宏——宏超窗部分会截断/忽略。
    render_width 手动指定浏览器布局宽度（可选，缺省统一 1920 桌面排版）；
    想要"大布局录小视频"可显式指定（如 quality=medium + render_width=1920：按 1920 排版、
    缩放输出 1280）。宏的坐标/元素定位均按布局视口计算，输出缩放不影响命中。
    agent_prompt 是录制完成后把视频注入给你查看时的关注点提示词（如"检查悬停动效是否流畅"）：
    留空则不注入、只返回视频引用（可用 view_video 自行查看）。
    script 为鼠标/键盘宏（元素为动作对象，t 为距上一个动作完成后的秒数，+t 增量）：
      {"t":0.5,"type":"move","selector":"#btn","speed":600,"timeout":5}  追踪移动到元素/坐标(x,y)
      {"t":2.0,"type":"jump","x":100,"y":200}              瞬移到坐标/元素
      {"t":3.0,"type":"click"}                             在鼠标当前位置点击（先用 move/jump 移过去）
      {"t":4.0,"type":"wait","secs":2}                     原地等待 2 秒（录悬停效果/动画过程）
      {"t":6.0,"type":"type","text":"hello"}               逐字符键盘输入（需先点击输入框聚焦）
      {"t":8.0,"type":"key","key":"Enter"}                 按键（Enter/Backspace/Tab/Escape/方向键等）
    show_cursor=False 时不注入虚拟光标（录纯页面动画，宏的真实输入事件照常生效）。
    quality: low/medium/high。high 体积大，只允许"刚生成完就发给用户"——发送后文件
    立即删除，不能注入给自己查看，也不留在 temp；要自己看效果请用 medium/low。
    medium/low 视频只存本轮 temp（对话结束即清，不长期保存）。
    """
    if agent is None:
        return {"result": "[录制失败：缺少会话上下文]", "no_compress": True}
    # 兼容 AI 传布尔值：true 用默认查看提示词，false 视为不注入
    default_agent_prompt = ("这是刚才录制的页面视频。请仔细观看并描述其中的页面内容、"
                            "动效/交互效果（以及鼠标操作后的页面反应），指出做得好与有问题的地方。")
    if isinstance(agent_prompt, bool):
        agent_prompt = default_agent_prompt if agent_prompt else ""
    agent_prompt = str(agent_prompt or "").strip()
    send_to_agent = bool(agent_prompt)   # 注入开关由提示词有无决定
    auto_duration = int(duration or 0) <= 0
    has_script = isinstance(script, list) and bool(script)
    if auto_duration and not has_script:
        return {"result": ("[录制失败：未指定 duration 时需要 script 宏来决定录制长度"
                           "（或显式传 duration 3~60 录固定时长）]"), "no_compress": True}
    duration = max(3, min(int(duration or 0), RECORD_MAX_DURATION)) if not auto_duration \
        else RECORD_MAX_DURATION   # 自动模式：保险窗（宏自守窗，正常在窗内自然结束）
    preset_name = str(quality or "medium").lower()
    preset = RECORD_QUALITY_PRESETS.get(preset_name)
    if preset is None:
        return {"result": (f"[录制失败：未知质量 {quality!r}（可选 low/medium/high）。"
                           "high 只能刚生成完就发给用户（send_to_user=true）并自动删除，"
                           "要自己查看效果请用 medium/low）"), "no_compress": True}
    delivery_only = preset_name in ("high")
    if delivery_only:
        # 高画质 = 大体积交付档：只能"生成→发用户→立即删"；注入自看/留 temp 都不允许
        if send_to_agent:
            return {"result": ("[高画质视频生成后立即删除，无法注入给你查看。"
                               "请留空 agent_prompt（要自己看效果请用 quality=medium/low），"
                               "只把视频发给用户（send_to_user=true）]"), "no_compress": True}
        if not send_to_user:
            return {"result": ("[高画质视频只能刚生成完就发给用户（send_to_user=true）然后自动删除，"
                               "不留在 temp。要自己查看效果请用 quality=medium/low]"),
                    "no_compress": True}
    if not isinstance(script, list):
        script = []
    source, source_error = _resolve_source(url, ref, agent)
    if source_error:
        return {"result": source_error, "no_compress": True}
    new_name = str(new_name or "").strip()
    if send_to_user and new_name and not is_safe_custom_name(new_name):
        return {"result": f"[发送失败：文件名 {new_name} 不合法（仅允许中英文/数字/_-.，不含路径）]",
                "no_compress": True}

    width = int(preset["output_width"])            # 输出宽度由档位单点定义
    height = width * 9 // 16
    # 布局视口（浏览器窗口）：缺省统一 1920（桌面排版，AI 无需考虑响应式）；
    # render_width 可显式覆盖。宏的元素定位按布局视口计算，输出缩放不影响命中。
    render_width = int(render_width or 0) or RECORD_DEFAULT_RENDER_WIDTH
    render_width = max(width, min(render_width, RECORD_LAYOUT_MAX_WIDTH))
    render_height = render_width * 9 // 16
    supersample = int(preset.get("supersample", 1))   # 设备缩放（DSF）：真超采样，布局不变
    video_name = f"{uuid4().hex}.mp4"
    ref_dir, out_ref = _create_file_ref(agent.user_id, "video_", video_name, agent)
    out_path = ref_dir / video_name

    frames: list[tuple[bytes, float]] = []
    notes: list[str] = []
    try:
        async with asyncio.timeout(duration + 120):
            async with CDPBrowser(render_width, render_height,
                                  scale_factor=supersample) as browser:
                await browser.navigate(source, wait_ms=BROWSER_NAV_WAIT_MS)
                if show_cursor:
                    await browser.inject_cursor()
                await browser.start_screencast(
                    lambda jpeg, ts: frames.append((jpeg, ts)),
                    quality=int(preset.get("jpeg_quality", 60)),
                    every_nth=int(preset.get("every_nth", 1)))
                try:
                    # notes 传引用：宏超窗被取消时，已记录的备注不丢
                    macro_task = asyncio.create_task(
                        run_macro(browser, script, None if auto_duration else duration,
                                  show_cursor, notes=notes))
                    if auto_duration:
                        # 宏决定时长：宏跑完（自守窗）即停录
                        await macro_task
                    else:
                        await asyncio.sleep(duration)
                        try:
                            # 硬性录制窗：宏自守窗后最多再宽限 8s（收尾动作），
                            # 仍不结束则取消——视频时长必须忠于 duration
                            await asyncio.wait_for(asyncio.shield(macro_task), timeout=8)
                        except asyncio.TimeoutError:
                            macro_task.cancel()
                            notes.append("宏未在录制窗内完成，已随录制结束截断")
                        except asyncio.CancelledError:
                            pass
                finally:
                    stop_epoch = time.time()   # 截断基准：缓冲/竞态迟到的帧不含在内
                    await browser.stop_screencast()
            frames = [f for f in frames if f[1] <= stop_epoch + 1]
        frame_span = (stop_epoch - frames[0][1]) if frames else None
        await frames_to_mp4(frames, out_path, width,
                            fps_cap=float(preset["fps_cap"]), crf=int(preset["crf"]),
                            preset=str(preset.get("preset", "veryfast")),
                            x264_params=str(preset.get("x264_params", "")),
                            span=frame_span)
    except TimeoutError:
        return {"result": "[录制失败：浏览器会话超时]", "no_compress": True}
    except CDPError as ex:
        return {"result": f"[录制失败：{exception_detail(ex)}]", "no_compress": True}
    size_mb = out_path.stat().st_size / 1048576
    layout_note = f"，布局 {render_width}x{render_height}" if render_width != width else ""
    summary = (f"已录制页面 {ref or url}（输出 {width}x{height}{layout_note}，"
               f"{size_mb:.1f} MiB，质量 {preset_name}），")
    if delivery_only:
        summary += "高画质视频发送后即删除。"
    else:
        summary += f"temp 引用 {out_ref}（对话结束自动清理）。"
    if notes:
        summary += "\n宏执行备注：\n- " + "\n- ".join(notes)

    if send_to_user:
        from .files import send_local_file
        ok, info = await send_local_file(session, out_path, new_name or None)
        summary += ("已把视频以文件形式发给用户：" + info if ok
                    else f"发送用户失败：{info}")
        if ok and delivery_only:
            # 高质量档即发即删：文件已交付，不再占空间；产出引用一并作废
            out_path.unlink(missing_ok=True)
            agent.ref_map.pop(out_ref, None)
            summary += "（视频文件已删除，不占用空间）"
            return {"result": summary, "sent_to_user": True, "no_compress": True}
        summary += f"\n视频留在 temp，引用 {out_ref}。"

    if send_to_agent:
        from .web import view_item
        view_result = await view_item(
            ref=out_ref, item_type="video_url",
            prompt=agent_prompt, agent=agent)
        # 注意顺序：ImageToolResult 是 str 子类，必须先判子类再判普通字符串
        if isinstance(view_result, ImageToolResult):
            return ImageToolResult(f"{summary}\n[录制的视频已直接附在输入中]\n{view_result}",
                                   view_result.image_parts)
        if isinstance(view_result, str) and view_result.startswith("["):
            summary += f"\n视频查看失败：{view_result}"
            return {"result": summary, "ref": out_ref, "no_compress": True}
        if isinstance(view_result, str):
            return {"result": f"{summary}\n视频分析结果：\n{view_result}",
                    "ref": out_ref, "no_compress": True}
        return {"result": summary, "ref": out_ref, "no_compress": True}
    return {"result": summary, "ref": out_ref, "no_compress": True}
