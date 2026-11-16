#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
离线知识库 (纯标准库实现, 零外部依赖, 断网可用)

- 词法: ASCII 词 + 中文 bigram (CJK 字符相邻成对), 适合中英混排知识库
- 索引: 倒排 + BM25, 全部落在本地 JSON, 不联网、不下载模型
- 对外能力: ingest(目录) / add_text / search / save / load
"""
from __future__ import annotations
import json
import math
import os
import re
import unicodedata
from pathlib import Path

CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uF900-\uFAFF]")
TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def tokenize(text: str):
    """返回词元列表: ascii 小写词 + 中文 bigram。"""
    text = (text or "").lower()
    toks = list(TOKEN_RE.findall(text))
    # 中文 bigram
    cjk_runs = []
    run = []
    for ch in text:
        if CJK.match(ch):
            run.append(ch)
        else:
            if run:
                cjk_runs.append(run)
                run = []
    if run:
        cjk_runs.append(run)
    for run in cjk_runs:
        if len(run) == 1:
            toks.append(run[0])
        else:
            for i in range(len(run) - 1):
                toks.append(run[i] + run[i + 1])
    return toks


def read_text(path: Path) -> str:
    try:
        raw = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""
    # 去掉 markdown 代码块/链接噪声, 仅留可读文本
    raw = re.sub(r"```.*?```", " ", raw, flags=re.S)
    raw = re.sub(r"!?\[[^\]]*\]\([^)]*\)", " ", raw)
    raw = re.sub(r"<[^>]+>", " ", raw)
    return raw


class KB:
    def __init__(self, root: str | os.PathLike):
        self.root = Path(root)
        self.docs_path = self.root / "kb_docs.jsonl"
        self.index_path = self.root / "kb_index.json"
        self.docs: list[dict] = []          # {id, title, text, source, mtime}
        self.df: dict[str, int] = {}        # term -> doc freq
        self.tf: list[dict[str, int]] = []  # doc idx -> term counts
        self.doc_len: list[int] = []
        self.avgdl = 0.0
        self.N = 0
        self.k1 = 1.5
        self.b = 0.75

    # ---------- 持久化 ----------
    def save(self):
        self.root.mkdir(parents=True, exist_ok=True)
        with self.docs_path.open("w", encoding="utf-8") as f:
            for d in self.docs:
                f.write(json.dumps(d, ensure_ascii=False) + "\n")
        payload = {
            "df": self.df, "tf": self.tf, "doc_len": self.doc_len,
            "avgdl": self.avgdl, "N": self.N, "k1": self.k1, "b": self.b,
        }
        self.index_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def load(self):
        if self.docs_path.exists():
            self.docs = [json.loads(l) for l in self.docs_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        if self.index_path.exists():
            p = json.loads(self.index_path.read_text(encoding="utf-8"))
            self.df, self.tf, self.doc_len = p["df"], p["tf"], p["doc_len"]
            self.avgdl, self.N = p.get("avgdl", 0.0), p.get("N", 0)
            self.k1, self.b = p.get("k1", 1.5), p.get("b", 0.75)
        return self

    # ---------- 写入 ----------
    def add_text(self, doc_id: str, text: str, title: str = "", source: str = ""):
        text = (text or "").strip()
        if not text:
            return False
        # 查重: 同 id 直接覆盖
        for i, d in enumerate(self.docs):
            if d["id"] == doc_id:
                self.docs[i] = {"id": doc_id, "title": title, "text": text, "source": source,
                                "mtime": _now()}
                self._reindex_doc(i, text)
                return True
        self.docs.append({"id": doc_id, "title": title, "text": text, "source": source, "mtime": _now()})
        self._reindex_doc(len(self.docs) - 1, text)
        return True

    def ingest_dir(self, d: str | os.PathLike, exts=(".md", ".txt", ".csv", ".json", ".html")):
        d = Path(d)
        if not d.exists():
            return 0
        n = 0
        for p in sorted(d.rglob("*")):
            if p.is_file() and p.suffix.lower() in exts:
                txt = read_text(p)
                if len(txt) < 40:
                    continue
                self.add_text("doc:%s" % p.name, txt, title=p.stem, source=str(p))
                n += 1
        return n

    def _reindex_doc(self, idx, text):
        toks = tokenize(text)
        counts: dict[str, int] = {}
        for t in toks:
            counts[t] = counts.get(t, 0) + 1
        # 更新 df: 若旧索引存在先减
        if idx < len(self.tf):
            for t in self.tf[idx]:
                self.df[t] = max(0, self.df.get(t, 0) - 1)
        self.tf.append(counts) if idx >= len(self.tf) else self.tf.__setitem__(idx, counts)
        if idx >= len(self.doc_len):
            self.doc_len.append(len(toks))
        else:
            self.doc_len[idx] = len(toks)
        for t in counts:
            self.df[t] = self.df.get(t, 0) + 1
        self.N = len(self.docs)
        self.avgdl = (sum(self.doc_len) / self.N) if self.N else 0.0

    # ---------- 检索 ----------
    def search(self, query: str, topk: int = 5):
        q_toks = tokenize(query)
        if not q_toks or not self.N:
            return []
        scores = [0.0] * self.N
        for qt in set(q_toks):
            df = self.df.get(qt, 0)
            if df == 0:
                continue
            idf = math.log(1 + (self.N - df + 0.5) / (df + 0.5))
            for i in range(self.N):
                f = self.tf[i].get(qt, 0)
                if f == 0:
                    continue
                dl = self.doc_len[i] or 1
                denom = f + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1))
                scores[i] += idf * (f * (self.k1 + 1)) / denom
        ranked = sorted(range(self.N), key=lambda i: scores[i], reverse=True)[:topk]
        out = []
        for i in ranked:
            if scores[i] <= 0:
                continue
            out.append({
                "id": self.docs[i]["id"], "title": self.docs[i].get("title", ""),
                "source": self.docs[i].get("source", ""), "score": round(scores[i], 4),
                "snippet": _snippet(self.docs[i]["text"]),
                "text": self.docs[i]["text"],
            })
        return out

    def __len__(self):
        return len(self.docs)


def _snippet(text: str, n: int = 220):
    text = re.sub(r"\s+", " ", text).strip()
    return text[:n] + ("…" if len(text) > n else "")


def _now():
    import datetime as dt
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(timespec="seconds")
