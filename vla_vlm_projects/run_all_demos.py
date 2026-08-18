from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
DEMOS = {
    "smolvla_so101": ROOT / "01_smolvla_so101_engineering/src/pipeline.py",
    "spatial_semantic_vla": ROOT / "02_spatial_semantic_vla_engineering/src/pipeline.py",
}

out = {}
for name, script in DEMOS.items():
    p = subprocess.run([sys.executable, str(script)], cwd=script.parents[1], check=True, capture_output=True, text=True)
    out[name] = json.loads(p.stdout)
print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
