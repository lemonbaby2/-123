#!/usr/bin/env python3
"""Render a five-minute, captioned SOP/CVAT training MP4 from real screenshots."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


SANS = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
SERIF = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc"


@dataclass(frozen=True)
class Scene:
    source: str
    title: str
    caption: str
    duration: int
    annotated: bool = True


SCENES = [
    Scene("FLOW", "全链路总览", "先看完整闭环：采集、AI 候选、人工复核、Reviewer、数据冻结、训练、实时 SOP 与 MES。", 20, False),
    Scene("01_SOP登录页_未填写凭据.png", "登录 SOP 工作台", "使用本人岗位账号。账号、密码、恢复码不进入截图、视频和公开仓库。", 15, False),
    Scene("02_SOP总览与闭环架构.png", "01 总览", "左侧菜单按 02 至 07 顺序执行。AI 候选不等于人工真值，量产验收前保持 HOLD。", 20),
    Scene("03_02数据获取与清洗.png", "02 数据获取与清洗", "绑定工位和来源，检查 ffprobe、SHA256 与 H.264 代理。原始 MP4 只保存一次。", 20),
    Scene("04_03_AI预标注与现场证据.png", "03 工位级 AI 预标", "选择工位专用标签模板；本轮不逐个标电阻、电容、电感。候选状态保持 pending_review。", 20),
    Scene("05_04_SOP人工复核与CVAT双向同步.png", "04 SOP 初审与 CVAT 桥接", "先删除明显误框、补框和核对标签，再打开绑定的官方 CVAT Job。", 20),
    Scene("11_CVAT任务列表.png", "打开正确的 CVAT 任务", "核对任务名称、缩略图、视频帧数和工位。培训任务与生产任务必须分开。", 15),
    Scene("12_CVAT完整标注工作台.png", "认识 CVAT 工作台", "左侧是绘制工具，中间是视频画布，顶部保存与逐帧，右侧是对象列表，底部是时间轴。", 20),
    Scene("13_CVAT矩形框_形状与Track选择.png", "选择矩形 Shape 或 Track", "固定单帧目标选择“形状”；连续移动目标选择“跟踪轨迹”。标签必须来自当前工位模板。", 20),
    Scene("14_CVAT新建并选中矩形框.png", "拖动绘制并检查边界", "从左上拖到右下，框贴合工位级目标。画完后在右侧对象列表核对标签和帧号。", 20),
    Scene("15_CVAT_Delete删除演示框.png", "单击选框，再按 Delete", "确认只有目标对象高亮后再删除。误删立即撤销；不要边播放边连续按 Delete。", 20),
    Scene("16_CVAT_Track与关键帧演示.png", "Track、关键帧与结束帧", "起始帧创建 Track；遮挡、转向和步骤边界补关键帧；目标消失后的下一帧设为 Outside。", 25),
    Scene("06_05数据集构建与质量冻结.png", "Reviewer 通过后冻结数据集", "只同步 annotation-only 和 Frame Manifest。按完整视频或 SN 拆分，禁止相邻帧随机泄漏。", 20),
    Scene("07_06训练验证与部署.png", "06 温控训练、验证与注册", "训练前暂停预标，单 GPU 温控执行。固定测试集通过后才进入 Model Registry。", 20),
    Scene("08_07实时SOP与MES.png", "07 实时 SOP 与 MES", "左侧看实时视频、ROI、框和延迟；右侧看步骤、标准、置信度和 PASS/NG/REWORK/HOLD。", 20),
    Scene("END", "培训完成后的独立练习", "每人完成：3 个 Shape、1 次 Delete、1 条 Track、Reviewer 驳回修正、annotation-only 回流和训练门禁口述。", 5, False),
]


def font(size: int, serif: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(SERIF if serif else SANS, size)


def fit_image(image: Image.Image, width: int, height: int) -> Image.Image:
    ratio = min(width / image.width, height / image.height)
    size = (max(1, int(image.width * ratio)), max(1, int(image.height * ratio)))
    return image.resize(size, Image.Resampling.LANCZOS)


def wrap_text(draw: ImageDraw.ImageDraw, text: str, max_width: int, size: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for char in text:
        candidate = current + char
        if draw.textbbox((0, 0), candidate, font=font(size))[2] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = char
    if current:
        lines.append(current)
    return lines[:2]


def build_slide(scene: Scene, number: int, screenshots: Path, flowchart: Path, output: Path) -> None:
    canvas = Image.new("RGB", (1920, 1080), "#eef2f6")
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, 1920, 125), fill="#0a2847")
    draw.rectangle((0, 915, 1920, 1080), fill="#0a2847")
    draw.rounded_rectangle((40, 28, 118, 106), radius=14, fill="#1f8168")
    draw.text((79, 66), f"{number:02d}", font=font(30), fill="white", anchor="mm")
    draw.text((145, 25), scene.title, font=font(48, True), fill="white")
    draw.text((145, 83), "宁波视觉 SOP · CVAT 工人标注与训练会议教学", font=font(22), fill="#a9ddcf")

    if scene.source == "FLOW":
        source = Image.open(flowchart).convert("RGB")
    elif scene.source == "END":
        source = Image.new("RGB", (1400, 700), "white")
        card = ImageDraw.Draw(source)
        items = [
            "使用本人岗位账号，培训任务与生产任务分开",
            "AI 候选必须人工复核，Reviewer 通过后才能冻结",
            "训练优先 annotation-only，不长期保存全量 PNG",
            "训练与预标互斥，温控优先，量产前保持 HOLD",
        ]
        card.text((80, 60), "会后四条确认", font=font(54, True), fill="#0a2847")
        for idx, item in enumerate(items, start=1):
            y = 165 + (idx - 1) * 120
            card.rounded_rectangle((80, y, 142, y + 62), radius=12, fill="#1f8168")
            card.text((111, y + 31), str(idx), font=font(28), fill="white", anchor="mm")
            card.text((175, y + 10), item, font=font(31), fill="#263746")
    else:
        path = screenshots / ("讲解标注" if scene.annotated and (screenshots / "讲解标注" / scene.source).is_file() else "") / scene.source
        source = Image.open(path).convert("RGB")

    fitted = fit_image(source, 1780, 750)
    canvas.paste(fitted, ((1920 - fitted.width) // 2, 145 + (750 - fitted.height) // 2))
    lines = wrap_text(draw, scene.caption, 1740, 31)
    for line_no, line in enumerate(lines):
        draw.text((95, 940 + line_no * 48), line, font=font(31), fill="white")
    draw.text((1820, 1037), f"{sum(s.duration for s in SCENES[:number - 1]) // 60}:{sum(s.duration for s in SCENES[:number - 1]) % 60:02d}", font=font(23), fill="#a9ddcf", anchor="ra")
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, quality=96)


def run(command: list[str]) -> None:
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def render(slides: Path, output: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="sop-meeting-video-") as temp_name:
        temp = Path(temp_name)
        clips: list[Path] = []
        for index, scene in enumerate(SCENES, start=1):
            clip = temp / f"{index:02d}.mp4"
            run(
                [
                    "ffmpeg", "-y", "-loop", "1", "-framerate", "25", "-i", str(slides / f"{index:02d}.png"),
                    "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
                    "-t", str(scene.duration), "-c:v", "libx264", "-preset", "ultrafast", "-crf", "24",
                    "-pix_fmt", "yuv420p", "-r", "25", "-c:a", "aac", "-b:a", "96k", "-shortest", str(clip),
                ]
            )
            clips.append(clip)
        concat = temp / "concat.txt"
        concat.write_text("".join(f"file '{clip}'\n" for clip in clips), encoding="utf-8")
        output.parent.mkdir(parents=True, exist_ok=True)
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", "-movflags", "+faststart", str(output)])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--screenshots", type=Path, required=True)
    parser.add_argument("--flowchart", type=Path, required=True)
    parser.add_argument("--slides", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if sum(scene.duration for scene in SCENES) != 300:
        raise RuntimeError("Training video timeline must be exactly 300 seconds")
    for index, scene in enumerate(SCENES, start=1):
        build_slide(scene, index, args.screenshots, args.flowchart, args.slides / f"{index:02d}.png")
    render(args.slides, args.output)
    print(args.output)


if __name__ == "__main__":
    main()
