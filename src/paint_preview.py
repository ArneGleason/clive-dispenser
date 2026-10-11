"""Repaint preview meshes with the full colour job (for quick looks)."""
import sys
import time

import numpy as np
import trimesh

import paint

d = sys.argv[1]
for part, fn in (("head", paint.head_colours), ("body", paint.body_colours)):
    if len(sys.argv) > 2 and part not in sys.argv[2:]:
        continue
    t = time.time()
    m = trimesh.load(f"{d}/{part}.ply", process=False)
    c = fn(np.asarray(m.vertices), np.asarray(m.vertex_normals))
    m.visual.vertex_colors = np.hstack([c * 255, np.full((len(c), 1), 255)]).astype(np.uint8)
    m.export(f"{d}/{part}_painted.ply")
    print(part, len(c), f"{time.time() - t:.1f}s", flush=True)
