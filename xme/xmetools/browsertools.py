"""最小 CDP（Chrome DevTools Protocol）直连：一次性 headless chrome 会话。

用 aiohttp 自带的 ws 客户端直连 --remote-debugging-port，零额外依赖。
每次调用启动一个独立 chrome 进程（随机调试端口），用完即杀，无常驻状态。

- CDPBrowser：async 上下文管理器，提供导航 / JS 求值 / 真实输入注入 / 屏幕录制；
- run_macro：按时间轴回放鼠标/键盘宏（move 连续移动 / jump 瞬移 / click / type / key），
  可选虚拟光标（注入 DOM 的箭头 div，入镜可见，带点击涟漪）；
- frames_to_mp4：把 screencast 帧按时间戳合成 H.264 yuv420p 视频（QQ 兼容）。
"""
import asyncio
import base64
import json
import shutil
import tempfile
import time
from pathlib import Path

import aiohttp
from nonebot.log import logger


class CDPError(RuntimeError):
    """CDP 连接/命令/页面执行错误。"""


_CDP_START_TIMEOUT = 15.0   # 等 chrome 调试端口就绪
_CMD_TIMEOUT = 10.0         # 单条 CDP 命令默认超时
_WS_MAX_MSG = 64 * 1024 * 1024  # screencast 帧可能很大

# 键名 → (key, code, windowsVirtualKeyCode)：宏 key 动作的内置映射
_KEY_CODES = {
    "enter": ("Enter", "Enter", 13),
    "backspace": ("Backspace", "Backspace", 8),
    "tab": ("Tab", "Tab", 9),
    "escape": ("Escape", "Escape", 27),
    "space": (" ", "Space", 32),
    "arrowleft": ("ArrowLeft", "ArrowLeft", 37),
    "arrowup": ("ArrowUp", "ArrowUp", 38),
    "arrowright": ("ArrowRight", "ArrowRight", 39),
    "arrowdown": ("ArrowDown", "ArrowDown", 40),
    "delete": ("Delete", "Delete", 46),
    "home": ("Home", "Home", 36),
    "end": ("End", "End", 35),
}

# 虚拟光标 + 点击涟漪：注入为固定定位 DOM，pointer-events 不影响页面本身
_CURSOR_JS = """
(() => {
  if (window.__cursor) return "exists";
  const cur = document.createElement('div');
  cur.style.cssText = 'position:fixed;left:0;top:0;z-index:2147483647;pointer-events:none;will-change:transform;width:20px;height:20px;';
  cur.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24">' +
    '<path d="M4 2 L4 20 L9 15 L12.5 22 L15.5 20.5 L12 14 L19 14 Z" ' +
    'fill="rgba(30,30,30,.85)" stroke="white" stroke-width="1.4"/></svg>';
  const ripple = document.createElement('div');
  ripple.style.cssText = 'position:fixed;z-index:2147483646;pointer-events:none;border-radius:50%;' +
    'border:3px solid rgba(255,90,90,.85);width:12px;height:12px;opacity:0;left:0;top:0;margin:-6px 0 0 -6px;';
  const style = document.createElement('style');
  style.textContent = '@keyframes __xme_ripple_fx { 0% { transform: scale(.4); opacity: .9; } ' +
    '100% { transform: scale(2.6); opacity: 0; } }';
  document.head.appendChild(style);
  document.documentElement.appendChild(cur);
  document.documentElement.appendChild(ripple);
  window.__cursor = {
    x: 6, y: 6,
    moveTo(x, y, instant) {
      this.x = x; this.y = y;
      cur.style.transition = instant ? 'none' : 'transform 40ms linear';
      cur.style.transform = `translate(${x}px, ${y}px)`;
    },
    clickFx(x, y) {
      ripple.style.left = x + 'px'; ripple.style.top = y + 'px';
      ripple.style.animation = 'none'; void ripple.offsetWidth;
      ripple.style.animation = '__xme_ripple_fx .5s ease-out';
    },
  };
  cur.style.transform = 'translate(6px, 6px)';
  return "ok";
})()
"""


class CDPBrowser:
    """一次性 headless chrome（--remote-debugging-port=0）+ 单 page 的 CDP 会话。

    async with CDPBrowser(width, height) as b:
        await b.navigate(url)
        ...
    退出时保证 chrome 进程被杀、临时 profile 被清。
    """

    def __init__(self, width: int = 1280, height: int = 720, scale_factor: float = 1.0):
        self.width = int(width)
        self.height = int(height)
        # 设备缩放因子：>1 时布局视口仍是 width×height，但物理渲染像素翻倍
        # （真超采样：帧尺寸 = CSS 尺寸 × factor，合成时缩回，布局不错乱）
        self.scale_factor = max(1.0, float(scale_factor))
        self._proc = None
        self._profile = None
        self._http = None
        self._ws = None
        self._recv_task = None
        self._pending: dict[int, asyncio.Future] = {}
        self._msg_id = 0
        self._frame_cb = None   # on_frame(jpeg_bytes, timestamp)

    # ---------- 生命周期 ----------

    async def __aenter__(self) -> "CDPBrowser":
        self._profile = tempfile.mkdtemp(prefix="xme_cdp_")
        port_file = Path(self._profile) / "DevToolsActivePort"
        launch_args = [
            "google-chrome",
            "--headless=new", "--disable-gpu", "--hide-scrollbars", "--mute-audio",
            "--no-first-run", "--disable-extensions", "--no-default-browser-check",
            "--remote-debugging-port=0", f"--user-data-dir={self._profile}",
            f"--window-size={self.width},{self.height}",
        ]
        if self.scale_factor > 1.0:
            launch_args.append(f"--force-device-scale-factor={self.scale_factor}")
        launch_args.append("about:blank")
        self._proc = await asyncio.create_subprocess_exec(
            *launch_args,
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
        )
        deadline = time.monotonic() + _CDP_START_TIMEOUT
        while time.monotonic() < deadline:
            if port_file.is_file():
                break
            if self._proc.returncode is not None:
                await self.close()
                raise CDPError(f"chrome 启动即退出（code={self._proc.returncode}）")
            await asyncio.sleep(0.1)
        else:
            await self.close()
            raise CDPError("等待 chrome 调试端口就绪超时")
        try:
            port = int(port_file.read_text(encoding="utf-8").splitlines()[0].strip())
            self._http = aiohttp.ClientSession()
            async with self._http.get(f"http://127.0.0.1:{port}/json/list",
                                      timeout=aiohttp.ClientTimeout(total=5)) as resp:
                targets = await resp.json(content_type=None)
            page = next((t for t in targets if t.get("type") == "page"), None)
            if not page or not page.get("webSocketDebuggerUrl"):
                raise CDPError(f"未找到可用的 page 调试目标（{len(targets)} 个 target）")
            self._ws = await self._http.ws_connect(
                page["webSocketDebuggerUrl"], max_msg_size=_WS_MAX_MSG,
                timeout=aiohttp.ClientWSTimeout(ws_close=10))
        except Exception:
            await self.close()
            raise
        self._recv_task = asyncio.create_task(self._recv_loop())
        return self

    async def __aexit__(self, *exc) -> None:
        await self.close()

    async def close(self) -> None:
        if self._recv_task is not None:
            self._recv_task.cancel()
            try:
                await self._recv_task
            except (asyncio.CancelledError, Exception):
                pass
            self._recv_task = None
        if self._ws is not None and not self._ws.closed:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None
        if self._http is not None:
            try:
                await self._http.close()
            except Exception:
                pass
            self._http = None
        if self._proc is not None and self._proc.returncode is None:
            try:
                self._proc.terminate()
                await asyncio.wait_for(self._proc.wait(), 5)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass
            self._proc = None
        if self._profile is not None:
            shutil.rmtree(self._profile, ignore_errors=True)
            self._profile = None

    # ---------- 协议底层 ----------

    async def _recv_loop(self) -> None:
        try:
            async for msg in self._ws:
                if msg.type != aiohttp.WSMsgType.TEXT:
                    break
                data = json.loads(msg.data)
                if "id" in data:
                    fut = self._pending.pop(data["id"], None)
                    if fut is not None and not fut.done():
                        if data.get("error"):
                            fut.set_exception(CDPError(
                                f"{data['error'].get('message', 'CDP 错误')}"))
                        else:
                            fut.set_result(data.get("result") or {})
                elif data.get("method") == "Page.screencastFrame" and self._frame_cb:
                    params = data.get("params") or {}
                    # ack 在接收循环内直发（纯写缓冲不等响应）：chrome 收到 ack 才推
                    # 下一帧，任何调度延迟都会直接吃掉采集帧率
                    self._msg_id += 1
                    await self._ws.send_str(json.dumps({
                        "id": self._msg_id, "method": "Page.screencastFrameAck",
                        "params": {"sessionId": params.get("sessionId")}}))
                    try:
                        jpeg = base64.b64decode(params.get("data") or "")
                        ts = float((params.get("metadata") or {}).get("timestamp") or 0)
                        self._frame_cb(jpeg, ts)
                    except Exception:
                        logger.exception("处理 screencast 帧失败")
        except asyncio.CancelledError:
            raise
        except Exception as ex:
            logger.warning(f"CDP 接收循环结束: {type(ex).__name__}: {ex}")

    async def _command(self, method: str, params: dict, timeout: float = _CMD_TIMEOUT) -> dict:
        if self._ws is None or self._ws.closed:
            raise CDPError("CDP 连接已关闭")
        self._msg_id += 1
        fut: asyncio.Future = asyncio.get_running_loop().create_future()
        self._pending[self._msg_id] = fut
        try:
            await self._ws.send_str(json.dumps({"id": self._msg_id, "method": method,
                                                "params": params}))
            return await asyncio.wait_for(fut, timeout)
        except asyncio.TimeoutError:
            raise CDPError(f"CDP 命令超时: {method}") from None
        finally:
            self._pending.pop(self._msg_id, None)

    # ---------- 页面操作 ----------

    async def navigate(self, url: str, wait_ms: int = 2000, timeout: float = 30.0) -> None:
        """导航并等待文档加载完成（readyState 轮询，容忍导航期间的执行上下文切换）。"""
        await self._command("Page.enable", {})
        await self._command("Page.navigate", {"url": url}, timeout=timeout)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                if await self.evaluate("document.readyState") == "complete":
                    break
            except Exception:
                pass
            await asyncio.sleep(0.2)
        if wait_ms > 0:
            await asyncio.sleep(wait_ms / 1000)

    async def evaluate(self, expression: str):
        """执行 JS 并取返回值（returnByValue）；页面抛错转 CDPError。"""
        result = await self._command("Runtime.evaluate", {
            "expression": expression, "returnByValue": True,
            "awaitPromise": False, "userGesture": True,
        })
        if result.get("exceptionDetails"):
            desc = (result["exceptionDetails"].get("exception") or {}).get("description") or "未知 JS 错误"
            raise CDPError(f"JS 执行失败: {desc[:200]}")
        return result.get("result", {}).get("value")

    # ---------- 真实输入注入 ----------

    async def dispatch_mouse(self, mtype: str, x: float, y: float, clicked: bool = False) -> None:
        params = {"type": mtype, "x": round(x, 1), "y": round(y, 1)}
        if clicked:
            params.update({"button": "left", "clickCount": 1})
        await self._command("Input.dispatchMouseEvent", params)

    async def dispatch_char(self, char: str) -> None:
        """输入一个可见字符（type=char 携带 text，页面收到真实按键输入）。"""
        await self._command("Input.dispatchKeyEvent", {
            "type": "keyDown", "text": char, "unmodifiedText": char,
            "key": char, "code": "", "windowsVirtualKeyCode": 0,
        })
        await self._command("Input.dispatchKeyEvent", {
            "type": "keyUp", "key": char, "code": "", "windowsVirtualKeyCode": 0,
        })

    async def dispatch_key(self, name: str) -> None:
        """按一个特殊键（Enter/Backspace/Tab/Escape/方向键等，见 _KEY_CODES）。"""
        entry = _KEY_CODES.get(str(name).lower())
        if entry is None:
            raise CDPError(f"不支持的按键: {name}（支持：{'、'.join(_KEY_CODES)}）")
        key, code, vk = entry
        await self._command("Input.dispatchKeyEvent", {
            "type": "keyDown", "key": key, "code": code, "windowsVirtualKeyCode": vk,
        })
        await self._command("Input.dispatchKeyEvent", {
            "type": "keyUp", "key": key, "code": code, "windowsVirtualKeyCode": vk,
        })

    # ---------- 屏幕录制 ----------

    async def start_screencast(self, on_frame, quality: int = 60, every_nth: int = 1) -> None:
        """开始录屏；on_frame(jpeg_bytes, timestamp) 在每帧到达时被同步调用。

        every_nth：chrome 每渲染 N 帧采集 1 帧（控制推帧量，防帧洪峰挤占 CDP 通道）。
        """
        self._frame_cb = on_frame
        await self._command("Page.startScreencast", {
            "format": "jpeg", "quality": int(quality),
            # 不限制帧尺寸：scale_factor>1 时帧保持物理分辨率（超采样由合成端缩回）
            "everyNthFrame": max(1, int(every_nth)),
        })

    async def stop_screencast(self) -> None:
        try:
            await self._command("Page.stopScreencast", {})
        finally:
            self._frame_cb = None

    # ---------- 虚拟光标 ----------

    async def inject_cursor(self) -> None:
        result = await self.evaluate(_CURSOR_JS)
        if result != "ok":
            logger.debug("虚拟光标已存在，跳过注入")


def _js_str(value) -> str:
    """把 Python 值转成安全的 JS 字符串字面量（selector 等外部输入进 JS 的唯一通道）。"""
    return json.dumps(str(value), ensure_ascii=False)


async def _target_center(browser: CDPBrowser, action: dict):
    """解析动作目标坐标：selector 取元素中心（找不到返回 None），否则 x/y。"""
    selector = action.get("selector")
    if selector:
        rect = await browser.evaluate(
            f"""(() => {{ const el = document.querySelector({_js_str(selector)});
                 if (!el) return null; const r = el.getBoundingClientRect();
                 if (r.width <= 0 && r.height <= 0) return null;
                 return [r.left + r.width / 2, r.top + r.height / 2]; }})()""")
        if not rect:
            return None
        return float(rect[0]), float(rect[1])
    return float(action.get("x", 0) or 0), float(action.get("y", 0) or 0)


_MACRO_STEP_SECS = 0.04      # move 步进周期（秒）：每步重取元素位置并派发 mouseMoved
_MACRO_ARRIVE_TOL = 3.0      # 到达判定：距目标中心 ≤3px 视为已到达
_MACRO_DEFAULT_SPEED = 600.0  # move 默认移动速度（CSS 像素/秒）


async def _move_tracked(browser: CDPBrowser, action: dict, pos: list,
                        show_cursor: bool, notes: list) -> None:
    """以 speed 像素/秒朝目标移动；selector 目标每步重取位置（悬停移位/动画元素也跟得上）。

    timeout 秒内未到达则瞬移到元素当前位置并继续（保证后续 click 能命中），
    记一条备注。pos 就地更新为最终鼠标位置。
    """
    speed = max(50.0, float(action.get("speed", _MACRO_DEFAULT_SPEED) or _MACRO_DEFAULT_SPEED))
    timeout = max(0.5, float(action.get("timeout", 16.0) or 16.0))
    deadline = time.monotonic() + timeout
    step_secs = _MACRO_STEP_SECS
    target_desc = action.get("selector") or f"{action.get('x')},{action.get('y')}"
    label = f"move({target_desc})"
    while True:
        target = await _target_center(browser, action)
        if target is None:
            notes.append(f"move：未找到元素 {action.get('selector')}，已跳过")
            return
        dist = ((target[0] - pos[0]) ** 2 + (target[1] - pos[1]) ** 2) ** 0.5
        if dist <= _MACRO_ARRIVE_TOL:
            # 已到达：补一次精确 mouseMoved，光标贴到元素中心
            pos[0], pos[1] = target
            await browser.dispatch_mouse("mouseMoved", target[0], target[1])
            if show_cursor:
                await browser.evaluate(
                    f"window.__cursor.moveTo({round(target[0],1)},{round(target[1],1)},true)")
            return
        if time.monotonic() >= deadline:
            # 超时兜底：瞬移到元素当前位置（后续 click 仍能命中），不中断序列
            pos[0], pos[1] = target
            await browser.dispatch_mouse("mouseMoved", target[0], target[1])
            if show_cursor:
                await browser.evaluate(
                    f"window.__cursor.moveTo({round(target[0],1)},{round(target[1],1)},true)")
            notes.append(f"move 追踪 {label} 超时（{timeout:g}s），已瞬移到元素当前位置并继续")
            return
        step = min(speed * step_secs, dist)
        ux, uy = (target[0] - pos[0]) / dist, (target[1] - pos[1]) / dist
        nx, ny = pos[0] + ux * step, pos[1] + uy * step
        await browser.dispatch_mouse("mouseMoved", nx, ny)
        if show_cursor:
            await browser.evaluate(f"window.__cursor.moveTo({round(nx,1)},{round(ny,1)},false)")
        pos[0], pos[1] = nx, ny
        await asyncio.sleep(step_secs)


async def _run_action(browser: CDPBrowser, action: dict, pos: list,
                      show_cursor: bool, notes: list) -> None:
    a_type = str(action.get("type") or "").lower()
    if a_type in ("move", "jump"):
        if a_type == "jump":
            target = await _target_center(browser, action)
            if target is None:
                notes.append(f"jump：未找到元素 {action.get('selector')}，已跳过")
                return
            pos[0], pos[1] = target
            await browser.dispatch_mouse("mouseMoved", target[0], target[1])
            if show_cursor:
                await browser.evaluate(
                    f"window.__cursor.moveTo({round(target[0],1)},{round(target[1],1)},true)")
            return
        await _move_tracked(browser, action, pos, show_cursor, notes)
        return
    if a_type == "click":
        # 在鼠标当前位置点击（移动由 move/jump 负责）
        x, y = pos
        await browser.dispatch_mouse("mousePressed", x, y, clicked=True)
        if show_cursor:
            await browser.evaluate(f"window.__cursor.clickFx({round(x, 1)},{round(y, 1)})")
        await browser.dispatch_mouse("mouseReleased", x, y, clicked=True)
        return
    if a_type == "type":
        text = str(action.get("text") or "")
        for ch in text:
            await browser.dispatch_char(ch)
            await asyncio.sleep(0.03)
        if not text:
            notes.append("type：text 为空，已跳过")
        return
    if a_type == "wait":
        # 原地等待（录制照常进行，页面动画/悬停效果自然呈现）
        await asyncio.sleep(max(0.0, float(action.get("secs", 1) or 1)))
        return
    if a_type == "key":
        await browser.dispatch_key(action.get("key") or "")
        return
    notes.append(f"未知动作类型 {a_type!r}，已跳过")


async def run_macro(browser: CDPBrowser, script: list, duration: float | None,
                    show_cursor: bool = True, notes: list | None = None) -> list[str]:
    """顺序回放宏，返回执行备注（传入 notes 列表则就地填充，宏被取消时已记录内容不丢）。

    每个动作的 t 是"距上一个动作完成后"的秒数（+t 增量，第一个动作相对录制开始）。
    move 以 speed 追踪 selector 位置（悬停移位也跟得上），超时自动瞬移兜底。
    duration 非 None 时为硬窗：累计耗时达到即停止（后续动作合并为一条总结备注）；
    duration 为 None 时不限窗，宏自然跑完（录制长度由宏决定）。
    单动作失败不中断整个宏。
    """
    if notes is None:
        notes = []
    limited = duration is not None
    actions = [a for a in (script or []) if isinstance(a, dict)]
    pos = [6.0, 6.0]
    start = time.monotonic()
    for index, action in enumerate(actions):
        if limited:
            remaining = duration - (time.monotonic() - start)
            if remaining <= 0:
                notes.append(f"累计耗时超出录制时长 {duration:g}s，"
                             f"剩余 {len(actions) - index} 个动作已忽略")
                break
        interval = max(0.0, float(action.get("t", 0) or 0))
        if interval > 0:
            # 睡眠钳到剩余窗内：AI 误把绝对时间点写成大 t 值时不会把录制拖长
            await asyncio.sleep(min(interval, remaining) if limited else interval)
        if limited and time.monotonic() - start > duration:
            notes.append(f"累计耗时超出录制时长 {duration:g}s，"
                         f"剩余 {len(actions) - index} 个动作已忽略")
            break
        try:
            await _run_action(browser, action, pos, show_cursor, notes)
        except Exception as ex:
            notes.append(f"{action.get('type')} 动作失败: {ex}")
    return notes


async def frames_to_mp4(frames: list[tuple[bytes, float]], out_path: Path,
                        width: int, fps_cap: float = 10.0, crf: int = 28,
                        preset: str = "veryfast", x264_params: str = "",
                        span: float | None = None) -> None:
    """把 screencast 帧（jpeg 字节, epoch 时间戳）按时间戳合成 mp4（H.264 yuv420p）。

    帧按 fps_cap 降采样后以固定帧率合成（时长精确 = 帧数/fps_cap）；无帧时抛 CDPError。
    span 传录制实际总跨度（秒）：末帧定格补齐到录制结束——wait/静止段没有新帧，
    但视频时长应覆盖这段（画面定格是正确行为）。
    """
    if not frames:
        raise CDPError("录制期间没有收到任何画面帧")
    frames = sorted(frames, key=lambda f: f[1])
    # 高帧率降采样：间隔小于 1/fps_cap 的帧直接丢弃（而不是拉长显示时长，
    # 否则动画页面每秒几十帧会把 8s 录制撑成几十秒的视频）
    t0 = frames[0][1]
    kept: list[bytes] = []
    last_ts = None
    for jpeg, ts in frames:
        if last_ts is not None and ts - last_ts < 1.0 / fps_cap:
            continue
        kept.append(jpeg)
        last_ts = ts
    tmp = Path(tempfile.mkdtemp(prefix="xme_frames_"))
    try:
        # 帧序列按 fps_cap 等间隔合成：wait/静止段没有新帧，用末帧定格补齐
        # （image2 序列输入，时长 = 帧数/fps_cap，精确可靠——concat demuxer 的
        # duration/重复帧在 ffmpeg 4.2 下行为不稳定，弃用）
        seq_dir = tmp / "seq"
        seq_dir.mkdir()
        count = 0
        for jpeg in kept:
            (seq_dir / f"{count:06}.jpg").write_bytes(jpeg)
            count += 1
        if span is not None:
            hold_frames = max(0, min(int(round(span * fps_cap)) - count, 60 * int(fps_cap)))
            for k in range(hold_frames):
                (seq_dir / f"{count + k:06}.jpg").write_bytes(kept[-1])
            count += hold_frames
        even_w = int(width) + (int(width) % 2)
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "ffmpeg", "-y", "-framerate", str(int(fps_cap)),
            "-i", str(seq_dir / "%06d.jpg"),
            "-frames:v", str(count),
            "-vf", f"scale={even_w}:-2,format=yuv420p",
            "-c:v", "libx264", "-preset", preset, "-crf", str(int(crf)),
        ]
        if x264_params:
            cmd += ["-x264-params", x264_params]
        cmd += ["-movflags", "+faststart", "-an", str(out_path)]
        proc = await asyncio.create_subprocess_exec(
            cmd[0], *cmd[1:],
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
        _, err = await asyncio.wait_for(proc.communicate(), 120)
        if proc.returncode != 0 or not out_path.is_file():
            detail = (err or b"")[-400:].decode("utf-8", "replace")
            raise CDPError(f"ffmpeg 合成失败（code={proc.returncode}）：{detail}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
