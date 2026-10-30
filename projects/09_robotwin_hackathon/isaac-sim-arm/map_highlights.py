"""从主日志里解析 8 次成功放置对应的仿真步数与视频时间轴，输出剪辑任务清单。"""
import re, json, sys, os

LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "run_rgb_cube_sorter.log")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "highlights.json")

step_re = re.compile(r"\[PICK\] step=(\d+)")
succ_re = re.compile(r"SUCCESS: Sorted (\w+)\. Total: (\d+)")

# 逐行扫描：维护最近一次出现的 step，遇到 SUCCESS 就记录
records = []
last_step = 0
with open(LOG, "r", encoding="utf-8", errors="replace") as f:
    for lineno, line in enumerate(f, 1):
        m = step_re.search(line)
        if m:
            last_step = int(m.group(1))
            continue
        s = succ_re.search(line)
        if s:
            records.append({"color": s.group(1), "total": int(s.group(2)),
                            "step": last_step, "lineno": lineno})

# 视频时间轴：每 2 步写 1 帧（steps % 2 == 0），30 fps
FPS = 30
STEPS_PER_FRAME = 2
for r in records:
    r["video_t"] = r["step"] / STEPS_PER_FRAME / FPS

print(f"{'#':>2} {'颜色':<6} {'累计':>3} {'step':>7} {'视频时间':>10}")
for i, r in enumerate(records, 1):
    print(f"{i:>2} {r['color']:<6} {r['total']:>3} {r['step']:>7} {r['video_t']:>9.2f}s")

json.dump({"fps": FPS, "steps_per_frame": STEPS_PER_FRAME,
           "total_steps": 20000, "duration_s": 20000 / STEPS_PER_FRAME / FPS,
           "successes": records}, open(OUT, "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print(f"\n已写出 {OUT}")
