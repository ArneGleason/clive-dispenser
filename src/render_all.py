"""Make the standard set of renders from a build directory.

    python3 render_all.py BUILD_DIR [--samples 96] [--only name]
"""
import argparse
import glob
import json
import os
import subprocess
import sys

ap = argparse.ArgumentParser()
ap.add_argument("build")
ap.add_argument("--samples", type=int, default=96)
ap.add_argument("--only")
args = ap.parse_args()
ply = os.path.abspath(os.path.join(args.build, "ply"))
out = os.path.abspath(os.path.join(args.build, "renders"))
os.makedirs(out, exist_ok=True)
here = os.path.dirname(os.path.abspath(__file__))


def parts(pose, hide=(), ghost=()):
    objs = []
    for f in sorted(glob.glob(f"{ply}/{pose}_*.ply")):
        name = os.path.basename(f)[len(pose) + 1:-4]
        if any(name.startswith(h) for h in hide):
            continue
        o = {"ply": f, "gloss": 0.28}
        if name.startswith("candy"):
            o.update(gloss=0.6, smooth_angle=60)
        if any(name.startswith(g) for g in ghost):
            o["alpha"] = 0.3
        objs.append(o)
    return objs


TEXT = []  # the nameplate lettering is part of the printed base now
SHOTS = {
    "hero_closed": dict(objects=parts("rest"), camera={"loc": [235, -255, 170], "target": [0, 2, 72], "lens": 62}),
    "hero_open": dict(objects=parts("open"), camera={"loc": [235, -255, 170], "target": [0, 2, 72], "lens": 62}),
    "front_closed": dict(objects=parts("rest"), camera={"loc": [260, 230, 150], "target": [0, 10, 80], "lens": 62}),
    "side_open": dict(objects=parts("open"), camera={"loc": [380, 40, 130], "target": [0, 8, 78], "lens": 62}),
    # Cutaways: drop Clive's right half (+x) and ghost the hopper so the stack shows.
    "cutaway_rest": dict(objects=parts("rest", hide=("body_right", "lid"), ghost=("sleeve",)),
                         camera={"loc": [330, 20, 120], "target": [0, 6, 78], "lens": 58}),
    "cutaway_open": dict(objects=parts("open", hide=("body_right", "lid"), ghost=("sleeve",)),
                         camera={"loc": [330, 20, 120], "target": [0, 6, 78], "lens": 58}),
}

for name, shot in SHOTS.items():
    if args.only and name != args.only:
        continue
    cfg = dict(shot, out=f"{out}/{name}.png", size=[1000, 1250], samples=args.samples, text=TEXT)
    path = f"{out}/{name}.json"
    json.dump(cfg, open(path, "w"), indent=1)
    r = subprocess.run([sys.executable, f"{here}/render.py", path], capture_output=True, text=True)
    print(name, "ok" if r.returncode == 0 else r.stderr[-2000:], flush=True)
