from __future__ import annotations
import argparse
from pathlib import Path

SAMPLE = [0.05, 0.12, 0.20, 0.35, 0.42, 0.38, 0.30]

def render_svg(values: list[float], width=760, height=320) -> str:
    pad = 40
    ymin, ymax = min(values + [-1.0]), max(values + [1.0])
    def sx(i): return pad + i * (width - 2 * pad) / max(1, len(values)-1)
    def sy(v): return height - pad - (v-ymin) * (height-2*pad) / max(1e-9, ymax-ymin)
    pts = " ".join(f"{sx(i):.1f},{sy(v):.1f}" for i, v in enumerate(values))
    circles = "\n".join(f'<circle cx="{sx(i):.1f}" cy="{sy(v):.1f}" r="4" fill="currentColor" />' for i,v in enumerate(values))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
            f'<rect width="100%" height="100%" fill="white"/>'
            f'<text x="40" y="25" font-family="sans-serif" font-size="18">SmolVLA action chunk - dimension 0 (dry-run)</text>'
            f'<line x1="{pad}" y1="{sy(0):.1f}" x2="{width-pad}" y2="{sy(0):.1f}" stroke="gray" stroke-dasharray="4 4"/>'
            f'<polyline points="{pts}" fill="none" stroke="black" stroke-width="2"/>'
            f'{circles}</svg>')

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', default='artifacts/action_chunk.svg')
    args = ap.parse_args()
    p = Path(args.output); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(render_svg(SAMPLE), encoding='utf-8')
    print(p)
