from __future__ import annotations
import argparse
from pathlib import Path
from pipeline import demo

def render_svg(objects, width=760, height=460):
    # top-down base-frame x/y visualization; not a metric CAD plot
    scale = 260.0; ox, oy = 120.0, 300.0
    items = []
    for obj in objects:
        x,y,_ = obj['base_xyz_m']
        px, py = ox + x*scale, oy - y*scale
        items.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="9" fill="none" stroke="black" stroke-width="2"/><text x="{px+13:.1f}" y="{py+5:.1f}" font-family="sans-serif" font-size="15">{obj["label"]} ({x:.2f},{y:.2f})m</text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
            f'<rect width="100%" height="100%" fill="white"/>'
            f'<text x="30" y="28" font-family="sans-serif" font-size="18">Semantic objects in robot base frame (dry-run)</text>'
            f'<line x1="{ox}" y1="30" x2="{ox}" y2="420" stroke="gray"/>'
            f'<line x1="30" y1="{oy}" x2="730" y2="{oy}" stroke="gray"/>'
            f'{"".join(items)}</svg>')

if __name__ == '__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--output', default='artifacts/semantic_scene.svg'); args=ap.parse_args()
    data=demo(); p=Path(args.output); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(render_svg(data['objects']), encoding='utf-8'); print(p)
