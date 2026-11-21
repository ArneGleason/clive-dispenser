"""Clive as ONE fused clay surface.

Every mass (skin, hair, cap, smock, trousers, boots, plinth) is a signed-distance
field in millimetres. Masses of the same material melt together with a wide
smooth union; different materials meet through a narrow one, which leaves the
soft glazed fillet a slip-cast figurine has at every contact seam. Nothing can
poke through anything else because there is only one surface at the end.

    python sculpt_clive.py out.ply [--voxel 0.3]

Axes: +Z up, Clive faces -Y, +X is his left (the winking side). Plinth top z=10.
Landmarks were measured off character-sculpt/references/clive-turnaround.png
at 0.1355 mm per pixel (108 mm overall).
"""
import argparse
import math

import numpy as np
import torch

dev = "cuda" if torch.cuda.is_available() else "cpu"
BIG = 1e3


def V(*a):
    return torch.tensor(a, dtype=torch.float32, device=dev)


# ---------------------------------------------------------------- primitives
def smin(a, b, k):
    h = torch.clamp(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b + (a - b) * h - k * h * (1 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


def sphere(p, c, r):
    return (p - V(*c)).norm(dim=-1) - r


def ellipsoid(p, c, r):
    r = V(*r)
    q = p - V(*c)
    k0 = (q / r).norm(dim=-1)
    k1 = (q / (r * r)).norm(dim=-1)
    return k0 * (k0 - 1) / (k1 + 1e-9)


def catmull(pts, rs, sub, closed=False):
    pts = np.asarray(pts, float)
    rs = np.asarray(rs, float)
    n = len(pts)
    P = np.c_[pts, rs]
    out = []
    spans = n if closed else n - 1
    for i in range(spans):
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
    out[:, 3] = np.maximum(out[:, 3], 0.55)
    return out[:, :3], out[:, 3]


def chain(p, pts, rs, sub=5, closed=False, scale=(1, 1, 1), margin=4.0):
    """Swept tapered strand through control points. `scale` squashes space first."""
    s = np.asarray(scale, float)
    pts, rs = catmull(np.asarray(pts, float) / s, rs, sub, closed)
    lo = pts.min(0) - rs.max() - margin
    hi = pts.max(0) + rs.max() + margin
    q = p / V(*s)
    inside = ((q > V(*lo)) & (q < V(*hi))).all(dim=-1)
    out = torch.full((p.shape[0],), BIG, device=dev)
    if not inside.any():
        return out
    q = q[inside]
    best = torch.full((q.shape[0],), BIG, device=dev)
    for i in range(len(pts) - 1):
        a, b = V(*pts[i]), V(*pts[i + 1])
        pa, ba = q - a, b - a
        h = torch.clamp((pa @ ba) / (ba @ ba + 1e-9), 0, 1)
        d = (pa - ba * h[:, None]).norm(dim=-1) - (rs[i] + (rs[i + 1] - rs[i]) * h)
        best = torch.minimum(best, d)
    out[inside] = best * float(s.min())
    return out


def strands(p, pts, rs, width_dir, n=3, spread=0.62, thin=0.6, k=0.4, sub=5, wobble=0.0):
    """A lock made of n fused sub-strands laid side by side along width_dir."""
    pts = np.asarray(pts, float)
    rs = np.asarray(rs, float)
    w = np.asarray(width_dir, float)
    w = w / np.linalg.norm(w)
    d = None
    for j in range(n):
        o = (j - (n - 1) / 2)
        off = pts + w[None, :] * (o * spread * rs[:, None] * 1.25)
        if wobble:
            off = off + w[None, :] * wobble * np.sin(np.arange(len(pts)) * 1.9 + j * 2.1)[:, None]
        s = chain(p, off, rs * thin, sub)
        d = s if d is None else smin(d, s, k)
    return d


def lock(start, down, out, length, r0, r1, lean=2.0, flick=2.0, sway=0.0):
    """Control points for a fat hanging lock whose end kicks outward and up."""
    start, down, out = (np.asarray(v, float) for v in (start, down, out))
    down = down / np.linalg.norm(down)
    out = out - down * (out @ down)
    out = out / np.linalg.norm(out)
    side = np.cross(down, out)
    pts = [start,
           start + down * length * 0.45 + out * lean * 0.55 + side * sway,
           start + down * length * 0.95 + out * lean - side * sway * 0.6,
           start + down * (length + 0.2) + out * (lean + flick * 0.75) - side * sway,
           start + down * (length - flick * 0.75) + out * (lean + flick * 1.35) - side * sway * 0.4]
    rs = np.array([r0, r0 * 1.1, r0, r1, r1 * 0.8])
    return np.array(pts), rs, side


def groove2(a, b, pts, w, depth):
    """Gaussian trench along a 2-D polyline in the (a, b) coordinates."""
    best = torch.full_like(a, BIG)
    for i in range(len(pts) - 1):
        ax, ay = pts[i]
        bx, by = pts[i + 1]
        pax, pay = a - ax, b - ay
        bax, bay = bx - ax, by - ay
        h = torch.clamp((pax * bax + pay * bay) / (bax * bax + bay * bay), 0, 1)
        best = torch.minimum(best, torch.hypot(pax - bax * h, pay - bay * h))
    return depth * torch.exp(-(best / w) ** 2)


# ---------------------------------------------------------------- head frame
HC = np.array([0.0, -20.0, 74.0])          # skull centre
PITCH = math.radians(10)                   # chin tucked, looking up from under the brim
ROLL = math.radians(-4)                    # ear dipped toward the open eye
YAW = math.radians(-5)                     # face turned a touch to the open-eye side
_fw = np.array([0, -math.cos(PITCH), -math.sin(PITCH)])
_up = np.array([0, -math.sin(PITCH), math.cos(PITCH)])
_x = np.array([1.0, 0, 0])


def _rot(v, axis, ang):
    axis = axis / np.linalg.norm(axis)
    return v * math.cos(ang) + np.cross(axis, v) * math.sin(ang) + axis * (axis @ v) * (1 - math.cos(ang))


_x, _up = _rot(_x, _fw, ROLL), _rot(_up, _fw, ROLL)
_x, _fw = _rot(_x, _up, YAW), _rot(_fw, _up, YAW)
XA, FW, UP = _x, _fw, _up


def H(x, f, u):
    """Head-local (x across, f out of the face, u up) -> world."""
    return HC + x * XA + f * FW + u * UP


def to_local(p):
    q = p - V(*HC)
    return torch.stack([q @ V(*XA), q @ V(*FW), q @ V(*UP)], -1)


EYE_C = (-6.0, 9.6, 2.9)                  # open eye (his right, -X)
EYE_R = 4.0
GAZE = np.array([0.20, 1.0, 0.16])
GAZE = GAZE / np.linalg.norm(GAZE)
MOUTH = (0.9, -9.7)                        # x, u of the grin centre


def mouth_coords(pl):
    """Bend space so a plain ellipsoid becomes a crooked, up-curled grin."""
    dx = pl[:, 0] - MOUTH[0]
    u = pl[:, 2] - MOUTH[1] - 0.050 * dx * dx - 0.16 * dx
    f = pl[:, 1] + 0.050 * dx * dx
    return torch.stack([dx, f, u], -1)


def face_skin(pl):
    x, f, u = pl[:, 0], pl[:, 1], pl[:, 2]
    d = ellipsoid(pl, (0, 0, 0), (12.3, 13.5, 13.5))
    d = smin(d, sphere(pl, (0, 3.5, -6), 10.3), 3.0)
    # brow ridge: one bar that dips at the nose root, heavier over the wink
    d = smin(d, chain(pl, [(-9.8, 8.8, 7.6), (-4.5, 10.6, 7.9), (0, 12.0, 5.4), (4, 11.6, 6.3), (9.8, 9.2, 6.6)],
                      [1.8, 1.9, 2.0, 2.3, 2.0]), 1.6)
    # cheeks: the wink-side one rides higher and fuller, pushing the lid shut
    d = smin(d, sphere(pl, (-7.5, 8.8, -3.6), 4.6), 2.4)
    d = smin(d, sphere(pl, (7.5, 9.9, -0.9), 5.2), 2.6)
    d = smax(d, -sphere(pl, (EYE_C[0], EYE_C[1] + 4.6, EYE_C[2] + 0.1), 4.0), 1.0)   # open-eye socket
    d = smin(d, ellipsoid(pl, (5.9, 10.2, 3.0), (3.8, 3.2, 2.6)), 1.6)          # closed lid bulge
    # nose: strawberry bulb, wings, short bridge
    nose = sphere(pl, (0.2, 15.3, -0.7), 4.6)
    nose = smin(nose, sphere(pl, (-3.6, 13.0, -2.1), 2.5), 1.3)
    nose = smin(nose, sphere(pl, (3.9, 13.0, -2.0), 2.5), 1.3)
    nose = smin(nose, chain(pl, [(0, 11.3, 5.0), (0.1, 13.8, 1.6)], [2.0, 2.7], sub=1), 1.6)
    d = smin(d, nose, 1.3)
    d = smax(d, -sphere(pl, (-1.9, 14.6, -4.6), 1.0), 0.5)             # nostrils
    d = smax(d, -sphere(pl, (2.3, 14.6, -4.6), 1.0), 0.5)
    # open-eye lids as shells round the ball; upper lid slants down toward the nose
    lid = sphere(pl, EYE_C, EYE_R + 0.8)
    upper = smax(lid, (EYE_C[2] + 2.15 - 0.22 * (x - EYE_C[0]) - 0.07 * (x - EYE_C[0]) ** 2) - u, 0.35)
    lower = smax(lid, u - (EYE_C[2] - 2.35 + 0.04 * (x - EYE_C[0]) + 0.07 * (x - EYE_C[0]) ** 2), 0.35)
    d = smin(d, smin(upper, lower, 0.3), 0.6)
    # ears, tipped out from under the cap
    for s in (-1, 1):
        ear = ellipsoid(pl, (s * 13.3, -0.8, -0.6), (1.9, 3.1, 4.0))
        ear = smax(ear, -ellipsoid(pl, (s * 15.0, 0.1, -0.3), (1.5, 1.9, 2.6)), 0.7)
        d = smin(d, ear, 1.0)
    # lower lip under the grin
    lip = []
    for dx in (-5.2, -2.6, 0.0, 2.6, 5.4):
        lip.append((MOUTH[0] + dx, 13.5 - 0.050 * dx * dx, MOUTH[1] + 0.050 * dx * dx + 0.16 * dx - 2.4))
    d = smin(d, chain(pl, lip, [0.9, 1.3, 1.5, 1.3, 0.9]), 0.9)
    # surface creases, carved along the face rather than floated on it
    front = torch.sigmoid((f - 7.5) * 1.5)
    cut = groove2(x, u, [(2.5, 1.9), (4.2, 3.4), (6.0, 4.0), (7.9, 3.5), (9.6, 2.0)], 0.55, 1.35)  # wink arc
    cut = cut + groove2(x, u, [(10.3, 2.7), (12.2, 3.9)], 0.5, 0.6)                              # laugh lines
    cut = cut + groove2(x, u, [(10.3, 1.3), (12.2, 0.2)], 0.5, 0.6)
    cut = cut + groove2(x, u, [(-6.5, 9.0), (-2, 8.6), (2, 8.3), (6.5, 7.9)], 0.45, 0.4)           # forehead
    return d + cut * front


def mouth_cavity(pl):
    return ellipsoid(mouth_coords(pl), (0, 12.6, 0), (6.3, 3.6, 2.15))


def teeth(pl):
    m = mouth_coords(pl)
    t = ellipsoid(m, (0, 10.5, 0.75), (5.7, 2.6, 1.5))
    gap = torch.abs(torch.remainder(m[:, 0] + 0.3 + 1.0, 2.0) - 1.0)
    return smax(t, 0.17 - gap, 0.2)


def eyeball(pl):
    c = V(*EYE_C)
    q = pl - c
    ball = q.norm(dim=-1) - EYE_R
    g = V(*GAZE)
    ball = smax(ball, (q @ g) - (EYE_R - 0.42), 0.06)                  # flat iris disc
    return torch.maximum(ball, -((q - g * (EYE_R + 0.15)).norm(dim=-1) - 0.95))  # pupil pit


# ---------------------------------------------------------------- hair
def hair(p, pl):
    d = torch.full((p.shape[0],), BIG, device=dev)

    def add(part, k=0.55):
        nonlocal d
        d = smin(d, part, k)

    # eyebrows: the open-eye one cocked, the other clamped down on the wink
    add(chain(pl, [(-1.8, 13.4, 6.4), (-5.6, 13.6, 8.6), (-9.4, 11.8, 8.6), (-12.0, 9.0, 6.6)],
              [1.2, 1.7, 1.5, 1.0]), 0.5)
    add(chain(pl, [(1.8, 13.9, 6.0), (5.8, 14.6, 7.5), (9.6, 12.8, 7.6), (12.2, 9.8, 5.6)],
              [1.2, 1.7, 1.5, 1.0]), 0.5)
    # moustache: two wings parted under the nose, drooping past the grin, tips flicked up
    for s, lift in ((-1, 0.0), (1, 1.1)):
        path = [(s * 1.3, 15.4, -4.3), (s * 4.6, 15.4, -6.5 + 0.2 * lift), (s * 9.0, 13.4, -7.3 + 0.5 * lift),
                (s * 12.9, 10.4, -5.6 + lift), (s * 15.0, 8.6, -2.8 + lift), (s * 14.6, 8.0, -0.9 + lift)]
        add(strands(pl, path, [1.2, 2.3, 2.3, 1.8, 1.3, 0.9], (0, 0.25, 1), n=3, spread=0.5, thin=0.66, k=0.3), 0.45)

    # beard: an under-mass so nothing is hollow, then S-wave locks that own the surface
    chin = H(0, 6.0, -11.5)
    tip = np.array([-3.4, -27.0, 41.6])
    under = chain(p, [chin, (-1.0, -25.0, 58.5), (-2.4, -25.4, 50.5), tip + (0, 1.2, 3.0)],
                  [8.8, 8.0, 5.4, 2.4], scale=(1.45, 1, 1))
    add(under, 1.0)
    n = 8
    for i in range(n):
        s = -1 + 2 * i / (n - 1)
        a = abs(s)
        start = H(12.4 * s, 12.6 - 6.8 * s * s, -13.0 + 5.8 * s * s)
        end = tip + np.array([11.5 * s, -1.6 * (1 - a), 14.5 * a ** 1.25 + (1.6 if i % 2 else 0.0)])
        fwd = np.array([0, -2.8 * (1 - a * a) - 0.5, 0])
        pts = []
        for t in (0, 0.2, 0.4, 0.6, 0.8, 1.0):
            wave = 1.7 * math.sin(2 * math.pi * 1.2 * t + 0.5 * i) * (0.35 + 0.65 * t)
            pts.append(start + (end - start) * t + fwd * math.sin(math.pi * t) + np.array([wave, 0, 0]))
        pts.append(pts[-1] + np.array([-1.6, -0.6, 0.9]))                # every tip kicks toward his right
        rs = np.array([2.5, 3.2, 3.3, 3.0, 2.4, 1.7, 1.1]) * (1.0 - 0.1 * a)
        add(strands(p, pts, rs, (1, 0, 0), n=2, spread=0.5, thin=0.74, k=0.3, sub=4), 0.42)
    for i in range(n - 1):                                             # second tier, set back
        s = -1 + 2 * (i + 0.5) / (n - 1)
        a = abs(s)
        start = H(11.0 * s, 11.2 - 6.0 * s * s, -12.4 + 5.2 * s * s)
        end = tip + np.array([12.5 * s, 1.6, 18.0 * a ** 1.2 + 7.0])
        pts = []
        for t in (0, 0.33, 0.66, 1.0):
            wave = 1.4 * math.sin(2 * math.pi * 1.0 * t + 0.5 * i + 1.5) * (0.35 + 0.65 * t)
            pts.append(start + (end - start) * t + np.array([wave, -0.8 * math.sin(math.pi * t), 0]))
        add(chain(p, pts, np.array([2.4, 3.0, 2.3, 1.4])), 0.45)

    # cap rim in world space: locks start tucked beneath it and bloom once clear
    def rim(phi, r, drop):
        a = math.radians(phi)
        e1 = np.array([1.0, 0, 0])
        e2 = np.cross(e1, BRIM_N)                    # points forward (-Y)
        return BRIM_C + r * (HAT_SX * math.sin(a) * e1 + math.cos(a) * e2) - BRIM_N * drop

    hub = BRIM_C - BRIM_N * 1.5

    def ringlet(c, out, R, r, a0, turn=1.0):
        """A fat curl: most of a circle lying against the head, dimple in the middle."""
        out = out / np.linalg.norm(out)
        e1 = np.cross(out, [0, 0, 1.0])
        e1 = e1 / np.linalg.norm(e1)
        e2 = np.cross(out, e1)
        n = 9
        pts = [c + R * (1 - 0.25 * j / n) * (math.cos(a0 + turn * 5.2 * j / n) * e1 + math.sin(a0 + turn * 5.2 * j / n) * e2)
               + out * 0.9 * j / n for j in range(n + 1)]
        return chain(p, pts, np.linspace(r, r * 0.72, n + 1), sub=2)

    rng = np.random.default_rng(7)
    # sideburn curls in front of each ear, running down into the beard
    for s in (-1, 1):
        for phi, drop, R, r in ((50, 2.6, 1.7, 1.9), (70, 4.2, 2.0, 2.2), (60, 8.0, 1.9, 2.1)):
            c = rim(s * phi, 14.9, drop)
            add(ringlet(c, c - hub + (0, 0, drop - 1.5), R, r, rng.uniform(0, 6.28), turn=s), 0.6)
        add(chain(p, [H(s * 12.8, 6.0, -2.5), H(s * 13.8, 6.2, -6.5), H(s * 12.4, 8.4, -10.5)], [2.8, 3.3, 3.0]), 0.8)
    # collar of curls from ear to ear: two staggered rows, bigger toward the nape
    for row, (drop, K, off) in enumerate(((3.6, 8, 0.0), (8.0, 9, 0.5))):
        for i in range(K):
            phi = 104 + (256 - 104) * (i + off * 0) / (K - 1)
            back = 1 - abs(phi - 180) / 76
            c = rim(phi, 15.2 + 1.1 * row, drop + rng.uniform(-0.5, 0.5) + 0.8 * back * row)
            R = 1.9 + 0.3 * back + rng.uniform(-0.15, 0.25)
            add(ringlet(c, c - hub + (0, 0, drop - 1.5), R, R + 0.25, rng.uniform(0, 6.28),
                        turn=1 if (i + row) % 2 else -1), 0.6)
    # hair under-mass hugging the skull behind the ears
    shell = ellipsoid(pl, (0, -0.8, 0), (14.3, 15.6, 14.5))
    shell = smax(shell, pl[:, 1] + 3.0, 1.0)
    shell = smax(shell, pl[:, 2] - 5.0, 1.0)
    shell = smax(shell, 65.0 - p[:, 2], 1.5)
    add(shell, 1.2)
    return d


# ---------------------------------------------------------------- cap
BRIM_C = np.array([0.0, -18.6, 78.6])
_t = math.radians(10)
BRIM_N = np.array([0.0, math.sin(_t), math.cos(_t)])
BRIM_N = _rot(BRIM_N, np.array([0, 1.0, 0]), math.radians(-3))
BRIM_R = 15.9
HAT_SX = 0.89                              # cap is narrower across than front-to-back

HAT_SPINE = np.array([
    BRIM_C - BRIM_N * 3.0, BRIM_C + BRIM_N * 3.5, (0.6, -15.6, 88.3), (1.8, -13.2, 94.6), (4.0, -10.8, 99.8),
    (7.2, -8.6, 103.6), (10.6, -7.2, 104.9), (13.3, -6.6, 103.5), (14.3, -6.8, 101.3), (13.2, -7.3, 99.9)])
HAT_R = np.array([15.2, 15.5, 13.3, 10.2, 7.4, 5.0, 3.6, 2.7, 2.1, 1.6])


def cap(p):
    p = p * V(1 / HAT_SX, 1, 1)
    pts, rs = catmull(HAT_SPINE / np.array([HAT_SX, 1, 1]), HAT_R, 6)
    seglen = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    cum = np.r_[0, np.cumsum(seglen)] / seglen.sum()
    best = torch.full((p.shape[0],), BIG, device=dev)
    ds, ts, ns = [], [], []
    for i in range(len(pts) - 1):
        a, b = V(*pts[i]), V(*pts[i + 1])
        pa, ba = p - a, b - a
        h = torch.clamp((pa @ ba) / (ba @ ba), 0, 1)
        d = (pa - ba * h[:, None]).norm(dim=-1) - (rs[i] + (rs[i + 1] - rs[i]) * h)
        best = torch.minimum(best, d)
        ds.append(d); ts.append(cum[i] + h * (cum[i + 1] - cum[i])); ns.append(a + ba * h[:, None])
    # soft-nearest spine parameter, so the fold phase never jumps between segments
    wsum = torch.zeros_like(best)
    tt = torch.zeros_like(best)
    near = torch.zeros_like(p)
    for d, t, nn in zip(ds, ts, ns):
        w = torch.exp(-(d - best) / 1.6)
        wsum += w; tt += w * t; near += w[:, None] * nn
    tt, near = tt / wsum, near / wsum[:, None]
    th = torch.atan2(p[:, 0] - near[:, 0], -(p[:, 1] - near[:, 1]))
    amp = 1.7 * torch.clamp((tt - 0.10) / 0.12, 0, 1) * torch.clamp((0.93 - tt) / 0.35, 0.22, 1)
    # slouch rolls: tilted so they spiral, deeper at the back where the cloth sags
    fold = amp * torch.sin(2 * math.pi * 2.7 * tt + 1.5 * torch.sin(th + 0.5) + 0.6 * torch.cos(2 * th))
    fold = torch.where(fold < 0, fold * 0.75, fold)                    # round rolls, narrower creases
    body = best - fold
    # rolled brim, a little wavy, pressed down over hair and ear tops
    q = p - V(*(BRIM_C / np.array([HAT_SX, 1, 1])))
    n = V(*BRIM_N)
    hgt = q @ n
    rad = q - hgt[:, None] * n
    rho = rad.norm(dim=-1)
    th2 = torch.atan2(rad[:, 0], -rad[:, 1])
    R = BRIM_R + 0.4 * torch.sin(3 * th2 + 1.0)
    w = 0.55 * torch.sin(2 * th2 + 0.4)
    brim = torch.sqrt((rho - R) ** 2 + ((hgt - w) / 1.2) ** 2) - 2.25
    return smin(body, brim, 0.9) * HAT_SX


# ---------------------------------------------------------------- body
BUM = [(-7.0, 21.5, 48.5), (7.0, 21.5, 48.5)]
BUM_R = 11.4
WAIST = [(0, -14.9, 33.3), (7, -14.6, 34.2), (14.0, -11.6, 35.0), (18.0, -2, 35.6), (16.6, 9.5, 36.3),
         (9.5, 17.0, 36.8), (0, 18.2, 36.6), (-9.5, 17.0, 36.8), (-16.6, 9.5, 36.3), (-18.0, -2, 35.6),
         (-14.0, -11.6, 35.0), (-7, -14.6, 34.2)]


def lower_skin(p):
    d = smin(sphere(p, BUM[0], BUM_R), sphere(p, BUM[1], BUM_R), 2.2)
    for s in (-1, 1):
        d = smin(d, chain(p, [(s * 8.2, 14, 46), (s * 8.6, 3.5, 35)], [10.3, 9.4], sub=1, margin=60), 3.0)
    return d


def hands(p):
    d = torch.full((p.shape[0],), BIG, device=dev)
    for s in (-1, 1):
        palm = ellipsoid(p, (s * 9.3, -13.4, 37.9), (4.5, 3.0, 3.7))
        arm = chain(p, [(s * 17.4, -11.8, 46.8), (s * 12.4, -12.8, 40.6)], [4.0, 3.6], sub=1)
        h = smin(palm, arm, 1.6)
        fing = None
        for i in range(4):
            x = s * (5.5 + 2.45 * i)
            drop = 0.5 * i * (i - 3) * 0.3                       # middle fingers reach lowest
            f = chain(p, [(x, -15.4, 38.0), (x, -16.9, 35.6 + drop), (x * 1.0, -16.2, 33.0 + drop),
                          (x, -14.0, 32.2 + drop)], [1.45, 1.45, 1.35, 1.2], sub=4)
            fing = f if fing is None else smin(fing, f, 0.22)
        thumb = chain(p, [(s * 5.2, -14.0, 39.2), (s * 3.5, -15.9, 36.6), (s * 3.2, -16.3, 33.9)],
                      [1.7, 1.6, 1.3], sub=4)
        h = smin(h, fing, 0.9)
        h = smin(h, thumb, 0.7)
        d = torch.minimum(d, h)
    return d


def smock(p, lower):
    sc = (1.3, 1, 1)
    torso = chain(p, [(0, -6, 57), (0, 15, 54.7)], [11.5, 13.0], sub=1, scale=sc, margin=40)
    y, z, ax = p[:, 1], p[:, 2], p[:, 0].abs()
    # cloth pulled taut over the hunch, gathering toward the hem
    wr = 0.45 * torch.cos(2 * math.pi * (lower - 1.5) / 4.6) * torch.exp(-(lower.clamp(min=0) / 7.5) ** 2)
    wr = wr * torch.sigmoid((y - 4) * 0.6)
    torso = torso - wr
    d = smin(torso, ellipsoid(p, (0, -10.5, 47.5), (11.5, 6.6, 11.5)), 3.0)
    for s in (-1, 1):
        sl = chain(p, [(s * 15.6, -4.5, 60.2), (s * 18.6, -9.6, 53.5), (s * 18.0, -12.0, 46.6)], [8.6, 7.9, 6.3], sub=4)
        th = torch.atan2(p[:, 1] + 9, (p[:, 0] - s * 17.5))
        sl = sl - (0.42 * torch.sin(1.05 * z + 1.6 * torch.sin(th + s) + s) * (0.6 + 0.4 * torch.sin(2 * th + 0.7))) * torch.sigmoid((56 - z) * 0.7)
        # rolled cuff: a fat ring round the forearm, tipped with the arm
        c0 = V(s * 17.9, -12.1, 45.6)
        axn = V(s * 0.09, 0.33, 0.94)
        axn = axn / axn.norm()
        q = p - c0
        hh = q @ axn
        cuff = torch.sqrt(((q - hh[:, None] * axn).norm(dim=-1) - 5.3) ** 2 + (hh / 1.25) ** 2) - 2.0
        d = smin(d, sl, 2.6)
        d = smin(d, cuff, 0.4)
    # rolled hem riding wherever the cloth ends against bare skin
    hem = torch.sqrt(torso ** 2 + (lower - 0.4) ** 2) - 1.45
    hem = smax(hem, 5.0 - y, 1.5)
    hem = smax(hem, 40.0 - z, 1.5)
    return smin(d, hem, 0.6)


def trousers(p):
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    s = torch.sign(x)
    ax = x.abs()
    # two real legs, gathered: each fold wraps its own leg, tilts, swells and dies away
    th = torch.atan2(y - 2.4, ax - 8.8)
    flare = 1 + 0.016 * (z - 26).clamp(min=0)
    col = (torch.sqrt(((ax - 8.8) / (9.3 * flare)) ** 2 + ((y - 2.4) / (12.6 * flare)) ** 2) - 1) * 9.3
    zz = z + 2.3 * torch.sin(th + 0.8 * s) + 1.0 * torch.sin(2 * th + 1.0 + s)
    roll = torch.cos(2 * math.pi * zz / 5.6 + 0.9 * s)
    roll = torch.where(roll < 0, roll * 0.6, roll) * (0.72 + 0.28 * torch.sin(3 * th + 1.7 * s))
    col = col - 1.3 * roll
    col = smax(col, (z - 30.0).abs() - 6.2, 2.4)
    # the legs part along a seam below the seat
    legs = col + 1.5 * torch.exp(-(x / 1.7) ** 2) * torch.sigmoid((32.5 - z) * 1.2)
    fly = ellipsoid(p, (0, -10.6, 30.2), (9.0, 4.6, 5.2))
    pouch = ellipsoid(p, (0, 12.5, 31.0), (9.5, 5.0, 5.0))             # sagging seat between the legs
    seat = ellipsoid(p, (0, 2.0, 33.6), (16.6, 14.8, 3.2))
    d = smin(smin(smin(legs, fly, 2.0), pouch, 2.0), seat, 1.6)
    d = smin(d, ellipsoid(torch.stack([ax, y, z], -1), (11.5, -9.5, 31.5), (6.0, 4.6, 4.2)), 1.8)   # tented by each fist
    seam = torch.exp(-(x / 0.5) ** 2) * torch.sigmoid((34.2 - z) * 3)
    d = d + 0.5 * seam * (torch.sigmoid((-8 - y) * 2) + torch.sigmoid((y - 12) * 2))   # fly and seat seams
    # waistband: one rolled rim, dragged forward and taut between the fists
    band = chain(p, WAIST, [1.55] * len(WAIST), sub=5, closed=True, scale=(1, 1, 1.9), margin=6)
    band = band - 0.3 * torch.sin(2.6 * ax + 0.4 * z) * torch.sigmoid((-6 - y) * 1.5) * torch.sigmoid((ax - 2.5) * 2)
    return smin(d, band, 0.9)


def boots(p):
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    d = torch.full((p.shape[0],), BIG, device=dev)
    for s in (-1, 1):
        shaft = torch.hypot(x - s * 9.0, y - 1.0) - (8.7 - 0.05 * (z - 10))
        shaft = smax(shaft, (z - 17) - 8.6, 1.2)
        foot = chain(p, [(s * 9.0, 2.0, 15.6), (s * 9.8, -5.5, 15.4), (s * 10.8, -11.6, 15.0)], [8.2, 8.0, 7.8], sub=3, scale=(1, 1, 0.74))
        b = smin(shaft, foot, 2.2)
        b = b + 0.45 * torch.exp(-((y + 6.0 - 0.5 * (z - 17)) / 0.8) ** 2) * torch.sigmoid((z - 17) * 2)  # instep crease
        top = torch.sqrt((torch.hypot(x - s * 9.0, y - 1.0) - 8.2) ** 2 + (z - 24.6) ** 2) - 1.3
        b = smin(b, top, 0.5)
        ax, ay = s * 9.0, 2.2
        bx, by = s * 10.8, -11.6
        pax, pay = x - ax, y - ay
        bax, bay = bx - ax, by - ay
        h = torch.clamp((pax * bax + pay * bay) / (bax * bax + bay * bay), 0, 1)
        sole2 = torch.hypot(pax - bax * h, pay - bay * h) - (8.9 - 0.3 * h)
        sole = smax(sole2, (z - 10.6).abs() - 2.0, 0.5)
        b = smin(b, sole, 0.9)
        d = torch.minimum(d, b)
    return torch.maximum(d, 8.0 - z)


def plinth(p):
    rho = torch.hypot(p[:, 0], p[:, 1])
    z = p[:, 2]
    R = 23.7 - 0.07 * z
    qx = rho - (R - 1.6)
    qz = (z - 5).abs() - (5 - 1.6)
    return torch.hypot(qx.clamp(min=0), qz.clamp(min=0)) + torch.minimum(torch.maximum(qx, qz), torch.zeros_like(qx)) - 1.6


# ---------------------------------------------------------------- assembly
GROUPS = ["plinth", "boots", "cloth", "skin", "hair", "cap", "eye", "teeth", "brass"]
SEAM = 0.7     # fillet width between different materials


def clive(p):
    pl = to_local(p)
    cav = mouth_cavity(pl)
    low = lower_skin(p)
    g = {}
    g["plinth"] = plinth(p)
    g["boots"] = boots(p)
    g["cloth"] = torch.minimum(smock(p, low), trousers(p))
    skin = face_skin(pl)
    neck = chain(p, [H(0, -2, -8), (0, -9, 60)], [8.5, 9.0], sub=1)
    skin = smin(skin, neck, 2.0)
    skin = torch.minimum(skin, low)
    skin = torch.minimum(skin, hands(p))
    g["skin"] = smax(skin, -cav, 0.5)
    g["hair"] = smax(hair(p, pl), -(cav - 0.3), 0.5)
    g["cap"] = cap(p)
    g["eye"] = eyeball(pl)
    g["teeth"] = teeth(pl)
    brass = ellipsoid(p, (0, -16.3, 33.4), (1.3, 0.9, 1.3))                          # waistband button
    for zb in (40.2, 45.6):
        yb = -10.5 - 6.6 * math.sqrt(1 - ((zb - 47.5) / 11.5) ** 2)
        brass = torch.minimum(brass, ellipsoid(p, (0, yb + 0.1, zb), (1.15, 0.8, 1.15)))
    g["brass"] = brass
    return torch.stack([g[k] for k in GROUPS])


def fuse(G):
    d = G[0]
    for i in range(1, G.shape[0]):
        k = 0.25 if GROUPS[i] in ("eye", "teeth", "brass") else SEAM
        d = smin(d, G[i], k)
    return d


PAINT = {
    "plinth": (0.86, 0.80, 0.66), "boots": (0.33, 0.17, 0.08), "cloth": (0.10, 0.20, 0.55),
    "skin": (0.86, 0.62, 0.47), "hair": (0.88, 0.84, 0.74), "cap": (0.66, 0.08, 0.06),
    "eye": (0.93, 0.92, 0.88), "teeth": (0.93, 0.90, 0.80), "brass": (0.62, 0.45, 0.15),
}


def paint(p):
    G = clive(p)
    idx = G.argmin(0)
    col = torch.tensor([PAINT[k] for k in GROUPS], device=dev)[idx]
    pl = to_local(p)
    skin = idx == GROUPS.index("skin")
    blush = torch.zeros(p.shape[0], device=dev)
    for c, r in (((0.2, 16.0, -0.9), 5.2), ((-8.0, 11.5, -3.4), 3.6), ((8.2, 12.6, -1.6), 3.8)):
        blush = torch.maximum(blush, torch.clamp(1 - (pl - V(*c)).norm(dim=-1) / r, 0, 1) ** 0.7)
    rose = V(0.83, 0.36, 0.33)
    col = torch.where(skin[:, None], col + (rose - col) * (0.75 * blush)[:, None], col)
    inside = skin & (mouth_cavity(pl) < 0.35)
    col = torch.where(inside[:, None], V(0.28, 0.07, 0.06).expand_as(col), col)
    eye = idx == GROUPS.index("eye")
    q = pl - V(*EYE_C)
    off = (q - V(*GAZE) * (q @ V(*GAZE))[:, None]).norm(dim=-1)
    facing = (q @ V(*GAZE)) > 0
    col = torch.where((eye & facing & (off < 2.05))[:, None], V(0.36, 0.20, 0.08).expand_as(col), col)
    col = torch.where((eye & facing & (off < 0.9))[:, None], V(0.03, 0.02, 0.02).expand_as(col), col)
    return col, idx


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("output")
    ap.add_argument("--voxel", type=float, default=0.3)
    args = ap.parse_args()
    from skimage import measure
    v = args.voxel
    lo = np.array([-30.0, -47.0, -1.0])
    hi = np.array([30.0, 38.0, 111.0])
    n = np.ceil((hi - lo) / v).astype(int) + 1
    axes = [torch.arange(k, device=dev, dtype=torch.float32) * v + float(o) for k, o in zip(n, lo)]
    vol = torch.empty(tuple(n), dtype=torch.float32)
    step = max(1, 1_500_000 // int(n[1] * n[2]))
    for i in range(0, int(n[0]), step):
        X, Y, Z = torch.meshgrid(axes[0][i:i + step], axes[1], axes[2], indexing="ij")
        p = torch.stack([X.reshape(-1), Y.reshape(-1), Z.reshape(-1)], -1)
        vol[i:i + step] = fuse(clive(p)).reshape(X.shape).cpu()
    solid = vol < 0
    idx = solid.nonzero().float() * v + torch.tensor(lo, dtype=torch.float32)
    com = idx.mean(0).numpy()
    print(f"solid volume {solid.sum().item() * v ** 3 / 1000:.1f} cm3, centre of mass {com.round(1)} "
          f"({math.hypot(com[0], com[1]):.1f} mm from the plinth axis; plinth radius 23 mm)")
    verts, faces, _, _ = measure.marching_cubes(vol.numpy(), 0.0, spacing=(v, v, v))
    verts = verts + lo
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    g = coo_matrix((np.ones(len(faces) * 2), (np.r_[faces[:, 0], faces[:, 1]], np.r_[faces[:, 1], faces[:, 2]])),
                   shape=(len(verts), len(verts)))
    _, lab = connected_components(g, directed=False)
    keep = lab == np.bincount(lab).argmax()
    remap = np.cumsum(keep) - 1
    faces = remap[faces[keep[faces].all(1)]]
    verts = verts[keep]
    cols, ids = [], []
    for i in range(0, len(verts), 1_000_000):
        c, k = paint(torch.tensor(verts[i:i + 1_000_000], dtype=torch.float32, device=dev))
        cols.append(c.cpu().numpy())
        ids.append(k.cpu().numpy())
    cols = (np.clip(np.concatenate(cols), 0, 1) * 255).astype(np.uint8)
    with open(args.output, "wb") as fh:
        fh.write((f"ply\nformat binary_little_endian 1.0\nelement vertex {len(verts)}\n"
                  "property float x\nproperty float y\nproperty float z\n"
                  "property uchar red\nproperty uchar green\nproperty uchar blue\n"
                  f"element face {len(faces)}\nproperty list uchar int vertex_indices\nend_header\n").encode())
        vt = np.empty(len(verts), dtype=[("p", "<f4", 3), ("c", "u1", 3)])
        vt["p"], vt["c"] = verts, cols
        fh.write(vt.tobytes())
        ft = np.empty(len(faces), dtype=[("n", "u1"), ("i", "<i4", 3)])
        ft["n"], ft["i"] = 3, faces[:, ::-1]
        fh.write(ft.tobytes())
    ext = verts.max(0) - verts.min(0)
    print(f"{len(verts)} verts, {len(faces)} faces, bounds {ext.round(1)} mm, min {verts.min(0).round(1)}")


if __name__ == "__main__":
    main()
