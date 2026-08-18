from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
TESTS = [
    ROOT / "01_smolvla_so101_engineering/tests/test_pipeline.py",
    ROOT / "02_spatial_semantic_vla_engineering/tests/test_pipeline.py",
]

for test in TESTS:
    print(f"=== {test.relative_to(ROOT)} ===")
    subprocess.run([sys.executable, str(test), "-v"], cwd=test.parents[1], check=True)
print("all VLA/VLM engineering tests passed")
