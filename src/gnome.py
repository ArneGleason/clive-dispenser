"""Clive's sculpted shape as signed distance fields.

Two independent shapes: the body (static) and the head (rides on the lever).
Each is a dict of paint regions so renders and colour prints can be painted
per region. The big volumes around the mechanism (torso, belly, pelvis,
sacrum, bum) are deliberately simple: build.py checks the walls around the
mechanism against them. Surface detail is only ever added on the outside.
"""
import math
from functools import lru_cache

import numpy as np

from noise import fbm
from params import from_torso, to_torso
from sdf import (axis_coords, capsule, chain, ellipse2d, ellipsoid, extrude, length, rbox, round_rect, smax,
                 smin, sphere, ssub, torus, torus_var, union)

# Base paint colours (sRGB 0..1) for each region.
PAINT = {
    "base": (0.80, 0.74, 0.62),
    "sole": (0.20, 0.12, 0.07),
    "boot": (0.47, 0.27, 0.13),
    "lace": (0.82, 0.72, 0.52),
    "trousers": (0.13, 0.26, 0.66),
    "waistband": (0.10, 0.20, 0.55),
    "skin": (0.99, 0.82, 0.70),
    "jacket": (0.14, 0.33, 0.80),
    "cuff": (0.11, 0.27, 0.70),
    "belt": (0.10, 0.08, 0.07),
    "buckle": (0.92, 0.74, 0.27),
    "button": (0.92, 0.74, 0.27),
    "patch": (0.64, 0.47, 0.29),
    "beard": (0.96, 0.94, 0.88),
    "hat": (0.86, 0.10, 0.07),
    "eye": (0.97, 0.97, 0.95),
    "lip": (0.86, 0.36, 0.36),
    "mouth": (0.35, 0.06, 0.06),
}

# Head placement (torso frame) and facing.
HEAD_T = (0.0, 11.0, 64.0)
HEAD_C = from_torso(*HEAD_T)
HEAD_R = 12.5
HEAD_YAW = 100.0  # degrees; positive turns his face toward +x (looking back over his shoulder)

ARM = {s: dict(shoulder=from_torso(19.0 * s, -2.0, 42.0), elbow=(27.0 * s, 10.0, 70.0), wrist=(25.0 * s, -1.0, 50.5))
       for s in (-1, 1)}
BELT_V = 11.0


def head_local(p):
    """Coordinates in a frame centred on the head: a=his right, b=out of his face, c=up."""
    x, y, z = p
    ry = math.radians(HEAD_YAW)
    f = (math.sin(ry), math.cos(ry))
    r = (math.cos(ry), -math.sin(ry))
    dx, dy, dz = x - HEAD_C[0], y - HEAD_C[1], z - HEAD_C[2]
    return dx * r[0] + dy * r[1], dx * f[0] + dy * f[1], dz


def bump(d, p, amp, noise_fn):
    """Push the surface outward by amp * noise (noise in -1..1), only near the surface."""
    m = (d < amp + 0.6) & (d > -2.0)
    if not np.any(m):
        return d
    out = np.array(d, copy=True)
    out[m] = d[m] - amp * (0.5 + 0.5 * noise_fn(tuple(a[m] for a in p)))
    return out


def _first_hit(fn, start, direction, max_d=80.0, step=0.02):
    """Where a ray first enters the solid fn (for placing buttons, laces...)."""
    d = np.asarray(direction, float)
    d /= np.linalg.norm(d)
    s = np.arange(0, max_d, step)
    pts = np.asarray(start, float)[:, None] + d[:, None] * s
    inside = fn((pts[0], pts[1], pts[2])) < 0
    if not inside.any():
        raise ValueError(f"ray from {start} missed")
    return pts[:, int(np.argmax(inside))]


# --- boots -------------------------------------------------------------------
def _boot_upper(p, s):
    bx = 10.5 * s
    toe = ellipsoid(p, (bx + 0.8 * s, 7.0, 14.2), (8.4, 11.0, 6.3))
    heel = ellipsoid(p, (bx, -4.5, 14.8), (7.8, 6.8, 6.6))
    shaft = capsule(p, (bx, -1.0, 13.0), (bx, -1.2, 23.0), 8.0)
    tip = ellipsoid(p, (bx + 1.2 * s, 15.5, 15.6), (5.2, 3.6, 3.4))
    return smin(union([toe, heel, shaft], 2.5), tip, 2.0)


def _boot_sole(p, s):
    x, y, z = p
    bx = 10.5 * s
    fp = smin(ellipse2d(x, y, (bx + 0.8 * s, 7.4), (9.0, 11.8)), ellipse2d(x, y, (bx, -4.8), (8.4, 7.4)), 3.0)
    return extrude(fp, z, 8.6, 12.0, 0.7)


@lru_cache(None)
def _lace_points(s):
    bx = 10.5 * s
    up = lambda q: _boot_upper(q, s)
    rows = []
    for y in (8.0, 10.5, 13.0):
        rows.append([_first_hit(up, (bx + dx, y, 40.0), (0, 0, -1)) for dx in (-2.4, 2.4)])
    return rows


def _laces(p, s):
    rows = _lace_points(s)
    out = None
    for (l0, r0), (l1, r1) in zip(rows, rows[1:]):
        for a, b in ((l0, r1), (r0, l1)):
            d = capsule(p, tuple(a + [0, 0, 0.35]), tuple(b + [0, 0, 0.35]), 0.6)
            out = d if out is None else np.minimum(out, d)
    top = (rows[0][0] + rows[0][1]) / 2 + np.array([0, -0.5, 0.6])
    for side in (-1, 1):   # the bow
        out = np.minimum(out, ellipsoid(p, tuple(top + [side * 2.0, -0.4, 0.5]), (1.9, 0.9, 1.3)))
    return out


# --- trousers round the ankles ------------------------------------------------
def _trousers(p, s):
    x = 10.5 * s
    tr = capsule(p, (x, -1.0, 20.0), (x, -2.0, 40.0), 8.8)
    rolls = [(21.5, 8.9, 2.4, (0.06, 0.04)), (25.5, 9.4, 3.0, (0.10, 0.05)), (30.0, 9.9, 3.4, (-0.12, 0.08)),
             (34.5, 9.5, 3.1, (0.08, -0.10)), (39.0, 10.0, 3.4, (-0.05, 0.12))]
    for z, big, small, (tx, ty) in rolls:
        wob = lambda phi, small=small, z=z: small + 0.6 * np.sin(5 * phi + z) + 0.3 * np.sin(11 * phi + 2 * z)
        tr = smin(tr, torus_var(p, (x + tx * 6, -1.5 + ty * 8, z), (tx * s, ty, 1), big, wob), 2.0)
    return bump(tr, p, 0.7, lambda q: fbm(q, 0.22, 3, seed=7 + s, stretch=(1, 1, 0.45)))


def _waistband(p):
    """The dropped trousers' waistband: a ring round both knees that sags between them."""
    x, y, z = p
    zc = 44.0 - 2.6 * (1 - np.clip((x / 21.5) ** 2, 0, 1))
    ring = np.abs(ellipse2d(x, y, (0, -2.5), (21.5, 11.5)))
    q0, q1 = ring - 0.9 + 0.6, np.abs(z - zc) - 2.2 + 0.6
    return length(np.maximum(q0, 0), np.maximum(q1, 0)) + np.minimum(np.maximum(q0, q1), 0) - 0.6


# --- arms and hands -------------------------------------------------------------
def _sleeve(p, s):
    a = ARM[s]
    sh, el, wr = (np.array(a[k]) for k in ("shoulder", "elbow", "wrist"))
    d = smin(capsule(p, tuple(sh), tuple(el), 7.2, 6.4), capsule(p, tuple(el), tuple(wr), 6.4, 5.6), 2.0)
    for frac, seg in ((0.82, (sh, el)), (0.9, (sh, el)), (0.12, (el, wr)), (0.22, (el, wr))):
        c = seg[0] + (seg[1] - seg[0]) * frac
        d = smin(d, torus(p, tuple(c), tuple(seg[1] - seg[0]), 6.1, 0.9), 1.0)   # elbow creases
    return bump(d, p, 0.3, lambda q: fbm(q, 0.18, 2, seed=30 + s))


def _cuff(p, s):
    a = ARM[s]
    el, wr = np.array(a["elbow"]), np.array(a["wrist"])
    ax = wr - el
    c = wr - ax / np.linalg.norm(ax) * 1.5
    return torus(p, tuple(c), tuple(ax), 5.4, 1.8)


def _hand(p, s):
    palm = ellipsoid(p, (24.4 * s, -1.0, 46.2), (2.8, 4.6, 4.2))
    fingers = [chain(p, [(23.8 * s, yk, 48.6), (21.8 * s, yk, 49.6), (19.6 * s, yk, 47.2), (19.2 * s, yk, 45.2)],
                     [1.75, 1.65, 1.5, 1.35], 0.6) for yk in (-4.2, -1.6, 1.0, 3.5)]
    thumb = chain(p, [(25.3 * s, 2.0, 46.5), (24.8 * s, 5.0, 44.8), (23.4 * s, 6.6, 42.9)], [2.0, 1.7, 1.45], 0.6)
    return smin(smin(palm, union(fingers, 0.4), 1.2), thumb, 1.0)


def _patch(p):
    """Elbow patch on his left sleeve."""
    el = np.array(ARM[-1]["elbow"])
    out = el + 6.0 * np.array([-0.45, -0.85, 0.25]) / np.linalg.norm([-0.45, -0.85, 0.25])
    return smax(_sleeve(p, -1) - 0.45, sphere(p, tuple(out), 5.2), 0.3)


# --- jacket ---------------------------------------------------------------------
def _jacket_core(t):
    torso = ellipsoid(t, (0, -1.5, 27.0), (23.0, 25.0, 26.0))
    belly = smin(ellipsoid(t, (0, 7.5, 8.0), (19.5, 18.0, 15.5)),
                 ellipsoid(t, (0, 12.0, -4.0), (20.0, 15.5, 9.5)), 4.0)  # pot belly hides the tray's front end
    return smin(torso, belly, 3.0)


@lru_cache(None)
def _front_u(v):
    """Front surface of the jacket (torso frame u) on the centre line at height v."""
    return float(_first_hit(_jacket_core, (0, 60.0, v), (0, -1, 0))[1])


def _belt(t):
    return smax(_jacket_core(t) - 1.0, np.abs(t[2] - BELT_V) - 2.3, 0.4)


def _buckle(t):
    uf = _front_u(BELT_V) + 1.0
    frame = rbox(t, (0, uf, BELT_V), (4.4, 1.0, 3.6), 0.6)
    frame = np.maximum(frame, -rbox(t, (0, uf, BELT_V), (2.6, 3.0, 1.8), 0.3))
    prong = capsule(t, (-2.6, uf + 0.6, BELT_V), (0.8, uf + 0.6, BELT_V), 0.5)
    return np.minimum(frame, prong)


def _buttons(t):
    return union([ellipsoid(t, (0, _front_u(v) + 0.3, v), (2.1, 0.9, 2.1)) for v in (19.5, 26.5)])


def _jacket(p, t):
    core = _jacket_core(t)
    hem_r = lambda phi: 6.0 + 0.7 * np.sin(6 * phi + 1.2 * np.sin(3 * phi)) + 0.25 * np.sin(13 * phi)
    hem = torus_var(t, (0, -2.5, 9.0), (0, 0.35, 1), 18.0, hem_r)
    collar = torus_var(t, (0, 2.0, 49.0), (0, 0.4, 1), 12.5, lambda phi: 4.5 + 0.4 * np.sin(5 * phi))
    filler = ellipsoid(t, (0, -15.0, 13.0), (15.0, 8.5, 6.0))   # hidden under the hem; backs the hopper
    j = union([core, hem, collar, filler], 3.0)
    # Horizontal folds across the back where the jacket is hitched up.
    x, u, v = t
    win = np.clip((v - 12) / 4, 0, 1) * np.clip((28 - v) / 4, 0, 1) * np.clip((-u - 4) / 6, 0, 1)
    m = (j < 1.2) & (j > -2) & (win > 0)
    if np.any(m):
        sub = tuple(a[m] for a in t)
        ridge = np.maximum(0, np.sin(1.15 * sub[2] + 1.8 * fbm(sub, 0.08, 2, seed=40))) ** 6
        j = np.array(j, copy=True)
        j[m] = j[m] - 0.6 * ridge * win[m]
    j = bump(j, t, 0.25, lambda q: fbm(q, 0.2, 2, seed=41))
    sleeves = union([_sleeve(p, s) for s in (-1, 1)])
    return smin(j, sleeves, 2.5)


# --- base -----------------------------------------------------------------------
BASE_C, BASE_HX, BASE_HY = (0.0, 6.0), 34.0, 42.0
BASE_FRONT_Y = BASE_C[1] - BASE_HY        # the face that carries the CLIVE lettering
BASE_Z0, BASE_Z1 = -3.0, 9.0


def _base(p):
    x, y, z = p
    d = extrude(round_rect(x, y, BASE_C, BASE_HX, BASE_HY, 13.0), z, BASE_Z0, BASE_Z1, 1.4)
    panel = np.clip((24 - np.abs(x)) / 3, 0, 1) * np.clip((BASE_FRONT_Y + 4 - y) / 2, 0, 1)
    m = (d > -2) & (d < 1)
    if np.any(m):  # rough stone with shallow pits, but a smooth nameplate under the lettering
        sub = tuple(a[m] for a in p)
        rough = 0.35 * (0.5 + 0.5 * fbm(sub, 0.3, 3, seed=3))
        pit = 0.5 * np.clip((fbm(sub, 0.45, 2, seed=4) - 0.45) / 0.25, 0, 1)
        d = np.array(d, copy=True)
        d[m] = d[m] + (pit - rough) * (1 - panel[m])
    return d


def body_regions(p):
    t = to_torso(p)
    reg = {"base": _base(p)}
    reg["sole"] = union([_boot_sole(p, s) for s in (-1, 1)])
    reg["boot"] = bump(union([_boot_upper(p, s) for s in (-1, 1)]), p, 0.2, lambda q: fbm(q, 0.35, 2, seed=5))
    reg["lace"] = union([_laces(p, s) for s in (-1, 1)])
    reg["trousers"] = union([_trousers(p, s) for s in (-1, 1)])
    reg["waistband"] = _waistband(p)

    legs, cheeks = [], []
    for s in (-1, 1):
        x = 10.5 * s
        legs.append(capsule(p, (x * 0.98, -2.5, 40), (x * 0.95, -6, 60), 9.4))
        cheeks.append(ellipsoid(t, (10.5 * s, -12.5, -1.0), (14.0, 15.0, 15.0)))
    pelvis = ellipsoid(t, (0, -6.0, -6.0), (11.0, 16.0, 7.5))     # floor under the tray channel
    sacrum = ellipsoid(t, (0, -15.5, 8.0), (9.0, 8.0, 9.0))       # backs the bottom of the hopper
    skin = smin(smin(union(cheeks, 1.0), union([pelvis, sacrum], 2.0), 3.0), union(legs), 3.0)
    reg["skin"] = smin(skin, union([_hand(p, s) for s in (-1, 1)]), 1.0)

    reg["jacket"] = _jacket(p, t)
    reg["cuff"] = union([_cuff(p, s) for s in (-1, 1)])
    reg["belt"] = _belt(t)
    reg["buckle"] = _buckle(t)
    reg["button"] = _buttons(t)
    reg["patch"] = _patch(p)
    return reg


# --- head -----------------------------------------------------------------------
HAT_BASE = (HEAD_C[0], HEAD_C[1] - 2.5, HEAD_C[2] + 10.5)


def _hat(p):
    hb = np.array(HAT_BASE)
    pts = [hb, hb + (0, -2.5, 13.0), hb + (-0.5, -7.0, 26.0), hb + (-2.5, -15.5, 38.0), hb + (-4.0, -21.0, 41.5)]
    hat = chain(p, [tuple(q) for q in pts], [13.6, 11.2, 7.4, 2.6, 0.9], 2.0)
    hat = smax(hat, hb[2] - 0.8 - p[2], 0.6)   # flat bottom: the hat sits on the head, not over the face
    h, _, ang = axis_coords(p, tuple(hb), tuple(pts[3] - hb))
    m = (hat < 1.5) & (hat > -2)
    if np.any(m):  # soft creases spiralling up the cone
        sub = tuple(a[m] for a in p)
        fold = (0.5 + 0.5 * np.sin(5 * ang[m] + 0.18 * h[m] + 2.2 * fbm(sub, 0.06, 2, seed=21))) ** 2
        win = np.clip(h[m] / 6, 0, 1) * np.clip((38 - h[m]) / 8, 0, 1)
        hat = np.array(hat, copy=True)
        hat[m] = hat[m] - 0.7 * fold * win
    hat = bump(hat, p, 0.25, lambda q: fbm(q, 0.15, 2, seed=22))
    brim = torus_var(p, tuple(hb + (0, 0, 0.2)), (0, -0.12, 1), 12.9, lambda phi: 2.3 + 0.35 * np.sin(4 * phi + 1))
    return smin(hat, brim, 1.0)


def head_regions(p):
    q = head_local(p)
    reg = {}
    skin = [ellipsoid(q, (0, 0, 0.8), (HEAD_R, HEAD_R, 13.5)),
            ellipsoid(q, (0, 4.0, -4.0), (11.0, 9.0, 9.0)),            # jaw
            ellipsoid(q, (0, 13.0, -0.8), (5.0, 4.8, 5.0)),            # nose bulb
            capsule(q, (0, 11.2, 3.5), (0, 12.5, 0.5), 2.2),           # bridge
            sphere(q, (-6.6, 8.8, -3.6), 4.3), sphere(q, (6.6, 8.8, -3.6), 4.3)]   # cheeks
    for s in (-1, 1):
        skin.append(ssub(ellipsoid(q, (12.3 * s, -0.5, 0.5), (2.4, 4.2, 5.4)),
                         ellipsoid(q, (13.6 * s, 0.2, 0.3), (1.6, 2.6, 3.6)), 0.6))      # ears
    d = union(skin, 1.5)
    for s in (-1, 1):
        d = ssub(d, sphere(q, (1.9 * s, 15.2, -4.3), 1.1), 0.6)                         # nostrils
        d = ssub(d, ellipsoid(q, (4.5 * s, 11.6, 4.2), (2.8, 1.6, 2.2)), 1.0)            # eye sockets
    lids = [chain(q, [(-2.3, 11.4, 5.6), (-4.5, 12.0, 6.1), (-6.8, 11.2, 5.4)], [0.9, 1.0, 0.8]),   # open eye
            chain(q, [(2.2, 11.9, 4.4), (4.5, 12.4, 3.8), (6.8, 11.6, 4.3)], [1.0, 1.15, 0.9])]    # wink
    lids.append(chain(q, [(-2.4, 11.6, 2.6), (-4.5, 12.2, 2.3), (-6.7, 11.4, 2.9)], [0.8, 0.95, 0.7]))  # smiling lower lid
    d = smin(d, union(lids), 0.6)
    # Neck stub below the head that holds the lever socket (torso frame; must not move).
    reg["skin"] = smin(d, capsule(to_torso(p), (0, 10.0, 58.0), (0, 9.0, 47.5), 7.0), 2.0)
    reg["eye"] = union([sphere(q, (-4.5, 10.6, 4.2), 2.0), sphere(q, (4.5, 10.2, 3.8), 1.7)])
    grin = [(-4.8, 11.4, -6.0), (-2.4, 12.6, -8.0), (0.0, 13.0, -8.6), (2.4, 12.6, -8.0), (4.8, 11.4, -6.0)]
    reg["mouth"] = chain(q, [(g[0] * 0.9, g[1] - 0.9, g[2]) for g in grin], [0.6, 0.8, 0.9, 0.8, 0.6])
    reg["lip"] = ellipsoid(q, (0, 12.5, -9.7), (2.6, 1.2, 0.9))

    beard = [ellipsoid(q, (0, 6.0, -10.0), (11.0, 6.8, 11.5))]
    for i in range(11):
        f = -1.35 + 2.7 * i / 10
        sf, cf = math.sin(f), math.cos(f)
        beard.append(chain(q, [(10.5 * sf, 3.0 + 6.5 * cf, -3.0 - 2.5 * cf), (7.5 * sf, 6.0 + 5.5 * cf, -12.0 - 3 * cf),
                               (2.5 * sf, 8.5 + 3.0 * cf, -21.5 - 2.5 * cf), (1.2 * sf, 10.5 + 1.5 * cf, -23.5 - 1.5 * cf)],
                           [3.4, 3.0, 2.0, 0.9], 0.8))
    for s in (-1, 1):
        beard.append(chain(q, [(0.8 * s, 13.3, -4.6), (4.5 * s, 13.0, -5.9), (8.5 * s, 11.0, -5.6),
                               (10.6 * s, 8.8, -3.4), (10.2 * s, 8.4, -1.6)], [2.4, 2.6, 2.0, 1.3, 0.8], 0.6))  # moustache
        beard.append(chain(q, [(2.0 * s, 12.2, 7.2), (5.0 * s, 12.2, 8.8), (8.6 * s, 10.6, 7.6)], [0.9, 1.15, 0.6]))  # arched brows
        beard.append(chain(q, [(3.2 * s, 11.6, 8.2), (6.2 * s, 11.4, 9.6), (9.6 * s, 9.8, 8.8)], [0.8, 1.0, 0.5]))
        beard.append(ellipsoid(q, (10.8 * s, 2.0, -3.0), (3.0, 4.0, 6.0)))               # sideburns
    beard.append(ellipsoid(q, (0, -4.0, -5.0), (12.6, 9.5, 8.5)))                       # hair at the back
    hair = ssub(union(beard, 0.8), chain(q, grin, [0.9, 1.2, 1.3, 1.2, 0.9]), 0.5)   # open a grin under the moustache
    reg["beard"] = bump(hair, q, 0.45, lambda r: fbm(r, 0.55, 2, seed=11, stretch=(1.0, 1.0, 0.22)))
    reg["hat"] = _hat(p)
    return reg


def combine(regions, k=0.8):
    return union(list(regions.values()), k)


def label(regions):
    names = list(regions)
    stack = np.stack([regions[n] for n in names])
    return [names[i] for i in np.argmin(stack, axis=0)]


def region_weights(regions, soft=0.2):
    names = list(regions)
    stack = np.stack([regions[n] for n in names])
    w = np.exp(-(stack - stack.min(axis=0)) / soft)
    return names, w / w.sum(axis=0)


def paint_colours(regions, soft=0.2):
    """Flat per-point colour, softly blended across region borders."""
    names, w = region_weights(regions, soft)
    cols = np.array([PAINT[n] for n in names])
    return w.T @ cols
