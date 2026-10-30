"""模拟策略服务器：不加载真实模型，输出脚本化动作块，用于验证桥接控制闭环。
输出动作块 = 起始关节 + 正弦扫动（弧度），夹爪恒 0.5。
用法: python mock_policy_server.py --port 8006
"""
import argparse, math, sys, time
import numpy as np

import asyncio
import websockets.asyncio.server as _server

from msgpack_numpy import Packer, unpackb


class MockPolicy:
    def __init__(self, use_length=25):
        self.use_length = use_length
        self.global_step = 0
        self.home_rad = np.array([0.3, 0.05, -1.6, 0.3, 1.55, 0.05])  # 接近当前臂形态
        self.amp = np.array([0.35, 0.15, 0.25, 0.15, 0.15, 0.15])
        self.freq = 0.15

    def infer(self, obs):
        if obs.get("reset"):
            self.global_step = 0
            print("[mock] reset, robo_name =", obs.get("robo_name"))
            return dict(action=None)
        t = np.arange(self.use_length)
        chunk = self.home_rad[None, :] + self.amp[None, :] * np.sin(
            2 * math.pi * self.freq * (self.global_step + t)[:, None] / self.use_length)
        eff = np.full((self.use_length,), 0.5, dtype=np.float32)
        self.global_step += self.use_length
        # 与真实 server 输出格式一致: 原始键 action(chunk,7)
        full = np.concatenate([chunk.astype(np.float32), eff[:, None]], axis=1)
        return {"action": full}


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8006)
    ap.add_argument("--host", default="0.0.0.0")
    args = ap.parse_args()

    policy = MockPolicy()

    async def handler(ws):
        print(f"[mock] 连接来自 {ws.remote_address}")
        packer = Packer()
        await ws.send(packer.pack({"server": "mock", "use_length": policy.use_length}))
        while True:
            try:
                obs = unpackb(await ws.recv())
                act = policy.infer(obs)
                await ws.send(packer.pack(act))
            except Exception as e:
                print("[mock] 连接关闭:", e)
                break

    async with _server.serve(handler, args.host, args.port, compression=None, max_size=None):
        print(f"[mock] 模拟策略服务器监听 {args.host}:{args.port}")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
