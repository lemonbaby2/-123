#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
离线自主 agent 核心

一次"思考-行动"闭环:
  understand(问句) -> 检索知识库 -> 本地合成答案 -> 自我校验 -> 决策
并对外提供动作分发 (action dispatcher), 用于"自主决策与执行":
  - answer     : 基于知识库答疑 (默认)
  - daily_vla  : 触发一次 VLA 每日验收 (记录动作与结果)
  - ingest     : 吸收一份新文档到知识库
  - reconcile  : 对历史"错误"项重新核对
"""
from __future__ import annotations
import json
import datetime as dt
from pathlib import Path
from .kb import KB
from .llm import synthesize
from .verify import verify


def now_iso():
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(timespec="seconds")


class Agent:
    def __init__(self, kb: KB, model: str = "qwen2.5:7b"):
        self.kb = kb
        self.model = model

    def understand(self, query: str, topk: int = 5):
        passages = self.kb.search(query, topk=topk)
        answer, used_llm = synthesize(query, passages, self.model)
        ok, reason, score = verify(query, answer, passages)
        return {
            "query": query, "answer": answer, "used_llm": used_llm,
            "verified": ok, "verify_reason": reason, "groundedness": score,
            "passages": [{"id": p["id"], "title": p.get("title", ""),
                          "score": p["score"], "snippet": p["snippet"]} for p in passages],
            "at": now_iso(),
        }

    # ---- 动作分发: 自主决策与执行 ----
    def act(self, action: str, payload: dict | None = None):
        payload = payload or {}
        if action == "answer":
            return self.understand(payload.get("query", ""))
        if action == "daily_vla":
            return self._act_daily_vla(payload)
        if action == "ingest":
            return self._act_ingest(payload)
        if action == "reconcile":
            return {"action": "reconcile", "note": "调用 selflearn.reconcile()", "payload": payload}
        return {"action": action, "error": "unknown action"}

    def _act_daily_vla(self, payload):
        # 真实执行交给 DGX 上的 vla_accept(已在 systemd 定时器里每天跑);
        # 这里在离线 agent 侧记录"已规划动作 + 期望产物", 用于自学习记忆。
        return {
            "action": "daily_vla", "planned": True, "target": "WALL-OSS-0.5",
            "expected_artifact": "reports/<date>/report.md + curves",
            "at": now_iso(),
        }

    def _act_ingest(self, payload):
        path = payload.get("path")
        if not path:
            return {"action": "ingest", "ok": False, "reason": "no path"}
        p = Path(path)
        if p.is_dir():
            n = self.kb.ingest_dir(p)
            self.kb.save()
            return {"action": "ingest", "ok": True, "docs_added": n, "kb_size": len(self.kb)}
        if p.is_file():
            txt = p.read_text(encoding="utf-8", errors="ignore")
            ok = self.kb.add_text("doc:%s" % p.name, txt, title=p.stem, source=str(p))
            self.kb.save()
            return {"action": "ingest", "ok": ok, "kb_size": len(self.kb)}
        return {"action": "ingest", "ok": False, "reason": "path not found"}
