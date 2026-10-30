"""验证 stream_load 的真实加载路径（零内存，meta 构建 + dry-run）

目的：在本机（无 GPU / 内存不足）确认 deploy/stream_load.py 的分片遍历、
      fused 键匹配、shape 校验、缺键检测逻辑对真实 ckpt 完全正确。
      这样在 GPU 机器上只需一次真跑，不必反复试错。

覆盖：
  [1] meta 设备构建 6.38B 模型（不分配内存）
  [2] stream_load_state_dict(dry_run=True) 走真实分片遍历
  [3] fused 布局：1708 键逐个 shape 比对
  [4] eager 布局兜底：fused→eager 自动拆分键名也逐个比对
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import torch
import yaml

REPO = Path(r"E:\研究生学习\黑客松\tmp\lingbot-vla-v2")
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "deploy"))

MODEL_PATH = Path(r"D:\lingbot_models\robotwin_ckpt\hf_ckpt\lingbot-vla-v2-6b-robotwin")
QWEN_PATH = Path(r"D:\lingbot_models\Qwen3-VL-4B-Instruct")


def build_meta_model(moe_layout: str = "fused"):
    yaml_path = MODEL_PATH.parent.parent.parent / "lingbotvla_cli.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(yaml_path)
    tc = yaml.safe_load(yaml_path.read_text())
    tm = dict(tc["model"])
    tm.update(tc["train"])
    tm["moe_implementation"] = moe_layout

    from lingbotvla.models.vla.lingbot_vla.configuration_lingbot_vla import LingbotVLAV2Config
    from lingbotvla.models.vla.lingbot_vla.qwen3vl_in_vla import apply_lingbot_qwen3_vl_patch
    from lingbotvla.models.vla.lingbot_vla.modeling_lingbot_vla_v2 import LingbotVlaV2Policy

    config = LingbotVLAV2Config(**tm)
    for k, v in tm.items():
        if not hasattr(config, k):
            setattr(config, k, v)
    config.attention_implementation = "eager"
    config.tokenizer_path = str(QWEN_PATH)
    config.use_cache = True
    apply_lingbot_qwen3_vl_patch()

    with torch.device("meta"):
        policy = LingbotVlaV2Policy(config)
    return policy, config


def main() -> int:
    t0 = time.time()
    import stream_load

    print("=" * 64)
    print("stream_load 真实加载路径验证（dry-run，零内存）")
    print("=" * 64)

    # ---------- [1] 分片完整性 ----------
    print("\n[1] 分片完整性")
    if not stream_load.verify_shards(str(MODEL_PATH)):
        print("    !! 分片损坏")
        return 2

    rc = 0
    for layout in ("fused", "eager"):
        print(f"\n{'='*64}\n[{layout}] meta 构建 + dry-run 校验")
        tm0 = time.time()
        policy, config = build_meta_model(layout)
        n = sum(p.numel() for p in policy.parameters())
        sd_keys = len(policy.state_dict())
        print(f"    模型构建 {n/1e9:.2f}B 参数 / {sd_keys} state_dict 键  "
              f"{time.time()-tm0:.0f}s")

        try:
            stats = stream_load.stream_load_state_dict(
                policy, str(MODEL_PATH), strict=True, moe_layout=layout, dry_run=True
            )
        except Exception as e:
            print(f"    ❌ 校验失败 [{layout}]: {type(e).__name__}: {e}")
            rc = 1
            del policy
            continue

        print(f"    ✅ [{layout}] 全部通过：{stats['tensors_copied']} 键 shape 逐一匹配，"
              f"{stats['shards']} 分片")

        # 反向核对：模型里是否有 ckpt 未提供的键
        expected = stream_load._expected_keys(str(MODEL_PATH))
        if expected is not None:
            if layout == "fused":
                missing = sorted(set(policy.state_dict().keys()) - expected)
                print(f"    模型有而 ckpt 无的键: {len(missing)}"
                      + (f"  例: {missing[:3]}" if missing else ""))
            else:
                print(f"    (eager 布局键名与 ckpt 不同，由 remap 覆盖，跳过反向比对)")

        del policy

    print("\n" + "=" * 64)
    print(f"总耗时 {time.time()-t0:.0f}s → {'ALL OK' if rc == 0 else 'HAS FAILURES'}")
    print("=" * 64)
    return rc


if __name__ == "__main__":
    sys.exit(main())
