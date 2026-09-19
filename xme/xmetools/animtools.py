"""动图（GIF / 动图 WEBP）读写与合成工具

提供跨插件复用的动图能力：帧读取、限制截断、静态卡片逐帧合成、GIF 编码、
卡片动图槽位占位与定位、入库压缩阶梯。动图相关限制常量集中在模块顶部，单点维护。
"""
from dataclasses import dataclass
from io import BytesIO
import base64

import numpy as np
from PIL import Image, ImageChops

from xme.xmetools.imgtools import get_image, limit_size

# 单个动图最大帧数：超出按时长补偿均匀抽帧（时间轴总长保持与原图一致）
MAX_ANIM_FRAMES = 150
# 动图单边最大像素，超出统一缩放
MAX_ANIM_DIM = 480
# 合成卡片 GIF 的输出体积上限（约 1.8MB，低于 QQ 透传线 2MB）
GIF_OUTPUT_MAX_BYTES = 1_887_436
# 入库校准的体积余量比例：按总预算的该比例校准，给后续留言增长留空间
ANIM_STORE_MARGIN = 0.75
# 入库压缩阶梯参数（按观感优先级排列）：
# 先抽帧封顶 ANIM_STORE_MAX_FRAMES（时长补偿掉帧率不降清晰度），
# 再缩放（目标较长边 ANIM_STORE_SCALE_TARGET px，下限 max(150px, 原尺寸 50%)），
# 在该尺寸内降色量，最后才进一步抽帧
ANIM_STORE_MAX_FRAMES = 30
ANIM_STORE_SCALE_TARGET = 200
ANIM_STORE_SCALE_FLOOR = 150
ANIM_STORE_COLORS = (256, 128, 64, 32)
# 二维码检测的最大抽样帧数
QR_SAMPLE_FRAMES = 5

# 动图槽位占位色：每个槽位一种视觉上相同的洋红（末位通道间隔 8，大于检测容差），
# 渲染截图后按颜色精确定位各槽位边界框，槽位数上限即列表长度
ANIM_SLOT_COLORS = [(255, 0, 255 - i * 8) for i in range(3)]


@dataclass
class AnimSequence:
    """一组动图帧：RGBA 帧列表 + 每帧时长（毫秒）+ 循环次数（0 为无限循环）"""
    frames: list[Image.Image]
    durations_ms: list[int]
    loop: int = 0

    @property
    def total_duration_ms(self) -> int:
        return max(1, sum(self.durations_ms))

    def frame_index_at(self, time_ms: int) -> int:
        """返回时间轴 time_ms 处（按总时长循环取模）应显示的帧下标"""
        if not self.durations_ms:
            return 0
        acc = 0
        t = time_ms % self.total_duration_ms
        for i, duration in enumerate(self.durations_ms):
            acc += duration
            if t < acc:
                return i
        return len(self.durations_ms) - 1


def is_animated(image: Image.Image) -> bool:
    """判断 PIL 图片是否为多帧动图"""
    return getattr(image, "n_frames", 1) > 1


def load_anim_sequence(path_or_image, max_frames=MAX_ANIM_FRAMES, max_dim=MAX_ANIM_DIM) -> AnimSequence:
    """读取动图为帧序列：逐帧取合成后的完整画布帧（Pillow ≥9 自动合并局部帧）

    帧数超过 max_frames 时按时长补偿均匀抽帧（保留帧的时长乘以步长），
    时间轴总长与原图保持一致，只降低帧率不裁剪长度；静图返回单帧序列
    """
    image = get_image(path_or_image)
    loop = image.info.get("loop", 0)
    if not is_animated(image):
        return AnimSequence(frames=[image.convert("RGBA")], durations_ms=[100], loop=0)
    n_frames = image.n_frames
    # 先扫一遍每帧时长，估算均匀抽帧步长（帧数预算），
    # 被保留帧的时长取"到下一保留帧之间的原始时长之和"，总时长严格不变
    durations_all = []
    for index in range(n_frames):
        image.seek(index)
        durations_all.append(max(10, int(image.info.get("duration", 100))))
    stride = max(1, -(-n_frames // max_frames))
    frames: list[Image.Image] = []
    durations: list[int] = []
    for index in range(0, n_frames, stride):
        image.seek(index)
        frames.append(image.convert("RGBA"))
        durations.append(sum(durations_all[index:min(index + stride, n_frames)]))
    if max_dim > 0 and max(frames[0].size) > max_dim:
        frames = [limit_size(frame, max_dim) for frame in frames]
    return AnimSequence(frames=frames, durations_ms=durations, loop=loop)


def _flatten_rgb(image: Image.Image) -> Image.Image:
    """RGBA 图片平铺到白底转 RGB（GIF 仅 1 位透明，整卡透明度无法保留）"""
    if image.mode == "RGB":
        return image
    rgba = image.convert("RGBA")
    background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    return Image.alpha_composite(background, rgba).convert("RGB")


def _quantize_frame(image: Image.Image, colors: int = 256) -> Image.Image:
    """单帧量化为指定颜色数的调色板模式，每帧独立调色板互不挤占

    含透明像素（alpha < 128）时保留 1 位透明：量化少用一色并预留最后一个
    索引作透明色（GIF 仅支持 1 位透明，半透明按阈值二值化）
    """
    if image.mode == "RGBA":
        low_alpha, _ = image.getchannel("A").getextrema()
        if low_alpha < 128:
            transparent_mask = image.getchannel("A").point(lambda a: 255 if a < 128 else 0)
            palette_img = image.convert("RGB").quantize(colors=max(2, colors - 1), method=Image.Quantize.FASTOCTREE)
            palette_img.putpalette(palette_img.getpalette()[:255 * 3] + [0, 0, 0])
            palette_img.paste(255, (0, 0), transparent_mask)
            palette_img.info["transparency"] = 255
            return palette_img
    return _flatten_rgb(image).quantize(colors=colors, method=Image.Quantize.FASTOCTREE)


def _encode_gif_bytes(frames, durations_ms: list[int], loop: int = 0) -> bytes:
    """把帧迭代器编码为 GIF bytes（生成器逐帧消费，内存同时只保留单帧）

    GIF 帧延迟以 10ms 为单位，用最大余数法把逐帧取整误差分摊到各帧，
    总时长偏差不超过 10ms
    """
    total_cs = max(1, round(sum(durations_ms) / 10))
    delays = [max(1, d // 10) for d in durations_ms]
    diff = total_cs - sum(delays)
    if diff:
        order = sorted(range(len(durations_ms)), key=lambda i: durations_ms[i] % 10, reverse=True)
        for k in range(abs(diff)):
            idx = order[k % len(order)]
            if diff > 0:
                delays[idx] += 1
            elif delays[idx] > 1:
                delays[idx] -= 1
    iterator = iter(frames)
    buffer = BytesIO()
    first = next(iterator)
    first.save(buffer, format="GIF", save_all=True, append_images=iterator,
               duration=[d * 10 for d in delays], loop=loop, disposal=2, optimize=False)
    return buffer.getvalue()


def save_anim_sequence(sequence: AnimSequence, path: str, colors: int = 256) -> None:
    """把帧序列保存为 GIF 文件，保留每帧时长与循环设置，可指定量化颜色数"""
    data = _encode_gif_bytes((_quantize_frame(frame, colors) for frame in sequence.frames),
                             sequence.durations_ms, loop=sequence.loop)
    with open(path, "wb") as f:
        f.write(data)


def slot_placeholder_base64(slot_index: int) -> str:
    """指定槽位占位色 1x1 PNG 的 base64；扔瓶渲染占位与截图定位共用同一颜色表"""
    buffer = BytesIO()
    Image.new("RGB", (1, 1), ANIM_SLOT_COLORS[slot_index]).save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


def find_slot_boxes(card: Image.Image, slot_count: int) -> list[tuple[int, int, int, int]]:
    """在卡片截图（已裁剪）中按占位色定位各动图槽位的边界框 (left, top, right, bottom)

    Args:
        card: 卡片截图
        slot_count: 动图槽位数量，颜色按 ANIM_SLOT_COLORS 顺序对应

    Returns:
        list[tuple[int, int, int, int]]: 与槽位顺序一致的边界框列表

    Raises:
        ValueError: 某个槽位的占位色未在截图中出现（渲染异常时）
    """
    arr = np.asarray(card.convert("RGB")).astype(np.int16)
    boxes = []
    for slot_index in range(slot_count):
        color = np.array(ANIM_SLOT_COLORS[slot_index], dtype=np.int16)
        mask = np.all(np.abs(arr - color) <= 2, axis=2)
        ys, xs = np.where(mask)
        if len(xs) < 1:
            raise ValueError(f"未在卡片截图中定位到第 {slot_index} 个动图槽位")
        boxes.append((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))
    return boxes


def assemble_composited_gif(base_card: Image.Image, paste_boxes: list[tuple[int, int, int, int]],
                            sequences: list[AnimSequence], frame_messy=None, frame_stride: int = 1,
                            quantize_colors: int = 256) -> bytes:
    """把若干动图序列合成到静态卡片上，输出 GIF bytes

    以总时长最长的序列为主轴：输出帧取自主轴，每帧时刻其余序列按本地时间
    循环取模取帧贴入对应槽位；短序列因此在主轴时长内循环播放。
    抽帧（frame_stride）时保留帧取"到下一保留帧之间的原始时长之和"，
    成片总时长不变。

    Args:
        base_card: 已完成静态渲染（含混乱效果）的卡片图
        paste_boxes: 每个槽位的 (left, top, right, bottom)，与 sequences 一一对应
        frame_messy: 可选回调 (frame, boxes) -> frame，在每帧合成后做扰动
        frame_stride: 帧采样步长，>1 时隔帧输出（用于压缩体积，不裁剪时长）
        quantize_colors: 每帧量化的颜色数

    Returns:
        bytes: GIF 文件数据
    """
    if len(paste_boxes) != len(sequences):
        raise ValueError("paste_boxes 与 sequences 数量不一致")
    master_index = max(range(len(sequences)), key=lambda i: sequences[i].total_duration_ms)
    master = sequences[master_index]
    master_indices = list(range(0, len(master.frames), frame_stride))
    master_total = len(master.durations_ms)
    # 保留帧时长取"到下一保留帧之间的原始时长之和"，抽帧不改变总时长
    durations = [sum(master.durations_ms[i:min(i + frame_stride, master_total)])
                 for i in master_indices]

    def _iter_frames():
        for master_idx in master_indices:
            time_ms = sum(master.durations_ms[:master_idx])
            frame = base_card.copy()
            for box, sequence in zip(paste_boxes, sequences):
                region = sequence.frames[sequence.frame_index_at(time_ms)]
                box_size = (box[2] - box[0], box[3] - box[1])
                if region.size != box_size:
                    region = region.resize(box_size)
                # 带 alpha 蒙版合成：动图透明区域透出卡片背景
                frame.paste(region, (box[0], box[1]), region)
            if frame_messy is not None:
                frame = frame_messy(frame, paste_boxes)
            yield _quantize_frame(frame, quantize_colors)

    return _encode_gif_bytes(_iter_frames(), durations, loop=0)


def assemble_composited_gif_within_size(base_card: Image.Image, paste_boxes: list[tuple[int, int, int, int]],
                                        sequences: list[AnimSequence], frame_messy=None,
                                        max_bytes: int = GIF_OUTPUT_MAX_BYTES, min_frames: int = 2) -> tuple[bytes, int] | None:
    """带体积预算的卡片动图合成：超过 max_bytes 时循环抽帧重编码并比对体积

    每轮按"体积与帧数近似线性"估算抽帧步长快速收敛；抽帧时时长按步长
    补偿，成片总时长不变。抽到不足 min_frames 帧仍超限返回 None。

    Returns:
        tuple[bytes, int] | None: (GIF 数据, 实际使用的抽帧步长)，超限无法压缩为 None
    """
    master_count = max(len(s.frames) for s in sequences)
    stride = 1
    data = assemble_composited_gif(base_card=base_card, paste_boxes=paste_boxes,
                                   sequences=sequences, frame_messy=frame_messy, frame_stride=stride)
    while len(data) > max_bytes:
        next_stride = max(stride + 1, -(-stride * len(data) // max_bytes))
        if master_count // next_stride < min_frames:
            return None
        stride = next_stride
        data = assemble_composited_gif(base_card=base_card, paste_boxes=paste_boxes,
                                       sequences=sequences, frame_messy=frame_messy, frame_stride=stride)
    return data, stride


def sample_sequence(sequence: AnimSequence, stride: int) -> AnimSequence:
    """按步长均匀抽帧，保留帧的时长取"到下一保留帧之间的原始时长之和"，
    总时长严格不变，返回新序列"""
    stride = max(1, stride)
    durations = sequence.durations_ms
    sampled = []
    for i in range(0, len(durations), stride):
        sampled.append(sum(durations[i:min(i + stride, len(durations))]))
    return AnimSequence(frames=sequence.frames[::stride], durations_ms=sampled, loop=sequence.loop)


def trim_transparent_border(sequence: AnimSequence, alpha_threshold: int = 10) -> AnimSequence:
    """裁掉所有帧叠加后完全透明的边框（观感无损），返回新序列"""
    if not sequence.frames or sequence.frames[0].mode != "RGBA":
        return sequence
    alpha_max = None
    for frame in sequence.frames:
        alpha = frame.getchannel("A")
        alpha_max = alpha if alpha_max is None else ImageChops.lighter(alpha_max, alpha)
    visible = alpha_max.point(lambda a: 255 if a >= alpha_threshold else 0)
    bbox = visible.getbbox()
    if not bbox or bbox == (0, 0, *sequence.frames[0].size):
        return sequence
    return AnimSequence(frames=[frame.crop(bbox) for frame in sequence.frames],
                        durations_ms=list(sequence.durations_ms), loop=sequence.loop)


def scale_sequence(sequence: AnimSequence, factor: float) -> AnimSequence:
    """按比例缩放所有帧（时长不变），返回新序列"""
    if factor >= 0.999:
        return sequence
    width, height = sequence.frames[0].size
    size = (max(1, int(width * factor)), max(1, int(height * factor)))
    return AnimSequence(frames=[frame.resize(size) for frame in sequence.frames],
                        durations_ms=list(sequence.durations_ms), loop=sequence.loop)


def compress_anim_sequence(sequence: AnimSequence, budget_bytes: int,
                           shell_size: tuple[int, int] = (640, 1200)) -> tuple[AnimSequence, int, int]:
    """入库压缩阶梯：透明裁边（无损）→ 抽帧封顶 30 帧 → 缩放至约 200px → 在该尺寸内降色 → 最后进一步抽帧

    缩放下限为 max(ANIM_STORE_SCALE_FLOOR, 原尺寸 50%)（取大值，小图不过度缩小）。
    每个候选用纯色壳合成实测体积（超 24 帧时按帧数比例探测估算，控制编码成本）；
    所有抽帧均时长补偿，成片总时长与原图一致。

    Returns:
        tuple[AnimSequence, int, int]: (处理后的序列, 缩放百分比, 颜色数)
    """

    def measure(candidate: AnimSequence, colors: int) -> int:
        # 探测编码：超 probe_frames 帧时按比例折算，避免阶梯每步都全量编码
        probe_frames = 24
        stride = max(1, -(-len(candidate.frames) // probe_frames))
        probe = sample_sequence(candidate, stride)
        shell = Image.new("RGBA", shell_size, (32, 34, 40, 255))
        width, height = probe.frames[0].size
        box = (10, 10, min(10 + width, shell_size[0] - 10), min(10 + height, shell_size[1] - 10))
        data = assemble_composited_gif(base_card=shell, paste_boxes=[box], sequences=[probe],
                                       quantize_colors=colors)
        return int(len(data) * len(candidate.frames) / len(probe.frames))

    seq = trim_transparent_border(sequence)
    capped = sample_sequence(seq, -(-len(seq.frames) // ANIM_STORE_MAX_FRAMES))
    long_edge = max(seq.frames[0].size)
    final_edge = max(ANIM_STORE_SCALE_TARGET, ANIM_STORE_SCALE_FLOOR, long_edge * 0.5)
    if long_edge > final_edge:
        factors = [f for f in (1.0, 0.85, 0.7, 0.55, final_edge / long_edge)
                   if long_edge * f >= final_edge - 0.5]
    else:
        factors = [1.0]
    factors = sorted(set(round(f, 4) for f in factors), reverse=True)
    scaled = {f: scale_sequence(capped, f) for f in factors}
    floor_factor = factors[-1]

    # 阶梯：未处理原图 → 30 帧封顶 → 逐级缩放（256 色）→ 在缩放下限降色 → 进一步抽帧
    candidates = [(seq, 1.0, 256)]
    candidates += [(scaled[f], f, 256) for f in factors
                   if not (f == 1.0 and len(capped.frames) == len(seq.frames))]
    candidates += [(scaled[floor_factor], floor_factor, colors)
                   for colors in ANIM_STORE_COLORS[1:]]
    for frames_target in (20, 15, 10, 6):
        candidates += [(sample_sequence(scaled[floor_factor], -(-len(scaled[floor_factor].frames) // frames_target)),
                        floor_factor, colors) for colors in ANIM_STORE_COLORS]

    for candidate, factor, colors in candidates:
        if measure(candidate, colors) <= budget_bytes:
            return candidate, int(factor * 100), colors
    last = candidates[-1]
    return last[0], int(last[1] * 100), last[2]


def sample_frames(sequence: AnimSequence, count: int) -> list[Image.Image]:
    """从帧序列均匀抽样至多 count 帧（首帧必含），用于逐帧内容安全检测"""
    frames = sequence.frames
    if len(frames) <= count:
        return list(frames)
    step = (len(frames) - 1) / (count - 1)
    return [frames[round(i * step)] for i in range(count)]
