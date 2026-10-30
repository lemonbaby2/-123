# -*- coding: utf-8 -*-
"""
LingBot-VLA 2.0 部署补丁一键应用（幂等，可重复执行）
用途: 在任何新机器（GPU 服务器 / 机器人本机）部署前跑一次，抹平以下环境差异：
  1. lerobot 0.6.1 与 lingbotvla 的 API 差异（sync_bucket / hf_transform_to_torch）
  2. Windows/CPU 环境 triton 缺失（stub 包，仅保证导入；GPU 机器有真 triton 会自动跳过）
  3. 无 CUDA / 无 flash_attn 时的注意力回退（eager）与设备探测降级
  4. websockets 13.x sync API 不接受 ping_interval
用法:
  python apply_patches.py --repo E:/path/to/lingbot-vla-v2 [--venv-site-packages PATH] [--dry-run]
说明: 每处补丁执行前检查是否已应用；已应用则跳过，不会重复插入。
"""
import argparse
import json
import re
import sys
from pathlib import Path

LOG = []


def log(kind, msg):
    LOG.append((kind, msg))
    print(f"[{kind}] {msg}", flush=True)


# ---------------- 仓库补丁 ----------------

def patch_device_key(repo: Path, dry=False):
    """无 CUDA 时 group_gemm 设备探测降级（否则 import 期崩）"""
    p = repo / "lingbotvla/ops/group_gemm/utils/device.py"
    if not p.exists():
        return log("SKIP", f"not found: {p}")
    src = p.read_text(encoding="utf-8")
    if "no-CUDA env" in src or "return \"CPU\"" in src:
        return log("OK", "device.py already patched")
    src = src.replace(
        "    import torch\n\n    if torch.cuda.get_device_capability() == (8, 0):",
        "    import torch\n\n    if not torch.cuda.is_available():\n"
        "        return \"CPU\"  # local patch: no-CUDA env (CPU smoke); pretuned configs fall back\n\n"
        "    if torch.cuda.get_device_capability() == (8, 0):",
    )
    if not dry:
        p.write_text(src, encoding="utf-8")
    log("PATCH", "device.py: get_device_key -> CPU fallback")


def patch_pretuned_log(repo: Path, dry=False):
    """pretuned 日志里 torch.cuda.get_device_name() 在 CPU 上崩"""
    p = repo / "lingbotvla/ops/group_gemm/utils/pretuned.py"
    if not p.exists():
        return log("SKIP", f"not found: {p}")
    src = p.read_text(encoding="utf-8")
    if "CPU-safe device name" in src:
        return log("OK", "pretuned.py already patched")
    old = (
        "            if not envvars.is_untuned_warning_suppressed():\n"
        "                import torch\n\n"
        "                logger.debug(\n"
        "                    f\"No pre-tuned hyperparameter for kernel [{name}], using fallback config, \"\n"
        "                    \"performance may suffer. You may have triton version or device name mismatch. \"\n"
        "                    f\"You have triton=={triton.__version__} and device name [{torch.cuda.get_device_name()}]\",\n"
        "                )\n"
    )
    new = (
        "            if not envvars.is_untuned_warning_suppressed():\n"
        "                import torch\n\n"
        "                # local patch: CPU-safe device name (no CUDA on Windows CPU env)\n"
        "                try:\n"
        "                    dev_name = torch.cuda.get_device_name() if torch.cuda.is_available() else \"CPU\"\n"
        "                except Exception:\n"
        "                    dev_name = \"CPU\"\n\n"
        "                logger.debug(\n"
        "                    f\"No pre-tuned hyperparameter for kernel [{name}], using fallback config, \"\n"
        "                    \"performance may suffer. You may have triton version or device name mismatch. \"\n"
        "                    f\"You have triton=={triton.__version__} and device name [{dev_name}]\",\n"
        "                )\n"
    )
    if old not in src:
        return log("WARN", "pretuned.py pattern not matched (version drift?) — inspect manually")
    if not dry:
        p.write_text(src.replace(old, new), encoding="utf-8")
    log("PATCH", "pretuned.py: CPU-safe device name")


def patch_attn_impl(repo: Path, dry=False):
    """QwenvlWithExpertV2Model 硬编码 flash_attention_2 -> 无 flash_attn 时回退 eager"""
    p = repo / "lingbotvla/models/vla/lingbot_vla/modeling_lingbot_vla_v2.py"
    if not p.exists():
        return log("SKIP", f"not found: {p}")
    src = p.read_text(encoding="utf-8")
    if "_use_fa" in src:
        return log("OK", "modeling_lingbot_vla_v2.py already patched")
    old = (
        '        vlm_config = AutoConfig.from_pretrained(self.config.tokenizer_path)\n'
        '        if self.config.vocab_size not in (0, 257152):\n'
        '            vlm_config.text_config.vocab_size = self.config.vocab_size\n'
        '        vlm_config._attn_implementation = "flash_attention_2"\n'
        '        vlm_config.text_config._attn_implementation = "flash_attention_2"\n'
        '        vlm_config.vision_config._attn_implementation = self.config.vit_attn_implementation\n'
    )
    new = (
        '        # local patch: flash_attention_2 only when CUDA + flash_attn available; else eager (portable)\n'
        '        import importlib.util as _ilu\n'
        '        _use_fa = torch.cuda.is_available() and _ilu.find_spec("flash_attn") is not None\n'
        '        _attn_impl = "flash_attention_2" if _use_fa else "eager"\n'
        '        vlm_config = AutoConfig.from_pretrained(self.config.tokenizer_path)\n'
        '        if self.config.vocab_size not in (0, 257152):\n'
        '            vlm_config.text_config.vocab_size = self.config.vocab_size\n'
        '        vlm_config._attn_implementation = _attn_impl\n'
        '        vlm_config.text_config._attn_implementation = _attn_impl\n'
        '        vlm_config.vision_config._attn_implementation = self.config.vit_attn_implementation if _use_fa else "eager"\n'
    )
    if old not in src:
        return log("WARN", "attn patch pattern not matched — inspect manually")
    src = src.replace(old, new)
    src = src.replace(
        '        self.config.qwen_expert_config._attn_implementation = "flash_attention_2"',
        '        self.config.qwen_expert_config._attn_implementation = _attn_impl',
    )
    if not dry:
        p.write_text(src, encoding="utf-8")
    log("PATCH", "modeling_lingbot_vla_v2.py: attn impl adaptive (flash_attention_2/eager)")


def patch_ws_client(repo: Path, dry=False):
    """websockets 13.x sync connect 不接受 ping_interval/ping_timeout"""
    p = repo / "deploy/websocket_client_policy.py"
    if not p.exists():
        return log("SKIP", f"not found: {p}")
    src = p.read_text(encoding="utf-8")
    if "ping_interval=ping_interval," not in src:
        return log("OK", "websocket_client_policy.py already patched")
    old = (
        '                ping_interval = _optional_float_env("WEBSOCKET_PING_INTERVAL")\n'
        '                ping_timeout = _optional_float_env("WEBSOCKET_PING_TIMEOUT")\n'
        '                conn = websockets.sync.client.connect(\n'
        '                    self._uri,\n'
        '                    compression=None,\n'
        '                    max_size=None,\n'
        '                    additional_headers=headers,\n'
        '                    ping_interval=ping_interval,\n'
        '                    ping_timeout=ping_timeout,\n'
        '                )\n'
    )
    new = (
        '                conn = websockets.sync.client.connect(\n'
        '                    self._uri,\n'
        '                    compression=None,\n'
        '                    max_size=None,\n'
        '                    additional_headers=headers,\n'
        '                    # local patch: websockets 13.x sync API 不接受 ping_interval/ping_timeout\n'
        '                )\n'
    )
    if old not in src:
        return log("WARN", "ws client pattern not matched — inspect manually")
    if not dry:
        p.write_text(src.replace(old, new), encoding="utf-8")
    log("PATCH", "websocket_client_policy.py: drop ping args (websockets 13.x)")


def patch_cli_yaml_fallback(repo: Path, dry=False):
    """lingbotvla_cli.yaml 三级路径找不到时回退二级（避免 GPU 机器上首个报错就是 FileNotFound）"""
    p = repo / "deploy/lingbot_vla_v2_policy.py"
    if not p.exists():
        return log("SKIP", f"not found: {p}")
    src = p.read_text(encoding="utf-8")
    if "LINGBOT_CLI_YAML_FALLBACK" in src:
        return log("OK", "cli yaml fallback already patched")

    old = "        training_config_path = Path(path_to_pi_model).parent.parent.parent/'lingbotvla_cli.yaml'\n"
    new = (
        "        # local patch (LINGBOT_CLI_YAML_FALLBACK): 官方按三级上找配置；\n"
        "        # 兼容只有二级的目录布局，避免新版代码/旧目录结构不一致时报 FileNotFound\n"
        "        training_config_path = Path(path_to_pi_model).parent.parent.parent/'lingbotvla_cli.yaml'\n"
        "        if not training_config_path.is_file():\n"
        "            _alt = Path(path_to_pi_model).parent.parent/'lingbotvla_cli.yaml'\n"
        "            if _alt.is_file():\n"
        "                print(f'⚠️  cli yaml 在二级位置找到: {_alt}')\n"
        "                training_config_path = _alt\n"
        "            else:\n"
        "                raise FileNotFoundError(\n"
        "                    f'lingbotvla_cli.yaml 未找到。已查找: {training_config_path} 与 {_alt}'\n"
        "                )\n"
    )
    if old not in src:
        return log("WARN", "cli yaml path pattern not matched — inspect manually")
    if not dry:
        p.write_text(src.replace(old, new, 1), encoding="utf-8")
    log("PATCH", "lingbot_vla_v2_policy.py: cli yaml 三级/二级路径容错")


def patch_low_mem_load(repo: Path, dry=False):
    """LINGBOT_LOW_MEM=1 时分片流式加载，把主机内存峰值从 ~51GB 压到 ~13GB

    16GB 显存卡（如 RTX 5060 Ti 16G）本身够跑 6.38B bf16，但官方加载流程
    要求主机内存 ≥56GB；低内存模式让 32GB 内存的机器也能起。
    """
    p = repo / "deploy/lingbot_vla_v2_policy.py"
    if not p.exists():
        return log("SKIP", f"not found: {p}")
    src = p.read_text(encoding="utf-8")
    if "LINGBOT_LOW_MEM" in src:
        return log("OK", "low-mem streaming load already patched")

    old = (
        "        self.vla = LingBotVlaV2InferencePolicy(config, eval=True)\n"
        "\n"
        "        self.load_model_weights(path_to_pi_model, strict=True)\n"
    )
    new = (
        "        self.vla = LingBotVlaV2InferencePolicy(config, eval=True)\n"
        "\n"
        "        # local patch (LINGBOT_LOW_MEM): 分片流式加载，峰值主机内存 ~13GB 而非 ~51GB\n"
        "        if os.environ.get('LINGBOT_LOW_MEM', '0') == '1':\n"
        "            try:\n"
        "                from deploy.stream_load import stream_load_state_dict\n"
        "            except ImportError:\n"
        "                from stream_load import stream_load_state_dict\n"
        "            _layout = os.environ.get('LINGBOT_MOE_LAYOUT', 'fused')\n"
        "            print(f'[low-mem] streaming load, moe_layout={_layout}')\n"
        "            stream_load_state_dict(\n"
        "                self.vla, path_to_pi_model, strict=True, moe_layout=_layout\n"
        "            )\n"
        "        else:\n"
        "            self.load_model_weights(path_to_pi_model, strict=True)\n"
    )
    if old not in src:
        return log("WARN", "load_model_weights call site not matched — inspect manually")
    if not dry:
        src = src.replace(old, new, 1)

    # 2) 在 load_vla 之前把默认 dtype 切成 bf16（模型直接以 bf16 分配）
    old2 = (
        "        apply_lingbot_qwen3_vl_patch()\n"
        "\n"
        "        self.vla = self.load_vla(path_to_pi_model)\n"
    )
    new2 = (
        "        apply_lingbot_qwen3_vl_patch()\n"
        "\n"
        "        # local patch (LINGBOT_LOW_MEM): bf16 构建，模型内存减半（25.5GB -> 12.8GB）\n"
        "        if os.environ.get('LINGBOT_LOW_MEM', '0') == '1':\n"
        "            try:\n"
        "                from deploy.stream_load import enable_bf16_build\n"
        "            except ImportError:\n"
        "                from stream_load import enable_bf16_build\n"
        "            enable_bf16_build()\n"
        "\n"
        "        self.vla = self.load_vla(path_to_pi_model)\n"
    )
    if old2 in src:
        if not dry:
            src = src.replace(old2, new2, 1)
    else:
        log("WARN", "enable_bf16_build insertion point not matched")

    if not dry:
        p.write_text(src, encoding="utf-8")
    log("PATCH", "lingbot_vla_v2_policy.py: LINGBOT_LOW_MEM 流式加载 + bf16 构建")


def patch_mock_action_key(repo: Path, dry=False):
    """mock server 输出改为真实格式 action(chunk,7)，让 mock 测试验证真协议"""
    p = repo / "deploy/mock_policy_server.py"
    if not p.exists():
        return log("SKIP", f"not found: {p}")
    src = p.read_text(encoding="utf-8")
    if '"action": full' in src:
        return log("OK", "mock_policy_server.py already patched")
    old = (
        '        return {\n'
        '            "action.arm.position": chunk.astype(np.float32),\n'
        '            "action.effector.position": eff,\n'
        '        }\n'
    )
    new = (
        '        # 与真实 server 输出格式一致: 原始键 action(chunk,7)\n'
        '        full = np.concatenate([chunk.astype(np.float32), eff[:, None]], axis=1)\n'
        '        return {"action": full}\n'
    )
    if old not in src:
        return log("SKIP", "mock server already uses action key or pattern drift")
    if not dry:
        p.write_text(src.replace(old, new), encoding="utf-8")
    log("PATCH", "mock_policy_server.py: output action(chunk,7)")


def patch_bridge_action_parse(repo: Path, dry=False):
    """bridge 解析真实 server 输出：action(chunk,7) -> arm/effector，兼容旧拆分键"""
    p = repo / "deploy/realman_bridge.py"
    if not p.exists():
        return log("SKIP", f"not found: {p}")
    src = p.read_text(encoding="utf-8")
    if 'if "action" in act:' in src:
        return log("OK", "realman_bridge.py already patched")
    old = (
        '        arm_act = np.asarray(act["action.arm.position"], dtype=np.float64)\n'
        '        eff_act = np.asarray(act["action.effector.position"], dtype=np.float64).reshape(-1)\n'
    )
    new = (
        '        # 真实 server 输出原始键 action(chunk,7: 6关节rad+夹爪)；兼容旧拆分键\n'
        '        if "action" in act:\n'
        '            full = np.asarray(act["action"], dtype=np.float64)\n'
        '            arm_act = full[..., :6]\n'
        '            eff_act = full[..., 6:7]\n'
        '        else:\n'
        '            arm_act = np.asarray(act["action.arm.position"], dtype=np.float64)\n'
        '            eff_act = np.asarray(act["action.effector.position"], dtype=np.float64).reshape(-1)\n'
    )
    if old not in src:
        return log("WARN", "bridge parse pattern not matched — inspect manually")
    if not dry:
        p.write_text(src.replace(old, new), encoding="utf-8")
    log("PATCH", "realman_bridge.py: parse action(chunk,7)")


# ---------------- 依赖包补丁 ----------------

def patch_lerobot(sp: Path, dry=False):
    if not sp or not (sp / "lerobot").exists():
        return log("SKIP", "lerobot not found in site-packages (skip if GPU env differs)")
    changed = 0

    dm = sp / "lerobot/datasets/dataset_metadata.py"
    if dm.exists():
        src = dm.read_text(encoding="utf-8")
        if "from huggingface_hub import snapshot_download, sync_bucket" in src:
            src = src.replace(
                "from huggingface_hub import snapshot_download, sync_bucket",
                "from huggingface_hub import snapshot_download\n"
                "try:\n"
                "    from huggingface_hub import sync_bucket\n"
                "except ImportError:  # hub<1.0: bucket sync not available (not needed for local datasets)\n"
                "    sync_bucket = None",
            )
            src = src.replace(
                '        if self.repo_type == "bucket":\n            self.root.mkdir(parents=True, exist_ok=True)\n            sync_bucket(',
                '        if self.repo_type == "bucket":\n'
                '            if sync_bucket is None:\n'
                '                raise ImportError("sync_bucket requires huggingface-hub>=1.0; bucket datasets unsupported")\n'
                '            self.root.mkdir(parents=True, exist_ok=True)\n'
                '            sync_bucket(',
            )
            if not dry:
                dm.write_text(src, encoding="utf-8")
            changed += 1
            log("PATCH", "lerobot: sync_bucket optional import")

    ut = sp / "lerobot/datasets/utils.py"
    if ut.exists():
        src = ut.read_text(encoding="utf-8")
        if "def hf_transform_to_torch" not in src:
            shim = '''

# --- compat shim for lingbot-vla-v2 (hf_transform_to_torch removed in lerobot>=0.4) ---
def hf_transform_to_torch(items_dict: dict) -> dict:
    """Transform a Hugging Face dataset item dict to torch tensors (legacy lerobot API)."""
    import numpy as _np

    torch_items = {}
    for key, value in items_dict.items():
        if isinstance(value, _np.ndarray):
            if value.dtype == _np.uint16:
                value = value.astype(_np.int32)
            torch_items[key] = torch.from_numpy(value)
        elif isinstance(value, list) and len(value) > 0 and isinstance(value[0], _np.ndarray):
            torch_items[key] = [
                torch.from_numpy(v.astype(_np.int32) if v.dtype == _np.uint16 else v) for v in value
            ]
        else:
            torch_items[key] = value
    return torch_items
'''
            if not dry:
                ut.write_text(src + shim, encoding="utf-8")
            changed += 1
            log("PATCH", "lerobot: add hf_transform_to_torch shim")

    if changed == 0:
        log("OK", "lerobot already patched")


def patch_triton_stub(sp: Path, dry=False):
    """Windows/无 triton 环境：安装最小 stub（GPU 机器有真 triton 时自动跳过）"""
    if not sp:
        return log("SKIP", "no --venv-site-packages given")
    try:
        import importlib.util
        if importlib.util.find_spec("triton") is not None:
            import triton
            if not getattr(triton, "__file__", "").endswith("site-packages\\triton\\__init__.py") or "stub" not in (
                Path(triton.__file__).read_text(encoding="utf-8", errors="ignore")[:500]
            ):
                return log("OK", f"real triton present ({getattr(triton, '__version__', '?')}) — skip stub")
    except Exception:
        pass

    d = sp / "triton"
    if d.exists() and (d / "__init__.py").exists():
        return log("OK", "triton stub already installed")
    if dry:
        return log("PATCH?", "would install triton stub")

    d.mkdir(parents=True, exist_ok=True)
    (d / "__init__.py").write_text('''"""Minimal triton stub (LingBot-VLA deploy on Windows/no-triton env).
Only satisfies module-level imports; GPU kernels are never launched (moe_implementation=eager).
Do NOT use for training or fused MoE.
"""
__version__ = "3.4.0"


class Config:
    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.num_warps = kwargs.get("num_warps", 4)
        self.num_stages = kwargs.get("num_stages", 2)


class KernelInterface:
    """Stub base class for kernel wrappers."""

    def run(self, *args, **kwargs):
        raise RuntimeError("triton stub: no GPU kernel available")


def autotune(configs=None, key=None, **kwargs):
    def deco(fn):
        return fn
    return deco


def heuristics(values=None, **kwargs):
    def deco(fn):
        return fn
    return deco


def jit(fn=None, **kwargs):
    if fn is None:
        def deco(f):
            return f
        return deco
    return fn


def cdiv(a, b):
    return -(-a // b)


def next_power_of_2(n):
    return 1 << (n - 1).bit_length()


class runtime:
    class driver:
        @staticmethod
        def active():
            raise RuntimeError("triton stub: no GPU driver")


class _Placeholder:
    def __init__(self, *a, **k):
        pass

    def __call__(self, *a, **k):
        return self

    def __getattr__(self, n):
        return _Placeholder()


def __getattr__(name):
    return _Placeholder()
''', encoding="utf-8")
    (d / "language.py").write_text('''"""triton.language stub."""


class _Any:
    def __init__(self, *a, **k): pass

    def __call__(self, *a, **k): return _Any()

    def __getattr__(self, n): return _Any()


def __getattr__(name):
    return _Any()
''', encoding="utf-8")
    (d / "language").mkdir(exist_ok=True)
    (d / "language" / "__init__.py").write_text((d / "language.py").read_text(encoding="utf-8"), encoding="utf-8")
    (d / "backends").mkdir(exist_ok=True)
    (d / "backends" / "__init__.py").write_text("", encoding="utf-8")
    (d / "backends" / "compiler.py").write_text('"""triton.backends.compiler stub (no AttrsDescriptor -> torch falls back)."""\n', encoding="utf-8")
    (d / "compiler").mkdir(exist_ok=True)
    (d / "compiler" / "__init__.py").write_text("", encoding="utf-8")
    (d / "compiler" / "compiler.py").write_text('"""triton.compiler.compiler stub."""\n', encoding="utf-8")
    log("PATCH", "triton stub installed")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="lingbot-vla-v2 仓库根目录")
    ap.add_argument("--venv-site-packages", default=None, help="目标 venv 的 site-packages（可选）")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    if not (repo / "lingbotvla").exists():
        sys.exit(f"ERROR: {repo} 不是 lingbot-vla-v2 仓库根目录")
    sp = Path(args.venv_site_packages).resolve() if args.venv_site_packages else None

    print(f"repo={repo}\nsite-packages={sp}\ndry_run={args.dry_run}\n" + "-" * 60)
    patch_device_key(repo, args.dry_run)
    patch_pretuned_log(repo, args.dry_run)
    patch_attn_impl(repo, args.dry_run)
    patch_ws_client(repo, args.dry_run)
    patch_cli_yaml_fallback(repo, args.dry_run)
    patch_low_mem_load(repo, args.dry_run)
    patch_mock_action_key(repo, args.dry_run)
    patch_bridge_action_parse(repo, args.dry_run)
    patch_lerobot(sp, args.dry_run)
    patch_triton_stub(sp, args.dry_run)
    print("-" * 60)
    ok = sum(1 for k, _ in LOG if k in ("OK", "PATCH"))
    warn = [m for k, m in LOG if k == "WARN"]
    print(f"done: {ok} ok/patched, {len(warn)} warnings")
    for w in warn:
        print("  WARN:", w)


if __name__ == "__main__":
    main()
