import json
import pathlib

CR = pathlib.Path("/home/nvidia/microduck-course-run")
OFFICIAL = CR / "topic/02-可运行代码/microduck-playground-official"
ARTIFACTS = CR / "artifacts"
CONVERTED = CR / "converted"

# --- 1) run_all.py: 注入新环境变量 + 打开 01/05 训练开关 ---
p = CR / "run_all.py"
s = p.read_text(encoding="utf-8")

inject = (
    "    'MICRODUCK_OFFICIAL_ROOT': '%s',\n"
    "    'MICRODUCK_BASKETBALL_ARTIFACT_ROOT': '%s',\n"
    "    'MOTRIX_ROOT': '%s',\n"
    "    'MOTRIX_PYTHON': '%s',\n"
    "    'MICRODUCK_JUMP_HOME': '%s',\n"
    "    'MICRODUCK_GPU_LADDER_CLIMBER': '%s',\n"
    "    'MICRODUCK_GPU_LADDER_GETUP': '%s',\n"
    "    'LIGHTNAV_ROOT': '%s',\n"
    "    'LIGHTNAV_MODEL_ENV': '%s',\n"
    "    'LIGHTNAV_MODEL_PATH': '%s',\n"
    "    'LIGHTNAV_ROBOT_MODEL': '%s',\n"
    "    'LIGHTNAV_WALKING_POLICY': '%s',\n"
    "    'LIGHTNAV_OUTPUT': '%s',\n"
) % (
    str(OFFICIAL),
    str(ARTIFACTS / "basketball"),
    str(CR / "topic/02-可运行代码/MotrixLab"),
    str(CR / "topic/02-可运行代码/MotrixLab/.venv/bin/python"),
    str(CR / "jump-home"),
    str(CONVERTED / "official_ladder_climber.opset11.onnx"),
    str(CONVERTED / "official_ladder_getup.opset11.onnx"),
    "/home/nvidia/LightNav-0",
    str(CR / "envs/lightnav-0"),
    str(CR / "checkpoints/LightNav-0"),
    "/home/nvidia/workspaces/microduck_rl/src/mjlab_microduck/robot/microduck/robot_allcollisions.xml",
    str(CR / "checkpoints/microduck-navigation/alpha_walking.onnx"),
    str(CR / "recordings/lightnav"),
)

anchor = "    'MICRODUCK_MODEL_ROOT': '/home/nvidia/microduck-course-run',\n}"
assert anchor in s, "anchor not found"
s = s.replace(anchor, "    'MICRODUCK_MODEL_ROOT': '/home/nvidia/microduck-course-run',\n" + inject + "}")

# 01/05 打开训练开关（失败可回退预训练）
s = s.replace("('01', {'MICRODUCK_RUN_BASKETBALL_SMOKE': '1'}, False),",
              "('01', {'MICRODUCK_RUN_BASKETBALL_SMOKE': '1', 'MICRODUCK_TRAIN_MODE': 'scratch'}, True),")
s = s.replace("('05', {'MICRODUCK_RUN_FASTSAC_SMOKE': '1'}, False),",
              "('05', {'MICRODUCK_RUN_FASTSAC_SMOKE': '1', 'MICRODUCK_TRAIN_MODE': 'scratch'}, True),")
p.write_text(s, encoding="utf-8")
print("run_all.py patched:",
      "MICRODUCK_OFFICIAL_ROOT" in s,
      "MICRODUCK_RUN_BASKETBALL_SMOKE': '1', 'MICRODUCK_TRAIN_MODE': 'scratch'}, True" in s,
      "MICRODUCK_RUN_FASTSAC_SMOKE': '1', 'MICRODUCK_TRAIN_MODE': 'scratch'}, True" in s)

# --- 2) nb06: 硬编码 official-root 改成本地路径 ---
nb6 = CR / "topic/03-Notebook/06_梯面攀爬_接触与部署模板.ipynb"
nb = json.loads(nb6.read_text(encoding="utf-8"))
old = "/home/ubuntu/workspaces/microduck-playground-official/experiments/desk-climb"
new = str(OFFICIAL / "experiments/desk-climb")
hits = 0
for cell in nb["cells"]:
    src = "".join(cell["source"])
    if old in src:
        cell["source"] = [line.replace(old, new) for line in cell["source"]]
        hits += 1
nb6.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print("nb06 official-root patched cells:", hits)

# --- 3) converted 软链：getup onnx ---
CONVERTED.mkdir(parents=True, exist_ok=True)
getup_src = ARTIFACTS / "climb/models/getup.onnx"
getup_dst = CONVERTED / "official_ladder_getup.opset11.onnx"
if getup_src.is_file():
    if getup_dst.is_symlink() or getup_dst.exists():
        getup_dst.unlink()
    getup_dst.symlink_to(getup_src)
    print("getup symlink:", getup_dst, "->", getup_src)
bb = CONVERTED / "basketball.opset11.onnx"
print("basketball.opset11.onnx exists:", bb.is_file(), "->", (bb.resolve() if bb.is_symlink() else ""))
climber = CONVERTED / "official_ladder_climber.opset11.onnx"
print("climber.opset11.onnx exists:", climber.is_file())
print("PATCH_DONE")
