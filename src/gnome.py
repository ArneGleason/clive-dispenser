"""Clive's sculpted shape as signed distance fields.

Two independent shapes: the body (static) and the head (rides on the lever).
Each is a dict of paint regions so renders can be coloured per region.
"""
import math

import numpy as np

from params import from_torso, to_torso
from sdf import capsule, ellipsoid, round_slab, smin, sphere, torus, union

# Paint colours (linear-ish sRGB 0..1) used by the renderer.
PAINT = {
    "base": (0.78, 0.72, 0.60),
    "boot": (0.36, 0.20, 0.10),
    "trousers": (0.10, 0.22, 0.62),
    "skin": (0.98, 0.80, 0.68),
    "jacket": (0.12, 0.30, 0.78),
    "beard": (0.95, 0.92, 0.84),
    "hat": (0.85, 0.08, 0.06),
    "cheek": (0.98, 0.55, 0.50),
    "eye": (0.05, 0.04, 0.04),
}

# Head placement (torso frame) and facing.
HEAD_T = (0.0, 11.0, 64.0)
HEAD_C = from_torso(*HEAD_T)
HEAD_R = 12.5
HEAD_YAW = 100.0  # degrees; positive turns his face toward +x (looking back over his shoulder)


def _head_local(p):
    """Coordinates in a frame centred on the head: a=right, b=face, c=up."""
    x, y, z = p
    ry = math.radians(HEAD_YAW)
    f = (math.sin(ry), math.cos(ry))
    r = (math.cos(ry), -math.sin(ry))
    dx, dy, dz = x - HEAD_C[0], y - HEAD_C[1], z - HEAD_C[2]
    return dx * r[0] + dy * r[1], dx * f[0] + dy * f[1], dz


def _bunched_trousers(p, x):
    """Baggy trousers round the ankles: a stack of uneven rolls."""
    tr = capsule(p, (x, -1.0, 21.0), (x, -2.0, 40.0), 8.8)
    rolls = [(24.0, 9.2, 3.0, (0.10, 0.05)), (29.0, 9.8, 3.4, (-0.12, 0.08)),
             (34.5, 9.4, 3.1, (0.08, -0.10)), (39.5, 10.0, 3.5, (-0.05, 0.12))]
    for z, big, small, (tx, ty) in rolls:
        tr = smin(tr, torus(p, (x + tx * 6, -1.5 + ty * 8, z), (tx * (1 if x > 0 else -1), ty, 1), big, small), 2.2)
    for i, (dx, dy, dz) in enumerate([(6, 4, 27), (-6, -4, 32), (5, -6, 37), (-5, 6, 31), (0, 8, 36)]):
        tr = smin(tr, ellipsoid(p, (x + dx * 0.9, -1.5 + dy * 0.9, dz), (4.0, 4.0, 3.0)), 2.0)
    return tr


def body_regions(p):
    t = to_torso(p)
    reg = {}
    reg["base"] = round_slab(p, (0, 7), 34, 42, 0.0, 9.0, 2.0)

    boots, trousers, legs, cheeks, hands, sleeves = [], [], [], [], [], []
    for s in (-1, 1):
        x = 10.5 * s
        boots.append(smin(ellipsoid(p, (x, 5, 13.5), (9.2, 15.5, 7.8)),
                          capsule(p, (x, -1, 10), (x, -1, 22), 8.4), 2.5))
        trousers.append(_bunched_trousers(p, x))
        legs.append(capsule(p, (x * 0.98, -2.5, 40), (x * 0.95, -6, 60), 9.4))
        cheeks.append(ellipsoid(t, (10.5 * s, -12.5, -1.0), (14.0, 15.0, 15.0)))
        hand = (19.5 * s, 2.0, 45.0)
        hands.append(smin(sphere(p, hand, 5.4),
                          capsule(p, hand, (20.0 * s, 6.5, 42.5), 2.4), 1.5))
        shoulder = from_torso(19.0 * s, -2.0, 42.0)
        elbow = (26.0 * s, 14.0, 70.0)
        wrist = (20.5 * s, 3.5, 50.0)
        sleeves.append(smin(capsule(p, shoulder, elbow, 7.2, 6.4),
                            capsule(p, elbow, wrist, 6.4, 5.6), 2.0))

    reg["boot"] = union(boots)
    reg["trousers"] = union(trousers)
    # The cheeks get only a tiny blend so the cleft stays crisp.
    pelvis = ellipsoid(t, (0, -6.0, -6.0), (11.0, 16.0, 7.5))     # floor under the tray channel
    sacrum = ellipsoid(t, (0, -15.5, 8.0), (9.0, 8.0, 9.0))       # backs the bottom of the hopper
    reg["skin"] = smin(smin(union(cheeks, 1.0), union([pelvis, sacrum], 2.0), 3.0), union(legs), 3.5)
    reg["skin"] = smin(reg["skin"], union(hands), 1.0)

    torso = ellipsoid(t, (0, -1.5, 27.0), (23.0, 25.0, 26.0))
    belly = smin(ellipsoid(t, (0, 7.5, 8.0), (19.5, 18.0, 15.5)),
                 ellipsoid(t, (0, 12.0, -4.0), (20.0, 15.5, 9.5)), 4.0)  # pot belly hides the tray's front end
    hem = torus(t, (0, -2.5, 9.0), (0, 0.35, 1), 18.0, 5.5)
    collar = torus(t, (0, 2.0, 49.0), (0, 0.4, 1), 12.5, 4.5)
    reg["jacket"] = smin(union([torso, belly, hem, collar], 3.0), union(sleeves), 2.5)
    return reg


def head_regions(p):
    a, b, c = _head_local(p)
    q = (a, b, c)
    reg = {}
    skin = [sphere(q, (0, 0, 0), HEAD_R),
            ellipsoid(q, (0, 11.8, -1.0), (4.6, 4.6, 5.0)),          # nose
            ellipsoid(q, (-12.0, -1.0, 0.5), (2.6, 4.0, 5.2)),       # ears
            ellipsoid(q, (12.0, -1.0, 0.5), (2.6, 4.0, 5.2))]
    reg["skin"] = union(skin, 1.5)
    reg["cheek"] = union([sphere(q, (-6.2, 8.8, -2.5), 4.4),
                          sphere(q, (6.2, 8.8, -2.5), 4.4)], 0.5)
    reg["eye"] = union([sphere(q, (-4.3, 11.2, 2.6), 1.7),
                        sphere(q, (4.3, 11.2, 2.6), 1.7)])
    beard = [ellipsoid(q, (0, 6.5, -9.0), (12.0, 7.5, 12.5)),
             ellipsoid(q, (-4.2, 11.0, -5.8), (5.2, 2.8, 2.6)),      # moustache
             ellipsoid(q, (4.2, 11.0, -5.8), (5.2, 2.8, 2.6)),
             capsule(q, (-8.0, 10.0, 6.0), (-2.5, 11.2, 6.8), 1.5),  # brows
             capsule(q, (2.5, 11.2, 6.8), (8.0, 10.0, 6.0), 1.5),
             ellipsoid(q, (0, -3.0, -6.0), (12.8, 9.0, 8.0))]        # back of beard / hair
    reg["beard"] = union(beard, 1.2)

    # Hat: a bent cone, built in global coordinates so it points up.
    x, y, z = p
    hc = HEAD_C
    base = (hc[0], hc[1] - 2.0, hc[2] + 6.5)
    mid = (base[0], base[1] - 6.0, base[2] + 22.0)
    tip = (base[0] - 3.0, base[1] - 17.0, base[2] + 41.0)
    hat = smin(capsule(p, base, mid, 13.6, 8.0), capsule(p, mid, tip, 8.0, 1.2), 2.0)
    hat = smin(hat, torus(p, base, (0, -0.1, 1), 12.6, 2.2), 1.0)
    reg["hat"] = hat
    # Neck stub below the head that holds the lever socket.
    reg["skin"] = smin(reg["skin"], capsule(to_torso(p), (0, 10.0, 58.0), (0, 9.0, 47.5), 7.0), 2.0)
    return reg


def combine(regions, k=1.2):
    return union(list(regions.values()), k)


def label(regions):
    names = list(regions)
    stack = np.stack([regions[n] for n in names])
    return [names[i] for i in np.argmin(stack, axis=0)]


def paint_colours(regions, soft=0.35):
    """Per-point colour, softly blended across region borders."""
    names = list(regions)
    stack = np.stack([regions[n] for n in names])
    w = np.exp(-(stack - stack.min(axis=0)) / soft)
    w /= w.sum(axis=0)
    cols = np.array([PAINT[n] for n in names])
    return (w.T @ cols)
