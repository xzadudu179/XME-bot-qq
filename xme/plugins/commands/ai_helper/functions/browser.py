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
from xme.xmetools.browsertools import (CDPBrowser, CDPError, run_macro,
                                        frames_to_mp4)

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


async def _record_core(source: str, duration: int | None, script: list, show_cursor: bool,
                       render_width: int, preset: dict, agent,
                       make_ref: bool = True) -> tuple[Path, str, list[str], str | None]:
    """两个录制工具共享的录制核心：headless+GPU 渲染页面，CDP 采集画面后编码成 mp4。

    宏回放与画面采集并行。duration 为 None 时不限窗（宏决定时长，宏完成即停录）；
    为数值时为硬窗（宏超窗部分截断/忽略）。make_ref=False 时不登记 temp 引用
    （即发即删的交付档用——AI 不应拿到可保存的引用）。宏的元素定位按布局视口计算。
    返回 (视频文件路径, temp 引用, 宏执行备注, 错误文案——成功为 None)。
    """
    notes: list[str] = []
    fps = float(preset["fps"])
    width = int(preset["output_width"])            # 输出宽度由档位单点定义
    render_width = int(render_width or 0) or RECORD_DEFAULT_RENDER_WIDTH
    render_width = max(width, min(render_width, RECORD_LAYOUT_MAX_WIDTH))
    render_height = render_width * 9 // 16
    video_name = f"{uuid4().hex}.mp4"
    if make_ref:
        ref_dir, out_ref = _create_file_ref(agent.user_id, "video_", video_name, agent)
        out_path = ref_dir / video_name
    else:
        out_ref = ""
        out_path = agent.get_temp_path() / video_name

    frames: list[tuple[bytes, float]] = []
    try:
        async with asyncio.timeout(duration + 120 if duration else RECORD_MAX_DURATION + 120):
            async with CDPBrowser(render_width, render_height) as browser:
                await browser.navigate(source, wait_ms=BROWSER_NAV_WAIT_MS)
                if show_cursor:
                    await browser.inject_cursor()
                await browser.start_capture(
                    lambda jpeg, ts: frames.append((jpeg, ts)),
                    quality=int(preset.get("jpeg_quality", 95)))
                started = time.monotonic()
                try:
                    macro_task = asyncio.create_task(
                        run_macro(browser, script, duration, show_cursor, notes=notes))
                    if duration is None:
                        # 宏决定时长：宏跑完（自守窗）即停录
                        await macro_task
                        span = time.monotonic() - started
                    else:
                        await asyncio.sleep(duration)
                        span = float(duration)
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
                    await browser.stop_capture()
        if not frames:
            return out_path, out_ref, notes, "[录制失败：未采集到任何画面帧]"
        await frames_to_mp4(frames, out_path, width, fps=fps, span=span,
                            crf=int(preset["crf"]),
                            preset=str(preset.get("preset", "veryfast")),
                            x264_params=str(preset.get("x264_params", "")))
    except TimeoutError:
        return out_path, out_ref, notes, "[录制失败：浏览器会话超时]"
    except CDPError as ex:
        return out_path, out_ref, notes, f"[录制失败：{exception_detail(ex)}]"
    if not out_path.is_file() or out_path.stat().st_size <= 0:
        return out_path, out_ref, notes, "[录制失败：未产出有效视频]"
    return out_path, out_ref, notes, None


async def record_page(url: str = "", duration: int = 0, script=None,
                      show_cursor: bool = True, agent_prompt: str = "",
                      render_width: int = 0, ref: str = "",
                      agent=None, session=None):
    """录制页面一段时间并合成视频（medium 质量的工作档）：宏回放（可选虚拟光标）→ mp4。

    产出的视频留在 temp（引用 ref 可用 view_video 查看、save_to_history 转存），
    填写 agent_prompt 可把视频注入给你亲自检查动效/交互效果。
    url 与 ref 二选一（ref 为 temp 里的本地页面引用——录自己刚写的 html 动画直接传 ref）。
    duration 可省略：省略时录制在所有宏动作完成后自动结束（此时必须提供 script）；
    指定 duration（3~60）时优先于宏——宏超窗部分会截断/忽略。
    render_width 手动指定浏览器布局宽度（可选，缺省统一 1920 桌面排版）；
    想要"大布局录小视频"可显式指定（如 quality=medium + render_width=1920：按 1920 排版、
    缩放输出 1280）。宏的坐标/元素定位均按布局视口计算，输出缩放不影响命中。
    script 为鼠标/键盘宏（元素为动作对象，t 为距上一个动作完成后的秒数，+t 增量）：
      {"t":0.5,"type":"move","selector":"#btn","speed":600,"timeout":5}  追踪移动到元素/坐标(x,y)
      {"t":2.0,"type":"jump","x":100,"y":200}              瞬移到坐标/元素
      {"t":3.0,"type":"click"}                             在鼠标当前位置点击（先用 move/jump 移过去）
      {"t":4.0,"type":"wait","secs":2}                     原地等待 2 秒（录悬停效果/动画过程）
      {"t":6.0,"type":"type","text":"hello"}               逐字符键盘输入（需先点击输入框聚焦）
      {"t":8.0,"type":"key","key":"Enter"}                 按键（Enter/Backspace/Tab/Escape/方向键等）
    show_cursor=False 时不注入虚拟光标（录纯页面动画，宏的真实输入事件照常生效）。
    视频只存本轮 temp（对话结束即清，不长期保存）。
    要生成发给用户的高清成品视频请改用 record_page_hd。
    """
    if agent is None:
        return {"result": "[录制失败：缺少会话上下文]", "no_compress": True}
    auto_duration = int(duration or 0) <= 0
    has_script = isinstance(script, list) and bool(script)
    if auto_duration and not has_script:
        return {"result": ("[录制失败：未指定 duration 时需要 script 宏来决定录制长度"
                           "（或显式传 duration 3~60 录固定时长）]"), "no_compress": True}
    preset = RECORD_QUALITY_PRESETS["medium"]
    source, source_error = _resolve_source(url, ref, agent)
    if source_error:
        return {"result": source_error, "no_compress": True}

    run_duration = None if auto_duration else max(3, min(int(duration), RECORD_MAX_DURATION))
    out_path, out_ref, notes, error = await _record_core(
        source, run_duration, script, show_cursor, render_width, preset, agent)
    if error:
        return {"result": error, "no_compress": True}
    size_mb = out_path.stat().st_size / 1048576
    out_w = int(preset["output_width"])
    summary = (f"已录制页面 {ref or url}（输出 {out_w}x{out_w * 9 // 16}"
               f"@{preset['fps']}fps，{size_mb:.1f} MiB，medium 质量），"
               f"temp 引用 {out_ref}（对话结束自动清理）。")
    if notes:
        summary += "\n宏执行备注：\n- " + "\n- ".join(notes)
    if agent_prompt:
        from .web import view_item
        view_result = await view_item(
            ref=out_ref, item_type="video_url", prompt=agent_prompt, agent=agent)
        # 注意顺序：ImageToolResult 是 str 子类，必须先判子类再判普通字符串
        if isinstance(view_result, ImageToolResult):
            return ImageToolResult(f"{summary}\n[录制的视频已直接附在输入中]\n{view_result}",
                                   view_result.image_parts)
        if isinstance(view_result, str) and view_result.startswith("["):
            return {"result": f"{summary}\n视频查看失败：{view_result}",
                    "ref": out_ref, "no_compress": True}
        if isinstance(view_result, str):
            return {"result": f"{summary}\n视频分析结果：\n{view_result}",
                    "ref": out_ref, "no_compress": True}
    return {"result": summary, "ref": out_ref, "no_compress": True}


async def record_page_hd(url: str = "", duration: int = 0, script=None,
                         show_cursor: bool = True, render_width: int = 0,
                         new_name: str = "", ref: str = "",
                         agent=None, session=None):
    """录制页面为高质量视频（1920 宽、30fps、高码率）并立即以私聊文件发给用户。

    专为"最终交付给用户的高清页面动画/交互视频"设计：录制完成后直接发给用户，
    视频随即删除——无法保存、没有引用、也不能注入给你查看；
    需要先自己检查效果请用 record_page（medium 质量）。
    url 与 ref 二选一；duration/script/show_cursor/render_width 与 record_page 相同
    （duration 可省略 = 宏完即停）。new_name 为发给用户的视频文件名（默认"页面录制.mp4"）。
    """
    if agent is None:
        return {"result": "[录制失败：缺少会话上下文]", "no_compress": True}
    if session is None or getattr(session, "bot", None) is None:
        return {"result": "[录制失败：无法获取会话上下文（高质量视频必须发给用户）]",
                "no_compress": True}
    auto_duration = int(duration or 0) <= 0
    has_script = isinstance(script, list) and bool(script)
    if auto_duration and not has_script:
        return {"result": ("[录制失败：未指定 duration 时需要 script 宏来决定录制长度"
                           "（或显式传 duration 3~60 录固定时长）]"), "no_compress": True}
    preset = RECORD_QUALITY_PRESETS["max"]
    source, source_error = _resolve_source(url, ref, agent)
    if source_error:
        return {"result": source_error, "no_compress": True}
    new_name = str(new_name or "").strip() or "页面录制.mp4"
    if not is_safe_custom_name(new_name):
        return {"result": f"[发送失败：文件名 {new_name} 不合法（仅允许中英文/数字/_-.，不含路径）]",
                "no_compress": True}

    run_duration = None if auto_duration else max(3, min(int(duration), RECORD_MAX_DURATION))
    out_path, out_ref, notes, error = await _record_core(
        source, run_duration, script, show_cursor, render_width, preset, agent,
        make_ref=False)
    if error:
        return {"result": error, "no_compress": True}
    size_mb = out_path.stat().st_size / 1048576
    dur_text = "宏决定" if auto_duration else f"{run_duration}s"
    out_w = int(preset["output_width"])
    summary = (f"已录制页面 {ref or url}（输出 {out_w}x{out_w * 9 // 16}"
               f"@{preset['fps']}fps，{dur_text}，{size_mb:.1f} MiB，高质量），")
    if notes:
        summary += "\n宏执行备注：\n- " + "\n- ".join(notes)

    from .files import SEND_OK, SEND_UNKNOWN, send_local_file
    status, info = await send_local_file(session, out_path, new_name)
    if status == SEND_UNKNOWN:
        # 超时：协议端可能仍在读该文件上传，画面已发出与否不可知——
        # 既不删文件（删了会打断上传，残留由 temp 清理收尾），也不让 AI 盲目重发（会重复投递）
        return {"result": f"{summary}[发送结果未知：{info}｜文件保留待 temp 清理]",
                "no_compress": True}
    out_path.unlink(missing_ok=True)   # 即发即删：确认送达或确认失败都不留文件
    if status != SEND_OK:
        return {"result": f"{summary}[发送用户失败：{info}，视频已删除，请重试]",
                "no_compress": True}
    return {"result": f"{summary}已把视频以文件形式发给用户：{info}（发送后已删除，不占用空间）。",
            "sent_to_user": True, "no_compress": True}
