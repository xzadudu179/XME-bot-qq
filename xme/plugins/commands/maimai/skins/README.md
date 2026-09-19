# 自定义 B50 查分卡皮肤指南

写一个 `.py` 文件放进本目录即可成为一张新皮肤，无需 import 插件任何代码。
重启 bot 后用 `/mai b50 -s 皮肤名` 临时使用，或把 `constants.py` 的
`DEFAULT_SKIN` 改成你的皮肤名设为默认。

- `official.py`：官方素材 + flex/grid 流式排版，当前默认（也是唯一的内置皮肤）

## 契约（只有两条）

```python
NAME = "myskin"                    # 皮肤名（/mai b50 -s myskin）

def render(data) -> str:
    """接收 B50CardData，返回完整 HTML 文档字符串。"""
    return f"<!DOCTYPE html><html>...</html>"
```

- 模块文件名不要以 `_` 开头（会被跳过）
- `render` 里抛异常不会炸 bot：命令层会降级为文本成绩单，并在日志告警
- 加载失败（语法错误等）也只跳过该皮肤，不影响其他皮肤

## 你会拿到的数据

### data（B50CardData）

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `username` | str | 水鱼用户名 |
| `rating` | int | DX Rating（建议配合 `data.rating_frame` 展示段位框） |
| `nickname` | str \| None | 水鱼昵称（可能为 None） |
| `plate` | str | 水鱼牌位铭牌文字（可能为 None） |
| `dx` | list[B50SongScore] | 15 条最佳新谱成绩 |
| `sd` | list[B50SongScore] | 35 条最佳旧谱成绩 |
| `covers` | dict[str, str] | 曲绘：**key 是字符串化的曲目 id**（`str(song_id)`），值是可直接放进 `<img src>` 的 data URI（下载失败时为远程 URL，404 曲目为远程 URL，靠 `onerror` 隐藏） |
| `badges` | dict[str, str] | 徽章：key 为 `fc fcp ap app fs fsp fdx fdxp sync`，值同上；`badges.get(score.fc)`、`badges.get(score.fs)` 直接取用 |
| `rating_frame` | str | 按 rating 匹配的段位框图片 URI（灰/蓝/绿/黄/橙/紫/红/银/金/白金/彩 11 档），空串表示缺资源 |
| `avatar_uri` | str | 玩家头像 URI（查自己/@人时有 QQ 头像，查陌生用户名为空串） |
| `background_uri` | str | 卡头默认背景图 URI |
| `star_icons` | dict[int, str] | DX 星贴片：星数 1~5 -> 游戏原版"N 星"整图贴片 URI（`<img>` 一次即为该星数完整图） |
| `chart_icons` | dict[str, str] | 谱面类型贴图：`"dx"` / `"sd"` -> 官方类型图标 URI |
| `pic` | 函数 | `data.pic("相对路径")` 直接取资源包 `pic/` 下任意图片的 data URI（如 `data.pic("UI_DNM_DaniPlate_01.png")`）；可用名单看 `static/maimai/resource/pic/` 目录或 `python gen.py --list-pic` |
| `ui` | dict[str, str] | official 皮肤的官方 UI 小件袋：`b50_bg`（整卡背景）、`logo`、`plate`（默认姓名框）、`default_icon`、`name_plate`、`digit_0~9`（rating 数字贴图）、`diff_bg_b50_score_{难度}`（行底图）、`rank_{评级}`、`combo_{fc}`、`sync_{fs}`、`star_{星数}`（星条） |

### 单条成绩（B50SongScore）

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `song_id` | int | 曲目 id（配合 `data.covers` 取曲绘） |
| `title` | str | 曲名（已处理，直接用） |
| `type` | str | `"dx"` / `"sd"`（已小写） |
| `is_dx` | bool | 是否 DX 谱（等价 `type == "dx"`） |
| `level` | str | 等级，如 `"14"` |
| `level_index` | int | 难度序号 0 基本 ~ 4 智 |
| `level_label` | str | 难度名，如 `"Master"` |
| `ds` | float | 定数，如 `14.3` |
| `achievements` | float | 达成率，如 `100.747` |
| `ra` | int | 单曲 Rating |
| `rate` | str | 评级字母，如 `"sssp"` |
| `dx_score` | int | DX 分数原始值 |
| `stars` | int \| None | DX 星级 0~5（缺物量数据时为 None；≥95% 5★、≥90% 4★、≥85% 3★、≥70% 2★、≥50% 1★） |
| `fc` | str | `""` / `fc` / `fcp` / `ap` / `app` |
| `fs` | str | `""` / `fs` / `fsp` / `fdx` / `fdxp` / `sync` |

## 渲染注意事项

1. **返回完整 HTML 文档**（含 `<head>`），最终经 Chrome 截图成图片，截图后自动裁掉透明边
2. **`body` 背景设为透明**（`background: transparent`），只有你的卡片容器有底色，否则裁剪无效、出图带大黑边
3. **宽度自定**：截图视口 1920×2500，内容建议 900~1200px 宽；高度不用管，裁剪自适应
4. 图片 URI 已全部是 data URI（离线可渲染），也可以自己加任意远程图片
5. 曲名/用户名等文本**记得 `html.escape`**，防止特殊字符破坏排版
6. 50 条成绩建议双列网格 + `overflow: hidden; text-overflow: ellipsis` 处理长曲名

## 可复用的现成资源

- 配色变量与 Melete 字体：`from xme.xmetools.templates import HIUN_COLORS, FONTS_STYLE`
  （提供 `--bg-color` `--text-color` `--color-primary` `--grey-color` `--border-color` 等 CSS 变量）
- maimai 风格数字字体内嵌写法：参考 `default.py` 的 `_load_font_face()`（SGM 子集，仅数字/拉丁）
- 内置皮肤 `official.py` 有完整实现可抄：grid 排版、官方贴图、星级/徽章/曲绘处理

## 最小可用示例（复制改名即可跑）

```python
"""我的 B50 皮肤。"""
import html
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..render import B50CardData

NAME = "mine"


def render(data: "B50CardData") -> str:
    def row(s) -> str:
        cover = data.covers.get(str(s.song_id), "")
        stars = "★" * s.stars if s.stars else ""
        badge = "".join(f'<img src="{data.badges[k]}" height="14">'
                        for k in (s.fc, s.fs) if data.badges.get(k))
        kind = "DX" if s.is_dx else "SD"
        return (f'<div class="row">'
                f'<img class="jk" src="{cover}" onerror="this.style.display=\'none\'">'
                f'<span class="ti">{kind} {html.escape(s.title)}</span>'
                f'<span>{s.ds:.1f} | {s.achievements:.4f}% | ra{s.ra} {stars} {badge}</span>'
                f'</div>')

    rows = "".join(row(s) for s in data.dx + data.sd)
    avatar = f'<img src="{data.avatar_uri}" width="64" style="border-radius:50%">' if data.avatar_uri else ""
    frame = data.rating_frame or ""
    return f"""
<!DOCTYPE html><html><head><meta charset="utf-8"><style>
body {{ background: transparent; font-family: sans-serif; }}
main {{ width: 900px; background: #101024; border-radius: 16px; padding: 20px; color: #eee; }}
.head {{ display: flex; gap: 12px; align-items: center; margin-bottom: 12px;
        background-image: url('{frame}'); background-size: auto 100%;
        background-repeat: no-repeat; padding: 8px 16px; min-height: 96px; }}
.row {{ display: flex; gap: 8px; align-items: center; padding: 2px 0; font-size: 13px; }}
.jk {{ width: 36px; height: 36px; object-fit: cover; border-radius: 4px; }}
.ti {{ flex: 1; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }}
</style></head><body>
<main>
  <div class="head">{avatar}<h2>{html.escape(data.username)}</h2><h2 style="color:#7fd7ff">{data.rating}</h2></div>
  {rows}
</main></body></html>
"""
```

## 想动的数据没有？

成绩自带曲名/定数/物量之外的数据（如曲目版本、流派分类）在水鱼
`music_data` 曲目表里都有，可以在皮肤里自己联表：把它作为参数传给
`render` 目前不支持，需要的话在 `render.py` 的 `B50CardData` 里加字段
（`build_b50_card_data` 负责填充），或在群里提需求。

## 素材来源与替换

- `rating_frame`、`background_uri`、`chart_icons`、`star_icons` 均为**官方切图**
- rating 框 / DX 星贴片 / 谱面类型图标来自官方资源包
  （maimaiDX(Hoshino) 的 static 资源，`RESOURCE_DIR/pic/`，bot 启动时自动下载，
  目录已 gitignore）：`pic/prism_plus/UI_CMN_DXRating_01~11.png`（01 灰 → 11 彩）、
  `pic/status_dxstar_1~5.png`（N 星整图贴片）、`pic/DX.png` / `SD.png`
- 资源包未同步完成前，段位框/星贴片/类型图标暂缺，查分卡自动降级（无框、★ 字形、无角标）
- 想手动更新某张图：替换 `RESOURCE_DIR/pic/` 下对应文件即可
- `static/maimai/background.png` 为入库的官方 b50 背景（maimai-bot classical 资源）
- 徽章来自落雪前端同款 webp（`static/maimai/badges/`，入库）
