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

    def __init__(self, width: int = 1280, height: int = 720):
        self.width = int(width)
        self.height = int(height)
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
        self._proc = await asyncio.create_subprocess_exec(
            "google-chrome",
            "--headless=new", "--disable-gpu", "--hide-scrollbars", "--mute-audio",
            "--no-first-run", "--disable-extensions", "--no-default-browser-check",
            "--remote-debugging-port=0", f"--user-data-dir={self._profile}",
            f"--window-size={self.width},{self.height}",
            "about:blank",
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
                    asyncio.create_task(self._ack_screencast(params.get("sessionId")))
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

    async def _ack_screencast(self, session_id) -> None:
        try:
            await self._command("Page.screencastFrameAck", {"sessionId": session_id}, timeout=5)
        except Exception:
            pass

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

    async def start_screencast(self, on_frame, quality: int = 60) -> None:
        """开始录屏；on_frame(jpeg_bytes, timestamp) 在每帧到达时被同步调用。"""
        self._frame_cb = on_frame
        await self._command("Page.startScreencast", {
            "format": "jpeg", "quality": int(quality),
            "maxWidth": self.width, "maxLength": self.height,
            "everyNthFrame": 1,
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


async def _move_smoothly(browser: CDPBrowser, pos: list, tx: float, ty: float,
                         dur: float, show_cursor: bool) -> None:
    """连续移动：40ms 步进派发 mouseMoved 并同步虚拟光标。"""
    steps = max(1, min(int(dur / 0.04), 200))
    for i in range(1, steps + 1):
        x = pos[0] + (tx - pos[0]) * i / steps
        y = pos[1] + (ty - pos[1]) * i / steps
        await browser.dispatch_mouse("mouseMoved", x, y)
        if show_cursor:
            await browser.evaluate(f"window.__cursor.moveTo({round(x,1)},{round(y,1)},false)")
        await asyncio.sleep(dur / steps)
    pos[0], pos[1] = tx, ty


async def _run_action(browser: CDPBrowser, action: dict, pos: list,
                      show_cursor: bool, notes: list) -> None:
    a_type = str(action.get("type") or "").lower()
    if a_type in ("move", "jump"):
        target = await _target_center(browser, action)
        if target is None:
            notes.append(f"t={action.get('t')} 的 {a_type}：未找到元素 {action.get('selector')}，已跳过")
            return
        if a_type == "move":
            await _move_smoothly(browser, pos, target[0], target[1],
                                 float(action.get("dur", 0.8) or 0.8), show_cursor)
        else:
            pos[0], pos[1] = target
            await browser.dispatch_mouse("mouseMoved", target[0], target[1])
            if show_cursor:
                await browser.evaluate(
                    f"window.__cursor.moveTo({round(target[0],1)},{round(target[1],1)},true)")
        return
    if a_type == "click":
        target = await _target_center(browser, action)
        if target is None:
            notes.append(f"t={action.get('t')} 的 click：未找到元素 {action.get('selector')}，已跳过")
            return
        if abs(target[0] - pos[0]) > 1 or abs(target[1] - pos[1]) > 1:
            await _move_smoothly(browser, pos, target[0], target[1], 0.25, show_cursor)
        await browser.dispatch_mouse("mousePressed", target[0], target[1], clicked=True)
        if show_cursor:
            await browser.evaluate(f"window.__cursor.clickFx({round(target[0],1)},{round(target[1],1)})")
        await browser.dispatch_mouse("mouseReleased", target[0], target[1], clicked=True)
        return
    if a_type == "type":
        text = str(action.get("text") or "")
        for ch in text:
            await browser.dispatch_char(ch)
            await asyncio.sleep(0.03)
        if not text:
            notes.append(f"t={action.get('t')} 的 type：text 为空，已跳过")
        return
    if a_type == "key":
        await browser.dispatch_key(action.get("key") or "")
        return
    notes.append(f"t={action.get('t')} 的未知动作类型 {a_type!r}，已跳过")


async def run_macro(browser: CDPBrowser, script: list, duration: float,
                    show_cursor: bool = True) -> list[str]:
    """按时间轴回放宏（t 为相对此刻的秒数），返回执行备注（跳过/失败的动作）。

    t 超出 duration 的动作忽略；动作抛错不中断整个宏（记 notes 继续）。
    """
    notes: list[str] = []
    actions = [a for a in (script or []) if isinstance(a, dict)]
    overdue = [a for a in actions if float(a.get("t", 0) or 0) > duration]
    if overdue:
        notes.append(f"{len(overdue)} 个动作的 t 超出录制时长 {duration}s，已忽略")
    pos = [6.0, 6.0]
    t0 = time.monotonic()
    for action in sorted((a for a in actions
                          if float(a.get("t", 0) or 0) <= duration),
                         key=lambda a: float(a.get("t", 0) or 0)):
        delay = float(action.get("t", 0) or 0) - (time.monotonic() - t0)
        if delay > 0:
            await asyncio.sleep(delay)
        try:
            await _run_action(browser, action, pos, show_cursor, notes)
        except Exception as ex:
            notes.append(f"t={action.get('t')} 的 {action.get('type')} 动作失败: {ex}")
    return notes


async def frames_to_mp4(frames: list[tuple[bytes, float]], out_path: Path,
                        width: int, fps_cap: float = 10.0) -> None:
    """把 screencast 帧（jpeg 字节, epoch 时间戳）按时间戳合成 mp4（H.264 yuv420p）。

    帧间距即 concat duration（上限 2s，下限 1/fps_cap 防闪帧）；无帧时抛 CDPError。
    """
    if not frames:
        raise CDPError("录制期间没有收到任何画面帧")
    frames = sorted(frames, key=lambda f: f[1])
    # 高帧率降采样：间隔小于 1/fps_cap 的帧直接丢弃（而不是拉长显示时长，
    # 否则动画页面每秒几十帧会把 8s 录制撑成几十秒的视频）
    t0 = frames[0][1]
    kept: list[tuple[bytes, float]] = []   # (jpeg, 相对首帧的秒数)
    last_ts = None
    for jpeg, ts in frames:
        if last_ts is not None and ts - last_ts < 1.0 / fps_cap:
            continue
        kept.append((jpeg, ts - t0))
        last_ts = ts
    n = len(kept)
    tmp = Path(tempfile.mkdtemp(prefix="xme_frames_"))
    try:
        lines = ["ffconcat version 1.0"]
        for i, (jpeg, rel_ts) in enumerate(kept):
            frame_file = tmp / f"f{i:05}.jpg"
            frame_file.write_bytes(jpeg)
            if i + 1 < n:
                dur = kept[i + 1][1] - rel_ts
            else:
                dur = (kept[-1][1] - kept[-2][1]) if n >= 2 else 1.0 / fps_cap
            dur = min(max(dur, 0.05), 2.0)
            lines.append(f"file '{frame_file.resolve()}'")
            lines.append(f"duration {dur:.3f}")
        # concat demuxer 的最后一帧 duration 不生效：末帧条目重复一次
        lines.append(f"file '{(tmp / f'f{n-1:05}.jpg').resolve()}'")
        list_file = tmp / "list.txt"
        list_file.write_text("\n".join(lines), encoding="utf-8")
        even_w = int(width) + (int(width) % 2)
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
            "-vf", f"scale={even_w}:-2,format=yuv420p",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
            "-movflags", "+faststart", "-an", str(out_path),
        ]
        proc = await asyncio.create_subprocess_exec(
            cmd[0], *cmd[1:],
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
        _, err = await asyncio.wait_for(proc.communicate(), 120)
        if proc.returncode != 0 or not out_path.is_file():
            detail = (err or b"")[-400:].decode("utf-8", "replace")
            raise CDPError(f"ffmpeg 合成失败（code={proc.returncode}）：{detail}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
