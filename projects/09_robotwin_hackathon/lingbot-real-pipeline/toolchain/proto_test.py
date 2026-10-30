# -*- coding: utf-8 -*-
"""协议回归测试：mock server 输出 action(chunk,7) -> 客户端切片解析 -> 校验形状与限幅逻辑
用法: python proto_test.py   （自动起 mock server -> 连 -> 断言 -> 退出）
"""
import subprocess, sys, time, socket
import numpy as np

REPO = r"E:\研究生学习\黑客松\tmp\lingbot-vla-v2"
PORT = 8014

sys.path.insert(0, REPO)
from deploy.websocket_client_policy import WebsocketClientPolicy


def wait_port(port, timeout=20):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except OSError:
            time.sleep(0.3)
    return False


srv = subprocess.Popen(
    [sys.executable, "-u", f"{REPO}/deploy/mock_policy_server.py", "--port", str(PORT)],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=REPO, text=True,
)
try:
    assert wait_port(PORT), "mock server 未启动"
    print(f"[proto] mock server up on {PORT}")
    policy = WebsocketClientPolicy("127.0.0.1", PORT)
    print(f"[proto] server metadata={policy.get_server_metadata()}")
    policy.reset("realman_gen65bi")
    print("[proto] reset ok")

    obs = {
        "observation.images.cam_high": np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8),
        "observation.images.cam_wrist": np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8),
        "observation.state": np.zeros(7, dtype=np.float32),
        "task": "pick up the block",
    }
    for i in range(3):
        act = policy.infer(obs)
        print(f"[proto] infer#{i+1} keys={list(act.keys())}")
        assert "action" in act, f"缺少 action 键: {list(act.keys())}"
        full = np.asarray(act["action"], dtype=np.float64)
        print(f"        action shape={full.shape}")
        assert full.ndim == 2 and full.shape[1] == 7, f"形状错误 {full.shape}"
        arm, eff = full[:, :6], full[:, 6]
        # 模拟 bridge 的单位换算与限幅（rad -> 0.001deg）
        deg = np.rad2deg(arm)
        step_clip = np.clip(deg, -160, 160)
        print(f"        arm[0] deg={np.round(step_clip[0],1)} eff[0]={eff[0]:.3f}")
        assert np.isfinite(full).all(), "动作含 NaN/Inf"
        assert (eff >= -0.5).all() and (eff <= 1.5).all(), "夹爪超范围"
    try: policy.close()
    except AttributeError: pass
    print("[proto] PROTOCOL TEST PASSED: action(chunk,7) -> arm[:6] + effector[6] 解析正确")
finally:
    srv.terminate()
    try:
        out = srv.communicate(timeout=5)[0]
    except subprocess.TimeoutExpired:
        srv.kill(); out = ""
    if out:
        print("--- server log ---")
        print(out[-800:])
