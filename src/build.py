"""Build every printable part of Clive, check the mechanism, export files.

    python3 build.py OUT_DIR [--grid 0.45]

Writes OUT_DIR/stl/*.stl (print files), OUT_DIR/ply/*.ply (coloured, for
renders) and OUT_DIR/report.md (the virtual test results).
"""
import argparse
import json
import math
import os
import time

import manifold3d as mf
import numpy as np
import trimesh

import gnome
import mechanism as M
import params as P
from meshing import save_ply, save_stl, sdf_mesh, to_manifold

ap = argparse.ArgumentParser()
ap.add_argument("out")
ap.add_argument("--grid", type=float, default=P.GRID)
args = ap.parse_args()
for d in ("stl", "ply"):
    os.makedirs(os.path.join(args.out, d), exist_ok=True)
T0 = time.time()
log = []


def say(msg):
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)
    log.append(msg)


def body_sdf(p):
    return gnome.combine(gnome.body_regions(p))


def head_sdf(p):
    return gnome.combine(gnome.head_regions(p))


# --- sculpt -----------------------------------------------------------------
BODY_BOX = ((-45, -45, -1), (45, 52, 118))
HEAD_BOX = ((-30, 10, 70), (30, 70, 165))
sculpt = to_manifold(*sdf_mesh(body_sdf, *BODY_BOX, step=args.grid))
head_raw = to_manifold(*sdf_mesh(head_sdf, *HEAD_BOX, step=args.grid))
head_fat = to_manifold(*sdf_mesh(lambda p: head_sdf(p) - 0.63, *HEAD_BOX, step=max(args.grid, 0.6)))
TEXT_STL = os.path.join(os.path.dirname(__file__), "..", "assets", "clive_text.stl")
if os.path.exists(TEXT_STL):
    tm = trimesh.load(TEXT_STL)
    sculpt = sculpt + to_manifold(tm.vertices, tm.faces)
    TEXT_BOUNDS = tm.bounds
else:
    TEXT_BOUNDS = None
say(f"sculpt meshed: body {sculpt.num_tri()} tris, head {head_raw.num_tri()} tris")

# --- how far back does the bum stick out across the tray footprint? -------
xs = np.linspace(-P.TRAY_W / 2, P.TRAY_W / 2, 21)
vs = np.linspace(-P.TRAY_H, 0, 9)
us = np.arange(-50, 0, 0.1)
X, V, U = np.meshgrid(xs, vs, us, indexing="ij")
inside = body_sdf(P.from_torso(X, U, V)) < 0
first = np.where(inside.any(axis=2), us[np.argmax(inside, axis=2)], np.inf)
rear_u = float(first.min())
D = M.Design(rear_u)
say(f"bum surface at u={rear_u:.1f}; tray travel {D.travel:.1f} mm; head tilt {D.theta:.1f} deg; "
    f"pin at u={D.pin_u:.1f}")

# --- parts ------------------------------------------------------------------
g = M.to_global
cav = g(D.cavities())
angles = np.linspace(-D.over, D.theta + D.over, 28)
head_sweep = mf.Manifold.batch_boolean(
    [g(M.tilt(M.to_torso_frame(head_fat), a)) for a in angles], mf.OpType.Add)
lid = sculpt ^ g(D.lid_region())

# Alignment dowels (1.75 mm filament) wherever the split face has solid material.
dowel_r = 1.0
candidates = [(0, 22, 4.5), (0, -20, 4.5), (0, 40, 4.5)] + \
             [P.from_torso(0, u, v) for u, v in [(-3, 46), (-14, -10), (12, -12), (-22, 20), (16, 22), (0, 50)]]
dowels = []
for c in candidates:
    test = mf.Manifold.cylinder(14, 2.6, circular_segments=24).rotate((0, 90, 0)).translate((-7, c[1], c[2]))
    if (test - sculpt).volume() < 1e-3 and (test ^ cav).volume() < 1e-3 and (test ^ head_sweep).volume() < 1e-3 \
            and (test ^ lid).volume() < 1e-3:
        dowels.append(c)
dowel_cut = mf.Manifold.batch_boolean(
    [mf.Manifold.cylinder(13, dowel_r, circular_segments=24).rotate((0, 90, 0)).translate((-6.5, c[1], c[2])) for c in dowels],
    mf.OpType.Add) if dowels else mf.Manifold()
say(f"{len(dowels)} alignment dowels placed")

body = sculpt - cav - head_sweep - lid - dowel_cut
left, right = body.split_by_plane((1, 0, 0), 0.0)  # (x >= 0, x < 0)


def drop_slivers(m):
    """Keep real pieces only (the split can leave zero-volume crumbs)."""
    parts = [c for c in m.decompose() if c.volume() > 1.0]
    return mf.Manifold.batch_boolean(parts, mf.OpType.Add), len(parts)


left, nl = drop_slivers(left)
right, nr = drop_slivers(right)
if nl > 1 or nr > 1:
    say(f"WARNING: a body half has loose pieces ({nl}, {nr})")
right, left = left, right

head = head_raw - g(D.head_socket())
lever = g(D.lever())
pin = g(D.pin())
axle = g(D.axle())
trays = {c: g(D.tray(c)) ^ (sculpt + g(M.box(-20, 20, D.rear_u + 4, 60, -30, 30))) for c in P.CANDY}
sleeves = {c: g(D.sleeve(c)) for c in P.CANDY}
say("parts built")

# --- virtual tests ----------------------------------------------------------
report = {"travel_mm": round(D.travel, 2), "head_tilt_deg": round(D.theta, 1), "checks": []}
ok_all = True


def check(name, ok, detail=""):
    global ok_all
    ok_all &= ok
    report["checks"].append({"name": name, "ok": bool(ok), "detail": detail})
    say(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")


for c in P.CANDY:
    ok, msgs = P.candy_checks(c)
    check(f"candy fit: {c}", ok, "; ".join(msgs))

for name, m in [("body", body), ("left half", left), ("right half", right), ("head", head), ("lever", lever),
                ("lid", lid)] + [(f"tray {c}", t) for c, t in trays.items()] + [(f"sleeve {c}", s) for c, s in sleeves.items()]:
    check(f"solid is watertight: {name}", m.status() == mf.Error.NoError and m.volume() > 0,
          f"volume {m.volume() / 1000:.1f} cm3, genus {m.genus()}")

# Range of motion: step the head from rest to full tilt and look for collisions.
EPS = 0.05  # mm^3 of overlap we treat as numerical noise
worst = {}
for a in np.linspace(0, D.theta, 12):
    s = D.tray_shift(a)
    tilt = lambda m: g(M.tilt(M.to_torso_frame(m), a))
    shift = lambda m: m.translate((0, s * P.CA, -s * P.SA))
    L, H, PN = tilt(lever), tilt(head), tilt(pin)
    for c in P.CANDY:
        T = shift(trays[c])
        pairs = {"lever/body": (L, body), "head/body": (H, body), "tray/body": (T, body),
                 "pin/body": (PN, body), "tray/sleeve": (T, sleeves[c]), "lever/sleeve": (L, sleeves[c]),
                 "lever/tray": (L, T), "pin/tray": (PN, T), "head/tray": (H, T), "lid/lever": (lid, L)}
        for k, (m1, m2) in pairs.items():
            vol = (m1 ^ m2).volume()
            worst[k] = max(worst.get(k, 0), vol)
for k, vol in worst.items():
    if vol >= EPS and k.startswith("lever"):
        a = D.theta
        for i, piece in enumerate(D.lever_parts()):
            other = body if k == "lever/body" else None
            if other is not None:
                say(f"  lever piece {i} overlap at full tilt: {(g(M.tilt(piece, a)) ^ other).volume():.2f}")
    check(f"no collision through full travel: {k}", vol < EPS, f"max overlap {vol:.3f} mm3")

# Does a candy in the pocket come fully out of the bum at full travel?
for c in P.CANDY:
    bx, bu = P.sleeve_bore(c)
    pocket = g(M.box(-bx / 2, bx / 2, P.SLEEVE_U - bu / 2, P.SLEEVE_U + bu / 2, -2, 0))
    out = pocket.translate((0, -D.travel * P.CA, D.travel * P.SA))
    check(f"pocket fully outside at full travel: {c}", (out ^ sculpt).volume() < EPS,
          f"overlap {(out ^ sculpt).volume():.2f} mm3")

# Wall thickness around closed cavities, measured against the sculpt surface.
pts, _ = trimesh.sample.sample_surface_even(trimesh.Trimesh(*[np.asarray(a) for a in (
    cav.to_mesh().vert_properties[:, :3], cav.to_mesh().tri_verts)], process=False), 40000, seed=1)
x, u, v = P.to_torso((pts[:, 0], pts[:, 1], pts[:, 2]))
intentional = (u < D.rear_u + 8) & (v < 1)                    # the bum hatch
intentional |= v > P.SLEEVE_TOP_V - 1                         # refill opening
intentional |= np.abs(x) > 10.5                               # axle hole ends live in the split face plane
depth = -body_sdf((pts[:, 0], pts[:, 1], pts[:, 2]))
thin = (~intentional) & (depth < P.MIN_WALL)
if thin.any():
    bad = pts[thin]
    tx, tu, tv = P.to_torso((bad[:, 0], bad[:, 1], bad[:, 2]))
    cells = {}
    for a, b, c, d in zip(tx, tu, tv, depth[thin]):
        key = (int(round(a / 6) * 6), int(round(b / 6) * 6), int(round(c / 6) * 6))
        cells[key] = min(cells.get(key, 99), d)
    worst_cells = sorted(cells.items(), key=lambda kv: kv[1])[:8]
    detail = f"{thin.sum()} of {len(pts)} samples thinner than {P.MIN_WALL} mm; worst cells (x,u,v): " + \
             ", ".join(f"{k}:{d:.1f}" for k, d in worst_cells)
else:
    detail = f"thinnest wall {depth[~intentional].min():.2f} mm"
check("walls around the mechanism", not thin.any(), detail)

spring = D.spring_report()
report["spring"] = spring
say(f"spring: rest length {spring['rest_length']:.1f} mm, pressed {spring['pressed_length']:.1f} mm; "
    f"use OD <= {spring['max_od']} mm, free length {spring['recommended_free_length'][0]:.0f}-"
    f"{spring['recommended_free_length'][1]:.0f} mm")
report["capacity"] = {c: int((P.SLEEVE_TOP_V - P.SLEEVE_GAP_BOTTOM) // P.CANDY[c]["thick"]) + 1 for c in P.CANDY}
report["all_ok"] = bool(ok_all)

# --- export -----------------------------------------------------------------
stl = os.path.join(args.out, "stl")
save_stl(left, f"{stl}/body_left.stl")
save_stl(right, f"{stl}/body_right.stl")
save_stl(head, f"{stl}/head.stl")
save_stl(lever, f"{stl}/lever.stl")
save_stl(lid, f"{stl}/refill_lid.stl")
save_stl(pin, f"{stl}/tray_pin_3mm_optional.stl")
save_stl(axle, f"{stl}/axle_3mm_optional.stl")
for c in P.CANDY:
    save_stl(trays[c], f"{stl}/tray_{c}.stl")
    save_stl(sleeves[c], f"{stl}/hopper_{c}.stl")


def paint(fn):
    def colour(v):
        c = gnome.paint_colours(fn((v[:, 0], v[:, 1], v[:, 2])))
        if TEXT_BOUNDS is not None:
            lo, hi = TEXT_BOUNDS
            on_text = np.all((v >= lo - 0.05) & (v <= hi + 0.05), axis=1) & (v[:, 2] > 9.05)
            c[on_text] = (0.10, 0.07, 0.05)
        return c
    return colour


ply = os.path.join(args.out, "ply")
MECH = {"lever": (0.92, 0.75, 0.20), "tray": (0.95, 0.93, 0.88), "sleeve": (0.55, 0.75, 0.95), "pin": (0.6, 0.6, 0.62)}
CANDY_COLOURS = [(0.98, 0.55, 0.70), (0.98, 0.85, 0.30), (0.98, 0.60, 0.35)]


def candy_solid(c):
    k = P.CANDY[c]
    r = min(k["thick"], k["width"]) * (0.45 if k["shape"] == "pill" else 0.18)
    L, W, H = k["length"] / 2 - r, k["width"] / 2 - r, k["thick"] / 2 - r
    corners = [mf.Manifold.sphere(r, 24).translate((sx * L, su * W, sv * H))
               for sx in (-1, 1) for su in (-1, 1) for sv in (-1, 1)]
    return mf.Manifold.batch_hull(corners)


def untilt(v, a):
    """Undo a head tilt on global vertex positions (for colouring)."""
    x, u, w = P.to_torso((v[:, 0], v[:, 1], v[:, 2]))
    t = math.radians(a)
    ru, rv = u - P.PIVOT_U, w - P.PIVOT_V
    u2 = P.PIVOT_U + ru * math.cos(t) - rv * math.sin(t)
    v2 = P.PIVOT_V + ru * math.sin(t) + rv * math.cos(t)
    return np.stack(P.from_torso(x, u2, v2), axis=1)


for pose, a in (("rest", 0.0), ("open", D.theta)):
    s = D.tray_shift(a)
    tilt = lambda m: g(M.tilt(M.to_torso_frame(m), a))
    shift = lambda m: m.translate((0, s * P.CA, -s * P.SA))
    for side, m in (("left", left), ("right", right)):
        save_ply(m, f"{ply}/{pose}_body_{side}.ply", paint(gnome.body_regions))
    save_ply(lid, f"{ply}/{pose}_lid.ply", paint(gnome.body_regions))
    save_ply(tilt(head), f"{ply}/{pose}_head.ply", lambda v: paint(gnome.head_regions)(untilt(v, a)))
    save_ply(tilt(lever), f"{ply}/{pose}_lever.ply", color=MECH["lever"])
    save_ply(tilt(pin), f"{ply}/{pose}_pin.ply", color=MECH["pin"])
    save_ply(axle, f"{ply}/{pose}_axle.ply", color=MECH["pin"])
    save_ply(g(D.spring_coil(a)), f"{ply}/{pose}_spring.ply", color=(0.75, 0.76, 0.80))
    save_ply(shift(trays["pez"]), f"{ply}/{pose}_tray.ply",
             lambda v: paint(gnome.body_regions)(v - np.array([0, s * P.CA, -s * P.SA])))
    save_ply(sleeves["pez"], f"{ply}/{pose}_sleeve.ply", color=MECH["sleeve"])
    # Candies: one in the pocket, the rest stacked in the hopper.
    t = P.CANDY["pez"]["thick"]
    depth = t + P.POCKET_EXTRA
    spots = [(P.SLEEVE_U + s, -depth + t / 2)]
    floor = -depth + t if pose == "rest" else 0.0   # stack rests on the pocket candy, or on the tray top
    spots += [(P.SLEEVE_U, floor + t / 2 + i * t) for i in range(6)]
    for i, (cu, cv) in enumerate(spots):
        save_ply(g(candy_solid("pez").translate((0, cu, cv))), f"{ply}/{pose}_candy{i}.ply",
                 color=CANDY_COLOURS[i % 3])

with open(os.path.join(args.out, "report.json"), "w") as f:
    json.dump(report, f, indent=2)
say(f"ALL CHECKS {'PASSED' if ok_all else 'DID NOT PASS'}")
