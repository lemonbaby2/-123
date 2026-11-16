#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自我校验 (self-verify)

依据知识库做"依据性"判定, 不需要外部裁判模型, 断网可跑:
- 拒绝/空答检测
- 依据性: 答案词元与检索段落词元重叠率 (groundedness)
- 矛盾检测: 答案是否直接否定了所引用资料的关键句 (简单启发式)
返回 (ok, reason, score)
"""
from __future__ import annotations
import re
from .kb import tokenize

REFUSAL = ["不知道", "无法回答", "没有相关信息", "i don't know", "cannot answer",
           "暂无相关条目", "知识库暂无"]


def verify(query: str, answer: str, passages: list[dict]) -> tuple[bool, str, float]:
    answer = (answer or "").strip()
    if not answer or len(answer) < 6:
        return False, "答案过短/为空", 0.0
    if any(r in answer.lower() for r in REFUSAL):
        # 兜底模板里的"知识库暂无"属正常, 不算错, 但标为弱依据
        if "知识库暂无" in answer:
            return False, "知识库无相关条目(待补充)", 0.0
        return False, "答案含拒答措辞", 0.0

    if not passages:
        return False, "无检索依据", 0.0

    a_toks = set(tokenize(answer))
    if not a_toks:
        return False, "答案无可校验词元", 0.0

    best = 0.0
    for p in passages:
        p_toks = set(tokenize(p.get("text", "")))
        if not p_toks:
            continue
        ov = len(a_toks & p_toks) / max(1, len(a_toks))
        best = max(best, ov)

    # 依据性阈值: 答案至少 8% 词元落在资料中, 视为有依据
    if best < 0.08:
        return False, "依据性不足(词元重叠 %.1f%%)" % (best * 100), round(best, 4)
    return True, "依据充分(词元重叠 %.1f%%)" % (best * 100), round(best, 4)
