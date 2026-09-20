# 浏览器工具：元素监听（monitor_element）与页面录制（record_page）。
# 浏览器驱动与宏回放的实现在 xme/xmetools/browsertools.py（一次性 headless chrome CDP 会话）。
"""浏览器类工具：页面元素监听与页面录制（宏回放，录制成视频）。"""
import asyncio
import json
import time
from uuid import uuid4

from nonebot.log import logger
from xme.xmetools.filetools import _create_file_ref, is_safe_custom_name
from xme.xmetools.reqtools import assert_public_http_url
from xme.xmetools import browsertools
from xme.xmetools.browsertools import CDPBrowser, CDPError, run_macro, frames_to_mp4

from ..constants import (BROWSER_NAV_WAIT_MS, MONITOR_MAX_DURATION, MONITOR_MAX_INTERVAL,
                         RECORD_MAX_DURATION, RECORD_MAX_WIDTH, RECORD_MIN_WIDTH)
from ._common import exception_detail, ImageToolResult


def _check_url(url: str) -> str | None:
    """导航前校验：仅 http/https 且非内网地址（SSRF）；返回错误文案或 None。"""
    url = (url or "").strip()
    if not url.lower().startswith(("http://", "https://")):
        return "[url 需要以 http:// 或 https:// 开头]"
    try:
        assert_public_http_url(url)
    except Exception as ex:
        return f"[url 被拒绝：{exception_detail(ex)}]"
    return None


async def monitor_element(url: str, selector: str, duration: int = 20,
                          interval: int = 2, attr: str = "", agent=None):
    """监听页面元素在一段时间内的取值变化，返回变化时间线。

    selector 为 CSS 选择器；attr 留空取元素可见文本（innerText），
    填属性名（如 value/href/class）则取对应属性。
    """
    duration = max(1, min(int(duration), MONITOR_MAX_DURATION))
    interval = max(1, min(int(interval), MONITOR_MAX_INTERVAL))
    if not (selector or "").strip():
        return {"result": "[监听失败：selector 不能为空]", "no_compress": True}
    url_error = _check_url(url)
    if url_error:
        return {"result": url_error, "no_compress": True}
    attr_expr = f"el.getAttribute({json.dumps(str(attr))}) ?? el.value" if attr else "el.innerText"
    sample_expr = (f"""(() => {{ const el = document.querySelector({json.dumps(str(selector))});
         if (!el) return null; return String({attr_expr} ?? ""); }})()""")
    samples: list[tuple[float, str | None]] = []
    error = ""
    try:
        async with asyncio.timeout(duration * 2 + 60):
            async with CDPBrowser(1280, 720) as browser:
                await browser.navigate(url, wait_ms=BROWSER_NAV_WAIT_MS)
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


async def record_page(url: str, duration: int = 20, script=None, width: int = 1280,
                      show_cursor: bool = True, send_to_agent: bool = True,
                      send_to_user: bool = False, new_name: str = "",
                      agent=None, session=None):
    """录制页面一段时间并合成视频：宏回放（可选虚拟光标）→ mp4 → 发给 agent/用户。

    script 为鼠标/键盘宏时间轴（元素为动作对象，t 为相对录制开始的秒数）：
      {"t":0.5,"type":"move","selector":"#btn","dur":1.0}  连续平滑移动到元素/坐标(x,y)
      {"t":2.0,"type":"jump","x":100,"y":200}              瞬移到坐标/元素
      {"t":3.0,"type":"click","selector":"#btn"}           点击（可带 selector 自动移过去）
      {"t":4.0,"type":"type","text":"hello"}               逐字符键盘输入（需先点击输入框聚焦）
      {"t":6.0,"type":"key","key":"Enter"}                 按键（Enter/Backspace/Tab/Escape/方向键等）
    show_cursor=False 时不注入虚拟光标（录纯页面动画，宏的真实输入事件照常生效）。
    视频只存本轮 temp（对话结束即清，不长期保存）。
    """
    if agent is None:
        return {"result": "[录制失败：缺少会话上下文]", "no_compress": True}
    duration = max(3, min(int(duration), RECORD_MAX_DURATION))
    width = max(RECORD_MIN_WIDTH, min(int(width), RECORD_MAX_WIDTH))
    if not isinstance(script, list):
        script = []
    url_error = _check_url(url)
    if url_error:
        return {"result": url_error, "no_compress": True}
    new_name = str(new_name or "").strip()
    if send_to_user and new_name and not is_safe_custom_name(new_name):
        return {"result": f"[发送失败：文件名 {new_name} 不合法（仅允许中英文/数字/_-.，不含路径）]",
                "no_compress": True}

    height = width * 9 // 16
    video_name = f"{uuid4().hex}.mp4"
    ref_dir, ref = _create_file_ref(agent.user_id, "video_", video_name, agent)
    out_path = ref_dir / video_name

    frames: list[tuple[bytes, float]] = []
    notes: list[str] = []
    try:
        async with asyncio.timeout(duration + 90):
            async with CDPBrowser(width, height) as browser:
                await browser.navigate(url, wait_ms=BROWSER_NAV_WAIT_MS)
                if show_cursor:
                    await browser.inject_cursor()
                await browser.start_screencast(
                    lambda jpeg, ts: frames.append((jpeg, ts)))
                try:
                    macro_task = asyncio.create_task(
                        run_macro(browser, script, duration, show_cursor))
                    await asyncio.sleep(duration)
                    await macro_task
                    notes = macro_task.result()
                finally:
                    stop_epoch = time.time()   # 截断基准：缓冲/竞态迟到的帧不含在内
                    await browser.stop_screencast()
            frames = [f for f in frames if f[1] <= stop_epoch + 1]
        frames_to_video_name = out_path
        await frames_to_mp4(frames, frames_to_video_name, width)
    except TimeoutError:
        return {"result": "[录制失败：浏览器会话超时]", "no_compress": True}
    except CDPError as ex:
        return {"result": f"[录制失败：{exception_detail(ex)}]", "no_compress": True}
    size_mb = out_path.stat().st_size / 1048576
    summary = (f"已录制页面 {url}（{duration}s，{width}x{height}，{size_mb:.1f} MiB），"
               f"temp 引用 {ref}（对话结束自动清理）。")
    if notes:
        summary += "\n宏执行备注：\n- " + "\n- ".join(notes)

    user_result = ""
    if send_to_user:
        from .files import send_local_file
        ok, info = await send_local_file(session, out_path, new_name or None)
        user_result = ("已把视频以文件形式发给用户：" + info if ok
                       else f"发送用户失败：{info}")
        summary += f"\n{user_result}"

    if send_to_agent:
        from .web import view_item
        view_result = await view_item(
            ref=ref, item_type="video_url",
            prompt="这是刚才录制的页面视频。请仔细观看并描述其中的页面内容、动效/交互效果"
                   "（以及鼠标操作后的页面反应），指出做得好与有问题的地方。",
            agent=agent)
        # 注意顺序：ImageToolResult 是 str 子类，必须先判子类再判普通字符串
        if isinstance(view_result, ImageToolResult):
            return ImageToolResult(f"{summary}\n[录制的视频已直接附在输入中]\n{view_result}",
                                   view_result.image_parts)
        if isinstance(view_result, str) and view_result.startswith("["):
            summary += f"\n视频查看失败：{view_result}"
            return {"result": summary, "ref": ref, "no_compress": True}
        if isinstance(view_result, str):
            return {"result": f"{summary}\n视频分析结果：\n{view_result}",
                    "ref": ref, "no_compress": True}
        return {"result": summary, "ref": ref, "no_compress": True}
    return {"result": summary, "ref": ref, "no_compress": True}
