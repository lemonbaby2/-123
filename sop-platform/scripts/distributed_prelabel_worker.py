from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

import cv2
from ultralytics import YOLOE


DEFAULT_MODEL = Path("/home/xjai/sop-model-store/yoloe-26s-seg.pt")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Thermally controlled distributed SOP prelabel worker")
    parser.add_argument("--coordinator", default=os.getenv("SOP_PRELABEL_COORDINATOR", "http://127.0.0.1:8116"))
    parser.add_argument("--token", default=os.getenv("SOP_PRELABEL_WORKER_TOKEN", ""))
    parser.add_argument("--node-id", default=os.getenv("SOP_PRELABEL_NODE_ID", f"{socket.gethostname()}-gpu0"))
    parser.add_argument("--video-id", default=os.getenv("SOP_PRELABEL_VIDEO_ID", ""), help="只领取指定视频，适合小规模验收")
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--batch", type=int, default=4)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--confidence", type=float, default=0.18)
    parser.add_argument("--max-temperature", type=float, default=70.0)
    parser.add_argument("--resume-temperature", type=float, default=62.0)
    parser.add_argument("--cooldown-seconds", type=float, default=0.25)
    parser.add_argument("--idle-seconds", type=float, default=30.0)
    parser.add_argument("--once", action="store_true")
    return parser.parse_args()


def gpu_temperature() -> float | None:
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=3, check=False,
        )
        return float(result.stdout.strip().splitlines()[0]) if result.returncode == 0 else None
    except (OSError, ValueError, IndexError, subprocess.TimeoutExpired):
        return None


def gpu_name() -> str:
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=3, check=False,
        )
        return result.stdout.strip().splitlines()[0] if result.returncode == 0 else "unknown"
    except (OSError, IndexError, subprocess.TimeoutExpired):
        return "unknown"


class Coordinator:
    def __init__(self, url: str, token: str) -> None:
        self.url = url.rstrip("/")
        self.token = token
        self.opener = build_opener(ProxyHandler({}))

    def post(self, route: str, payload: dict) -> object:
        request = Request(
            f"{self.url}{route}",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json", "X-SOP-Worker-Token": self.token},
            method="POST",
        )
        try:
            with self.opener.open(request, timeout=90) as response:
                body = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            message = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"coordinator HTTP {exc.code}: {message[:500]}") from exc
        if not body.get("ok"):
            raise RuntimeError(str(body.get("message") or "coordinator rejected request"))
        return body.get("result")


def wait_for_safe_temperature(args: argparse.Namespace) -> float | None:
    temperature = gpu_temperature()
    if temperature is None or temperature < args.max_temperature:
        return temperature
    while temperature is not None and temperature > args.resume_temperature:
        print(f"thermal pause: GPU {temperature:.0f} C, resume at <= {args.resume_temperature:.0f} C", flush=True)
        time.sleep(20)
        temperature = gpu_temperature()
    return temperature


def normalize_results(
    results: list,
    jobs: list[tuple[int, float, int, int]],
    labels: list[str],
    node_id: str,
    video_id: str,
) -> list[dict]:
    frames = []
    for result, (frame_index, video_time, width, height) in zip(results, jobs):
        detections = []
        for detection_index, box in enumerate(result.boxes or []):
            class_index = int(box.cls.item())
            if not 0 <= class_index < len(labels):
                continue
            confidence = float(box.conf.item())
            x1, y1, x2, y2 = [float(value) for value in box.xyxy[0].tolist()]
            if x2 - x1 < 12 or y2 - y1 < 12:
                continue
            detections.append({
                "annotation_id": f"sop-broad:{video_id}:{frame_index}:{detection_index}:{labels[class_index]}",
                "video_time": round(video_time, 6),
                "label": labels[class_index],
                "confidence": round(confidence, 5),
                "box": [
                    round(max(0.0, x1 / width), 6), round(max(0.0, y1 / height), 6),
                    round(min(1.0, x2 / width), 6), round(min(1.0, y2 / height), 6),
                ],
                "box_pixels": [round(x1, 1), round(y1, 1), round(x2, 1), round(y2, 1)],
                "box_format": "normalized_xyxy",
                "region": "SOP工位待分区",
                "track_id": None,
                "source": f"YOLOE工位级全帧预标注/{node_id}",
            })
        frames.append({"frame": frame_index, "detections": detections})
    return frames


def process_job(args: argparse.Namespace, coordinator: Coordinator, model: YOLOE, job: dict) -> None:
    source = Path(str(job["source_path"]))
    if not source.is_file():
        raise RuntimeError(f"worker 无法访问视频路径: {source}")
    prompts = [str(item["prompt"]) for item in job["label_schema"].get("prompts", [])]
    labels = [str(item["label"]) for item in job["label_schema"].get("prompts", [])]
    if not prompts or len(prompts) != len(labels):
        raise RuntimeError("标签模板为空或格式错误")
    model.set_classes(prompts, model.get_text_pe(prompts))
    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        raise RuntimeError(f"无法打开视频: {source.name}")
    fps = float(capture.get(cv2.CAP_PROP_FPS) or job.get("fps") or 30)
    start_frame = max(0, int(job.get("completed_frames") or 0))
    if start_frame:
        capture.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    batch_frames = []
    batch_jobs: list[tuple[int, float, int, int]] = []
    frame_index = start_frame
    model_name = args.model.name
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            height, width = frame.shape[:2]
            batch_frames.append(frame)
            batch_jobs.append((frame_index, frame_index / fps, width, height))
            frame_index += 1
            if len(batch_frames) < args.batch:
                continue
            temperature = wait_for_safe_temperature(args)
            results = model.predict(
                batch_frames, imgsz=args.imgsz, conf=args.confidence, iou=0.5,
                max_det=30, device=0, verbose=False,
            )
            frames = normalize_results(results, batch_jobs, labels, args.node_id, str(job["video_id"]))
            accepted = coordinator.post("/api/prelabel/worker/submit", {
                "node_id": args.node_id, "job_id": job["job_id"], "video_id": job["video_id"],
                "model_name": model_name, "gpu_temperature": temperature, "frames": frames,
            })
            print(
                f"{job['video_id']} frame={frame_index}/{job['total_frames']} "
                f"accepted={accepted['accepted_frames']} temperature={temperature}", flush=True,
            )
            batch_frames.clear()
            batch_jobs.clear()
            if accepted.get("pause_requested"):
                coordinator.post("/api/prelabel/worker/finish", {
                    "node_id": args.node_id, "job_id": job["job_id"], "status": "paused",
                })
                return
            if args.cooldown_seconds > 0:
                time.sleep(args.cooldown_seconds)
        if batch_frames:
            temperature = wait_for_safe_temperature(args)
            results = model.predict(
                batch_frames, imgsz=args.imgsz, conf=args.confidence, iou=0.5,
                max_det=30, device=0, verbose=False,
            )
            accepted = coordinator.post("/api/prelabel/worker/submit", {
                "node_id": args.node_id, "job_id": job["job_id"], "video_id": job["video_id"],
                "model_name": model_name, "gpu_temperature": temperature,
                "frames": normalize_results(results, batch_jobs, labels, args.node_id, str(job["video_id"])),
            })
            if accepted.get("pause_requested"):
                coordinator.post("/api/prelabel/worker/finish", {
                    "node_id": args.node_id, "job_id": job["job_id"], "status": "paused",
                })
                return
        coordinator.post("/api/prelabel/worker/finish", {
            "node_id": args.node_id, "job_id": job["job_id"], "status": "completed",
        })
    finally:
        capture.release()


def main() -> None:
    args = parse_args()
    if not args.token:
        raise RuntimeError("必须通过 SOP_PRELABEL_WORKER_TOKEN 提供私有 worker 令牌")
    if not args.model.is_file():
        raise RuntimeError(f"模型不存在: {args.model}")
    coordinator = Coordinator(args.coordinator, args.token)
    capabilities = {
        "gpu": gpu_name(), "model": args.model.name, "batch": args.batch,
        "imgsz": args.imgsz, "thermal_limit_c": args.max_temperature,
        "label_mode": "sop-broad", "full_frame": True,
    }
    coordinator.post("/api/prelabel/worker/register", {
        "node_id": args.node_id, "hostname": socket.gethostname(),
        "gpu_temperature": gpu_temperature(), "capabilities": capabilities,
    })
    model = YOLOE(str(args.model))
    while True:
        claim_payload = {"node_id": args.node_id}
        if args.video_id:
            claim_payload["video_id"] = args.video_id
        job = coordinator.post("/api/prelabel/worker/claim", claim_payload)
        if not job:
            print("no pending jobs", flush=True)
            if args.once:
                return
            time.sleep(args.idle_seconds)
            continue
        try:
            process_job(args, coordinator, model, job)
        except Exception as exc:
            try:
                coordinator.post("/api/prelabel/worker/finish", {
                    "node_id": args.node_id, "job_id": job["job_id"], "status": "failed", "error": str(exc),
                })
            except Exception:
                pass
            raise
        if args.once:
            return


if __name__ == "__main__":
    main()
