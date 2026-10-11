"""SDF -> watertight mesh -> manifold3d solid, plus mesh I/O helpers."""
import manifold3d as mf
import numpy as np
import trimesh
from skimage.measure import marching_cubes

from params import GRID


def sdf_mesh(fn, lo, hi, step=GRID):
    """Mesh the zero level of fn over the box lo..hi (mm)."""
    # The odd offset keeps grid vertices off planes we later cut on (like x = 0).
    axes = [np.arange(lo[i] - 2 * step + 0.0137, hi[i] + 2 * step, step, dtype=np.float32) for i in range(3)]
    d = np.empty([len(a) for a in axes], np.float32)
    chunk = max(1, int(4e6 // (len(axes[1]) * len(axes[2]))))
    for i in range(0, len(axes[0]), chunk):   # in slabs, to keep memory bounded
        X, Y, Z = np.meshgrid(axes[0][i:i + chunk], axes[1], axes[2], indexing="ij")
        d[i:i + chunk] = fn((X, Y, Z))
    # Close the volume so the surface is watertight.
    d[0, :, :] = d[-1, :, :] = d[:, 0, :] = d[:, -1, :] = d[:, :, 0] = d[:, :, -1] = 1.0
    verts, faces, _, _ = marching_cubes(d, 0.0, spacing=(step, step, step))
    verts += np.array([a[0] for a in axes])
    faces = faces.astype(np.int64)
    if trimesh.Trimesh(verts, faces, process=False).volume < 0:
        faces = faces[:, ::-1]
    return verts.astype(np.float64), faces


def to_manifold(verts, faces):
    mesh = mf.Mesh(vert_properties=np.asarray(verts, np.float32),
                   tri_verts=np.asarray(faces, np.uint32))
    m = mf.Manifold(mesh)
    if m.status() != mf.Error.NoError:
        raise RuntimeError(f"mesh is not manifold: {m.status()}")
    return m


def from_manifold(m):
    mesh = m.to_mesh()
    return np.asarray(mesh.vert_properties)[:, :3].astype(np.float64), np.asarray(mesh.tri_verts).astype(np.int64)


def save_stl(m, path):
    v, f = from_manifold(m)
    trimesh.Trimesh(v, f, process=False).export(path)


def save_ply(m, path, color_fn=None, color=None):
    """Save a PLY with per-vertex colours for rendering."""
    v, f = from_manifold(m)
    tm = trimesh.Trimesh(v, f, process=False)
    if color_fn is not None:
        rgb = color_fn(v)
    else:
        rgb = np.tile(color, (len(v), 1))
    tm.visual.vertex_colors = np.hstack([np.clip(rgb * 255, 0, 255), np.full((len(v), 1), 255)]).astype(np.uint8)
    tm.export(path)
