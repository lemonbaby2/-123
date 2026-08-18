"""Dependency-free semantic-to-3D-to-action-bridge demo."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def backproject(u: float, v: float, z: float, K: dict[str, float]) -> list[float]:
    if z <= 0:
        raise ValueError('depth must be positive')
    return [(u-K['cx'])*z/K['fx'], (v-K['cy'])*z/K['fy'], z]

def transform_point(p: list[float], R: list[list[float]], t: list[float]) -> list[float]:
    return [sum(R[i][j]*p[j] for j in range(3)) + t[i] for i in range(3)]

def robust_depth(values: list[float], lo: float, hi: float) -> float:
    valid = sorted(v for v in values if lo <= v <= hi)
    if not valid:
        raise ValueError('no valid depth')
    n = len(valid)
    return valid[n//2] if n % 2 else 0.5*(valid[n//2-1] + valid[n//2])

def demo() -> dict[str, object]:
    cfg = json.loads((ROOT / 'config/system.json').read_text())
    K = cfg['camera_intrinsics']
    T = cfg['T_base_camera']
    detections = [
        {'label':'red cup','confidence':0.93,'uv':[350,265],'depth_samples':[0.62,0.61,0.0,0.63,4.2,0.62]},
        {'label':'blue fixture','confidence':0.88,'uv':[225,300],'depth_samples':[0.95,0.96,0.95,0.94]},
    ]
    objects = []
    for d in detections:
        if d['confidence'] < cfg['semantic_confidence_min']:
            continue
        z = robust_depth(d['depth_samples'], cfg['depth_min_m'], cfg['depth_max_m'])
        pc = backproject(d['uv'][0], d['uv'][1], z, K)
        pb = transform_point(pc, T['R'], T['t_m'])
        objects.append({'label':d['label'], 'confidence':d['confidence'], 'camera_xyz_m':[round(x,4) for x in pc], 'base_xyz_m':[round(x,4) for x in pb]})
    return {'project':'spatial_semantic_vla_engineering','mode':'dry-run','objects':objects,'next_stage':'VLA/MoveIt2 adapter after workspace + collision checks'}

if __name__ == '__main__':
    print(json.dumps(demo(), ensure_ascii=False, indent=2))
