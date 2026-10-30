#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 WorkBuddy 会话记录（*.jsonl）中抽取具身智能相关的对话档案。

用法：
    python extract_dialogues.py --scan          # 只统计，不写文件
    python extract_dialogues.py --emit OUTDIR   # 生成 markdown 档案

设计原则：
1. 只抽取「用户提问」+「助手最终回复」，不搬运 reasoning 与工具原始输出（体积大、含隐私）。
2. 强制脱敏：内网 IP、主机名、账号密码、token、绝对家目录路径。
3. 用关键词打分命中具身智能主题，命中不足的会话直接丢弃。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECTS = Path(r"C:\Users\lzp\.workbuddy\projects")

# ---------------------------------------------------------------- 主题词典
TOPICS = {
    "VLA（视觉-语言-动作）": [
        "vla", "openvla", "smolvla", "spatialvla", "starvla", "π0", "pi0", "rt-2",
        "lerobot", "action chunk", "动作分块", "模仿学习", "diffusion policy",
        "gr00t", "nvidia groot", "遥操作", "teleoperation",
    ],
    "VLM（视觉语言模型）": [
        "vlm", "qwen2.5-vl", "qwen3-vl", "视觉问答", "vision language", "grounded-sam",
    ],
    "世界模型 / Real2Sim": [
        "世界模型", "world model", "real2sim", "sim2real", "数字孪生",
        "isaac sim", "isaac lab", "isaaclab", "newton", "mjwarp", "mujoco warp",
        "域随机化", "domain random",
        # 上游统一词：具身智能本体叙述
        "具身智能", "具身", "embodied", "isaac", "mujoco", "仿真环境",
    ],
    "强化学习与运动控制": [
        "ppo", "rsl_rl", "强化学习", "mjlab", "microduck", "机器鸭",
        "四足", "机器狗", "humanoid", "人形机器人", "unitree go2",
        "unitree h1", "anymal", "cassie", "franka", "allegro",
        "灵巧手", "运动策略", "locomotion", "策略训练", "机器人训练",
    ],
    "SLAM / 三维重建": [
        "slam", "3dgs", "gaussian splatting", "高斯", "点云", "icp", "lio-sam",
        "loam", "vins", "rtk", "因子图", "gtsam", "回环",
    ],
    "边缘部署": [
        "tensorrt", "rknn", "hailo", "jetson", "orin", "rk3588", "int8",
        "量化", "边缘部署", "蒸馏",
    ],
    "工业视觉 / SOP": [
        "yolo", "sop", "cvat", "缺陷检测", "产线", "工位", "megvii",
        "视觉检测", "标注",
    ],
    "DGX / 算力": [
        "dgx", "spark", "gb10", "cuda", "算力",
    ],
}

ALL_KW = [(t, k) for t, kws in TOPICS.items() for k in kws]

# 强关键词：出现即说明会话确实在讲具身智能 / 机器人智能体，而不是顺带提一句
STRONG = [
    "具身智能", "具身", "embodied", "vla", "vlm", "openvla", "smolvla", "spatialvla",
    "starvla", "groot", "lerobot", "isaac sim", "isaac lab", "isaaclab", "mujoco",
    "mjlab", "mjwarp", "newton", "microduck", "机器鸭", "世界模型", "world model",
    "real2sim", "sim2real", "3dgs", "gaussian splatting", "slam", "四足", "机器狗",
    "humanoid", "人形机器人", "灵巧手", "allegro", "franka", "go2", " locomotion",
    "运动控制策略", "强化学习", "ppo", "域随机化", "遥操作", "模仿学习",
    "action chunk", "diffusion policy", "高斯", "点云配准", "vins", "lio-sam",
]

# 弱关键词：只用于给会话打主题标签，单独出现不足以入选
WEAK_ONLY = {"yolo", "sop", "cvat", "产线", "工位", "标注", "量化", "蒸馏", "dgx",
             "cuda", "算力", "tensorrt", "jetson", "orin", "rknn", "hailo"}

# ---------------------------------------------------------------- 脱敏规则
SCRUB = [
    # IPv4（含内网段），保留 127.0.0.1
    (re.compile(r"\b(?!127\.0\.0\.1)(?:\d{1,3}\.){3}\d{1,3}\b"), "<IP>"),
    # 主机名
    (re.compile(r"\bspark-[0-9a-f]{4}\b", re.I), "<DGX-HOST>"),
    (re.compile(r"\bDESKTOP-[A-Z0-9]{7}\b"), "<PC-HOST>"),
    (re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"), "<UUID>"),
    # 账号/密码（带冒号与不带冒号两种写法）
    (re.compile(r"(?i)(password|passwd|密码)\s*[:=：]\s*\S+"), r"\1: <REDACTED>"),
    (re.compile(r"(?i)(密码|口令)\s*[是为]?\s*[a-z0-9!@#_.-]{3,}"), r"\1 <REDACTED>"),
    (re.compile(r"\b(nvidia|xjai|lzp)/\d{4,}\b"), "<USER>/<PW>"),
    (re.compile(r"\bssh\s+\w+@<IP>", re.I), "ssh <USER>@<IP>"),
    # token / key
    (re.compile(r"\b(?:ghp|gho|ghs)_[A-Za-z0-9]{20,}\b"), "<TOKEN>"),
    (re.compile(r"\bsk-[A-Za-z0-9\-_]{16,}\b"), "<TOKEN>"),
    (re.compile(r"\bAKID[A-Za-z0-9]{16,}\b"), "<TOKEN>"),
    (re.compile(r"(?i)(api[_-]?key|token|secret)\s*[:=]\s*\S+"), r"\1: <REDACTED>"),
    # 家目录
    (re.compile(r"C:\\Users\\[^\\\s\"']+", re.I), r"C:\\Users\\<USER>"),
    (re.compile(r"/c/Users/[^/\s\"']+", re.I), "/c/Users/<USER>"),
    (re.compile(r"/home/(?!nvidia\b)[a-z][\w.-]*"), "/home/<USER>"),
    # 微信 / 手机 / 邮箱
    (re.compile(r"wxid_[a-z0-9]+", re.I), "<WXID>"),
    (re.compile(r"\b1[3-9]\d{9}\b"), "<PHONE>"),
    (re.compile(r"\b[\w.+-]+@(?:qq|163|gmail|outlook|foxmail)\.com\b", re.I), "<EMAIL>"),
    # 指向本机绝对路径的 Markdown 链接（/home/... 、/mnt/... ）在仓库里必然是死链，
    # 降级成行内代码，保留信息但不制造坏链接
    (re.compile(r"\[([^\]]{1,120})\]\((/[^)\s]*)\)"), r"`\1`"),
]

# 系统注入的噪声行：工具回显、背景任务完成通知、宿主前缀
NOISE_PREFIX = (
    "you are workbuddy", "chatcmpl-tool", "completed background command",
    "please continue with the conversation", "summary:", "this session is being continued",
    "command: ", "stdout:", "device node", "caveat:", "the following is",
)
NOISE_RE = re.compile(
    r"^(?:[A-Za-z0-9]{5,8}\s+chatcmpl-tool|<\w+|command:|stdout:|stderr:)", re.I
)

SR_BLOCK = re.compile(
    r"<(?:system-reminder|user_info|identity_context|project_context|project_layout|"
    r"connector-status|current_time|memory|task_management)[^>]*>.*?</(?:system-reminder|"
    r"user_info|identity_context|project_context|project_layout|connector-status|"
    r"current_time|memory|task_management)>",
    re.S | re.I,
)
TAG_BLOCK = re.compile(r"<[a-z_][a-z0-9_-]*\s+data-role=\"[^\"]*\">.*?</[a-z_][a-z0-9_-]*>", re.S | re.I)


def scrub(text: str) -> str:
    for pat, rep in SCRUB:
        text = pat.sub(rep, text)
    return text


def clean_user_text(text: str) -> str:
    text = SR_BLOCK.sub("", text)
    text = TAG_BLOCK.sub("", text)
    text = re.sub(r"<[^>]{1,80}>", "", text)
    text = re.sub(r"(?i)^you are workbuddy[,，]?\s*a powerful ai assistant\.?\s*", "", text.strip())
    text = text.strip()
    # 纯系统回显：整段以噪声前缀开头且不含问句特征的，直接丢弃
    low = text.lower()
    if any(low.startswith(p) for p in NOISE_PREFIX) or NOISE_RE.match(text):
        return ""
    return strip_automation(text)


def is_noise_assistant(text: str) -> bool:
    """助手侧的压缩摘要 / 交接语不是真实答复。"""
    low = text.strip().lower()
    return low.startswith(("summary:", "this session is being continued",
                           "please continue with the conversation"))


def ts_to_dt(ms) -> datetime:
    return datetime.fromtimestamp(ms / 1000, tz=timezone(timedelta(hours=8)))


def read_session(path: Path) -> dict:
    """解析单个会话 jsonl，返回 {title, cwd, start, end, turns:[(role, text)]}。"""
    title = None
    cwd = None
    turns = []
    first_ts = last_ts = None
    for line in path.open(encoding="utf-8", errors="replace"):
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        t = d.get("type")
        ts = d.get("timestamp")
        if isinstance(ts, (int, float)):
            first_ts = first_ts or ts
            last_ts = ts
        if t == "ai-title" and d.get("aiTitle"):
            title = d["aiTitle"]
        elif t == "session-meta":
            cwd = cwd or d.get("cwd")
        elif t == "message":
            role = d.get("role")
            if role not in ("user", "assistant"):
                continue
            parts = []
            for c in d.get("content") or []:
                if isinstance(c, dict) and c.get("type") in ("input_text", "text", "output_text"):
                    parts.append(c.get("text") or "")
            txt = "\n".join(p for p in parts if p).strip()
            if not txt:
                continue
            if role == "user":
                txt = clean_user_text(txt)
            if not txt or len(txt) < 4:
                continue
            turns.append((role, txt))
    return {
        "path": path,
        "title": title or "(无标题)",
        "cwd": cwd or "",
        "start": ts_to_dt(first_ts) if first_ts else None,
        "end": ts_to_dt(last_ts) if last_ts else None,
        "turns": turns,
    }


# 核心主题：至少要在一个核心主题上命中 2 个强关键词，才算是「讲具身智能」
# 而不是「顺手提了一句」。运维、教学、盘符清理这类会话会因此被挡在外面。
CORE_TOPICS = {
    "VLA（视觉-语言-动作）",
    "VLM（视觉语言模型）",
    "世界模型 / Real2Sim",
    "强化学习与运动控制",
    "SLAM / 三维重建",
}


def is_core(hits: Counter) -> bool:
    """核心主题上的强关键词命中总数 ≥ 2 才算具身智能会话。

    单个主题 ≥ 2 会被短会话挡住，跨主题求和更稳：比如一个会话既提
    「具身智能」又提「isaac」，主题标签可能分散在两个桶里。
    """
    return sum(hits.get(t, 0) for t in CORE_TOPICS) >= 2


# 明明沾了关键词、但主题是运维/教学/行政的会话：关键词是"顺带提的"
EXCLUDE_TITLE = re.compile(
    r"清理.*[盘區]|opencv 与 numpy|导出指定文件|AMD.*激励|生成AI课件|"
    r"CVAT 迁移|搭建三台设备摄像头|保障虚拟机",
    re.I,
)


def _hit(text: str, kw: str) -> bool:
    """英文关键词用词边界匹配，中文用子串。"""
    if kw.isascii():
        return re.search(r"(?<![a-z0-9])" + re.escape(kw) + r"(?![a-z0-9])", text) is not None
    return kw in text


def score(sess: dict) -> tuple[int, Counter]:
    """打分只看「用户提问」——用户问什么，主题就是什么。

    强关键词命中一次记 4 分，弱关键词记 1 分；同一关键词只计一次，
    避免长会话靠"提得多"把分数刷高。
    """
    user_blob = " ".join(t for r, t in sess["turns"] if r == "user").lower()
    title = sess["title"].lower()
    hits = Counter()

    strong_set = set()
    for topic, kws in TOPICS.items():
        for k in kws:
            if k in WEAK_ONLY:
                continue
            if _hit(user_blob, k) or _hit(title, k):
                strong_set.add(k)
                hits[topic] += 1

    weak_set = {k for k in WEAK_ONLY if _hit(user_blob, k) or _hit(title, k)}
    for topic, kws in TOPICS.items():
        for k in kws:
            if k in weak_set:
                hits[topic] += 0.2

    return len(strong_set) * 4 + int(len(weak_set) * 1), hits


def iter_sessions(exclude_ids=()):
    for p in sorted(PROJECTS.rglob("*.jsonl")):
        if p.stem in exclude_ids:
            continue
        try:
            yield read_session(p)
        except Exception as e:  # noqa: BLE001
            print(f"[skip] {p}: {e}", file=sys.stderr)


AUTO_WRAP = re.compile(r"^This is a scheduled automation task", re.I)
STEP_LINE = re.compile(r"^\s*\d[.、]\s")
PROCESS_LEAD = re.compile(
    r"^(?:i'll |i will |let me |let's |now |next,|looking at|first,|okay,|sure,|"
    r"i'm going to|i need to|checking|running )", re.I
)


def strip_automation(text: str) -> str:
    """定时自动化任务的开场模板不是用户的话，只留真正下达的内容。"""
    if not AUTO_WRAP.match(text.strip()):
        return text
    kept = [ln for ln in text.split("\n") if not STEP_LINE.match(ln)]
    body = "\n".join(kept).strip()
    return ("[定时自动化任务] " + body) if body else ""


def build_pairs(turns, max_pairs: int = 30):
    """把 (role, text) 序列配对成 [(user, assistant)]。

    一轮里助手可能输出多条消息（text → tool_call → text → …），过程语
    大多是 "I'll …"、"Let me …"。这里收口到该轮**最后一条有实质内容的
    回复**，它通常才是结论。
    """
    pairs = []
    cur_u = None
    bufs: list[str] = []

    def flush():
        nonlocal cur_u
        if cur_u is None:
            return
        cand = [t.strip() for t in bufs
                if len(t.strip()) >= 60 and not is_noise_assistant(t)]
        # 结论优先取末条；末条是过程语时回退到最长的一条
        a = ""
        if cand:
            a = cand[-1]
            if PROCESS_LEAD.match(a) and len(a) < 400 and len(cand) > 1:
                a = max(cand, key=len)
        pairs.append((cur_u, a))
        cur_u = None

    for role, text in turns:
        if role == "user":
            flush()
            bufs = []
            cur_u = text
        else:
            bufs.append(text)
    flush()

    # 去重（compact 摘要常把同一问题重复带入）
    seen, out = set(), []
    for u, a in pairs:
        key = re.sub(r"\s+", "", u)[:120]
        if key in seen:
            continue
        seen.add(key)
        out.append((u, a))
    return out[:max_pairs]


def slugify(title: str, fallback: str) -> str:
    # 括号必须去掉：文件名带 ( ) 会让 Markdown 链接在第一个 ) 处提前闭合
    s = re.sub(r"[\\/:*?\"<>|()\[\]\s]+", "_", title).strip("_")
    s = re.sub(r"_+", "_", s)
    return (s or fallback)[:60]


def clip(text: str, n: int) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text.strip())
    if len(text) <= n:
        return text
    cut = text[:n]
    # 尽量在段落/句子边界收口
    for sep in ("\n\n", "\n", "。", "；"):
        idx = cut.rfind(sep)
        if idx > n * 0.6:
            return cut[: idx + len(sep)] + "…（原文更长，已截断）"
    return cut + "…（原文更长，已截断）"


def dominant(hits: Counter) -> str:
    if not hits:
        return "未分类"
    return hits.most_common(1)[0][0]


def emit(keep, outdir: Path, min_score: int) -> None:
    sess_dir = outdir / "sessions"
    sess_dir.mkdir(parents=True, exist_ok=True)
    for old in sess_dir.glob("*.md"):
        old.unlink()

    index_rows = []
    for i, (sc, hits, s) in enumerate(keep, 1):
        pairs = build_pairs(s["turns"])
        if not pairs:
            continue
        date = s["start"].strftime("%Y-%m-%d") if s["start"] else "0000-00-00"
        title = scrub(s["title"]).strip() or "(无标题会话)"
        fname = f"{i:03d}_{date}_{slugify(title, 'session')}.md"
        tags = "、".join(t for t, _ in hits.most_common(3)) or "未分类"

        lines = [
            f"# {title}",
            "",
            f"| 项 | 值 |",
            f"|---|---|",
            f"| 日期 | {date} |",
            f"| 主题标签 | {tags} |",
            f"| 对话轮次 | {len(s['turns'])} |",
            f"| 收录问答 | {len(pairs)} |",
            "",
            "> 本文件由 `tools/extract_dialogues.py` 从 WorkBuddy 会话记录自动抽取。",
            "> 只保留用户提问与助手结论，已剔除工具原始输出；IP、账号、密码、token、",
            "> 本机用户名等敏感字段已脱敏。原始记录不在本仓库。",
            "",
            "---",
            "",
        ]
        for j, (u, a) in enumerate(pairs, 1):
            lines.append(f"## 第 {j} 轮")
            lines.append("")
            lines.append("**提问**")
            lines.append("")
            lines.append(clip(scrub(u), 1200))
            lines.append("")
            if a:
                lines.append("**结论**")
                lines.append("")
                lines.append(clip(scrub(a), 1600))
                lines.append("")
        (sess_dir / fname).write_text("\n".join(lines), encoding="utf-8")
        index_rows.append((i, date, title, fname, tags, len(pairs), sc))

    # ---------------- 索引 ----------------
    idx = [
        "# 具身智能对话档案索引",
        "",
        f"从 `C:\\Users\\<USER>\\.workbuddy\\projects` 的会话记录中抽取，",
        f"命中阈值 score ≥ {min_score}，共 **{len(index_rows)}** 个会话。",
        "",
        "打分口径：只看用户提问中的强关键词（VLA/VLM/Isaac/MuJoCo/世界模型/SLAM/"
        "强化学习/四足/灵巧手 等），同一关键词只计一次，避免长会话刷分。",
        "",
        "| # | 日期 | 会话 | 主要主题 | 收录问答 |",
        "|---|---|---|---|---|",
    ]
    for i, date, title, fname, tags, n, sc in index_rows:
        idx.append(f"| {i} | {date} | [{title}](sessions/{fname}) | {tags} | {n} |")
    idx.append("")
    idx.append("## 主题分布")
    idx.append("")
    cnt = Counter()
    for r in index_rows:
        for t in r[4].split("、"):
            if t:
                cnt[t] += 1
    idx.append("| 主题 | 会话数 |")
    idx.append("|---|---|")
    for t, c in cnt.most_common():
        idx.append(f"| {t} | {c} |")
    idx.append("")
    idx.append("> 说明：主题标签取每个会话命中数最高的三项；同一会话可计入多个主题。")
    (outdir / "INDEX.md").write_text("\n".join(idx), encoding="utf-8")
    print(f"[ok] 写出 {len(index_rows)} 个会话 + INDEX.md → {outdir}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan", action="store_true")
    ap.add_argument("--emit", metavar="OUTDIR")
    ap.add_argument("--min-score", type=int, default=8)
    args = ap.parse_args()

    rows = []
    # 当前这次会话不收录：它正在写本仓库，收进来会自我引用
    exclude = {"731fd88a-e323-4b06-afa1-88e8eccfbb76"}
    for s in iter_sessions(exclude):
        if not s["turns"]:
            continue
        sc, hits = score(s)
        rows.append((sc, hits, s))

    rows.sort(key=lambda r: -r[0])
    core_n = sum(1 for sc, h, _s in rows if sc >= args.min_score and is_core(h))
    print(f"总会话数（有正文）：{len(rows)}")
    print(f"命中阈值 >= {args.min_score}：{sum(1 for r in rows if r[0] >= args.min_score)}")
    print(f"其中满足核心主题条件：{core_n}")
    print("\n=== 主题 TOP15 ===")
    for sc, hits, s in rows[:15]:
        when = s["start"].strftime("%Y-%m-%d") if s["start"] else "?"
        print(f"{sc:6d}  {when}  {s['title'][:44]:<46} {dict(hits.most_common(3))}")

    if args.scan:
        return 0

    out = Path(args.emit or ".")
    out.mkdir(parents=True, exist_ok=True)
    keep = sorted(
        [(sc, hits, s) for sc, hits, s in rows
         if sc >= args.min_score and is_core(hits) and not EXCLUDE_TITLE.search(s["title"])],
        key=lambda r: (r[2]["start"] or datetime.min.replace(tzinfo=timezone.utc)),
    )
    emit(keep, out, args.min_score)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
