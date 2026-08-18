"""Validate a 4x4 rigid transform using paired 3D points.
Expected JSON: {"T":[[...4]x4], "camera_points":[...], "base_points":[...]}
"""
from __future__ import annotations
import argparse, json, math
from pathlib import Path

def transform(T,p):
    return [sum(T[i][j]*p[j] for j in range(3))+T[i][3] for i in range(3)]

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input', required=True); args=ap.parse_args()
    d=json.loads(Path(args.input).read_text()); errs=[]
    for pc,pb in zip(d['camera_points'],d['base_points']):
        q=transform(d['T'],pc); errs.append(math.sqrt(sum((q[i]-pb[i])**2 for i in range(3))))
    if not errs: raise SystemExit('no point pairs')
    out={'samples':len(errs),'rmse_m':math.sqrt(sum(e*e for e in errs)/len(errs)),'max_error_m':max(errs)}
    print(json.dumps(out, indent=2))
if __name__=='__main__': main()
