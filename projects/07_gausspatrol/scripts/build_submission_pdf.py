"""Build the competition technical-proposal PDF from committed metrics.

Optional dependency: reportlab. The core GaussPatrol demo does not require it.
"""

from __future__ import annotations

import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Flowable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


PROJECT = Path(__file__).resolve().parents[1]
METRICS = PROJECT / "artifacts/sample_run/metrics.json"
OUTPUT = PROJECT / "submission/GaussPatrol_technical_proposal_zh.pdf"


def register_fonts() -> tuple[str, str]:
    regular = Path(r"C:\Windows\Fonts\simhei.ttf")
    bold = Path(r"C:\Windows\Fonts\simhei.ttf")
    if not regular.exists():
        raise RuntimeError("Chinese font not found; edit register_fonts() for this operating system")
    pdfmetrics.registerFont(TTFont("GaussPatrolCN", str(regular)))
    pdfmetrics.registerFont(TTFont("GaussPatrolCN-Bold", str(bold)))
    return "GaussPatrolCN", "GaussPatrolCN-Bold"


class MetricBars(Flowable):
    def __init__(self, metrics: dict, font: str):
        super().__init__()
        self.metrics = metrics
        self.font = font
        self.width = 170 * mm
        self.height = 78 * mm

    def draw(self) -> None:
        canvas = self.canv
        nominal = self.metrics["nominal"]
        shifted = self.metrics["shifted"]
        rows = [
            ("路线完成率", nominal["route_completion_rate"], shifted["route_completion_rate"], 1.0, "%"),
            ("地图完整度", nominal["map_completeness"], shifted["map_completeness"], 1.0, "%"),
            ("缺陷 AP50", nominal["perception"]["ap50_11point"], shifted["perception"]["ap50_11point"], 1.0, ""),
            ("ATE RMSE", nominal["trajectory"]["ate_rmse_m"], shifted["trajectory"]["ate_rmse_m"], 0.15, "m"),
        ]
        canvas.setFont(self.font, 8)
        for index, (name, a, b, maximum, unit) in enumerate(rows):
            y = self.height - 15 * mm - index * 17 * mm
            canvas.setFillColor(colors.HexColor("#0f172a"))
            canvas.drawString(0, y + 5 * mm, name)
            for offset, value, color, label in ((3.5 * mm, a, "#0f766e", "Nominal"), (0, b, "#f97316", "Shifted")):
                canvas.setFillColor(colors.HexColor("#e2e8f0"))
                canvas.roundRect(35 * mm, y + offset, 110 * mm, 3 * mm, 1 * mm, fill=1, stroke=0)
                canvas.setFillColor(colors.HexColor(color))
                canvas.roundRect(35 * mm, y + offset, 110 * mm * min(1.0, value / maximum), 3 * mm, 1 * mm, fill=1, stroke=0)
                shown = f"{value*100:.1f}%" if unit == "%" else f"{value:.3f} {unit}".strip()
                canvas.setFillColor(colors.HexColor("#475569"))
                canvas.drawString(148 * mm, y + offset, f"{label} {shown}")
        canvas.setFillColor(colors.HexColor("#64748b"))
        canvas.drawString(0, 1 * mm, "Shifted 为压力仿真，不是真机 Sim-to-Real 数据。")


def add_page_number(canvas, document) -> None:
    canvas.saveState()
    canvas.setFont("GaussPatrolCN", 8)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.drawString(20 * mm, 12 * mm, "GaussPatrol 技术方案 - clean-room competition baseline")
    canvas.drawRightString(190 * mm, 12 * mm, f"第 {document.page} 页")
    canvas.restoreState()


def main() -> None:
    font, bold = register_fonts()
    metrics = json.loads(METRICS.read_text(encoding="utf-8"))
    styles = getSampleStyleSheet()
    title = ParagraphStyle("title_cn", parent=styles["Title"], fontName=bold, fontSize=24, leading=34, alignment=TA_CENTER, textColor=colors.HexColor("#0f172a"), spaceAfter=8 * mm)
    subtitle = ParagraphStyle("subtitle_cn", parent=styles["Normal"], fontName=font, fontSize=12, leading=20, alignment=TA_CENTER, textColor=colors.HexColor("#475569"))
    h1 = ParagraphStyle("h1_cn", parent=styles["Heading1"], fontName=bold, fontSize=16, leading=24, textColor=colors.HexColor("#0f3b5d"), spaceBefore=6 * mm, spaceAfter=3 * mm)
    h2 = ParagraphStyle("h2_cn", parent=styles["Heading2"], fontName=bold, fontSize=12, leading=18, textColor=colors.HexColor("#0f766e"), spaceBefore=4 * mm, spaceAfter=2 * mm)
    body = ParagraphStyle("body_cn", parent=styles["BodyText"], fontName=font, fontSize=9.5, leading=16, textColor=colors.HexColor("#1e293b"), spaceAfter=2.5 * mm)
    bullet = ParagraphStyle("bullet_cn", parent=body, leftIndent=5 * mm, firstLineIndent=-3 * mm, bulletIndent=1 * mm)
    small = ParagraphStyle("small_cn", parent=body, fontSize=8, leading=13, textColor=colors.HexColor("#64748b"))
    document = SimpleDocTemplate(str(OUTPUT), pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm, topMargin=18 * mm, bottomMargin=20 * mm, title="GaussPatrol 技术方案", author="GaussPatrol Team")
    story = [Spacer(1, 25 * mm), Paragraph("GaussPatrol", title), Paragraph("面向产业园区的多模态具身巡检与动态三维地图系统", subtitle), Spacer(1, 15 * mm), Paragraph("GOAI 2026 - 具身未来 / Embodied Future - 产业园区全地形巡逻", subtitle), Spacer(1, 14 * mm), Paragraph("版本：1.0（比赛技术方案草案）<br/>日期：2026-08-04<br/>开源状态：clean-room 仿真代码 MIT；真机 SDK/模型/数据待授权", subtitle), Spacer(1, 28 * mm), Paragraph("重要边界", h2), Paragraph("当前公开成绩来自二维确定性仿真。仓库未运行山猫 S10、LIO-SAM、FAST-LIVO2、YOLO、Isaac Lab 或真实 3DGS 训练，不把压力场景写成真机 Sim-to-Real。", body), PageBreak()]

    story.extend([Paragraph("1. 项目目标", h1), Paragraph("在坡道、碎石、低摩擦和动态人员/车辆环境中，机器人自主完成指定点位巡检，在安全约束下输出定位、设备缺陷、任务状态、Gaussian 场景资产和可审计报告。", body), Paragraph("成功条件", h2)])
    for item in ("完成全部任务点并返航；", "全过程零碰撞和零安全规则违规；", "定位或障碍感知异常时 safe stop；", "设备异常绑定图像、位姿、模型与任务 ID；", "实时导航不依赖 3DGS 或云服务。"): story.append(Paragraph("• " + item, bullet))

    story.extend([Paragraph("2. 系统架构", h1), Paragraph("系统分为实时安全平面、任务认知平面、地图可视化平面和评测平面。LiDAR/IMU/RGB-D 经过同步与质量门控后分别进入 LIO 与视觉感知；占据地图和动态体进入规划；地形状态进入限速/gait 策略；S10 adapter 负责最终命令与 watchdog；3DGS 和报告异步运行。", body)])
    architecture = [["层", "核心模块", "失效策略"], ["实时安全", "驱动、LIO、局部障碍、控制门控", "停车/回退厂商 gait"], ["任务认知", "点位状态机、缺陷检测、异常确认", "重试/跳过非关键检测"], ["地图可视化", "点云、Gaussian 资产、报告", "关闭非关键服务"], ["评测", "ATE/RPE、AP、完成率、日志", "保留失败回合"]]
    table = Table(architecture, colWidths=[28 * mm, 75 * mm, 57 * mm], repeatRows=1)
    table.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), font), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f3b5d")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("LEADING", (0, 0), (-1, -1), 13), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")])]))
    story.extend([table, PageBreak(), Paragraph("3. 算法方案", h1)])
    sections = [
        ("3.1 定位建图", "真机优先采用原始 LIO-SAM 或 FAST-LIVO2 上游实现，通过 ROS2 component 接入；用匹配残差、协方差、有效点、bias 和更新时间形成 OK/WARN/STOP 健康门控。公开仿真用 seeded odometry 与地标校正验证 ATE/RPE 管线。"),
        ("3.2 动态避障", "全局路线结合地形代价，移动体进入安全包络时停止当前段并重规划。真机使用 Nav2/MPPI/DWB 或等价局部规划，必须处理目标速度、遮挡、时间衰减和感知超时。"),
        ("3.3 缺陷识别", "YOLO 候选后端按设备/日期/场地拆分数据，报告 AP50/AP50-95、设备级 recall、漏检率和端到端 P95。当前合成 detector 只验证评分与审计。"),
        ("3.4 多地形控制", "当前规则层按 gravel/ramp/wet/rubble 限速并切换抽象 gait。复赛需要控制成员基于 S10 asset 在 Isaac Lab 训练/验证，并保留厂商 gait fallback。"),
        ("3.5 Gaussian 地图", "导航使用占据/点云地图，3DGS 异步生成可视化和巡检证据。动态人员必须 mask 或分层，避免写入静态地图。当前只导出 Gaussian-like PLY schema。"),
    ]
    for heading, text in sections: story.extend([Paragraph(heading, h2), Paragraph(text, body)])

    story.extend([Paragraph("4. 当前可复现结果", h1), MetricBars(metrics, font), Paragraph("指标来自仓库 artifacts/sample_run/metrics.json。路线、检测决策和几何指标使用固定 seed；wall runtime 与函数延迟依赖机器负载。", small)])
    result_rows = [["指标", "Nominal", "Shifted"], ["点位", "5/5", "5/5"], ["动态避障", "4/4", "4/4"], ["碰撞", "0", "0"], ["ATE RMSE", "0.0187 m", "0.1125 m"], ["缺陷 AP50", "1.000", "0.636"], ["地图完整度", "89.47%", "89.47%"], ["模型任务时间", "74.35 s", "90.45 s"]]
    result_table = Table(result_rows, colWidths=[65 * mm, 45 * mm, 45 * mm], repeatRows=1)
    result_table.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), font), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f766e")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")), ("ALIGN", (1, 1), (-1, -1), "CENTER"), ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")])]))
    story.extend([Spacer(1, 4 * mm), result_table, PageBreak(), Paragraph("5. ROS2/S10/Isaac Lab 集成", h1), Paragraph("仓库提供 topic/frame/安全契约和 Isaac Lab 地形课程草案。获得官方 SDK 后首先确认控制层级、gait 枚举、关节顺序、watchdog、URDF/惯量和硬件限制；未知接口不会在代码中伪造为已验证。", body)])
    for item in ("驱动与 TF 静态检查；", "抬架关节/轮方向和急停；", "0.1 m/s 平地与真值对比；", "单传感器、网络和节点崩溃注入；", "坡道、碎石、低摩擦逐项放开；", "最后引入动态人员和完整路线。"): story.append(Paragraph("• " + item, bullet))

    story.extend([Paragraph("6. 安全与风险", h1), Paragraph("硬件急停独立于主计算机。软件覆盖定位 age/跳变、障碍 stop distance、命令 watchdog、最大速度/角速度、地图边界、任务超时、通信断开和温度/电量。优先级为：安全与规则合规 > 全点位完成 > 自主模式 > 时间优化 > 高保真可视化。", body), Paragraph("最大团队短板", h2), Paragraph("当前缺少具有轮足/四足控制、Isaac Lab、强化学习/模仿学习、ros2_control 和真实 gait 调试经验的成员。建议把第三名核心成员明确设为运动控制负责人。", body)])

    story.extend([Paragraph("7. 开源与数据", h1), Paragraph("原创仿真代码按 MIT License 发布；当前仓库不含真实园区数据、个人图像、客户数据、厂商 SDK 或模型权重。LIO-SAM、FAST-LIVO2、Navigation2、Isaac Lab、Ultralytics 和 GraphDeCo 3DGS 仅作为候选依赖，采用前分别核对许可证、数据和模型条款。", body), Paragraph("8. 里程碑", h1)])
    milestones = [["阶段", "目标", "验收"], ["M0 已完成", "可复现闭环、测试、报告", "CI 与样例 artifact"], ["M1 SDK 到位", "ROS2 bring-up、TF、急停", "静态/抬架/低速"], ["M2 导航感知", "LIO、Nav2、YOLO", "rosbag + 指标"], ["M3 地形控制", "Isaac Lab + S10", "系留/逐地形"], ["M4 决赛", "全路线、长稳、演示", "成功和失败回合"]]
    milestone_table = Table(milestones, colWidths=[32 * mm, 70 * mm, 55 * mm], repeatRows=1)
    milestone_table.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), font), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f3b5d")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")), ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.extend([milestone_table, PageBreak(), Paragraph("9. 结论与真实性矩阵", h1), Paragraph("GaussPatrol 当前已经形成一条真实可运行、可测试、可审计的比赛工程基线。它证明闭环接口和评测资料完整，但不替代真机验证。下一阶段应集中资源获得 SDK/实机、补齐控制成员，并以零安全违规和全点位完成为第一目标。", body)])
    truth_rows = [["能力", "当前状态", "证据/下一步"], ["闭环仿真", "已运行", "代码、13 项测试、artifact"], ["动态避障", "二维仿真", "4/4 重规划，真机待测"], ["定位", "合成里程计", "ATE/RPE 管线；LIO 待接"], ["缺陷检测", "合成 detector", "AP 管线；真实 YOLO 待接"], ["Gaussian 地图", "PLY surrogate", "真实 3DGS 训练待接"], ["地形 gait", "规则意图", "Isaac Lab/S10 policy 待接"], ["Sim-to-Real", "未测", "禁止用 shifted 冒充"]]
    truth_table = Table(truth_rows, colWidths=[38 * mm, 43 * mm, 76 * mm], repeatRows=1)
    truth_table.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), font), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f766e")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")), ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")])]))
    story.extend([Spacer(1, 4 * mm), truth_table, Paragraph("赛前必须书面确认", h2)])
    for item in ("最终机器人型号、SDK 版本、控制权限和实机资源时间；", "任务点、路线边界、障碍/地形定义和安全判罚；", "最终计时公式以及自主导航/跟随模式系数；", "允许使用的传感器、外接算力、网络和预建地图；", "代码、模型、数据、视频和技术方案的公开范围。"): story.append(Paragraph("• " + item, bullet))
    story.extend([Paragraph("仓库交付", h2), Paragraph("README、技术方案、开发日志、评测协议、ROS2/S10/Isaac Lab 接入草案、数据与许可说明、提交清单、可运行代码、测试、JSON/JSONL、SVG、PLY 和 SHA-256 清单均随项目目录交付。", body)])
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    document.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    print(OUTPUT)


if __name__ == "__main__":
    main()
