#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地 LLM 接口 (仅回环, 离线可用)

- 优先: 本地 Ollama (http://127.0.0.1:11434) —— 模型需联网时预先 pull 一次
- 兜底: 无 Ollama / 严格离线时, 用检索增强的模板合成答案 (不依赖任何外部服务)
两个分支都只走 127.0.0.1, 不触发外部网络。
"""
from __future__ import annotations
import json
import urllib.request
import urllib.error

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
DEFAULT_MODEL = "qwen2.5:7b"  # 用户联网时 `ollama pull qwen2.5:7b` 一次即可离线用


def ollama_available(model: str = DEFAULT_MODEL, timeout: int = 8) -> bool:
    try:
        req = urllib.request.Request(OLLAMA_URL, data=json.dumps(
            {"model": model, "prompt": "ping", "stream": False}).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def query_ollama(prompt: str, model: str = DEFAULT_MODEL, timeout: int = 60, temperature: float = 0.2):
    req = urllib.request.Request(OLLAMA_URL, data=json.dumps(
        {"model": model, "prompt": prompt, "stream": False,
         "options": {"temperature": temperature}}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode()).get("response", "")


def synthesize(query: str, passages: list[dict], model: str = DEFAULT_MODEL) -> tuple[str, bool]:
    """返回 (答案, 是否使用本地LLM)。passages 为 kb.search 结果。"""
    if passages and ollama_available(model):
        ctx = "\n\n".join("[%d] %s" % (i + 1, p["text"][:1200]) for i, p in enumerate(passages))
        prompt = ("你是离线部署的工业机器人 VLA agent 助手, 只能依据下面【资料】回答, "
                  "不要编造资料外的事实。\n\n【资料】\n%s\n\n【问题】%s\n\n"
                  "请给出简洁、可执行的回答, 并在末尾用『来源:N』标注依据的资料编号。") % (ctx, query)
        try:
            ans = query_ollama(prompt, model)
            if ans.strip():
                return ans.strip(), True
        except Exception:
            pass
    # 兜底: 检索增强模板 (纯本地, 无模型也能跑)
    if not passages:
        return "（知识库暂无相关条目, 已记录到待补充队列）", False
    top = passages[0]
    return ("依据资料【%s】可知：%s\n（离线检索合成, 未调用外部模型; 若有本地 Ollama 将给出更完整回答）"
            % (top.get("title") or top.get("id"), top["snippet"])), False
