"""Render the Go2 LiDAR map into MP4 videos with a hand-rolled point renderer.

Outputs (site/dist/video):
  map_build.mp4   progressive point-cloud accumulation, 180 sensor frames
  map_orbit.mp4   turntable orbit around the finished map

Uses numpy + OpenCV only: perspective projection with a painter's-algorithm
depth sort, which keeps 190k points per frame fast enough for 24 fps output.
"""
import json
import pathlib
import subprocess

import cv2
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "site" / "dist" / "data"
OUT = ROOT / "site" / "dist" / "video"
OUT.mkdir(parents=True, exist_ok=True)
W, H = 960, 720
FPS = 24


def load():
    pos = np.fromfile(DATA / "map-positions.bin", dtype="<f4").reshape(-1, 3).astype(np.float64)
    col = np.fromfile(DATA / "map-colors.bin", dtype="u1").reshape(-1, 3)
    frame = np.fromfile(DATA / "map-frame.bin", dtype="<u2").astype(np.int32)
    meta = json.loads((DATA / "simulation.json").read_text())
    return pos, col, frame, meta


def camera(center, az, el, dist):
    az, el = np.deg2rad(az), np.deg2rad(el)
    eye = center + dist * np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])
    fwd = center - eye
    fwd /= np.linalg.norm(fwd)
    world_up = np.array([0.0, 0.0, 1.0])
    right = np.cross(fwd, world_up)
    n = np.linalg.norm(right)
    right = right / n if n > 1e-6 else np.array([1.0, 0.0, 0.0])
    up = np.cross(right, fwd)
    return eye, right, up, fwd


def project(pts, eye, right, up, fwd, fov=42.0):
    rel = pts - eye
    x = rel @ right
    y = rel @ up
    z = rel @ fwd
    f = H / (2.0 * np.tan(np.deg2rad(fov) / 2.0))
    safe = np.maximum(z, 1e-3)
    u = (W / 2.0 + f * x / safe)
    v = (H / 2.0 - f * y / safe)
    return u, v, z


def paint(canvas, u, v, z, colors, radius=1):
    """Draw points far-to-near so the nearest surface wins (painter's algorithm)."""
    ok = (z > 0.08) & (u >= 0) & (u < W) & (v >= 0) & (v < H)
    if not ok.any():
        return 0
    uu, vv, zz = u[ok], v[ok], z[ok]
    cc = colors[ok]
    order = np.argsort(-zz)
    ui = uu[order].astype(np.int32)
    vi = vv[order].astype(np.int32)
    if radius <= 1:
        canvas[vi, ui] = cc[order]
    else:
        cv2.circle(canvas, (0, 0), 0, (0, 0, 0), -1)
        for x, y, c in zip(ui, vi, cc[order]):
            cv2.circle(canvas, (int(x), int(y)), radius, c.tolist(), -1, cv2.LINE_AA)
    return int(ok.sum())


def grid_overlay(canvas, eye, right, up, fwd, half=8, step=1):
    pts = []
    for i in np.arange(-half, half + 1e-9, step):
        pts.append([[i, -half, 0.0], [i, half, 0.0]])
        pts.append([[-half, i, 0.0], [half, i, 0.0]])
    for seg in pts:
        u, v, z = project(np.array(seg, dtype=np.float64), eye, right, up, fwd)
        if (z > 0.08).all():
            cv2.line(canvas, (int(u[0]), int(v[0])), (int(u[1]), int(v[1])), (38, 46, 58), 1, cv2.LINE_AA)


def hud(canvas, lines, sub=None):
    y = 34
    for text, color, scale in lines:
        cv2.putText(canvas, text, (28, y), cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(canvas, text, (28, y), cv2.FONT_HERSHEY_SIMPLEX, scale, color, 1, cv2.LINE_AA)
        y += int(scale * 40)
    if sub:
        cv2.putText(canvas, sub, (28, H - 26), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (140, 150, 160), 1, cv2.LINE_AA)


class Writer:
    def __init__(self, path):
        self.path = path
        self.p = subprocess.Popen(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24",
             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
             "-c:v", "libx264", "-preset", "medium", "-crf", "20",
             "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(path)],
            stdin=subprocess.PIPE,
        )

    def write(self, frame):
        self.p.stdin.write(frame.tobytes())

    def close(self):
        self.p.stdin.close()
        self.p.wait()


def main():
    pos, colors_rgb, frame_idx, meta = load()
    colors = np.ascontiguousarray(colors_rgb[:, ::-1])  # BGR for OpenCV
    center = np.array([0.0, 0.0, 0.9])
    gt = np.array(meta["trajectory_gt"], dtype=np.float64)
    m17 = meta["runs"][0]
    nframes = int(frame_idx.max()) + 1
    print(f"points={len(pos)} frames={nframes} video_dir={OUT}", flush=True)

    # ---- video 1: progressive build -------------------------------------
    wr = Writer(OUT / "map_build.mp4")
    az, el, dist = 128.0, 26.0, 21.0
    for t in range(nframes + 18):
        k = min(t, nframes - 1)
        eye, right, up, fwd = camera(center, az + 12 * np.sin(t / 60.0), el, dist)
        canvas = np.full((H, W, 3), 12, dtype=np.uint8)
        grid_overlay(canvas, eye, right, up, fwd)
        mask = frame_idx <= k
        u, v, z = project(pos[mask], eye, right, up, fwd)
        n = paint(canvas, u, v, z, colors[mask])
        trail = gt[: k + 1]
        if len(trail) > 1:
            tu, tv, tz = project(trail, eye, right, up, fwd)
            for i in range(len(trail) - 1):
                if tz[i] > 0.08 and tz[i + 1] > 0.08:
                    cv2.line(canvas, (int(tu[i]), int(tv[i])), (int(tu[i + 1]), int(tv[i + 1])),
                             (90, 220, 250), 2, cv2.LINE_AA)
        hud(canvas, [
            ("Go2 LiDAR mapping - progressive build", (235, 240, 245), 0.78),
            (f"frame {k:03d} / {nframes - 1:03d}   points {n:6d}", (110, 220, 200), 0.60),
        ], sub=f"MuJoCo raycast + trimmed ICP | ATE {m17['ate_rmse_m']:.2f} m | RPE {m17['rpe_translation_rmse_m']:.3f} m | {m17['icp_mean_ms']:.1f} ms/frame")
        wr.write(canvas)
    wr.close()
    print("map_build.mp4 done", flush=True)

    # ---- video 2: turntable orbit ---------------------------------------
    wr = Writer(OUT / "map_orbit.mp4")
    centre_cloud = pos.mean(axis=0)
    centre_cloud[2] = 0.9
    for t in range(240):
        az = 360.0 * t / 240.0
        el = 22.0 + 12.0 * np.sin(np.deg2rad(az * 2))
        eye, right, up, fwd = camera(centre_cloud, az, el, 20.0)
        canvas = np.full((H, W, 3), 12, dtype=np.uint8)
        grid_overlay(canvas, eye, right, up, fwd)
        u, v, z = project(pos, eye, right, up, fwd)
        paint(canvas, u, v, z, colors)
        hud(canvas, [("Go2 LiDAR map - orbit", (235, 240, 245), 0.78)], sub=f"{len(pos)} points | material colour from simulator")
        wr.write(canvas)
    wr.close()
    print("map_orbit.mp4 done", flush=True)


if __name__ == "__main__":
    main()
