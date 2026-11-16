#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
离线自学习引擎 (Action 试错 + 对错分流记忆 + 满一月精确后上线)

每天内测窗口 (默认 20h) 内, 让 agent 对任务库做"试错-校验-记忆":
  - 正确 (verify ok)  -> memory/verified.jsonl   (固化回知识库记忆)
  - 错误 (verify fail) -> memory/recheck.jsonl    (标记原因, 等待复核)
  - reconcile(): 对 recheck 项基于已增长的知识库重新核对, 通过则转正

门控 (launch gate): 满 30 天 且 精确率>=0.90 且 知识库规模达标 -> 标记 go_live。
所有逻辑纯本地, 不联网。
"""
from __future__ import annotations
import json
import datetime as dt
from pathlib import Path

MEM = Path(__file__).resolve().parent.parent / "memory"
DAILY_BUDGET_S = 20 * 3600          # 每天内测 20 小时
GO_LIVE_DAYS = 30
GO_LIVE_PRECISION = 0.90
GO_LIVE_KB = 200                    # 知识库词表规模下限(唯一索引词元数, 非文档数)


def today():
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime("%Y-%m-%d")


def _load_state():
    p = MEM / "state.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"day": 0, "date": "", "seconds_today": 0, "total_seconds": 0,
            "iterations": 0, "correct": 0, "wrong": 0, "go_live": False,
            "last_task_idx": 0}


def _save_state(s):
    MEM.mkdir(parents=True, exist_ok=True)
    (MEM / "state.json").write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")


def _append(path_name, record):
    MEM.mkdir(parents=True, exist_ok=True)
    with (MEM / path_name).open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_tasks(path: str | Path):
    p = Path(path)
    if not p.exists():
        return []
    tasks = []
    if p.suffix == ".jsonl":
        for ln in p.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                try:
                    d = json.loads(ln)
                    tasks.append(d.get("query") or d.get("text") or d.get("q") or "")
                except Exception:
                    tasks.append(ln.strip())
    elif p.suffix == ".json":
        d = json.loads(p.read_text(encoding="utf-8"))
        tasks = [x.get("query") or x.get("text") or "" for x in d]
    else:
        tasks = [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return [t for t in tasks if t]


def run(agent, tasks: list[str], budget_seconds: int = DAILY_BUDGET_S, topk: int = 5):
    """执行一个内测窗口。返回本窗口统计。"""
    s = _load_state()
    if s["date"] != today():
        s["day"] += 1
        s["date"] = today()
        s["seconds_today"] = 0
    start = dt.datetime.now()
    idx = s["last_task_idx"]
    n = len(tasks)
    window = {"processed": 0, "correct": 0, "wrong": 0, "start": start.isoformat(), "elapsed_s": 0}
    while (dt.datetime.now() - start).total_seconds() < budget_seconds:
        if n == 0:
            break
        q = tasks[idx % n]
        idx += 1
        t0 = dt.datetime.now()
        res = agent.understand(q, topk=topk)
        dt_s = (dt.datetime.now() - t0).total_seconds()
        s["seconds_today"] += dt_s
        s["total_seconds"] += dt_s
        s["iterations"] += 1
        window["processed"] += 1
        rec = {"query": q, "at": res["at"], "verified": res["verified"],
               "verify_reason": res["verify_reason"], "groundedness": res["groundedness"],
               "used_llm": res["used_llm"], "answer": res["answer"][:400]}
        if res["verified"]:
            s["correct"] += 1
            window["correct"] += 1
            _append("verified.jsonl", rec)
        else:
            s["wrong"] += 1
            window["wrong"] += 1
            _append("recheck.jsonl", rec)
    s["last_task_idx"] = idx
    _save_state(s)
    window["elapsed_s"] = round((dt.datetime.now() - start).total_seconds(), 1)
    window["day"] = s["day"]
    window["total_iterations"] = s["iterations"]
    window["correct_total"] = s["correct"]
    window["wrong_total"] = s["wrong"]
    # kb_size 用"索引词表规模"(唯一词元数), 反映知识覆盖广度; 7 篇富文档即可轻松 >200
    window["go_live"] = _gate(s, kb_size=len(agent.kb.df))
    return window


def reconcile(agent, topk: int = 5, max_items: int = 200):
    """对 recheck 项基于已增长的知识库重新核对, 通过则转正。"""
    p = MEM / "recheck.jsonl"
    if not p.exists():
        return {"promoted": 0, "remaining": 0}
    kept = []
    promoted = 0
    for ln in p.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        rec = json.loads(ln)
        res = agent.understand(rec["query"], topk=topk)
        if res["verified"]:
            promoted += 1
            _append("verified.jsonl", {**rec, "promoted_at": res["at"],
                                       "corrected_answer": res["answer"][:400]})
        else:
            kept.append(ln)
    (MEM / "recheck.jsonl").write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
    return {"promoted": promoted, "remaining": len(kept)}


def _gate(s, kb_size: int):
    total = s["correct"] + s["wrong"]
    prec = (s["correct"] / total) if total else 0.0
    return bool(s["day"] >= GO_LIVE_DAYS and prec >= GO_LIVE_PRECISION and kb_size >= GO_LIVE_KB)


def status(kb=None):
    s = _load_state()
    total = s["correct"] + s["wrong"]
    prec = (s["correct"] / total) if total else 0.0
    kb_size = len(kb.df) if kb is not None else 0
    return {"day": s["day"], "iterations": s["iterations"],
            "correct": s["correct"], "wrong": s["wrong"],
            "precision": round(prec, 4),
            "go_live": _gate(s, kb_size=kb_size) or s["go_live"],
            "gate_requirement": {"days>=%d" % GO_LIVE_DAYS: s["day"] >= GO_LIVE_DAYS,
                                "precision>=%.2f" % GO_LIVE_PRECISION: prec >= GO_LIVE_PRECISION,
                                "kb_terms>=%d" % GO_LIVE_KB: kb_size >= GO_LIVE_KB}}
