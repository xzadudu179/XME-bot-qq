"""最小 CDP（Chrome DevTools Protocol）直连 + Xvfb 录屏：一次性浏览器会话。

用 aiohttp 自带的 ws 客户端直连 --remote-debugging-port，零额外依赖。
每次调用启动一个独立 chrome 进程（随机调试端口），用完即杀，无常驻状态。

- CDPBrowser：async 上下文管理器，提供导航 / JS 求值 / 真实输入注入；
  display 传 X display 字符串时以"有头"模式跑在对应 X server 上（供录屏）；
- XvfbDisplay：虚拟显示生命周期管理（配合 CDPBrowser 的有头模式与 ffmpeg x11grab 直录）；
- run_macro：按时间轴回放鼠标/键盘宏（move 连续追踪移动 / jump 瞬移 / click / type / key），
  可选虚拟光标（注入 DOM 的箭头 div，入镜可见，带点击涟漪）。
"""
import asyncio
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
_WS_MAX_MSG = 64 * 1024 * 1024  # ws 单条消息上限（防止大响应被拒）

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


class XvfbDisplay:
    """Xvfb 虚拟显示（async 上下文）：在空闲的 display 号上启动 Xvfb。

    async with XvfbDisplay(1920, 1080) as xvfb:
        # xvfb.display 形如 ":101"，供 chrome（--display）与 ffmpeg（x11grab）使用
        ...
    退出时终止 Xvfb 进程。
    """

    def __init__(self, width: int = 1920, height: int = 1080):
        self.screen = f"{int(width)}x{int(height)}x24"
        self.display = None
        self._proc = None

    async def __aenter__(self) -> "XvfbDisplay":
        for num in range(99, 150):
            if Path(f"/tmp/.X{num}-lock").exists():
                continue
            self._proc = await asyncio.create_subprocess_exec(
                "Xvfb", f":{num}", "-screen", "0", self.screen, "-nolisten", "tcp",
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
            # 等 X11 socket 就绪（/tmp/.X11-unix/X{num} 出现即监听中）
            sock = Path(f"/tmp/.X11-unix/X{num}")
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline and not sock.exists():
                if self._proc.returncode is not None:
                    break
                await asyncio.sleep(0.05)
            if sock.exists() and self._proc.returncode is None:
                self.display = f":{num}"
                return self
            if self._proc is not None and self._proc.returncode is None:
                self._proc.terminate()
                await asyncio.wait_for(self._proc.wait(), 3)
            self._proc = None
        raise CDPError("没有可用的 display 号（Xvfb 启动全部失败）")

    async def __aexit__(self, *exc) -> None:
        if self._proc is not None and self._proc.returncode is None:
            try:
                self._proc.terminate()
                await asyncio.wait_for(self._proc.wait(), 3)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass
        self._proc = None
        self.display = None


class CDPBrowser:
    """一次性 headless chrome（--remote-debugging-port=0）+ 单 page 的 CDP 会话。

    async with CDPBrowser(width, height) as b:
        await b.navigate(url)
        ...
    退出时保证 chrome 进程被杀、临时 profile 被清。
    """

    def __init__(self, width: int = 1280, height: int = 720,
                 display: str | None = None):
        self.width = int(width)
        self.height = int(height)
        # display 非 None 时以"有头"模式在该 X display 上运行（Xvfb 录屏用），
        # None 为传统 headless 模式
        self.display = display
        self._proc = None
        self._profile = None
        self._http = None
        self._ws = None
        self._recv_task = None
        self._pending: dict[int, asyncio.Future] = {}
        self._msg_id = 0

    # ---------- 生命周期 ----------

    async def __aenter__(self) -> "CDPBrowser":
        self._profile = tempfile.mkdtemp(prefix="xme_cdp_")
        port_file = Path(self._profile) / "DevToolsActivePort"
        import os
        launch_args = [
            "google-chrome", "--disable-gpu", "--hide-scrollbars", "--mute-audio",
            "--no-first-run", "--disable-extensions", "--no-default-browser-check",
            # 抑制各类弹窗/提示条（更新气泡、翻译条、崩溃恢复等），避免录进画面
            "--noerrdialogs", "--disable-infobars", "--disable-sync",
            "--disable-component-update", "--disable-background-networking",
            "--disable-session-crashed-bubble", "--hide-crash-restore-bubble",
            "--disable-features=Translate,TranslateUI,AcceptCHFrame,MediaRouter,"
            "OptimizationHints,ChromeWhatsNewUI,CalculateNativeWinOcclusion",
            "--remote-debugging-port=0", f"--user-data-dir={self._profile}",
            f"--window-size={self.width},{self.height}",
        ]
        if self.display is None:
            launch_args.insert(1, "--headless=new")
        else:
            # 有头模式（Xvfb 录屏）：kiosk 全屏——画面里没有标签栏/地址栏等浏览器 UI，
            # 视口即整个虚拟屏（录制画面纯净，视口高度也不再被浏览器 UI 挤占）
            launch_args.insert(1, "--kiosk")
            launch_args.append(f"--display={self.display}")
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
    last_step = time.monotonic()
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
        # 按真实经过时间推进（每步有两次 CDP 往返，固定步长会让实际速度明显偏慢、
        # 长距离移动撞 timeout 变瞬移）；速度以配置值为准，帧间位移自然平滑
        now = time.monotonic()
        step = min(speed * max(now - last_step, 1e-3), dist)
        last_step = now
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
