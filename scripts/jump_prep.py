import sys
from pathlib import Path

CODE = Path("/home/nvidia/microduck-course-run/topic/02-可运行代码/long-jump-learning")
sys.path.insert(0, str(CODE))

from jump_lesson import prepare_assets, prepare_environment

home = "/home/nvidia/microduck-course-run/jump-home"
source, model = prepare_assets(home)
print("ASSETS_OK", source, model)
python, result = prepare_environment(source, home)
print("ENV_OK", python)
print("JUMP_PREP_DONE")
