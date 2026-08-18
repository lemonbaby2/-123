"""OpenCV hand-eye calibration helper.
Input JSON contains arrays R_gripper2base, t_gripper2base, R_target2cam, t_target2cam.
All rotations are 3x3 matrices; translations use meters.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path


def main():
    import cv2
    import numpy as np
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()
    data = json.loads(Path(args.input).read_text())
    Rg = [np.asarray(x, dtype=float) for x in data['R_gripper2base']]
    tg = [np.asarray(x, dtype=float).reshape(3,1) for x in data['t_gripper2base']]
    Rt = [np.asarray(x, dtype=float) for x in data['R_target2cam']]
    tt = [np.asarray(x, dtype=float).reshape(3,1) for x in data['t_target2cam']]
    if not (len(Rg) == len(tg) == len(Rt) == len(tt) and len(Rg) >= 5):
        raise SystemExit('need >=5 synchronized pose pairs')
    R, t = cv2.calibrateHandEye(Rg, tg, Rt, tt, method=cv2.CALIB_HAND_EYE_TSAI)
    out = {'R_cam2gripper': R.tolist(), 't_cam2gripper_m': t.reshape(-1).tolist(), 'samples': len(Rg)}
    Path(args.output).write_text(json.dumps(out, indent=2), encoding='utf-8')
    print(json.dumps(out, indent=2))

if __name__ == '__main__': main()
