"""Turn 10 · Fable 2: new fists and a new bust for Clive, sculpted as signed-distance clay.

Everything here is in turn 9's frame (millimetres, +Z up, Clive faces -Y, +X is his
left and winking side) so the parts drop straight into Clive-GarmentAndHair.blend
beside the cap, smock, trousers and boots that this turn keeps.

    python sculpt_parts.py outdir [--voxel 0.16] [--only hands|bust]

Writes hand_L.ply, hand_R.ply and bust.ply. Vertex colour carries bookkeeping, not
paint: red = material group * 25, green = blush 0..255, blue = freckle mask.
assemble_turn.py turns those into material slots and attributes.
"""
import argparse
import math
from pathlib import Path

import numpy as np
import torch

dev = "cuda" if torch.cuda.is_available() else "cpu"
BIG = 1e3


def V(*a):
    return torch.tensor(a, dtype=torch.float32, device=dev)


# ---------------------------------------------------------------- clay tools
def smin(a, b, k):
    h = torch.clamp(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b + (a - b) * h - k * h * (1 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


def sphere(p, c, r):
    return (p - V(*c)).norm(dim=-1) - r


def ellipsoid(p, c, r, rot=None):
    q = p - V(*c)
    if rot is not None:
        q = q @ torch.tensor(rot, dtype=torch.float32, device=dev)
    r = V(*r)
    k0 = (q / r).norm(dim=-1)
    k1 = (q / (r * r)).norm(dim=-1)
    return k0 * (k0 - 1) / (k1 + 1e-9)


def rot_xyz(rx=0.0, ry=0.0, rz=0.0):
    """Columns are the ellipsoid's own axes in world space (degrees in)."""
    rx, ry, rz = (math.radians(a) for a in (rx, ry, rz))
    cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return (Rz @ Ry @ Rx)


def catmull(pts, rs, sub, closed=False):
    P = np.c_[np.asarray(pts, float), np.asarray(rs, float)]
    n = len(P)
    out = []
    for i in range(n if closed else n - 1):
        if closed:
            p0, p1, p2, p3 = P[(i - 1) % n], P[i], P[(i + 1) % n], P[(i + 2) % n]
        else:
            p0, p1, p2, p3 = P[max(i - 1, 0)], P[i], P[i + 1], P[min(i + 2, n - 1)]
        for j in range(sub):
            t = j / sub
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[0] if closed else P[-1])
    out = np.array(out)
    out[:, 3] = np.maximum(out[:, 3], 0.45)
    return out[:, :3], out[:, 3]


def chain(p, pts, rs, sub=5, closed=False, margin=4.0, squash=None):
    """A swept, tapering strand through control points.

    squash=(direction, factor) flattens the cross-section along `direction`, so a
    strand becomes a ribbon: the way carved hair locks and cloth rolls are built.
    """
    pts, rs = catmull(pts, rs, sub, closed)
    lo = pts.min(0) - rs.max() - margin
    hi = pts.max(0) + rs.max() + margin
    inside = ((p > V(*lo)) & (p < V(*hi))).all(dim=-1)
    out = torch.full((p.shape[0],), BIG, device=dev)
    if not inside.any():
        return out
    q = p[inside]
    best = torch.full((q.shape[0],), BIG, device=dev)
    if squash is not None:
        sd = V(*squash[0])
        sd = sd / sd.norm()
        sf = float(squash[1])
    for i in range(len(pts) - 1):
        a, b = V(*pts[i]), V(*pts[i + 1])
        pa, ba = q - a, b - a
        h = torch.clamp((pa @ ba) / (ba @ ba + 1e-9), 0, 1)
        off = pa - ba * h[:, None]
        if squash is not None:
            along = off @ sd
            off = off + sd[None, :] * (along * (1 / sf - 1))[:, None]
            d = (off.norm(dim=-1) - (rs[i] + (rs[i + 1] - rs[i]) * h)) * min(1.0, sf)
        else:
            d = off.norm(dim=-1) - (rs[i] + (rs[i + 1] - rs[i]) * h)
        best = torch.minimum(best, d)
    out[inside] = best
    return out


def groove_line(p, pts, w, depth, sub=4):
    """A V-ish trench of the given depth along a 3-D polyline: add the result to a field."""
    pts, _ = catmull(pts, np.ones(len(pts)), sub)
    best = torch.full((p.shape[0],), BIG, device=dev)
    lo, hi = pts.min(0) - 3 * w - 1, pts.max(0) + 3 * w + 1
    inside = ((p > V(*lo)) & (p < V(*hi))).all(dim=-1)
    if not inside.any():
        return torch.zeros_like(best)
    q = p[inside]
    b2 = torch.full((q.shape[0],), BIG, device=dev)
    for i in range(len(pts) - 1):
        a, b = V(*pts[i]), V(*pts[i + 1])
        pa, ba = q - a, b - a
        h = torch.clamp((pa @ ba) / (ba @ ba + 1e-9), 0, 1)
        b2 = torch.minimum(b2, (pa - ba * h[:, None]).norm(dim=-1))
    best[inside] = b2
    return depth * torch.exp(-(best / w) ** 2)


def mirror(pts):
    pts = np.array(pts, float)
    pts[:, 0] *= -1
    return pts


# ================================================================== HANDS
# Sheet reading (clive-turnaround.png, front and side): each fist is about 11.5 mm
# wide and 9 mm tall, as wide as the forearm above it, with a pudgy crease at the
# wrist. The hand is palm-down over the waistband: four fat fingers drape over the
# front of the band and curl under it, the thumb hooks behind it on the inner side,
# and the band runs straight through the grip. Turn 9's waistband top roll sits at
# z 34..37.2 with its front face at y = BAND_Y(x); the groove under it is at z 33.
def band_y(x):
    return -11.6 + 0.045 * max(abs(x) - 6.5, 0.0) ** 2


FINGERS = [  # x at the knuckle, radius, extra drop of the curl (middle finger hangs lowest)
    (6.0, 1.62, 0.10),
    (9.1, 1.72, 0.45),
    (12.15, 1.62, 0.25),
    (14.85, 1.40, -0.30),
]
WRIST = np.array([12.6, -12.9, 41.9])
CUFF = np.array([18.6, -8.6, 47.4])
KNUCKLE_Z = 36.5                                    # level with the middle of the band, as on the sheet


def hand(p, side=1, grip=0.0):
    """One fist. side=+1 is his left. `grip` nudges the curl so the two hands are not clones."""
    q = p.clone()
    q[:, 0] = q[:, 0] * side                       # sculpt the left hand, mirror for the right
    x, y, z = q[:, 0], q[:, 1], q[:, 2]

    # back of the hand: one plump pillow from the knuckle row up to the wrist, domed toward the viewer
    back = ellipsoid(q, (10.4, -13.6, 38.75), (6.0, 3.5, 3.6), rot_xyz(rx=-20, rz=-12))
    back = smin(back, ellipsoid(q, (10.8, -11.3, 38.6), (5.4, 2.8, 3.0), rot_xyz(rz=-12)), 1.4)   # palm pad on the band
    # forearm: as thick as the fist, running up into the rolled cuff
    axis = (CUFF - WRIST) / np.linalg.norm(CUFF - WRIST)
    arm = chain(q, [WRIST - axis * 1.2, WRIST + axis * 3.0, CUFF - axis * 0.6, CUFF + axis * 1.4],
                [4.0, 4.55, 4.7, 3.9], sub=4, margin=6)       # ends inside the rolled cuff
    d = smin(back, arm, 2.2)
    # the pudgy wrist crease: a short soft fold across the top of the wrist, fading round the sides
    t = (q - V(*WRIST)) @ V(*axis)
    across = (x - WRIST[0]) * 0.92 + (z - WRIST[2]) * -0.38        # along the fold, in the plane facing the viewer
    crease = 0.42 * torch.exp(-((t - 0.1 - 0.012 * across ** 2) / 0.5) ** 2) * torch.exp(-(across / 3.4) ** 2)
    d = d + crease * torch.sigmoid((-(y + 12.0)) * 1.5)

    # fingers: knuckle level with the band, first joint hanging down its face, tip hooked up behind it
    fing = None
    for i, (fx, fr, drop) in enumerate(FINGERS):
        yb = band_y(fx)
        lean = (fx - 10.4) * 0.045                  # the row fans a little
        dz = -drop - grip * (0.22 if i < 2 else -0.14)
        kz = KNUCKLE_Z + 0.30 * (i in (1, 2)) - 0.45 * (i == 3)
        pts = [(fx - lean * 2.0, yb - 1.9, kz + 1.2),
               (fx - lean, yb - 2.85, kz - 0.4 + dz * 0.3),
               (fx, yb - 2.95, kz - 2.05 + dz),
               (fx + lean * 0.6, yb - 1.7, kz - 3.35 + dz),
               (fx + lean, yb - 0.2, kz - 3.2 + dz)]
        f = chain(q, pts, [fr * 1.02, fr * 1.08, fr * 1.04, fr * 0.95, fr * 0.84], sub=5)
        fing = f if fing is None else smin(fing, f, 0.34)
    d = smin(d, fing, 1.35)
    # thumb: the fat pad at its root shows on the inner side; the tip hooks over the band and out of sight
    thumb = chain(q, [(7.0, -13.2, 40.2), (4.6, -14.5, 38.8), (3.25, -14.2, 37.0), (3.3, -12.4, 35.9), (3.8, -10.8, 36.2)],
                  [2.1, 2.05, 1.85, 1.6, 1.35], sub=5)
    d = smin(d, thumb, 1.2)

    # one shallow dimple above each knuckle, baby-fat style
    front = torch.sigmoid((-(y + 13.0)) * 2.0)
    dimple = torch.zeros_like(d)
    for i, (fx, fr, drop) in enumerate(FINGERS):
        kz = KNUCKLE_Z + 0.30 * (i in (1, 2)) - 0.45 * (i == 3)
        dimple = dimple + torch.exp(-(((x - fx + 0.25) / 0.8) ** 2 + ((z - kz - 2.05) / 0.62) ** 2))
    d = d + 0.13 * dimple * front
    return d


def hand_blush(p, side=1):
    """Rosy knuckles."""
    q = p.clone()
    q[:, 0] = q[:, 0] * side
    b = torch.zeros(p.shape[0], device=dev)
    for fx, fr, drop in FINGERS:
        b = torch.maximum(b, torch.exp(-(((q[:, 0] - fx) / 1.5) ** 2 + ((q[:, 2] - KNUCKLE_Z + 0.6) / 1.7) ** 2)))
    return 0.42 * b * torch.sigmoid((-(q[:, 1] + 12.5)) * 2.0)


# ================================================================== BUST
# One glazed piece: face skin, eye, teeth, brows, moustache and beard, fused with soft
# seams. It replaces turn 9's head, eye, brows, moustache, mouth, teeth and beard and
# has to sit under turn 9's cap (front rim at z 81.7..82.2) between turn 9's ears.
#
# Sheet reading (front view): everything is packed tight under the rim. Brows touch
# the rim, the open eye sits 4 mm below it, the nose is a 10 mm ball level with two
# round cheek apples, the moustache is 29 mm across with tips that curl up into the
# cheeks, and the grin shows a row of top teeth, higher on the winking side.
HC = np.array([0.0, -19.5, 71.5])                  # skull centre
PITCH = math.radians(6.0)                          # chin tucked a little, looking up from under the rim
FW = np.array([0.0, -math.cos(PITCH), -math.sin(PITCH)])
UP = np.array([0.0, -math.sin(PITCH), math.cos(PITCH)])
XA = np.array([1.0, 0.0, 0.0])


def H(x, f, u):
    """Head-local (x across, f out of the face, u up) -> world."""
    return HC + x * XA + f * FW + u * UP


def to_local(p):
    q = p - V(*HC)
    return torch.stack([q[:, 0], q @ V(*FW), q @ V(*UP)], -1)


EYE = np.array([-7.1, 9.0, 5.7])                   # open eye: his right
EYE_R = 4.6
GAZE = np.array([0.20, 1.0, 0.10])
GAZE = GAZE / np.linalg.norm(GAZE)
WINK = np.array([7.1, 9.9, 6.0])                   # winking eye: his left
MX, MU = 1.8, -5.2                                 # grin centre: off-centre toward the wink


def smile(dx):
    """The grin's centre line: both corners up, the winking side higher."""
    return 0.052 * dx * dx + 0.11 * dx


def lid_top(dx):
    return EYE[2] + 2.45 - 0.13 * dx - 0.105 * dx * dx


def lid_bot(dx):
    return EYE[2] - 2.05 + 0.03 * dx + 0.07 * dx * dx


def mouth_coords(pl):
    dx = pl[:, 0] - MX
    return torch.stack([dx, pl[:, 1] + 0.045 * dx * dx, pl[:, 2] - MU - smile(dx)], -1)


def groove2(a, b, pts, w, depth):
    """Gaussian trench along a 2-D polyline in the (a, b) coordinates: add it to carve."""
    best = torch.full_like(a, BIG)
    for i in range(len(pts) - 1):
        ax, ay = pts[i]
        bx, by = pts[i + 1]
        pax, pay = a - ax, b - ay
        bax, bay = bx - ax, by - ay
        h = torch.clamp((pax * bax + pay * bay) / (bax * bax + bay * bay), 0, 1)
        best = torch.minimum(best, torch.hypot(pax - bax * h, pay - bay * h))
    return depth * torch.exp(-(best / w) ** 2)


def arc(pts, sub=4):
    """Smooth a 2-D control polyline."""
    q, _ = catmull(np.c_[np.asarray(pts, float), np.zeros(len(pts))], np.ones(len(pts)), sub)
    return [tuple(v[:2]) for v in q]


WINK_ARC = arc([(-3.6, -1.2), (-2.0, -0.1), (0.1, 0.55), (2.2, 0.7), (3.9, 0.3)])
LID_FOLD = arc([(-3.9, 1.9), (-1.6, 3.55), (0.6, 3.75), (2.8, 3.0), (3.9, 1.7)])


def wink_cut(pl):
    wx, wu = pl[:, 0] - WINK[0], pl[:, 2] - WINK[2]
    return groove2(wx, wu, WINK_ARC, 0.6, 1.5)


def face_skin(pl):
    x, f, u = pl[:, 0], pl[:, 1], pl[:, 2]
    d = ellipsoid(pl, (0, 0.3, -1.5), (16.6, 15.0, 15.4))                         # skull, sized to sit under the cap
    d = smin(d, sphere(pl, (0, 3.2, -5.2), 11.4), 3.0)                            # lower face
    d = smin(d, chain(pl, [(-11, 9.4, 10.2), (-5, 11.6, 10.6), (0, 12.8, 8.4), (5, 12.4, 9.2), (11, 9.8, 8.9)],
                      [2.0, 2.0, 2.2, 2.5, 2.3]), 1.8)                            # brow ridge, dipping at the nose root
    d = smin(d, ellipsoid(pl, (0, 6.6, 8.6), (11.0, 7.0, 4.6)), 2.0)              # forehead, up to the inside of the cap rim
    d = smin(d, ellipsoid(pl, (-11.4, 8.3, 6.2), (4.6, 5.6, 5.2)), 2.6)           # temples
    d = smin(d, ellipsoid(pl, (11.4, 8.3, 6.2), (4.6, 5.6, 5.2)), 2.6)
    # cheek apples: round, level with the nose; the winking one rides higher and fuller
    d = smin(d, ellipsoid(pl, (-8.9, 10.3, -0.4), (5.0, 4.7, 4.2)), 2.8)
    d = smin(d, ellipsoid(pl, (8.9, 10.9, 0.9), (5.2, 4.9, 4.5)), 2.8)
    d = smax(d, -sphere(pl, (EYE[0], EYE[1] + 5.3, EYE[2] + 0.2), 4.6), 1.0)      # open-eye socket
    d = smin(d, ellipsoid(pl, tuple(WINK), (4.4, 3.5, 2.9)), 1.5)                 # closed lid bulge
    # nose: one big strawberry ball, drooping tip, round wings
    nose = ellipsoid(pl, (0, 16.4, 3.1), (5.0, 4.8, 4.0))
    nose = smin(nose, sphere(pl, (0, 17.9, 2.0), 3.5), 1.5)
    nose = smin(nose, sphere(pl, (-4.2, 14.2, 1.0), 2.45), 1.2)
    nose = smin(nose, sphere(pl, (4.2, 14.2, 1.0), 2.45), 1.2)
    nose = smin(nose, chain(pl, [(0, 12.4, 8.6), (0, 14.6, 6.0)], [2.0, 2.9], sub=1), 1.6)
    d = smin(d, nose, 1.0)
    d = smax(d, -sphere(pl, (-2.2, 16.2, -1.1), 1.0), 0.5)                        # nostrils
    d = smax(d, -sphere(pl, (2.2, 16.2, -1.1), 1.0), 0.5)
    # open-eye lids: a heavy upper lid and a lower lid pushed up by the smile
    dx = x - EYE[0]
    upper = smax(sphere(pl, tuple(EYE), EYE_R + 0.8), lid_top(dx) - u, 0.3)
    lower = smax(sphere(pl, tuple(EYE), EYE_R + 0.4), u - lid_bot(dx), 0.3)
    d = smin(d, upper, 0.7)
    d = smin(d, lower, 1.1)
    # chin and a fat lower lip under the grin
    d = smin(d, sphere(pl, (1.2, 9.4, -10.2), 4.2), 2.0)
    lip = [(MX + t, 14.6 - 0.045 * t * t, MU + smile(t) - 2.45) for t in (-6.0, -3.0, 0.0, 3.0, 6.2)]
    d = smin(d, chain(pl, lip, [0.85, 1.4, 1.7, 1.4, 0.85]), 0.8)
    # creases, carved along the surface: wink arc, laugh lines, lid fold, frown lines
    front = torch.sigmoid((f - 7.0) * 1.5)
    wx, wu = x - WINK[0], u - WINK[2]
    cut = wink_cut(pl)
    cut = cut + groove2(wx, wu, [(4.5, 0.9), (6.2, 2.0)], 0.48, 0.6)
    cut = cut + groove2(wx, wu, [(4.6, -0.3), (6.4, -1.0)], 0.48, 0.6)
    cut = cut + groove2(dx, u - EYE[2], LID_FOLD, 0.38, 0.4)
    cut = cut + groove2(dx, u - EYE[2], [(-5.0, 0.9), (-6.6, 1.9)], 0.45, 0.3)    # laugh lines by the open eye
    cut = cut + groove2(dx, u - EYE[2], [(-5.1, -0.4), (-6.8, -0.9)], 0.45, 0.3)
    cut = cut + groove2(x, u, [(-1.3, 8.0), (-0.8, 10.4)], 0.4, 0.5)             # frown lines between the brows
    cut = cut + groove2(x, u, [(1.4, 7.8), (1.0, 10.2)], 0.4, 0.5)
    return d + cut * front


def mouth_cavity(pl):
    return ellipsoid(mouth_coords(pl), (0, 13.0, 0), (6.7, 4.2, 2.15))


def teeth(pl):
    m = mouth_coords(pl)
    t = ellipsoid(m, (0, 11.5, 0.5), (6.3, 2.5, 1.8))
    gap = torch.abs(torch.remainder(m[:, 0] + 0.2 + 0.85, 1.7) - 0.85)
    return smax(t, 0.16 - gap, 0.18)


def eyeball(pl):
    q = pl - V(*EYE)
    g = V(*GAZE)
    ball = q.norm(dim=-1) - EYE_R
    ball = smax(ball, (q @ g) - (EYE_R - 0.36), 0.06)                             # flat iris disc
    return torch.maximum(ball, -((q - g * (EYE_R + 0.25)).norm(dim=-1) - 1.05))   # shallow pupil dish


def ribbon(p, pts, rs, normal, n=3, width=1.0, thin=0.42, k=0.3, core=0.78, sink=0.42, sub=5):
    """A carved lock: n fused strands laid side by side across the surface, over a fatter core.

    `normal` is the outward direction (one vector or one per control point). The strands
    leave engraved grooves between them; the core keeps the lock solid.
    """
    pts = np.asarray(pts, float)
    rs = np.asarray(rs, float)
    T = np.gradient(pts, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-9
    N = np.broadcast_to(np.asarray(normal, float), pts.shape).copy()
    N -= (N * T).sum(1, keepdims=True) * T
    N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-9
    Bn = np.cross(T, N)
    d = None
    for o in np.linspace(-1, 1, n):
        c = pts + Bn * (o * (width - thin) * rs[:, None])
        st = chain(p, c, rs * thin, sub)
        d = st if d is None else smin(d, st, k)
    if core:
        d = smin(d, chain(p, pts - N * (sink * rs[:, None]), rs * core, sub), k * 1.4)
    return d


def face_hair(pl):
    """Brows and moustache, in head-local space."""
    d = torch.full((pl.shape[0],), BIG, device=dev)
    # brows: feathered wings, low at the nose and swept up under the rim; the open-eye one is cocked
    for path, rs in (
        ([(-1.9, 14.5, 9.3), (-5.4, 14.9, 11.0), (-9.4, 13.6, 11.6), (-12.8, 10.9, 10.5), (-14.4, 9.4, 9.2)], [0.8, 1.3, 1.3, 1.0, 0.65]),
        ([(1.9, 14.7, 8.5), (5.4, 15.3, 9.9), (9.4, 14.3, 10.4), (12.8, 11.5, 9.2), (14.3, 9.9, 7.9)], [0.8, 1.3, 1.3, 1.0, 0.65]),
    ):
        nrm = [(q[0] / 16.0, 1.0, 0.25) for q in path]
        d = smin(d, ribbon(pl, path, rs, nrm, n=3, width=1.1, thin=0.5, k=0.25, core=0.7), 0.4)
    # moustache: two fat wings from under the nose, down past the grin, tips curled up into the cheeks
    for s, lift in ((-1, 0.0), (1, 0.9)):
        path = [(s * 1.5, 16.6, -1.9), (s * 5.0, 16.3, -3.3 + 0.2 * lift), (s * 9.4, 14.6, -4.5 + 0.5 * lift),
                (s * 13.5, 12.0, -3.5 + lift), (s * 16.0, 10.2, -1.0 + lift), (s * 16.2, 9.6, 1.4 + lift),
                (s * 14.9, 9.8, 2.6 + lift)]
        rs = [1.05, 2.05, 2.5, 2.15, 1.65, 1.2, 0.85]
        nrm = [(q[0] / 13.0, 1.0, 0.1) for q in path]
        d = smin(d, ribbon(pl, path, rs, nrm, n=3, width=1.05, thin=0.4, k=0.24, core=0.74, sink=0.58), 0.45)
    return d


# ---- beard: a teardrop apron whose surface is drawn with long S-locks -----------------
# t runs down the beard (0 at the lower lip, 1 at the tip; negative t climbs the jaw to the
# sideburns). a is the angle round it (0 at the front, +-90 at the jaw line).
from scipy.interpolate import PchipInterpolator as _P

_T = np.array([-0.40, -0.15, 0.0, 0.2, 0.45, 0.7, 0.9, 1.0])
_BEARD = {
    "z": _P(_T, 62.2 - 18.2 * _T),
    "yf": _P(_T, [-31.0, -32.6, -34.2, -35.5, -34.2, -31.2, -28.6, -27.4]),      # front of the apron, in profile
    "xc": _P(_T, [0.0, 0.0, 0.3, 0.7, 1.2, 1.8, 2.0, 1.2]),                      # the whole beard drifts, then hooks back
    "W": _P(_T, [16.6, 17.0, 17.2, 16.6, 13.6, 9.0, 4.6, 2.2]),                  # half width
    "D": _P(_T, [13.4, 13.2, 12.6, 11.2, 9.0, 6.2, 3.6, 2.2]),                   # half depth
}
_TT = np.linspace(-0.40, 1.0, 141)
_TAB = {k: torch.tensor(v(_TT), dtype=torch.float32, device=dev) for k, v in _BEARD.items()}


def beard_surface(a, t):
    """A point on the apron and its outward normal (numpy; a in radians)."""
    def pt(a, t):
        W, D = _BEARD["W"](t), _BEARD["D"](t)
        return np.stack([_BEARD["xc"](t) + W * np.sin(a), _BEARD["yf"](t) + D * (1 - np.cos(a)), _BEARD["z"](t)], -1)
    P = pt(a, t)
    da = pt(a + 1e-3, t) - P
    dt = pt(a, t + 1e-3) - P
    N = np.cross(da, dt)
    N /= np.linalg.norm(N, axis=-1, keepdims=True) + 1e-12
    return P, N


def beard_under(p):
    """The solid under the locks: the apron shrunk a little, closed off under the lip and at the sideburns."""
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    tq = ((62.2 - z) / 18.2).clamp(-0.40, 1.0)
    i = (tq + 0.40) / 1.40 * 140
    i0 = i.floor().long().clamp(0, 139)
    w = i - i0
    lk = lambda k: _TAB[k][i0] * (1 - w) + _TAB[k][i0 + 1] * w
    W, D, xc, yf = lk("W") - 1.5, lk("D") - 1.5, lk("xc"), lk("yf") + 1.5
    ex, ey = (x - xc) / W, (y - (yf + D)) / D
    d = (torch.sqrt(ex * ex + ey * ey + 1e-9) - 1) * torch.minimum(W, D)
    ang = torch.atan2(ex, -ey).abs()
    top = 60.6 + 10.0 * torch.clamp((ang - 0.5) / 0.75, 0, 1) ** 1.3              # under the lip in front, up to the sideburns at the sides
    d = smax(d, z - top, 1.4)
    d = smax(d, 44.6 - z, 1.2)
    return d


LOCKS = []   # (final angle round the apron in degrees, t start, t end, width factor)
for _i, _a in enumerate([-104, -91, -78, -65, -52, -40, -28, -16, -5, 6, 17, 29, 41, 54, 67, 80, 94]):
    _side = abs(_a) / 100.0
    _t0 = 0.10 - 0.47 * np.clip((abs(_a) - 30) / 55, 0, 1)
    _t1 = 1.0 - 0.52 * _side ** 1.6 - [0.0, 0.13, 0.05][_i % 3]
    LOCKS.append((_a, _t0, _t1, [1.2, 0.84, 1.1, 0.9, 1.25, 0.88, 1.12][_i % 7]))


def lock_path(a0, t0, t1, n=10, lift=0.5, phase=0.0):
    """One beard lock as a 3-D curve on the apron.

    Front locks leave the lip close together, fan outward round the apron, hang, then
    gather into the tip: the apron narrows, so the fan closes by itself. On top of that
    every lock swings round the apron and back (the S seen from the front) and lifts off
    it and settles again (the S seen from the side), a quarter-wave apart.
    """
    ts = np.linspace(t0, t1, n)
    u = np.clip((ts - t0) / 0.42, 0, 1)
    fan = np.clip(1 - (abs(a0) - 30) / 45, 0, 1)                 # sideburn locks simply follow the jaw down
    spread = 1 - 0.55 * fan * (1 - u * u * (3 - 2 * u))
    env = np.clip((ts - t0) / 0.22, 0.2, 1.0)
    wave = 2 * math.pi * 1.2 * ts + 0.011 * a0 + 0.6 + phase
    a = np.radians(a0) * spread + 0.17 * env * np.sin(wave)
    P, N = beard_surface(a, ts)
    P = P + N * (lift + 0.6 * np.sin(wave + math.pi / 2))[:, None]
    return ts, P, N


UNDER_LOCKS = []
for _i in range(len(LOCKS) - 1):
    _a = 0.5 * (LOCKS[_i][0] + LOCKS[_i + 1][0])
    _t0 = max(LOCKS[_i][1], LOCKS[_i + 1][1]) + 0.03
    _t1 = min(LOCKS[_i][2], LOCKS[_i + 1][2]) - 0.08 - 0.07 * (_i % 2)
    UNDER_LOCKS.append((_a, _t0, _t1, 0.92))


def beard(p):
    d = beard_under(p)
    for a0, t0, t1, wf in UNDER_LOCKS:
        ts, P, N = lock_path(a0, t0, t1, lift=-0.35, phase=0.9)
        r = wf * np.interp((ts - t0) / (t1 - t0), [0, 0.2, 0.6, 1.0], [1.1, 1.7, 1.8, 1.0])
        d = smin(d, ribbon(p, P, r, N, n=2, width=1.35, thin=0.48, k=0.22, core=0.7, sink=0.6, sub=4), 0.35)
    for li, (a0, t0, t1, wf) in enumerate(LOCKS):
        ts, P, N = lock_path(a0, t0, t1)
        r = wf * np.interp((ts - t0) / (t1 - t0), [0, 0.18, 0.5, 0.85, 1.0], [1.0, 1.6, 1.9, 1.55, 1.0])
        # the end rolls outward and up into a small volute
        side = np.cross(N[-1], [0, 0, 1.0])
        side = side / (np.linalg.norm(side) + 1e-9) * (1 if li % 2 else -1)
        end, rr = P[-1], r[-1]
        curlp = [end + N[-1] * 0.5 * rr + side * 0.7 * rr + np.array([0, 0, -0.45 * rr]),
                 end + N[-1] * 1.1 * rr + side * 1.5 * rr + np.array([0, 0, 0.1 * rr]),
                 end + N[-1] * 1.0 * rr + side * 1.3 * rr + np.array([0, 0, 1.0 * rr])]
        P = np.vstack([P, curlp])
        N = np.vstack([N, N[-1:], N[-1:], N[-1:]])
        r = np.r_[r, rr * 0.92, rr * 0.8, rr * 0.62]
        d = smin(d, ribbon(p, P, r, N, n=3, width=1.55, thin=0.4, k=0.2, core=0.74, sink=0.66, sub=4), 0.3)
    # the tip itself: one last lock hooked toward his right, as on the sheet
    hook = [(2.6, -29.4, 47.6), (2.2, -28.2, 45.2), (0.6, -27.4, 43.8), (-1.5, -27.6, 43.9), (-2.4, -28.4, 45.2), (-1.6, -28.9, 46.3)]
    d = smin(d, ribbon(p, hook, [2.0, 1.9, 1.7, 1.45, 1.15, 0.85], (0, -1, 0.2), n=3, width=1.1, thin=0.44, k=0.24), 0.5)
    return d


GROUPS = ["skin", "hair", "eye", "tooth"]


def bust(p, with_beard=True):
    pl = to_local(p)
    cav = mouth_cavity(pl)
    skin = face_skin(pl)
    skin = smin(skin, chain(p, [H(0, -2, -9), (0, -12, 60), (0, -10, 52)], [8.5, 9.0, 8.5], sub=2, margin=30), 2.0)   # neck, inside the smock
    hair = face_hair(pl)
    if with_beard:
        hair = smin(hair, beard(p), 0.5)
    g = [smax(skin, -cav, 0.45), smax(hair, -(cav - 0.25), 0.4), eyeball(pl), teeth(pl)]
    return torch.stack(g)


def fuse_bust(G):
    d = smin(G[0], G[1], 0.45)                     # hair grows out of the skin through a soft glazed seam
    d = smin(d, G[2], 0.15)
    return smin(d, G[3], 0.2)


def paint_bust(p, with_beard=True):
    """Material group, blush and freckle mask at each vertex."""
    G = bust(p, with_beard)
    idx = G.argmin(0)
    pl = to_local(p)
    x, f, u = pl[:, 0], pl[:, 1], pl[:, 2]
    skin = idx == 0
    grp = torch.zeros_like(idx)                    # 0 skin, 1 hair, 2 eye, 3 iris, 4 pupil, 5 tooth, 6 mouth, 7 lash
    grp[idx == 1] = 1
    grp[idx == 3] = 5
    m_ = mouth_coords(pl)
    # eye: iris, pupil and one flat catchlight
    q = pl - V(*EYE)
    g = V(*GAZE)
    off = (q - g * (q @ g)[:, None]).norm(dim=-1)
    facing = (q @ g) > 0
    eye = idx == 2
    grp[eye] = 2
    grp[eye & facing & (off < 2.2)] = 3
    grp[eye & facing & (off < 1.05)] = 4
    hl = V(-0.10, 0.93, 0.36)
    hl = hl / hl.norm()
    grp[eye & ((q / EYE_R - hl).norm(dim=-1) < 0.17)] = 2
    # dark lash line along the upper lid, and the wink drawn as one dark arc
    dx = x - EYE[0]
    lash = skin & (q.norm(dim=-1) < EYE_R + 1.3) & (q.norm(dim=-1) > EYE_R + 0.3) & (u > lid_top(dx) - 0.15) & (u < lid_top(dx) + 0.5) & (f > 11.5) & (dx > -4.0) & (dx < 3.3)
    lash = lash | (skin & (wink_cut(pl) > 0.62) & (f > 9.0))
    grp[lash] = 7
    grp[skin & (mouth_cavity(pl) < 0.05) & (m_[:, 2] > -1.45)] = 6
    # paint: rosy nose, cheek apples and lip; freckles on nose and cheeks
    blush = torch.zeros(p.shape[0], device=dev)
    frk = torch.zeros(p.shape[0], device=dev)
    for c, core, fade, amt in (((0, 16.9, 2.7), 5.0, 2.6, 0.95), ((-9.2, 11.6, -0.6), 3.4, 3.2, 0.7), ((9.2, 12.3, 0.7), 3.6, 3.2, 0.7)):
        fall = torch.clamp(1 - ((pl - V(*c)).norm(dim=-1) - core) / fade, 0, 1)
        fall = fall * fall * (3 - 2 * fall) * torch.sigmoid((f - 11.0) * 1.5)
        blush = torch.maximum(blush, amt * fall)
        frk = torch.maximum(frk, fall)
    m = mouth_coords(pl)
    lipz = torch.exp(-((m[:, 2] + 2.45) / 1.15) ** 2) * (m[:, 0].abs() < 6.6) * (f > 11.5)
    blush = torch.maximum(blush, 0.8 * lipz)
    blush = blush * skin
    return grp, blush, frk * skin


def build_bust(out, voxel, with_beard=True):
    lo, hi = np.array([-23.5, -45.5, 40.0]), np.array([23.5, 1.5, 88.5])
    verts, faces = mesh_field(lambda p: fuse_bust(bust(p, with_beard)), lo, hi, voxel)
    grp, blush, frk = [], [], []
    for i in range(0, len(verts), 600_000):
        a, b, c = paint_bust(torch.tensor(verts[i:i + 600_000], dtype=torch.float32, device=dev), with_beard)
        grp.append(a.cpu().numpy())
        blush.append(b.cpu().numpy())
        frk.append(c.cpu().numpy())
    rgb = np.zeros((len(verts), 3), np.uint8)
    rgb[:, 0] = np.concatenate(grp) * 25
    rgb[:, 1] = np.clip(np.concatenate(blush) * 255, 0, 255)
    rgb[:, 2] = np.clip(np.concatenate(frk) * 255, 0, 255)
    write_ply(out / "bust.ply", verts, faces, rgb)
    print("bust", len(verts), "verts", len(faces), "faces", verts.min(0).round(1), verts.max(0).round(1))


# ================================================================== MESHING
def mesh_field(fn, lo, hi, voxel):
    """Marching cubes over a box. fn(points) -> (G, N) group distances or (N,). Returns verts, faces."""
    from skimage import measure
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    n = np.ceil((hi - lo) / voxel).astype(int) + 1
    axes = [torch.arange(int(k), device=dev, dtype=torch.float32) * voxel + float(o) for k, o in zip(n, lo)]
    vol = torch.empty(tuple(int(k) for k in n), dtype=torch.float32)
    step = max(1, 1_200_000 // int(n[1] * n[2]))
    for i in range(0, int(n[0]), step):
        X, Y, Z = torch.meshgrid(axes[0][i:i + step], axes[1], axes[2], indexing="ij")
        pts = torch.stack([X.reshape(-1), Y.reshape(-1), Z.reshape(-1)], -1)
        d = fn(pts)
        if d.dim() == 2:
            d = fuse(d)
        vol[i:i + step] = d.reshape(X.shape).cpu()
    verts, faces, _, _ = measure.marching_cubes(vol.numpy(), 0.0, spacing=(voxel,) * 3)
    verts = verts + lo
    # keep the one real shell: drop crumbs and sealed voids
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    g = coo_matrix((np.ones(len(faces) * 2), (np.r_[faces[:, 0], faces[:, 1]], np.r_[faces[:, 1], faces[:, 2]])),
                   shape=(len(verts), len(verts)))
    _, lab = connected_components(g, directed=False)
    keep = lab == np.bincount(lab).argmax()
    remap = np.cumsum(keep) - 1
    faces = remap[faces[keep[faces].all(1)]]
    return verts[keep], faces[:, ::-1]


def fuse(G, seam=0.5):
    d = G[0]
    for i in range(1, G.shape[0]):
        d = smin(d, G[i], seam)
    return d


def write_ply(path, verts, faces, rgb):
    with open(path, "wb") as fh:
        fh.write((f"ply\nformat binary_little_endian 1.0\nelement vertex {len(verts)}\n"
                  "property float x\nproperty float y\nproperty float z\n"
                  "property uchar red\nproperty uchar green\nproperty uchar blue\n"
                  f"element face {len(faces)}\nproperty list uchar int vertex_indices\nend_header\n").encode())
        vt = np.empty(len(verts), dtype=[("p", "<f4", 3), ("c", "u1", 3)])
        vt["p"], vt["c"] = verts, rgb
        fh.write(vt.tobytes())
        ft = np.empty(len(faces), dtype=[("n", "u1"), ("i", "<i4", 3)])
        ft["n"], ft["i"] = 3, faces
        fh.write(ft.tobytes())


def at_verts(fn, verts, chunk=800_000):
    out = []
    for i in range(0, len(verts), chunk):
        out.append(fn(torch.tensor(verts[i:i + chunk], dtype=torch.float32, device=dev)).cpu().numpy())
    return np.concatenate(out, axis=-1)


def build_hands(out, voxel):
    for name, side, grip in (("hand_L", 1, 0.0), ("hand_R", -1, 1.0)):
        lo = np.array([1.0, -20.5, 30.0])
        hi = np.array([27.5, -1.5, 56.5])
        if side < 0:
            lo, hi = np.array([-hi[0], lo[1], lo[2]]), np.array([-lo[0], hi[1], hi[2]])
        verts, faces = mesh_field(lambda p: hand(p, side, grip), lo, hi, voxel)
        blush = at_verts(lambda p: hand_blush(p, side), verts)
        rgb = np.zeros((len(verts), 3), np.uint8)
        rgb[:, 1] = np.clip(blush * 255, 0, 255)
        write_ply(out / f"{name}.ply", verts, faces, rgb)
        print(name, len(verts), "verts", len(faces), "faces", verts.min(0).round(1), verts.max(0).round(1))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("outdir", type=Path)
    ap.add_argument("--voxel", type=float, default=0.16)
    ap.add_argument("--only", choices=("hands", "bust"))
    ap.add_argument("--no-beard", action="store_true", help="leave turn 9's beard in place")
    args = ap.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)
    if args.only in (None, "hands"):
        build_hands(args.outdir, args.voxel)
    if args.only in (None, "bust"):
        build_bust(args.outdir, args.voxel, not args.no_beard)


if __name__ == "__main__":
    main()
