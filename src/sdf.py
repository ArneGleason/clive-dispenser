"""Tiny vectorised signed-distance-field toolkit (numpy only).

Points are passed as a tuple of three equally shaped arrays (x, y, z).
Distances are approximate for some primitives; that is fine for meshing.
"""
import numpy as np


def length(*c):
    return np.sqrt(sum(a * a for a in c))


def sphere(p, c, r):
    x, y, z = p
    return length(x - c[0], y - c[1], z - c[2]) - r


def ellipsoid(p, c, r):
    x, y, z = p
    qx, qy, qz = (x - c[0]) / r[0], (y - c[1]) / r[1], (z - c[2]) / r[2]
    k0 = length(qx, qy, qz)
    k1 = length(qx / r[0], qy / r[1], qz / r[2])
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)


def capsule(p, a, b, ra, rb=None):
    """Capsule from a to b; tapered when rb differs from ra."""
    rb = ra if rb is None else rb
    x, y, z = p
    pa = (x - a[0], y - a[1], z - a[2])
    ba = np.subtract(b, a)
    h = np.clip((pa[0] * ba[0] + pa[1] * ba[1] + pa[2] * ba[2]) / np.dot(ba, ba), 0.0, 1.0)
    d = length(pa[0] - ba[0] * h, pa[1] - ba[1] * h, pa[2] - ba[2] * h)
    return d - (ra + (rb - ra) * h)


def torus(p, c, axis, big_r, small_r):
    x, y, z = p
    ax = np.asarray(axis, float) / np.linalg.norm(axis)
    rx, ry, rz = x - c[0], y - c[1], z - c[2]
    along = rx * ax[0] + ry * ax[1] + rz * ax[2]
    radial = length(rx - along * ax[0], ry - along * ax[1], rz - along * ax[2])
    return length(radial - big_r, along) - small_r


def round_slab(p, c, rx, ry, z0, z1, round_r):
    """Elliptic cylinder from z0 to z1 with rounded edges."""
    x, y, z = p
    k = min(rx, ry)
    d2 = (length((x - c[0]) / rx, (y - c[1]) / ry) - 1.0) * k + round_r
    dz = np.abs(z - (z0 + z1) / 2) - ((z1 - z0) / 2 - round_r)
    out = length(np.maximum(d2, 0), np.maximum(dz, 0))
    return out + np.minimum(np.maximum(d2, dz), 0) - round_r


def smin(a, b, k):
    """Polynomial smooth minimum (smooth union)."""
    if k <= 0:
        return np.minimum(a, b)
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b + (a - b) * h - k * h * (1.0 - h)


def union(ds, k=0.0):
    out = ds[0]
    for d in ds[1:]:
        out = smin(out, d, k)
    return out


def smax(a, b, k):
    """Smooth intersection."""
    return -smin(-a, -b, k)


def ssub(a, b, k):
    """Smoothly carve b out of a."""
    return -smin(-a, b, k)


def rbox(p, c, half, r=0.0):
    """Axis-aligned rounded box."""
    x, y, z = p
    qx = np.abs(x - c[0]) - (half[0] - r)
    qy = np.abs(y - c[1]) - (half[1] - r)
    qz = np.abs(z - c[2]) - (half[2] - r)
    out = length(np.maximum(qx, 0), np.maximum(qy, 0), np.maximum(qz, 0))
    return out + np.minimum(np.maximum(np.maximum(qx, qy), qz), 0) - r


def round_rect(x, y, c, hx, hy, corner):
    """2D rounded rectangle distance."""
    qx = np.abs(x - c[0]) - (hx - corner)
    qy = np.abs(y - c[1]) - (hy - corner)
    return length(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - corner


def ellipse2d(x, y, c, r):
    """Approximate 2D ellipse distance."""
    qx, qy = (x - c[0]) / r[0], (y - c[1]) / r[1]
    k0 = length(qx, qy)
    k1 = length(qx / r[0], qy / r[1])
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)


def extrude(d2, z, z0, z1, round_r=0.0):
    """Extrude a 2D distance between z0 and z1 with rounded edges."""
    w0 = d2 + round_r
    w1 = np.abs(z - (z0 + z1) / 2) - ((z1 - z0) / 2 - round_r)
    return length(np.maximum(w0, 0), np.maximum(w1, 0)) + np.minimum(np.maximum(w0, w1), 0) - round_r


def chain(p, pts, radii, k=0.5):
    """Tapered capsules along a polyline (for locks of hair, fingers, curls)."""
    out = None
    for i in range(len(pts) - 1):
        d = capsule(p, pts[i], pts[i + 1], radii[i], radii[i + 1])
        out = d if out is None else smin(out, d, k)
    return out


def basis(axis):
    """Unit axis plus two perpendicular unit vectors."""
    a = np.asarray(axis, float)
    a /= np.linalg.norm(a)
    helper = np.array([1.0, 0, 0]) if abs(a[0]) < 0.9 else np.array([0, 1.0, 0])
    e1 = np.cross(a, helper)
    e1 /= np.linalg.norm(e1)
    return a, e1, np.cross(a, e1)


def torus_var(p, c, axis, big_r, small_r_fn):
    """Torus whose tube radius varies with the angle around its axis."""
    x, y, z = p
    a, e1, e2 = basis(axis)
    rx, ry, rz = x - c[0], y - c[1], z - c[2]
    along = rx * a[0] + ry * a[1] + rz * a[2]
    c1 = rx * e1[0] + ry * e1[1] + rz * e1[2]
    c2 = rx * e2[0] + ry * e2[1] + rz * e2[2]
    phi = np.arctan2(c2, c1)
    return length(length(c1, c2) - big_r, along) - small_r_fn(phi)


def axis_coords(p, origin, axis):
    """Height along an axis, distance from it, and the angle around it."""
    x, y, z = p
    a, e1, e2 = basis(axis)
    rx, ry, rz = x - origin[0], y - origin[1], z - origin[2]
    h = rx * a[0] + ry * a[1] + rz * a[2]
    c1 = rx * e1[0] + ry * e1[1] + rz * e1[2]
    c2 = rx * e2[0] + ry * e2[1] + rz * e2[2]
    return h, length(c1, c2), np.arctan2(c2, c1)
