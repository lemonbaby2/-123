from __future__ import annotations
import argparse, glob, json
from pathlib import Path


def main():
    import cv2
    import numpy as np
    ap = argparse.ArgumentParser()
    ap.add_argument('--images', required=True)
    ap.add_argument('--cols', type=int, default=9)
    ap.add_argument('--rows', type=int, default=6)
    ap.add_argument('--square-size', type=float, default=0.024)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()

    objp = np.zeros((args.rows * args.cols, 3), np.float32)
    objp[:, :2] = np.mgrid[0:args.cols, 0:args.rows].T.reshape(-1, 2) * args.square_size
    objpoints, imgpoints = [], []
    image_size = None
    used = []
    for fn in sorted(glob.glob(args.images)):
        img = cv2.imread(fn)
        if img is None:
            continue
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        image_size = (gray.shape[1], gray.shape[0])
        ok, corners = cv2.findChessboardCorners(gray, (args.cols, args.rows))
        if not ok:
            continue
        corners = cv2.cornerSubPix(gray, corners, (11,11), (-1,-1), (cv2.TERM_CRITERIA_EPS+cv2.TERM_CRITERIA_MAX_ITER, 30, 1e-3))
        objpoints.append(objp.copy()); imgpoints.append(corners); used.append(fn)
    if len(objpoints) < 8:
        raise SystemExit(f'need >=8 valid calibration views, got {len(objpoints)}')
    rms, K, dist, rvecs, tvecs = cv2.calibrateCamera(objpoints, imgpoints, image_size, None, None)
    out = {'rms': float(rms), 'image_size': list(image_size), 'K': K.tolist(), 'dist': dist.reshape(-1).tolist(), 'used_images': used}
    p = Path(args.output); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(out, indent=2), encoding='utf-8')
    print(json.dumps(out, indent=2))

if __name__ == '__main__': main()
