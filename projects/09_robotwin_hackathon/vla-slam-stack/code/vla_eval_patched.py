import sys

from peft.tuners.tuners_utils import BaseTuner

_orig = BaseTuner.get_model_config


@staticmethod
def _patched(model, default=None):
    try:
        cfg = _orig(model)
    except Exception:
        return {}
    if cfg is None or not hasattr(cfg, "get"):
        return {}
    return cfg


BaseTuner.get_model_config = _patched

from lerobot.scripts.lerobot_eval import main

main()
