#!/usr/bin/env python3
"""Build callout screenshots and a print-ready SOP/CVAT flow diagram."""

from __future__ import annotations

import argparse
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


SANS = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
SERIF = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc"


CALLOUTS = {
    "02_SOP总览与闭环架构.png": (50, 175, 220, 470, "从 01 到 07 按顺序操作"),
    "03_02数据获取与清洗.png": (1290, 205, 250, 70, "先接入并校验视频"),
    "04_03_AI预标注与现场证据.png": (1310, 200, 225, 75, "启动工位级预标"),
    "05_04_SOP人工复核与CVAT双向同步.png": (1210, 200, 330, 80, "打开 CVAT 或执行同步"),
    "06_05数据集构建与质量冻结.png": (1305, 226, 235, 70, "Reviewer 通过后冻结"),
    "07_06训练验证与部署.png": (470, 385, 1040, 200, "选择已冻结视频与模型"),
    "08_07实时SOP与MES.png": (1230, 245, 300, 495, "右侧核对步骤与判定"),
    "11_CVAT任务列表.png": (1415, 170, 125, 50, "打开培训任务"),
    "12_CVAT完整标注工作台.png": (0, 125, 60, 520, "左侧工具栏"),
    "13_CVAT矩形框_形状与Track选择.png": (0, 265, 320, 320, "选择形状或跟踪轨迹"),
    "14_CVAT新建并选中矩形框.png": (445, 250, 450, 390, "框住工位级目标"),
    "15_CVAT_Delete删除演示框.png": (1250, 190, 335, 245, "选中对象后按 Delete"),
    "16_CVAT_Track与关键帧演示.png": (1240, 190, 345, 315, "Track 出现在对象列表"),
}


def font(size: int, serif: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(SERIF if serif else SANS, size)


def wrap(draw: ImageDraw.ImageDraw, text: str, max_width: int, size: int) -> list[str]:
    result: list[str] = []
    current = ""
    for char in text:
        candidate = current + char
        if draw.textbbox((0, 0), candidate, font=font(size))[2] <= max_width:
            current = candidate
        else:
            if current:
                result.append(current)
            current = char
    if current:
        result.append(current)
    return result


def annotate(source: Path, target: Path, box: tuple[int, int, int, int, str], number: int) -> None:
    image = Image.open(source).convert("RGB")
    draw = ImageDraw.Draw(image, "RGBA")
    x, y, w, h, label = box
    draw.rounded_rectangle((x, y, x + w, y + h), radius=10, outline=(220, 38, 38, 255), width=7)
    marker_x = min(image.width - 45, x + w - 15)
    marker_y = max(40, y - 10)
    draw.ellipse((marker_x - 28, marker_y - 28, marker_x + 28, marker_y + 28), fill=(220, 38, 38, 245))
    marker = str(number)
    marker_box = draw.textbbox((0, 0), marker, font=font(28))
    draw.text(
        (marker_x - (marker_box[2] - marker_box[0]) / 2, marker_y - 20),
        marker,
        font=font(28),
        fill="white",
    )
    label_width = max(300, min(620, draw.textbbox((0, 0), label, font=font(28))[2] + 50))
    label_x = min(image.width - label_width - 20, max(20, x))
    label_y = min(image.height - 75, y + h + 12)
    draw.rounded_rectangle((label_x, label_y, label_x + label_width, label_y + 58), radius=8, fill=(8, 26, 47, 235))
    draw.text((label_x + 20, label_y + 10), label, font=font(28), fill="white")
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target, quality=95)


def arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int]) -> None:
    draw.line((start, end), fill=(31, 129, 104), width=8)
    ex, ey = end
    draw.polygon([(ex, ey), (ex - 24, ey - 15), (ex - 24, ey + 15)], fill=(31, 129, 104))


def flowchart(output: Path) -> None:
    width, height = 2400, 1950
    image = Image.new("RGB", (width, height), "#f5f7fa")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, width, 150), fill="#0a2847")
    draw.text((90, 35), "宁波视觉 SOP + CVAT 标注、训练、推理与 MES 闭环", font=font(56, True), fill="white")
    draw.text((92, 105), "培训标准流程｜所有 AI 候选必须经人工复核与 Reviewer 验收", font=font(26), fill="#a9ddcf")

    nodes = [
        ("02 数据获取与清洗", "RTSP / UVC / SD 卡 / Google Drive / 本地 MP4\nffprobe、SHA256、H.264 代理；原片只保存一次"),
        ("03 工位级 AI 预标", "按工位标签模板生成 pending_review 候选\n电阻、电容、电感等微小元件暂不打框"),
        ("04 SOP 页面人工初审", "逐帧检查候选；删除误框、补框、改类别\n设置关键帧与目标轨迹范围"),
        ("推送到官方 CVAT", "整段代理视频 + 标签映射 + 已确认候选\n在官方工作台使用完整矩形、Track 与对象列表"),
        ("CVAT 标注员修正", "单击选框；移动、缩放、改标签、Delete\n遮挡、转向、步骤边界处补关键帧"),
        ("Reviewer 审核", "检查漏标、误标、类别混淆与 Track 漂移\n不通过退回；通过后记录审核人与版本"),
        ("CVAT → SOP 回流", "同步 annotation-only + Frame Manifest\n不重复导出全量 PNG，不传“带框视频”作训练真值"),
        ("05 Dataset Version 冻结", "按完整视频 / SN / 工位 / 日期划分 Train、Val、Test\n质量检查通过后冻结哈希、标签映射和拆分清单"),
        ("06 训练、验证与注册", "训练前暂停预标，单 GPU 温控执行\n固定测试集验收后进入 Model Registry；否则 HOLD"),
        ("07 实时 SOP + MES", "左侧 RTSP 检测；右侧步骤、置信度、纠正建议\n输出 PASS / NG / REWORK / HOLD 并记录证据"),
        ("Hard Case 回流", "误报、漏报、低置信度和稀有 NG 去重后回到 03/04\n形成可审计的持续改进闭环"),
    ]
    x = 150
    y = 205
    node_w = 970
    node_h = 210
    gap_y = 54
    positions: list[tuple[int, int]] = []
    for index, (title, body) in enumerate(nodes):
        col = 0 if index < 6 else 1
        row = index if col == 0 else index - 6
        node_x = 120 + col * 1160
        node_y = 200 + row * (node_h + gap_y)
        positions.append((node_x, node_y))
        fill = "#ffffff" if index not in (5, 8, 9) else "#fff8e7"
        border = "#1f8168" if index not in (5, 8, 9) else "#c68418"
        draw.rounded_rectangle((node_x, node_y, node_x + node_w, node_y + node_h), radius=18, fill=fill, outline=border, width=4)
        draw.rounded_rectangle((node_x + 20, node_y + 24, node_x + 86, node_y + 90), radius=14, fill=border)
        draw.text((node_x + 42, node_y + 34), str(index + 1), font=font(28), fill="white", anchor="ma")
        draw.text((node_x + 112, node_y + 25), title, font=font(34, True), fill="#0a2847")
        for line_no, line in enumerate(body.splitlines()):
            draw.text((node_x + 112, node_y + 92 + line_no * 43), line, font=font(25), fill="#3e4c59")

    for i in range(5):
        sx, sy = positions[i]
        ex, ey = positions[i + 1]
        draw.line((sx + node_w // 2, sy + node_h, ex + node_w // 2, ey), fill="#1f8168", width=8)
        draw.polygon(
            [(ex + node_w // 2, ey), (ex + node_w // 2 - 15, ey - 24), (ex + node_w // 2 + 15, ey - 24)],
            fill="#1f8168",
        )
    arrow(draw, (positions[5][0] + node_w, positions[5][1] + node_h // 2), (positions[6][0], positions[6][1] + node_h // 2))
    for i in range(6, 10):
        sx, sy = positions[i]
        ex, ey = positions[i + 1]
        draw.line((sx + node_w // 2, sy + node_h, ex + node_w // 2, ey), fill="#1f8168", width=8)
        draw.polygon(
            [(ex + node_w // 2, ey), (ex + node_w // 2 - 15, ey - 24), (ex + node_w // 2 + 15, ey - 24)],
            fill="#1f8168",
        )

    footer_y = 1820
    draw.rectangle((0, footer_y, width, height), fill="#0a2847")
    footer = "三条硬规则：AI 候选不等于人工真值｜训练与预标互斥，温控优先｜量产验收完成前必须保持 HOLD"
    draw.text((width // 2, footer_y + 58), footer, font=font(30, True), fill="white", anchor="mm")
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, quality=96)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--screenshots", type=Path, required=True)
    parser.add_argument("--flowchart", type=Path, required=True)
    args = parser.parse_args()
    annotated = args.screenshots / "讲解标注"
    for number, (filename, callout) in enumerate(CALLOUTS.items(), start=1):
        source = args.screenshots / filename
        if source.is_file():
            annotate(source, annotated / filename, callout, number)
    flowchart(args.flowchart)


if __name__ == "__main__":
    main()
