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
