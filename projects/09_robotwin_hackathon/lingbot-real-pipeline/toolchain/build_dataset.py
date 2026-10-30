"""把机器人侧 episodes 构建为 LeRobot 3.0 (v3.0) 格式数据集。
- observation.images.top / observation.images.wrist : video 480x640x3 (h264 yuv420p)
- observation.state : 6 关节角(deg) + 1 夹爪实际位置(0~1) = 7
- action           : 下一帧 state（一步行为克隆目标，演示数据语义）
用法: python build_dataset.py <episodes_dir> <输出repo_id> [root]
"""
import sys, os, json, glob
import numpy as np
import cv2
import av

from lerobot.datasets.lerobot_dataset import LeRobotDataset
from lerobot.configs.video import RGBEncoderConfig

def main():
    eps_dir = sys.argv[1] if len(sys.argv) > 1 else r"E:\研究生学习\黑客松\outputs\lingbot_real\episodes"
    repo_id = sys.argv[2] if len(sys.argv) > 2 else "lingbot/gen65bi-<ROBOT_USER>-demo"
    root = sys.argv[3] if len(sys.argv) > 3 else r"E:\研究生学习\黑客松\outputs\lingbot_real\datasets"

    features = {
        "observation.images.top": {"dtype": "video", "shape": [480, 640, 3],
                                   "names": ["height", "width", "channels"]},
        "observation.images.wrist": {"dtype": "video", "shape": [480, 640, 3],
                                     "names": ["height", "width", "channels"]},
        "observation.state": {"dtype": "float32", "shape": [7],
                              "names": ["joint1", "joint2", "joint3", "joint4", "joint5", "joint6", "gripper"]},
        "action": {"dtype": "float32", "shape": [7],
                   "names": ["joint1", "joint2", "joint3", "joint4", "joint5", "joint6", "gripper"]},
    }

    dataset = LeRobotDataset.create(
        repo_id=repo_id,
        fps=30,
        robot_type="realman_gen65bi",
        features=features,
        root=root,
        use_videos=True,
        rgb_encoder=RGBEncoderConfig(vcodec="h264", pix_fmt="yuv420p", crf=23, preset="medium", g=2),
        batch_encoding_size=1,
    )
    print("dataset root:", dataset.root)

    ep_dirs = sorted(glob.glob(os.path.join(eps_dir, "episode_*")))
    print(f"共 {len(ep_dirs)} 个 episode")

    for ep_dir in ep_dirs:
        meta = json.load(open(os.path.join(ep_dir, "meta.json")))
        task = meta.get("task", "demo")
        st = np.load(os.path.join(ep_dir, "states.npz"))
        joint = st["joint"].astype(np.float32)           # (N,6) deg
        gpos = st["gripper_pos"].astype(np.float32)       # (N,) 0~1
        state = np.concatenate([joint, gpos[:, None]], axis=1)   # (N,7)

        # 读双路视频帧
        def read_frames(path):
            cap = cv2.VideoCapture(path)
            frames = []
            while True:
                ok, fr = cap.read()
                if not ok:
                    break
                frames.append(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB))
            cap.release()
            return frames

        top = read_frames(os.path.join(ep_dir, "cam_top.mp4"))
        wrist = read_frames(os.path.join(ep_dir, "cam_wrist.mp4"))
        n = len(state)
        assert len(top) == n and len(wrist) == n, f"帧数不一致: state={n} top={len(top)} wrist={len(wrist)}"

        for t in range(n):
            act = state[min(t + 1, n - 1)]
            dataset.add_frame({
                "observation.images.top": top[t],
                "observation.images.wrist": wrist[t],
                "observation.state": state[t],
                "action": act,
                "task": task,
            })
        dataset.save_episode(parallel_encoding=False)
        print(f"  {os.path.basename(ep_dir)} [{task}] {n} 帧 -> episode_{dataset.meta.total_episodes - 1}")

    print("finalize (编码视频/写 meta)...")
    dataset.finalize()
    print("完成:", dataset.root)
    print("total_episodes:", dataset.meta.total_episodes, "total_frames:", dataset.meta.total_frames)
    return 0

if __name__ == "__main__":
    sys.exit(main())
