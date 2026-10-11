"""Mesh just the sculpt (no mechanism) for a quick look."""
import sys
import time

import gnome
from meshing import save_ply, sdf_mesh, to_manifold

out = sys.argv[1]
step = float(sys.argv[2]) if len(sys.argv) > 2 else 0.8
t = time.time()
if "--head-only" not in sys.argv:
  body = to_manifold(*sdf_mesh(lambda p: gnome.combine(gnome.body_regions(p)), (-45, -45, -4), (45, 52, 118), step))
  save_ply(body, f"{out}/body.ply", lambda v: gnome.paint_colours(gnome.body_regions((v[:, 0], v[:, 1], v[:, 2]))))
  print("body", f"{time.time()-t:.1f}s", body.num_tri(), flush=True)
head = to_manifold(*sdf_mesh(lambda p: gnome.combine(gnome.head_regions(p)), (-30, 10, 70), (30, 70, 165), step))
save_ply(head, f"{out}/head.ply", lambda v: gnome.paint_colours(gnome.head_regions((v[:, 0], v[:, 1], v[:, 2]))))
print("head", f"{time.time()-t:.1f}s", head.num_tri())
