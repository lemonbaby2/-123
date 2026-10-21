import pathlib

CR = pathlib.Path("/home/nvidia/microduck-course-run")
BAM = "/home/nvidia/.cache/uv/git-v0/checkouts/2baf9ba9fe47e195/62bd8ce"
COL = "/home/nvidia/.cache/uv/archive-v0/1jB7y7ZPFtA6jJjq"
STILTS = str(CR / "topic/02-可运行代码/microduck-playground-stilts/src")
OFFICIAL = str(CR / "topic/02-可运行代码/microduck-playground-official/src")

p = CR / "run_all.py"
s = p.read_text(encoding="utf-8")

PP_STILTS = f"'{BAM}:{STILTS}:{COL}'"
PP_OFFICIAL = f"'{BAM}:{OFFICIAL}:{COL}'"

# 01: official/src（篮球任务）
s = s.replace(
    "('01', {'MICRODUCK_RUN_BASKETBALL_SMOKE': '1', 'MICRODUCK_TRAIN_MODE': 'scratch'}, True),",
    "('01', {'MICRODUCK_RUN_BASKETBALL_SMOKE': '1', 'MICRODUCK_TRAIN_MODE': 'scratch', 'PYTHONPATH': %s}, True)," % PP_OFFICIAL,
)
# 02/03/04/06: stilts/src（既有验证路径）
for task in ("'02'", "'03'", "'04'", "'06'"):
    marker = "(%s, {}," % task
    if marker in s:
        s = s.replace(marker, "(%s, {'PYTHONPATH': %s}," % (task, PP_STILTS))
    else:
        # 03/04 已有 extra dict，插入 PYTHONPATH
        pass

# 03/04 的 extra dict 里补 PYTHONPATH（在 'MICRODUCK_WORKSPACE' 行后）
s = s.replace(
    "        'MICRODUCK_WORKSPACE': str(PLAY),\n    }, True),",
    "        'MICRODUCK_WORKSPACE': str(PLAY),\n        'PYTHONPATH': %s,\n    }, True)," % PP_STILTS,
)
p.write_text(s, encoding="utf-8")
print("PYTHONPATH patched. official count:", s.count(PP_OFFICIAL), "stilts count:", s.count(PP_STILTS))
import re
for line in s.splitlines():
    if re.match(r"\s*\('0", line):
        print(line.strip()[:150])
