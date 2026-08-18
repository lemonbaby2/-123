"""Eye-to-hand helper using OpenCV hand-eye calibration.
Coordinate conventions must be verified for your robot SDK. This script intentionally
requires explicit matrices rather than hiding frame semantics.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path

def invert_rt(R,t):
    Rt=[[R[j][i] for j in range(3)] for i in range(3)]
    ti=[-sum(Rt[i][j]*t[j] for j in range(3)) for i in range(3)]
    return Rt,ti

def main():
    import cv2, numpy as np
    ap=argparse.ArgumentParser(); ap.add_argument('--input',required=True); ap.add_argument('--output',required=True); args=ap.parse_args()
    d=json.loads(Path(args.input).read_text())
    Rg=[np.asarray(x,float) for x in d['R_gripper2base']]; tg=[np.asarray(x,float).reshape(3,1) for x in d['t_gripper2base']]
    Rt=[np.asarray(x,float) for x in d['R_target2cam']]; tt=[np.asarray(x,float).reshape(3,1) for x in d['t_target2cam']]
    R,t=cv2.calibrateHandEye(Rg,tg,Rt,tt,method=cv2.CALIB_HAND_EYE_PARK)
    out={'note':'verify frame direction against a held-out target pose','R_cam2gripper_like_solution':R.tolist(),'t_m':t.reshape(-1).tolist()}
    Path(args.output).write_text(json.dumps(out,indent=2),encoding='utf-8'); print(json.dumps(out,indent=2))
if __name__=='__main__': main()
