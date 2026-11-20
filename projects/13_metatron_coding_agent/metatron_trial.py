"""Metatron (arXiv:2610.38027) 方案的**可复现部分**在本机的完整试跑。

论文结构：
    frozen generative whole-body base policy  +  programmable "skill" layer
    skill = 普通代码，由 coding agent 依据仿真数据迭代改写

公开状态：NVIDIA 未发布 base policy 权重 / 训练代码 / MoCap 数据，
所以这里用一个**冻结的 PD 全身执行层替身**，完整复现论文的工作流：
    Coding Agent 写 skill 代码 -> MuJoCo 仿真验证 -> 打分/失败归因 -> 反馈迭代

Coding Agent 走 setup_local_models.py 建立的本地端点（无外网、无云端费用）。

用法：
    python metatron_trial.py --smoke              # 只验证物理引擎
    python metatron_trial.py --rounds 3           # 完整跑 3 轮迭代
    python metatron_trial.py --rounds 3 --task hurdle
"""
from __future__ import annotations

import argparse
import ast
import json
import math
import pathlib
import sys
import time
import urllib.request

# 复用统一接入脚本里的端点常量（不改动它）
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "agent_model_setup"))
try:
    from setup_local_models import BASE as OLLAMA_BASE, MODEL as DEFAULT_MODEL  # noqa
except Exception:
    OLLAMA_BASE, DEFAULT_MODEL = "http://127.0.0.1:11434/v1", "qwen3.5:9b-q4_K_M"

CODER_MODEL = "qwen2.5-coder:7b"   # 无 thinking、裁决/短代码输出稳定
HERE = pathlib.Path(__file__).parent
RESULTS = HERE / "results.json"

XML = """
<mujoco model="planar_biped">
  <option timestep="0.005" gravity="0 0 -9.81" integrator="RK4"/>
  <compiler angle="radian"/>
  <worldbody>
    <geom name="ground" type="plane" size="30 30 0.1" rgba="0.85 0.85 0.85 1"/>
    <geom name="hurdle" type="box" pos="1.3 0 0.075" size="0.07 0.6 0.075" rgba="0.9 0.2 0.2 1"/>
    <body name="torso" pos="0 0 1.05">
      <joint name="root_x" type="slide" axis="1 0 0"/>
      <joint name="root_z" type="slide" axis="0 0 1"/>
      <joint name="root_pitch" type="hinge" axis="0 1 0" limited="true" range="-1.0 1.0"/>
      <geom type="box" size="0.13 0.16 0.24" mass="12" contype="0" conaffinity="0" rgba="0.2 0.45 0.9 1"/>
      <body name="lthigh" pos="0 0.09 -0.22">
        <joint name="lhip" type="hinge" axis="0 1 0" limited="true" range="-1.3 1.3"/>
        <geom type="capsule" fromto="0 0 0 0 0 -0.40" size="0.045" mass="2"/>
        <body name="lshin" pos="0 0 -0.40">
          <joint name="lknee" type="hinge" axis="0 1 0" limited="true" range="0 1.7"/>
          <geom type="capsule" fromto="0 0 0 0 0 -0.38" size="0.04" mass="1.5"/>
          <geom name="lfoot" type="box" pos="0 0 -0.38" size="0.11 0.06 0.03"/>
        </body>
      </body>
      <body name="rthigh" pos="0 -0.09 -0.22">
        <joint name="rhip" type="hinge" axis="0 1 0" limited="true" range="-1.3 1.3"/>
        <geom type="capsule" fromto="0 0 0 0 0 -0.40" size="0.045" mass="2"/>
        <body name="rshin" pos="0 0 -0.40">
          <joint name="rknee" type="hinge" axis="0 1 0" limited="true" range="0 1.7"/>
          <geom type="capsule" fromto="0 0 0 0 0 -0.38" size="0.04" mass="1.5"/>
          <geom name="rfoot" type="box" pos="0 0 -0.38" size="0.11 0.06 0.03"/>
        </body>
      </body>
    </body>
  </worldbody>
  <actuator>
    <motor joint="root_pitch" gear="60" ctrllimited="true" ctrlrange="-1 1"/>
    <motor joint="lhip"  gear="70" ctrllimited="true" ctrlrange="-1 1"/>
    <motor joint="lknee" gear="70" ctrllimited="true" ctrlrange="-1 1"/>
    <motor joint="rhip"  gear="70" ctrllimited="true" ctrlrange="-1 1"/>
    <motor joint="rknee" gear="70" ctrllimited="true" ctrlrange="-1 1"/>
  </actuator>
</mujoco>
"""

JOINTS = ["root_pitch", "lhip", "lknee", "rhip", "rknee"]
TORSO_Z0 = 1.05  # qpos[1] 是 root_z 相对偏移，绝对高度 = TORSO_Z0 + qpos[1]
KP = {"root_pitch": 90.0, "lhip": 45.0, "lknee": 45.0, "rhip": 45.0, "rknee": 45.0}
KD = {"root_pitch": 12.0, "lhip": 4.0, "lknee": 4.0, "rhip": 4.0, "rknee": 4.0}


class FrozenExecutionLayer:
    """模拟论文里冻结的 base policy：把 prompt 翻译成关节指令。不可训练。"""

    def __init__(self):
        import mujoco
        self.m = mujoco.MjModel.from_xml_string(XML)
        self.d = mujoco.MjData(self.m)
        self.qadr = {j: self.m.jnt_qposadr[self.m.joint(j).id] for j in JOINTS}
        self.vadr = {j: self.m.jnt_dofadr[self.m.joint(j).id] for j in JOINTS}

    def reset(self, task: str):
        import mujoco
        mujoco.mj_resetData(self.m, self.d)
        if task == "walk":
            # 移除栏架：移到远处
            self.m.geom_pos[self.m.geom("hurdle").id][0] = 100.0
        else:
            self.m.geom_pos[self.m.geom("hurdle").id][0] = 1.3
        mujoco.mj_forward(self.m, self.d)

    def step(self, prompt: dict) -> None:
        """prompt = skill 层给出的高层目标；执行层负责平衡与关节协调。"""
        import mujoco
        vx = float(prompt.get("vx", 0.6))
        stride = float(prompt.get("stride", 0.5))
        lift = float(prompt.get("lift", 0.35))
        phase = float(prompt.get("phase", 0.0))
        bias = float(prompt.get("phase_bias", 0.0))

        phase = (phase + bias) % (2 * math.pi)
        target = {
            "root_pitch": float(prompt.get("torso_pitch", 0.0)),
            "lhip": stride * math.sin(phase),
            "lknee": lift * max(0.0, math.sin(phase + math.pi / 2)),
            "rhip": stride * math.sin(phase + math.pi),
            "rknee": lift * max(0.0, math.sin(phase + 3 * math.pi / 2)),
        }
        # vx 只影响步频（执行层把速度命令转成相位推进）
        self._phase_speed = max(1.0, min(14.0, 6.0 * vx))

        for i, j in enumerate(JOINTS):
            q = self.d.qpos[self.qadr[j]]
            v = self.d.qvel[self.vadr[j]]
            torque = KP[j] * (target[j] - q) - KD[j] * v
            self.d.ctrl[i] = max(-1.0, min(1.0, torque / 80.0))
        mujoco.mj_step(self.m, self.d)


# ---------------------------------------------------------------- skill 代码安全校验
ALLOWED_NODES = (
    ast.Module, ast.FunctionDef, ast.arguments, ast.arg, ast.Return, ast.Assign,
    ast.AugAssign, ast.Name, ast.Load, ast.Store, ast.Constant, ast.BinOp,
    ast.UnaryOp, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow,
    ast.USub, ast.UAdd, ast.Call, ast.If, ast.Compare, ast.BoolOp, ast.And,
    ast.Or, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Dict,
    ast.Subscript, ast.Tuple, ast.List, ast.Expr, ast.Not, ast.Invert, ast.IfExp,
    ast.Attribute, ast.Slice,
)


def compile_skill(code: str):
    """只允许纯函数、无 import / while / 属性访问，避免本地模型生成危险代码。"""
    tree = ast.parse(code)
    for node in ast.walk(tree):
        if not isinstance(node, ALLOWED_NODES):
            raise ValueError(f"不允许的语法节点: {type(node).__name__}")
    fn = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "skill"]
    if not fn:
        raise ValueError("未找到 def skill(state, t, dt)")
    ns = {
        "__builtins__": {"abs": abs, "min": min, "max": max, "float": float,
                         "int": int, "len": len, "range": range},
        "math": math, "sin": math.sin, "cos": math.cos, "pi": math.pi,
        "max": max, "min": min, "abs": abs,
    }
    exec(compile(tree, "<skill>", "exec"), ns)  # noqa: S102 - AST 白名单已过滤
    return ns["skill"]


def extract_code(text: str) -> str:
    if "```" in text:
        for block in text.split("```")[1::2]:
            b = block.strip()
            if b.startswith("python"):
                b = b[6:].strip()
            if "def skill" in b:
                return b
    i = text.find("def skill")
    return text[i:] if i >= 0 else text


# ---------------------------------------------------------------- 仿真评估
def evaluate(skill, task: str, episodes: int = 3, seconds: float = 6.0) -> dict:
    layer = FrozenExecutionLayer()
    dt = layer.m.opt.timestep
    steps = int(seconds / dt)
    runs = []

    for ep in range(episodes):
        layer.reset(task)
        phase = 0.0
        start_x = float(layer.d.qpos[0])
        max_x = start_x
        fell = False
        cleared = False
        min_height = 10.0
        for k in range(steps):
            t = k * dt
            x = float(layer.d.qpos[0])
            z = TORSO_Z0 + float(layer.d.qpos[1])
            pitch = float(layer.d.qpos[2])
            state = {"x": x, "z": z, "pitch": pitch, "vx": float(layer.d.qvel[0]),
                     "t": t, "hurdle_x": 1.3 if task == "hurdle" else 1e9,
                     "dist_to_hurdle": (1.3 - x) if task == "hurdle" else 1e9}
            try:
                out = skill(state, t, dt) or {}
            except Exception:
                out = {}
            # skill 输出的是 prompt；执行层的相位由速度推进，skill 可加 bias
            prompt = dict(out)
            prompt.setdefault("vx", 0.6)
            prompt.setdefault("stride", 0.5)
            prompt.setdefault("lift", 0.35)
            prompt.setdefault("phase_bias", 0.0)
            prompt["phase"] = phase
            layer.step(prompt)
            phase += layer._phase_speed * dt
            max_x = max(max_x, float(layer.d.qpos[0]))
            min_height = min(min_height, TORSO_Z0 + float(layer.d.qpos[1]))
            if abs(float(layer.d.qpos[2])) > 0.7 or (TORSO_Z0 + float(layer.d.qpos[1])) < 0.55:
                fell = True
                break
            if task == "hurdle" and float(layer.d.qpos[0]) > 1.55 and not fell:
                cleared = True
        runs.append({
            "distance": round(max_x - start_x, 3),
            "fell": fell,
            "cleared": cleared,
            "min_z": round(min_height, 3),
            "fail_x": round(float(layer.d.qpos[0]), 3),
            "fail_dist_to_hurdle": round(1.3 - float(layer.d.qpos[0]), 3)
                                  if task == "hurdle" else None,
        })

    dist = sum(r["distance"] for r in runs) / len(runs)
    fall_rate = sum(r["fell"] for r in runs) / len(runs)
    clear_rate = sum(r["cleared"] for r in runs) / len(runs)
    score = dist - 2.0 * fall_rate + (3.0 * clear_rate if task == "hurdle" else 0.0)
    return {"score": round(score, 3), "distance": round(dist, 3),
            "fall_rate": round(fall_rate, 3), "clear_rate": round(clear_rate, 3),
            "runs": runs}


BASE_SKILL = '''def skill(state, t, dt):
    """基线：固定步态 prompt，不使用任何状态反馈。"""
    return {"vx": 0.6, "stride": 0.5, "lift": 0.35, "phase_bias": 0.0,
            "torso_pitch": 0.0}
'''


def ask_coder(prev_code: str, metrics: dict, task: str, feedback: str,
              model: str = CODER_MODEL, base: str = OLLAMA_BASE,
              api_key: str = "ollama") -> str:
    sys_prompt = (
        "You are a robot skill programmer. You write ordinary Python code that "
        "maps robot state to a high-level motion prompt for a FROZEN whole-body "
        "controller. Output ONLY a Python function, no explanation.\n\n"
        "Signature: def skill(state, t, dt) -> dict\n"
        "state keys: x (forward pos, m), z (torso height, m), pitch (rad), vx, "
        "t, hurdle_x, dist_to_hurdle.\n"
        "Return dict keys: vx (0.2..1.2), stride (0.1..1.0), lift (0.1..1.2), "
        "phase_bias (-3.14..3.14), torso_pitch (-0.3..0.3).\n"
        "The frozen execution layer handles balance and joint coordination. "
        "Your code only decides high-level intent. No imports, no classes, no "
        "loops, no attributes other than state[...] and math.*.\n"
        "Keep it compact (<= 25 lines)."
    )
    usr = (
        f"Task: {task}. Previous skill code:\n```python\n{prev_code}\n```\n"
        f"Simulation result: {json.dumps(metrics, ensure_ascii=False)}\n"
        f"Failure analysis: {feedback}\n"
        "Rewrite the skill to improve the score. Output ONLY the complete "
        "function definition."
    )
    body = json.dumps({
        "model": model, "temperature": 0.2, "max_tokens": 700,
        "stream": False,
        "messages": [{"role": "system", "content": sys_prompt},
                     {"role": "user", "content": usr}],
    }).encode()
    req = urllib.request.Request(
        base.rstrip("/") + "/chat/completions", data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {api_key}"})
    with urllib.request.urlopen(req, timeout=240) as r:
        d = json.loads(r.read().decode("utf-8", "ignore"))
    return d["choices"][0]["message"]["content"]


def feedback_of(m: dict, task: str) -> str:
    bits = [f"score={m['score']}, 前进 {m['distance']}m, 跌倒率 {m['fall_rate']}"]
    if task == "hurdle" and m["clear_rate"] < 1.0:
        bits.append("未能越过 x=1.3m 的 0.15m 栏架；需在接近栏架时提高 lift 并调整相位")
    if m["fall_rate"] > 0:
        bits.append("躯干倾角超 0.7rad 或高度掉到 0.35m 以下，需减小 stride / 调整 torso_pitch")
    if m["distance"] < 2.0:
        bits.append("前进距离不足，可提高 vx 或增大 stride")
    tr = m["runs"][0]
    bits.append(
        f"运动轨迹: 跌倒/终止于 x={tr['fail_x']}m, "
        f"距栏 {tr['fail_dist_to_hurdle']}m, 最低躯干高度 {tr['min_z']}m; "
        "注意 lift 只影响屈膝幅度，stride 影响摆腿幅度，vx 影响步频")
    return "；".join(bits)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--task", choices=["walk", "hurdle"], default="hurdle")
    ap.add_argument("--episodes", type=int, default=3)
    ap.add_argument("--coder-model", default=CODER_MODEL)
    ap.add_argument("--coder-base", default=OLLAMA_BASE)
    ap.add_argument("--coder-key", default="ollama")
    ap.add_argument("--tag", default="local")
    args = ap.parse_args()

    if args.smoke:
        import mujoco
        layer = FrozenExecutionLayer()
        layer.reset("hurdle")
        for i in range(200):
            layer.step({"vx": 0.6, "stride": 0.5, "lift": 0.35,
                        "phase": i * 0.03, "phase_bias": 0.0})
        print("SMOKE OK | mujoco", mujoco.__version__,
              "| x=", round(float(layer.d.qpos[0]), 3),
              "z=", round(float(layer.d.qpos[1]), 3),
              "| nq=", layer.m.nq, "nu=", layer.m.nu)
        return 0

    print(f"端点={args.coder_base}  Coding Agent={args.coder_model}  任务={args.task}")
    print("-" * 74)
    history = []
    code = BASE_SKILL
    fn = compile_skill(code)
    m = evaluate(fn, args.task, args.episodes)
    print(f"R0 基线    score={m['score']:<7} dist={m['distance']:<6} "
          f"fall={m['fall_rate']:<5} clear={m['clear_rate']}")
    history.append({"round": 0, "source": "baseline", "code": code, "metrics": m})

    for rnd in range(1, args.rounds + 1):
        fb = feedback_of(m, args.task)
        t0 = time.time()
        try:
            raw = ask_coder(code, m, args.task, fb, args.coder_model,
                            args.coder_base, args.coder_key)
            cand = extract_code(raw)
            fn2 = compile_skill(cand)
            m2 = evaluate(fn2, args.task, args.episodes)
            verdict = "ACCEPT" if m2["score"] > m["score"] else "REJECT"
            print(f"R{rnd} {verdict:<6} score={m2['score']:<7} dist={m2['distance']:<6} "
                  f"fall={m2['fall_rate']:<5} clear={m2['clear_rate']}  "
                  f"({time.time() - t0:.0f}s)")
            history.append({"round": rnd, "source": "coding-agent", "code": cand,
                            "metrics": m2, "verdict": verdict, "feedback": fb})
            if verdict == "ACCEPT":
                code, m, fn = cand, m2, fn2
        except Exception as exc:
            print(f"R{rnd} ERROR  {type(exc).__name__}: {str(exc)[:110]}")
            history.append({"round": rnd, "error": f"{type(exc).__name__}: {exc}"})

    out = HERE / f"results_{args.tag}.json"
    out.write_text(json.dumps({
        "paper": "arXiv:2610.38027 METATRON (NVIDIA Research, 2026-10-27)",
        "task": args.task, "coder_model": args.coder_model,
        "endpoint": args.coder_base, "history": history,
        "best_score": max(h["metrics"]["score"] for h in history if "metrics" in h),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print("-" * 74)
    print("结果已落盘:", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
