"""统一接入本机 Ollama（含未来 Tailscale 远端）到所有 agent 软件。

设计原则
--------
- 只**新增**本地 provider / profile，**不改任何软件的默认模型**，避免动到
  李老师现有的官方账号与云端链路。
- 幂等：重复运行不会重复追加。
- 每次改动前自动备份到同目录 `.bak-YYYYmmdd-HHMMSS`。

用法
----
    python setup_local_models.py            # 写入
    python setup_local_models.py --verify  # 只读检查接入状态

统一端点：http://127.0.0.1:11434/v1   key: ollama
推荐模型：qwen3.5:9b-q4_K_M（tools / vision / 标准 tool_calls）
"""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import sys
import time

HOME = pathlib.Path.home()
BASE = "http://127.0.0.1:11434/v1"
MODEL = "qwen3.5:9b-q4_K_M"
ALL_MODELS = [
    "qwen3.5:9b-q4_K_M", "qwen3.5:2b-q4_K_M", "qwen2.5-coder:7b",
    "gpt-oss:20b", "deepseek-r1:14b", "deepseek-r1:70b", "qwen2.5vl:7b",
]

FILES = {
    "hermes": HOME / "AppData/Local/hermes/config.yaml",
    "codex": HOME / ".codex/config.toml",
    "opencode": HOME / ".config/opencode/opencode.json",
    "continue": HOME / ".continue/config.yaml",
}

MARKERS = {
    "hermes": None,
    "codex": "[model_providers.ollama-local]",
    "opencode": None,
    "continue": "qwen3.5:9b-q4_K_M",
}


def backup(p: pathlib.Path) -> str:
    dst = p.with_suffix(p.suffix + f".bak-{time.strftime('%Y%m%d-%H%M%S')}")
    shutil.copy2(p, dst)
    return dst.name


def setup_hermes(p: pathlib.Path, verify: bool) -> str:
    text = p.read_text(encoding="utf-8")
    if "deepseek-r1:14b" in text and 'provider: custom:ollama-local' in text:
        return "OK 已接入（无需改动）"
    if verify:
        return "MISS 仍待接入"
    backup(p)
    # 1) 补全 ollama-local 的模型清单
    old = """    models:
      - qwen3.5:9b-q4_K_M
      - qwen3.5:2b-q4_K_M
      - gpt-oss:20b"""
    new = """    models:
""" + "\n".join(f"      - {m}" for m in ALL_MODELS)
    if old in text:
        text = text.replace(old, new, 1)
    # 2) 本地模型作为第一兜底（云端全挂时 agent 仍能启动）
    fb = """fallback_model:
  - provider: custom:coreapi"""
    if fb in text:
        text = text.replace(
            fb,
            "fallback_model:\n"
            "  - provider: custom:ollama-local\n"
            f"    model: {MODEL}\n"
            "  - provider: custom:coreapi",
            1,
        )
    p.write_text(text, encoding="utf-8")
    return "OK 已写入（模型清单 + 本地兜底，默认模型未动）"


def setup_codex(p: pathlib.Path, verify: bool) -> str:
    text = p.read_text(encoding="utf-8")
    if MARKERS["codex"] in text:
        return "OK 已接入（无需改动）"
    if verify:
        return "MISS 仍待接入"
    backup(p)
    block = f'''

# --- 本地 Ollama（由 setup_local_models.py 追加；不改默认 provider） ---
[model_providers.ollama-local]
name = "Ollama Local"
base_url = "{BASE}"
wire_api = "chat"
env_key = "OLLAMA_API_KEY"
requires_openai_auth = false

[profiles.ollama-local]
model_provider = "ollama-local"
model = "{MODEL}"
'''
    p.write_text(text.rstrip() + block, encoding="utf-8")
    return "OK 已写入（新增 provider + profile：codex --profile ollama-local）"


def setup_opencode(p: pathlib.Path, verify: bool) -> str:
    cfg = json.loads(p.read_text(encoding="utf-8"))
    providers = cfg.setdefault("provider", {})
    if "ollama-local" in providers:
        return "OK 已接入（无需改动）"
    if verify:
        return "MISS 仍待接入"
    backup(p)
    providers["ollama-local"] = {
        "name": "Ollama Local (本机)",
        "npm": "@ai-sdk/openai-compatible",
        "options": {"apiKey": "ollama", "baseURL": BASE},
        "models": {m: {"name": m} for m in ALL_MODELS},
    }
    p.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return "OK 已写入（默认模型未动）"


def setup_continue(p: pathlib.Path, verify: bool) -> str:
    text = p.read_text(encoding="utf-8")
    if MARKERS["continue"] in text:
        return "OK 已接入（无需改动）"
    if verify:
        return "MISS 仍待接入"
    backup(p)
    entry = (
        "  - name: Ollama qwen3.5 9B (本机)\n"
        "    provider: ollama\n"
        f"    model: {MODEL}\n"
        "    apiBase: http://127.0.0.1:11434\n"
    )
    if "models: []" in text:
        text = text.replace("models: []", "models:\n" + entry.rstrip(), 1)
    else:
        text = text.rstrip() + "\n" + entry
    p.write_text(text, encoding="utf-8")
    return "OK 已写入（新增一条 ollama model）"


HANDLERS = {
    "hermes": setup_hermes,
    "codex": setup_codex,
    "opencode": setup_opencode,
    "continue": setup_continue,
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true", help="只读检查")
    args = ap.parse_args()

    print(f"统一端点: {BASE}   推荐模型: {MODEL}")
    print("-" * 72)
    for name, path in FILES.items():
        if not path.exists():
            print(f"{name:10s} SKIP  配置文件不存在: {path}")
            continue
        try:
            print(f"{name:10s} {HANDLERS[name](path, args.verify)}")
        except Exception as exc:
            print(f"{name:10s} FAIL  {type(exc).__name__}: {exc}")
    print("-" * 72)
    print("Claude Code / Cline / Copilot 需 Anthropic 协议网关，本机未装 litellm")
    print("或 claude-code-router，未自动改动；见交付说明。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
