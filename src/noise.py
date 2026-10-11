"""Vectorised 3D value noise and fractal noise (numpy only), range about -1..1."""
import numpy as np

_M = np.uint64(0xFFFFFFFF)


def _hash(ix, iy, iz, seed):
    h = (ix.astype(np.uint64) * np.uint64(73856093)) ^ (iy.astype(np.uint64) * np.uint64(19349663)) \
        ^ (iz.astype(np.uint64) * np.uint64(83492791)) ^ np.uint64(seed * 2654435761 & 0xFFFFFFFF)
    h &= _M
    h ^= h >> np.uint64(13)
    h = (h * np.uint64(1274126177)) & _M
    h ^= h >> np.uint64(16)
    return (h & np.uint64(0xFFFF)).astype(np.float32) / 32767.5 - 1.0


def value(x, y, z, seed=0):
    xi, yi, zi = np.floor(x), np.floor(y), np.floor(z)
    fx, fy, fz = x - xi, y - yi, z - zi
    ux, uy, uz = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy), fz * fz * (3 - 2 * fz)
    xi, yi, zi = xi.astype(np.int64), yi.astype(np.int64), zi.astype(np.int64)
    out = 0.0
    for dx in (0, 1):
        wx = ux if dx else 1 - ux
        for dy in (0, 1):
            wy = uy if dy else 1 - uy
            for dz in (0, 1):
                wz = uz if dz else 1 - uz
                out = out + wx * wy * wz * _hash(xi + dx, yi + dy, zi + dz, seed)
    return out


def fbm(p, freq, octaves=3, seed=0, stretch=(1.0, 1.0, 1.0)):
    """Fractal noise at `freq` cycles per mm; `stretch` squashes axes for streaky looks."""
    x, y, z = p
    total, amp, norm = 0.0, 1.0, 0.0
    f = freq
    for o in range(octaves):
        total = total + amp * value(x * f * stretch[0], y * f * stretch[1], z * f * stretch[2], seed + o * 101)
        norm += amp
        amp *= 0.5
        f *= 2.03
    return total / norm
