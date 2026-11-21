"""Build Clive turnaround-aligned pose & continuous-face sculpt in Blender 5.2.1.

Usage from repository root:
    blender -b --python-exit-code 1 -P experiments/2026-11-21-turnaround-pose-face/build_clive.py
"""
import math
import sys
from math import atan2, cos, exp, pi, sin, sqrt
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector


def clamp(v, lo=0.0, hi=1.0):
    return lo if v < lo else (hi if v > hi else v)


def smoothstep(e0, e1, x):
    t = clamp((x - e0) / (e1 - e0))
    return t * t * (3.0 - 2.0 * t)


def ga(v, c, w):
    d = (v - c) / w
    return exp(-d * d)


def smin(a, b, k):
    h = max(k - abs(a - b), 0.0) / k
    return min(a, b) - h * h * h * k * (1.0 / 6.0)


def sd_ellipsoid(p, c, r):
    q = Vector(((p.x - c.x) / r.x, (p.y - c.y) / r.y, (p.z - c.z) / r.z))
    k0 = q.length
    if k0 < 1e-8:
        return -min(r.x, r.y, r.z)
    q1 = Vector(((p.x - c.x) / (r.x * r.x), (p.y - c.y) / (r.y * r.y), (p.z - c.z) / (r.z * r.z)))
    return k0 * (k0 - 1.0) / max(q1.length, 1e-8)


def sd_capsule(p, a, b, r):
    pa = p - a
    ba = b - a
    h = clamp(pa.dot(ba) / max(ba.length_squared, 1e-10))
    return (pa - ba * h).length - r


def dist_polyline_2d(px, pz, pts_2d):
    best_d2 = 1e18
    best_t = 0.0
    best_dz = 0.0
    n_seg = len(pts_2d) - 1
    for i in range(n_seg):
        ax, az = pts_2d[i]
        bx, bz = pts_2d[i + 1]
        abx, abz = bx - ax, bz - az
        l2 = abx * abx + abz * abz
        u = clamp(((px - ax) * abx + (pz - az) * abz) / l2) if l2 > 1e-12 else 0.0
        qx, qz = ax + abx * u, az + abz * u
        dx, dz = px - qx, pz - qz
        d2 = dx * dx + dz * dz
        if d2 < best_d2:
            best_d2 = d2
            best_t = (i + u) / n_seg
            best_dz = dz
    return sqrt(best_d2), best_dz, best_t


def catmull_rom_resample(pts, samples_per_seg=3):
    n = len(pts)
    if n < 2:
        return list(pts)
    out = []
    for i in range(n - 1):
        p0 = pts[max(0, i - 1)]
        p1 = pts[i]
        p2 = pts[i + 1]
        p3 = pts[min(n - 1, i + 2)]
        steps = samples_per_seg if i < n - 2 else samples_per_seg + 1
        for s in range(steps):
            t = s / samples_per_seg
            t2, t3 = t * t, t * t * t
            vals = []
            for k in range(len(p1)):
                v = 0.5 * (
                    (2.0 * p1[k])
                    + (-p0[k] + p2[k]) * t
                    + (2.0 * p0[k] - 5.0 * p1[k] + 4.0 * p2[k] - p3[k]) * t2
                    + (-p0[k] + 3.0 * p1[k] - 3.0 * p2[k] + p3[k]) * t3
                )
                vals.append(v)
            vals[3] = max(0.2, vals[3])
            vals[4] = max(0.2, vals[4])
            out.append(tuple(vals))
    return out


def make_materials():
    palette = {
        "skin":  ((0.89, 0.55, 0.35), 0.24),
        "rose":  ((0.86, 0.30, 0.20), 0.22),
        "hair":  ((0.93, 0.85, 0.70), 0.23),
        "hat":   ((0.62, 0.042, 0.020), 0.15),
        "blue":  ((0.028, 0.145, 0.36), 0.17),
        "boot":  ((0.23, 0.085, 0.028), 0.19),
        "base":  ((0.84, 0.72, 0.52), 0.30),
        "mouth": ((0.05, 0.015, 0.010), 0.42),
        "tooth": ((0.96, 0.90, 0.76), 0.17),
        "eye":   ((0.97, 0.94, 0.87), 0.10),
        "iris":  ((0.18, 0.072, 0.018), 0.08),
        "pupil": ((0.014, 0.009, 0.007), 0.05),
        "brass": ((0.68, 0.42, 0.12), 0.20),
    }
    mats = {}
    for k, (rgb, rough) in palette.items():
        m = bpy.data.materials.new(k)
        m.diffuse_color = (*rgb, 1.0)
        bsdf = m.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
        bsdf.inputs["Roughness"].default_value = rough
        if "Coat Weight" in bsdf.inputs and k in ("hat", "blue", "boot", "hair", "skin", "rose", "eye", "tooth"):
            bsdf.inputs["Coat Weight"].default_value = 0.45
            bsdf.inputs["Coat Roughness"].default_value = 0.11
        mats[k] = m
    return mats


def create_mesh_obj(name, verts, faces, mat_name, mats, subsurf=2):
    sc = bpy.context.scene
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    ob = bpy.data.objects.new(name, me)
    sc.collection.objects.link(ob)
    me.materials.append(mats[mat_name])
    for poly in me.polygons:
        poly.use_smooth = True
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    if subsurf > 0:
        mod = ob.modifiers.new("Subdivision", "SUBSURF")
        mod.levels = subsurf
        mod.render_levels = subsurf
    return ob


def apply_multires_sculpt(ob, level_funcs, smooth_iters=None):
    sc = bpy.context.scene
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    ob.modifiers.clear()
    mod = ob.modifiers.new("Sculpt levels", "MULTIRES")
    max_lev = max(lev for lev, _ in level_funcs)
    fn_map = dict(level_funcs)
    sm_map = smooth_iters or {}
    for lev in range(1, max_lev + 1):
        bpy.ops.object.multires_subdivide(modifier=mod.name, mode="CATMULL_CLARK")
        if lev in fn_map:
            mod.levels = lev
            dg = bpy.context.evaluated_depsgraph_get()
            me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
            tmp = bpy.data.objects.new("_sculpt_tmp", me)
            sc.collection.objects.link(tmp)
            fn = fn_map[lev]
            deltas = [fn(v.co.copy(), v.normal.copy()) for v in me.vertices]
            for v, d in zip(me.vertices, deltas):
                v.co += d
            for _ in range(sm_map.get(lev, 0)):
                bm = bmesh.new()
                bm.from_mesh(me)
                bmesh.ops.smooth_vert(bm, verts=bm.verts, factor=0.32, use_axis_x=True, use_axis_y=True, use_axis_z=True)
                bm.to_mesh(me)
                bm.free()
            me.update()
            bpy.ops.object.select_all(action="DESELECT")
            ob.select_set(True)
            tmp.select_set(True)
            bpy.context.view_layer.objects.active = ob
            res = bpy.ops.object.multires_reshape(modifier=mod.name)
            if "FINISHED" not in res:
                raise RuntimeError(f"multires_reshape failed on {ob.name} level {lev}")
            bpy.data.objects.remove(tmp, do_unlink=True)
            bpy.data.meshes.remove(me)
    mod.levels = max_lev
    mod.sculpt_levels = max_lev
    mod.render_levels = max_lev
    return ob


def make_quad_sphere_verts_faces(n=12, front_focus=0.0):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=n - 1, use_grid_fill=True)
    verts = []
    for v in bm.verts:
        x, y, z = v.co
        x2, y2, z2 = x * x, y * y, z * z
        sx = x * sqrt(max(0.0, 1.0 - y2 / 2.0 - z2 / 2.0 + (y2 * z2) / 3.0))
        sy = y * sqrt(max(0.0, 1.0 - z2 / 2.0 - x2 / 2.0 + (z2 * x2) / 3.0))
        sz = z * sqrt(max(0.0, 1.0 - x2 / 2.0 - y2 / 2.0 + (x2 * y2) / 3.0))
        vec = Vector((sx, sy, sz)).normalized()
        if front_focus > 0.0:
            t = (1.0 - vec.y) * 0.5
            pull = front_focus * t * (1.0 - t)
            vec = (vec + Vector((0.0, -pull, 0.0))).normalized()
        verts.append(vec)
    faces = [tuple(v.index for v in f.verts) for f in bm.faces]
    bm.free()
    return verts, faces


def build_loft(name, rings, mat_name, mats, cap_ends=True, subsurf=2, multires_funcs=None, smooth_iters=None):
    N = len(rings[0])
    verts = [tuple(p) for r in rings for p in r]
    faces = []
    for j in range(len(rings) - 1):
        for i in range(N):
            faces.append((j * N + i, j * N + (i + 1) % N, (j + 1) * N + (i + 1) % N, (j + 1) * N + i))
    if cap_ends:
        c0 = sum((Vector(p) for p in rings[0]), Vector()) / N
        c1 = sum((Vector(p) for p in rings[-1]), Vector()) / N
        i0 = len(verts)
        verts.append(tuple(c0))
        i1 = len(verts)
        verts.append(tuple(c1))
        for i in range(N):
            faces.append((i0, (i + 1) % N, i))
            b = (len(rings) - 1) * N
            faces.append((i1, b + i, b + (i + 1) % N))
    ob = create_mesh_obj(name, verts, faces, mat_name, mats, subsurf=0 if multires_funcs else subsurf)
    if multires_funcs:
        apply_multires_sculpt(ob, multires_funcs, smooth_iters=smooth_iters)
    return ob


def build_sweep_tube(name, path, mat_name, mats, N=18, subsurf=2, multires_funcs=None,
                     profile_fn=None, up_hint=Vector((0, 0, 1)), resample=1, smooth_iters=None):
    if resample > 1:
        path = catmull_rom_resample(path, resample)
    pts = [Vector(p[:3]) for p in path]
    n_pts = len(pts)
    tans = []
    for j in range(n_pts):
        d = pts[min(n_pts - 1, j + 1)] - pts[max(0, j - 1)]
        tans.append(d.normalized() if d.length > 1e-8 else Vector((0, 0, 1)))
    normals = []
    binorms = []
    n0 = up_hint - tans[0] * up_hint.dot(tans[0])
    if n0.length < 1e-4:
        alt = Vector((1, 0, 0)) if abs(tans[0].x) < 0.8 else Vector((0, 1, 0))
        n0 = alt - tans[0] * alt.dot(tans[0])
    n0.normalize()
    b0 = tans[0].cross(n0).normalized()
    normals.append(n0)
    binorms.append(b0)
    for j in range(1, n_pts):
        axis = tans[j - 1].cross(tans[j])
        if axis.length > 1e-6:
            ang = math.acos(clamp(tans[j - 1].dot(tans[j]), -1.0, 1.0))
            rot = Matrix.Rotation(ang, 3, axis.normalized())
            nj = (rot @ normals[-1]).normalized()
        else:
            nj = normals[-1].copy()
        nj = (nj - tans[j] * nj.dot(tans[j])).normalized()
        bj = tans[j].cross(nj).normalized()
        normals.append(nj)
        binorms.append(bj)

    rings = []
    for j, p in enumerate(path):
        c = pts[j]
        ra, rb = p[3], p[4]
        nj, bj = normals[j], binorms[j]
        u = j / max(1, n_pts - 1)
        ring = []
        for i in range(N):
            th = 2.0 * pi * i / N
            cx, cy = cos(th), sin(th)
            if profile_fn:
                cx, cy = profile_fn(th, u, cx, cy)
            ring.append(c + bj * (ra * cx) + nj * (rb * cy))
        rings.append(ring)
    return build_loft(name, rings, mat_name, mats, cap_ends=True, subsurf=subsurf,
                      multires_funcs=multires_funcs, smooth_iters=smooth_iters)


# ==============================================================================
# 1. PLINTH
# ==============================================================================
def build_plinth(mats):
    levels = [
        (0.0,   22.2),
        (0.25,  23.4),
        (1.0,   23.6),
        (5.5,   23.2),
        (9.5,   22.7),
        (10.15, 22.3),
        (10.48, 21.5),
        (10.55, 19.5),
    ]
    N = 48
    rings = [[(r * cos(2 * pi * i / N), 1.0 + r * sin(2 * pi * i / N), z) for i in range(N)] for z, r in levels]
    return build_loft("Plinth | glazed stoneware base", rings, "base", mats, cap_ends=True, subsurf=2)


# ==============================================================================
# 2. BOOTS (sleek glazed leather, soft sole welt, clear heel block & arch cutaway)
# ==============================================================================
def build_boots(mats):
    objs = []
    N = 32
    for h in (-1, 1):
        cx = h * 9.8
        slices = [
            (10.50, -16.8, 14.8, 7.6, 6.8),
            (10.75, -17.5, 15.2, 8.1, 7.2),
            (11.70, -17.6, 15.2, 8.2, 7.2),
            (12.40, -17.3, 14.8, 7.9, 7.0),
            (13.80, -17.7, 14.6, 8.3, 7.2),
            (15.50, -17.1, 14.2, 8.2, 7.0),
            (17.10, -15.0, 13.5, 7.7, 6.7),
            (18.60, -11.0, 12.9, 7.1, 6.5),
            (19.90,  -6.5, 12.9, 6.9, 6.5),
            (21.30,  -5.4, 13.4, 7.3, 7.0),
            (22.60,  -5.2, 13.8, 7.0, 6.8),
            (24.00,  -5.0, 14.3, 7.4, 7.1),
            (25.20,  -4.5, 14.0, 6.7, 6.6),
        ]
        rings = []
        for z, yf, yb, wf, wb in slices:
            yc, ry = 0.5 * (yf + yb), 0.5 * (yb - yf)
            ring = []
            for i in range(N):
                t = 2.0 * pi * i / N
                sy, cx_u = sin(t), cos(t)
                f = 0.5 * (1.0 - sy)
                rx = wb + (wf - wb) * f
                y_raw = yc + ry * sy
                waist = ga(y_raw, 1.8, 4.2) * smoothstep(17.0, 11.2, z)
                rx *= (1.0 - 0.14 * waist)
                x = cx + rx * cx_u + h * 0.4 * f
                z_mod = z
                if z < 12.3 and -2.5 < y_raw < 5.0:
                    z_mod += 1.05 * ga(y_raw, 1.5, 2.3) * smoothstep(12.3, 10.6, z)
                if 13.5 < z < 18.0 and sy < -0.2:
                    z_mod += 0.65 * (-sy) * ga(z, 15.8, 1.8)
                ring.append((x, y_raw, z_mod))
            rings.append(ring)

        def boot_sculpt(lev):
            def fn(co, nor):
                x, y, z = co
                if lev == 1:
                    disp = 0.22 * ga(z, 11.3, 0.45) - 0.30 * ga(z, 12.35, 0.40)
                    if y > 4.5 and z < 16.5:
                        disp += 0.32 * ga(z, 14.2, 1.8) * smoothstep(3.5, 8.0, y)
                    disp -= 0.38 * ga(z, 19.2 - 0.12 * y, 0.7) * smoothstep(5.0, -6.0, y)
                    disp += 0.28 * ga(z, 21.4, 0.85) - 0.25 * ga(z, 22.7, 0.65)
                    return nor * disp
                return Vector((0, 0, 0))
            return fn

        objs.append(build_loft(
            f"Boot | {'left' if h > 0 else 'right'} leather boot",
            rings, "boot", mats, cap_ends=True, multires_funcs=[(1, boot_sculpt(1))]
        ))
    return objs


# ==============================================================================
# 3. BARE SEAT / PELVIS (sealed cleanly under smock arch & inside thighs — ZERO diaper bulge!)
# ==============================================================================
def build_seat(mats):
    unit_v, faces = make_quad_sphere_verts_faces(n=12)
    center = Vector((0.0, 12.5, 46.8))

    def seat_sdf(p):
        # Upper core seals cleanly behind arched smock hem (zero dark gap at top cleft!)
        d_core = sd_ellipsoid(p, Vector((0.0, 11.2, 50.2)), Vector((17.6, 17.8, 12.0)))
        ang = math.radians(-15.0)
        ca, sa = cos(ang), sin(ang)
        def rot_x(v, orig):
            d = v - orig
            return orig + Vector((d.x, d.y * ca - d.z * sa, d.y * sa + d.z * ca))
        pr = rot_x(p, Vector((0.0, 18.0, 46.2)))
        # Plump ceramic buttocks tucked cleanly into the angled waistband rim!
        d_l = sd_ellipsoid(pr, Vector((-9.4, 21.0, 46.8)), Vector((11.6, 13.5, 11.2)))
        d_r = sd_ellipsoid(pr, Vector(( 9.4, 21.0, 46.8)), Vector((11.6, 13.5, 11.2)))
        d_cheeks = smin(d_l, d_r, 2.3)
        d = smin(d_core, d_cheeks, 4.0)
        # Bilateral upper-thigh plugs strictly INSIDE each trouser leg (never at x=0, never protruding!)
        d_tl = sd_ellipsoid(p, Vector((-9.6, 5.2, 36.2)), Vector((6.6, 8.2, 4.8)))
        d_tr = sd_ellipsoid(p, Vector(( 9.6, 5.2, 36.2)), Vector((6.6, 8.2, 4.8)))
        d = smin(d, d_tl, 3.0)
        d = smin(d, d_tr, 3.0)
        # Keep lower center strictly above waistband so ZERO skin peeks out below trousers!
        if p.z < 37.5 and abs(p.x) < 6.0:
            d += 0.35 * smoothstep(37.5, 33.5, p.z) * ga(p.x, 0.0, 4.2)
        return d

    verts = []
    for u in unit_v:
        lo, hi = 4.0, 32.0
        for _ in range(18):
            mid = 0.5 * (lo + hi)
            if seat_sdf(center + u * mid) < 0.0:
                lo = mid
            else:
                hi = mid
        verts.append(tuple(center + u * (0.5 * (lo + hi))))

    ob = create_mesh_obj("Seat | bare rear", verts, faces, "skin", mats, subsurf=0)
    def seat_l1(co, nor):
        x, y, z = co
        back = smoothstep(22.0, 31.0, y)
        mid_z = smoothstep(56.5, 51.0, z) * smoothstep(34.5, 38.5, z)
        return Vector((0.0, -0.52 * ga(x, 0.0, 1.55) * back * mid_z, 0.0))
    return apply_multires_sculpt(ob, [(1, seat_l1)], smooth_iters={1: 1})


# ==============================================================================
# 4. LOWERED TROUSERS & UNIFIED WAISTBAND (snug fit against buttocks in rear_low!)
# ==============================================================================
def build_trousers(mats):
    objs = []
    N = 36
    for h in (-1, 1):
        cx = h * 9.8
        levels = [
            (22.8,  7.4,  9.3,  3.8, -0.05),
            (23.8,  9.0, 11.0,  3.6, -0.08),
            (25.3,  9.4, 11.7,  3.5, -0.09),
            (26.6,  8.5, 10.7,  3.4, -0.10),
            (28.0, 10.0, 12.5,  3.3, -0.11),
            (29.6, 10.1, 12.7,  3.2, -0.12),
            (30.8,  9.0, 11.6,  3.0, -0.12),
            (32.2, 10.5, 13.5,  2.8, -0.12),
            (33.8, 10.6, 13.9,  2.6, -0.12),
            (35.0,  9.6, 13.0,  2.3, -0.12),
            (36.0,  8.8, 12.0,  2.0, -0.11),
        ]
        rings = []
        for idx, (z0, rx, ry, yc, sl) in enumerate(levels):
            ring = []
            for i in range(N):
                t = 2.0 * pi * i / N
                ct, st = cos(t), sin(t)
                rx_eff = rx * (0.94 if h * ct < 0 else 1.02)
                asym = 1.0 + 0.042 * sin(2.0 * t + idx * 0.7 + h * 0.8) + 0.022 * cos(3.0 * t - idx * 0.5)
                y = yc + ry * asym * st
                x = cx + rx_eff * asym * ct
                z = z0 + sl * (y - 2.0) + 0.50 * sin(t + h * 0.7) * smoothstep(23.2, 26.5, z0)
                ring.append((x, y, z))
            rings.append(ring)

        def leg_sculpt(lev, side=h):
            def fn(co, nor):
                x, y, z = co
                if lev == 1:
                    u = z + 0.12 * (y - 2.0) + 0.7 * sin(x * 0.16 + side * 0.5)
                    fold = 0.34 * sin((u - 24.2) * 1.42) + 0.16 * cos((u - 25.0) * 0.85 + 0.12 * y)
                    return nor * (fold * smoothstep(22.8, 24.5, z) * smoothstep(36.2, 33.8, z))
                return Vector((0, 0, 0))
            return fn

        objs.append(build_loft(
            f"Trousers | {'left' if h > 0 else 'right'} pooled folds",
            rings, "blue", mats, cap_ends=True, multires_funcs=[(1, leg_sculpt(1))]
        ))

    # Unified Rolled Waistband Collar lifted +1.4 mm at rear so it hugs the buttocks with ZERO gap!
    N_wb = 48
    wb_profile = [
        (-3.2, 0.88, 0.88),
        (-2.0, 0.99, 1.00),
        (-0.6, 1.03, 1.04),
        ( 0.7, 1.02, 1.03),
        ( 1.5, 0.95, 0.96),
        ( 1.2, 0.82, 0.82),
        (-1.2, 0.75, 0.75),
    ]
    rings = []
    for dz_p, sx, sy in wb_profile:
        ring = []
        for i in range(N_wb):
            t = 2.0 * pi * i / N_wb
            ct, st = cos(t), sin(t)
            pinch = 1.0 - 0.08 * ga(ct, 0.0, 0.25)
            x = 20.1 * sx * ct
            y = 2.6 + 16.0 * sy * st * pinch
            # Rear sits snugly up at z=33.6 hugging the lower gluteal fold!
            z_base = (
                35.1 - 1.5 * st
                - 0.75 * ga(ct, 0.0, 0.22) * smoothstep(0.0, -1.0, st)
                - 0.55 * ga(ct, 0.0, 0.22) * smoothstep(0.0, 1.0, st)
            )
            hand_press = ga(abs(x), 8.5, 4.0) * smoothstep(-0.3, -0.9, st) * smoothstep(-1.0, 1.5, dz_p)
            z = z_base + dz_p - 0.85 * hand_press
            y += 0.55 * hand_press
            ring.append((x, y, z))
        rings.append(ring)
    objs.append(build_loft("Waistband | unified rolled rim", rings, "blue", mats, cap_ends=True, subsurf=2))

    # Center fly button
    fly_rings = [
        [(r * cos(2 * pi * i / 12), -13.9 - 0.65 * (1.0 - abs(dz) / 1.4) + 0.3 * sin(2 * pi * i / 12), 35.6 + dz) for i in range(12)]
        for dz, r in [(-1.2, 0.6), (-0.7, 1.25), (0.0, 1.38), (0.7, 1.25), (1.2, 0.6)]
    ]
    objs.append(build_loft("Waistband | fly button", fly_rings, "blue", mats, cap_ends=True, subsurf=1))

    # Solid inner trouser core sealing the dropped waistband opening from rear/oblique views
    ic_v, ic_f = make_quad_sphere_verts_faces(n=6)
    ic_verts = [(u.x * 16.5, 3.0 + u.y * 13.8, 33.4 + u.z * 3.1) for u in ic_v]
    objs.append(create_mesh_obj("Trousers | inner seat fill", ic_verts, ic_f, "blue", mats, subsurf=1))
    return objs


# ==============================================================================
# 5. HUNCHED BLUE SMOCK (HUGS UPPER BUTTOCKS TIGHTLY — ZERO DUCKTAIL, ZERO GAP!)
# ==============================================================================
def build_smock(mats):
    objs = []
    N = 48
    u_steps = [-0.07, -0.035, -0.01, 0.0, 0.025, 0.06] + [0.06 + 0.94 * k / 20.0 for k in range(1, 21)]
    rings = []
    for u in u_steps:
        inward = (-u / 0.07) * 2.5 if u < 0 else 0.0
        u_cl = max(0.0, u)
        ring = []
        for i in range(N):
            t = 2.0 * pi * i / N
            ct, st = cos(t), sin(t)
            back_f = 0.5 * (1.0 + st)

            # Rear hem hugs smoothly over the upper buttocks (zero corner notch, zero gap!)
            hem_z = 36.6 + 19.3 * (back_f ** 1.05)
            hem_x = 20.8 * ct
            hem_y = -13.8 + 43.2 * (back_f ** 1.02)

            col_x = 12.2 * ct
            col_y = -10.5 + 11.8 * st
            col_z = 66.8 + 3.2 * back_f

            mid_dome = sin(pi * u_cl)
            sh_bulge = sin(pi * clamp((u_cl - 0.15) / 0.85))
            x = hem_x * (1.0 - u_cl) + col_x * u_cl + ct * (3.4 * sh_bulge)
            y = (
                hem_y * (1.0 - u_cl)
                + col_y * u_cl
                + 4.4 * mid_dome * (back_f ** 0.72)
                - 2.4 * mid_dome * (1.0 - back_f)
            )
            z_lin = hem_z * (1.0 - u_cl) + col_z * u_cl
            hunch_lift = 9.0 * (u_cl ** 0.62) * ((1.0 - u_cl) ** 0.88) * (0.30 + 1.15 * back_f)
            z = z_lin + hunch_lift

            # Sleek ceramic rolled hem resting right on upper seat surface
            hem_lip = ga(u, 0.015, 0.032) * (0.95 if st > -0.25 else 0.50)
            rad_dir = Vector((ct, st, 0.15 * back_f)).normalized()
            x += rad_dir.x * (hem_lip - inward)
            y += rad_dir.y * (hem_lip - inward)
            z += (0.70 * (-u / 0.07) if u < 0 else 0.0) - 0.25 * hem_lip

            ring.append((x, y, z))
        rings.append(ring)

    def smock_sculpt(lev):
        def fn(co, nor):
            x, y, z = co
            if lev == 1:
                d_hem = z - (42.5 + 0.44 * y - 0.014 * x * x)
                mask = smoothstep(-6.0, 4.0, y) * smoothstep(2.2, 5.0, d_hem) * smoothstep(18.5, 11.5, d_hem)
                f1 =  0.72 * ga(d_hem,  5.0, 1.5) - 0.52 * ga(d_hem,  7.4, 1.0)
                f2 =  0.68 * ga(d_hem,  9.6, 1.5) - 0.48 * ga(d_hem, 11.9, 1.0)
                f3 =  0.52 * ga(d_hem, 14.0, 1.6)
                front_m = smoothstep(-9.0, -13.0, y) * smoothstep(37.0, 41.0, z) * smoothstep(55.0, 49.0, z)
                placket = -0.30 * ga(x, 0.8, 0.7) * front_m + 0.25 * ga(x, -0.4, 1.2) * front_m
                return nor * ((f1 + f2 + f3) * mask + placket)
            return Vector((0, 0, 0))
        return fn

    objs.append(build_loft(
        "Smock | hunched tunic with arched hem",
        rings, "blue", mats, cap_ends=True,
        multires_funcs=[(1, smock_sculpt(1))], smooth_iters={1: 1}
    ))

    btn_rings = [
        [(r * cos(2 * pi * i / 14), -15.1 - 0.65 * (1.0 - abs(dz) / 1.3) + 0.4 * sin(2 * pi * i / 14), 39.8 + dz) for i in range(14)]
        for dz, r in [(-1.05, 0.5), (-0.65, 1.12), (0.0, 1.25), (0.65, 1.12), (1.05, 0.5)]
    ]
    objs.append(build_loft("Smock | brass tunic button", btn_rings, "brass", mats, cap_ends=True, subsurf=1))
    return objs


# ==============================================================================
# 6. SLEEVES, CUFFS, FOREARMS & SEAMLESS SCULPTED HANDS (ZERO MITTEN STEP!)
# ==============================================================================
def build_arms_and_hands(mats):
    objs = []
    for h in (-1, 1):
        sl_path = [
            (h * 13.5, -2.0, 65.5, 6.4, 7.6),
            (h * 17.5, -4.6, 62.6, 7.0, 7.9),
            (h * 19.1, -6.8, 57.5, 6.6, 7.6),
            (h * 19.2, -8.2, 52.5, 6.4, 7.5),
            (h * 18.7, -9.0, 49.0, 5.9, 6.9),
            (h * 17.9, -9.3, 46.4, 5.0, 5.8),
        ]
        def sl_sculpt(lev):
            def fn(co, nor):
                x, y, z = co
                if lev == 1:
                    fold = 0.42 * ga(z, 54.0, 1.6) - 0.36 * ga(z, 51.6, 1.1) + 0.28 * ga(z, 58.0, 1.9)
                    return nor * fold
                return Vector((0, 0, 0))
            return fn
        objs.append(build_sweep_tube(
            f"Sleeve | {'left' if h > 0 else 'right'} upper sleeve",
            sl_path, "blue", mats, N=22, multires_funcs=[(1, sl_sculpt(1))],
            up_hint=Vector((0, 1, 0)), resample=2
        ))

        cuff_N = 28
        cuff_cx, cuff_cy, cuff_cz = h * 18.6, -8.8, 47.4
        cuff_rx, cuff_ry = 6.4, 7.5
        cuff_rings = []
        M_cuff = 14
        for j in range(M_cuff):
            phi = 2.0 * pi * j / M_cuff
            r_rad = 1.40 * cos(phi)
            r_z = 2.60 * sin(phi)
            crease = -0.28 * ga(sin(phi), 0.15, 0.25) * smoothstep(-0.2, 0.6, cos(phi))
            ring = []
            for i in range(cuff_N):
                t = 2.0 * pi * i / cuff_N
                ct, st = cos(t), sin(t)
                x = cuff_cx + (cuff_rx + r_rad + crease) * ct
                y = cuff_cy + (cuff_ry + r_rad + crease) * st
                z = cuff_cz + r_z - 1.15 * st - 0.7 * (h * ct)
                ring.append((x, y, z))
            cuff_rings.append(ring)
        cuff_rings.append(cuff_rings[0])
        objs.append(build_loft(f"Cuff | {'left' if h > 0 else 'right'} rolled cuff", cuff_rings, "blue", mats, cap_ends=False, subsurf=2))

        # Forearm seamlessly tapering & flattening into the knuckle ridge (ZERO stubby mitten shelf!)
        arm_path = [
            (h * 18.1, -8.8, 48.0, 4.6, 5.0),
            (h * 16.8, -9.6, 44.5, 4.4, 4.7),
            (h * 14.7, -10.8, 41.5, 3.9, 4.2),
            (h * 12.2, -12.1, 39.4, 3.6, 3.4),  # wrist
            (h *  9.7, -13.6, 37.9, 4.4, 2.4),  # flat-backed plump dorsum of hand
            (h *  8.3, -14.3, 36.7, 3.9, 1.55), # smooth knuckle ridge matching finger thickness!
        ]
        objs.append(build_sweep_tube(
            f"Forearm | {'left' if h > 0 else 'right'} forearm and palm",
            arm_path, "skin", mats, N=20, subsurf=2, up_hint=Vector((0, 1, 0)), resample=2
        ))

        # 4 plump fingers rooted seamlessly along the dorsal knuckle ridge (flush with back of hand!)
        finger_specs = [
            (0,  5.3, 37.0, 0.96, 1.32),
            (1,  7.4, 37.3, 1.04, 1.38),
            (2,  9.5, 37.6, 0.98, 1.32),
            (3, 11.5, 38.0, 0.85, 1.18),
        ]
        for idx, fx, fz, fl, fr in finger_specs:
            inw = -h * 1.1 * fl
            fpath = [
                (h * (fx + 1.0), -13.1, fz + 1.4, fr * 1.02, fr * 0.95),               # flush inside dorsal palm!
                (h * (fx + 0.2), -14.6, fz + 0.1, fr * 1.04, fr * 1.02),               # smooth knuckle arc
                (h * fx + inw * 0.55, -15.3, fz - 1.5 * fl, fr * 0.98, fr * 0.96),     # PIP bend over waistband rim
                (h * fx + inw * 0.95, -14.6, fz - 3.1 * fl, fr * 0.88, fr * 0.86),     # DIP curling under rim
                (h * fx + inw * 1.10, -13.3, fz - 3.9 * fl, fr * 0.68, fr * 0.66),     # soft fingertip
            ]
            objs.append(build_sweep_tube(
                f"Finger | {'L' if h > 0 else 'R'}{idx + 1}",
                fpath, "skin", mats, N=14, subsurf=2, up_hint=Vector((h, 0, 0)), resample=2
            ))

        thumb_path = [
            (h * 7.8, -12.8, 38.7, 1.45, 1.35),
            (h * 5.7, -13.6, 37.6, 1.48, 1.40),
            (h * 4.3, -14.2, 36.4, 1.30, 1.24),
            (h * 3.9, -13.4, 35.3, 0.90, 0.88),
        ]
        objs.append(build_sweep_tube(
            f"Thumb | {'left' if h > 0 else 'right'} thumb",
            thumb_path, "skin", mats, N=14, subsurf=2, up_hint=Vector((0, 0, 1)), resample=2
        ))
    return objs


# ==============================================================================
# 7. CONTINUOUS QUAD-SCULPTED HEAD & FACE (SILKY LIDS + SCULPTED IRIS + FULL GRIN!)
# ==============================================================================
def build_head_and_face(mats):
    objs = []
    unit_v, faces = make_quad_sphere_verts_faces(n=12, front_focus=0.38)
    hc = Vector((0.0, -18.8, 71.5))

    def head_base_sdf(p):
        d_skull = sd_ellipsoid(p, Vector((0.0, -18.5, 72.2)), Vector((16.5, 13.8, 11.8)))
        d_chk_w = sd_ellipsoid(p, Vector(( 10.2, -26.2, 71.9)), Vector((7.8, 6.8, 5.2)))
        d_chk_o = sd_ellipsoid(p, Vector((-10.4, -26.0, 70.6)), Vector((7.5, 6.4, 4.9)))
        d = smin(d_skull, d_chk_w, 4.8)
        d = smin(d, d_chk_o, 4.8)

        d_brow = sd_ellipsoid(p, Vector((0.0, -28.0, 78.0)), Vector((12.5, 5.0, 3.0)))
        d = smin(d, d_brow, 3.5)

        # True round bulbous strawberry nose!
        d_bridge = sd_capsule(p, Vector((0.0, -31.0, 75.5)), Vector((0.0, -34.2, 71.4)), 2.55)
        d_bulb = sd_ellipsoid(p, Vector((0.0, -35.2, 70.3)), Vector((5.35, 5.05, 3.85)))
        d_ala_l = sd_ellipsoid(p, Vector((-3.9, -33.2, 69.0)), Vector((2.2, 2.3, 1.85)))
        d_ala_r = sd_ellipsoid(p, Vector(( 3.9, -33.2, 69.0)), Vector((2.2, 2.3, 1.85)))
        d_nose = smin(d_bridge, d_bulb, 2.0)
        d_nose = smin(d_nose, d_ala_l, 1.4)
        d_nose = smin(d_nose, d_ala_r, 1.4)
        d = smin(d, d_nose, 2.6)

        d_jaw = sd_ellipsoid(p, Vector((0.0, -24.0, 62.5)), Vector((11.5, 7.5, 5.5)))
        d = smin(d, d_jaw, 3.5)
        return d

    verts = []
    for u in unit_v:
        lo, hi = 6.0, 28.0
        for _ in range(18):
            mid = 0.5 * (lo + hi)
            if head_base_sdf(hc + u * mid) < 0.0:
                lo = mid
            else:
                hi = mid
        verts.append(tuple(hc + u * (0.5 * (lo + hi))))

    # Smooth rosy glaze shader for nose & apple cheeks
    head_mat = mats["skin"].copy()
    head_mat.name = "skin_face"
    nt = head_mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    tc = nt.nodes.new("ShaderNodeTexCoord")

    def blush_dist(pt, fmin, fmax, peak):
        vm = nt.nodes.new("ShaderNodeVectorMath")
        vm.operation = "DISTANCE"
        vm.inputs[1].default_value = pt
        nt.links.new(tc.outputs["Object"], vm.inputs[0])
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["From Min"].default_value = fmin
        mr.inputs["From Max"].default_value = fmax
        mr.inputs["To Min"].default_value = peak
        mr.inputs["To Max"].default_value = 0.0
        mr.interpolation_type = "SMOOTHSTEP"
        nt.links.new(vm.outputs["Value"], mr.inputs["Value"])
        return mr.outputs["Result"]

    bn = blush_dist((0.0, -35.8, 70.3), 3.6, 6.4, 0.92)
    bc1 = blush_dist((11.0, -30.5, 72.0), 1.8, 6.4, 0.52)
    bc2 = blush_dist((-11.2, -30.2, 70.8), 1.8, 6.0, 0.48)
    m1 = nt.nodes.new("ShaderNodeMath")
    m1.operation = "MAXIMUM"
    nt.links.new(bn, m1.inputs[0])
    nt.links.new(bc1, m1.inputs[1])
    m2 = nt.nodes.new("ShaderNodeMath")
    m2.operation = "MAXIMUM"
    nt.links.new(m1.outputs["Value"], m2.inputs[0])
    nt.links.new(bc2, m2.inputs[1])

    mix_b = nt.nodes.new("ShaderNodeMix")
    mix_b.data_type = "RGBA"
    mix_b.inputs[6].default_value = (0.89, 0.55, 0.35, 1.0)
    mix_b.inputs[7].default_value = (0.85, 0.28, 0.19, 1.0)
    nt.links.new(m2.outputs["Value"], mix_b.inputs[0])
    nt.links.new(mix_b.outputs[2], bsdf.inputs["Base Color"])
    mats["skin_face"] = head_mat

    head_ob = create_mesh_obj("Head | continuous quad sculpt", verts, faces, "skin_face", mats, subsurf=0)

    wink_curve = [
        (3.7, 74.3),
        (5.8, 75.6),
        (8.6, 76.4),
        (11.1, 76.0),
        (13.1, 74.9),
    ]
    crow_upper = [(12.6, 75.3), (14.6, 76.3), (16.1, 77.0)]
    crow_mid   = [(12.9, 74.8), (15.1, 75.0), (16.5, 75.1)]
    crow_lower = [(12.7, 74.2), (14.7, 73.4), (16.0, 72.6)]

    open_cx, open_cz = -7.7, 75.2
    open_rx, open_rz = 3.55, 2.55

    # Crooked cheeky smile sweeping cleanly UP into the +X winking cheek (visible in FRONT & SIDE!)
    mouth_curve = [
        (-2.6, 63.9),
        ( 0.8, 63.4),
        ( 4.2, 63.9),
        ( 7.4, 65.4),
        (10.2, 67.8),
        (11.6, 69.2),
    ]

    def head_l1(co, nor):
        x, y, z = co
        d_s = head_base_sdf(co)
        eps = 0.25
        gx = head_base_sdf(co + Vector((eps, 0, 0))) - head_base_sdf(co - Vector((eps, 0, 0)))
        gy = head_base_sdf(co + Vector((0, eps, 0))) - head_base_sdf(co - Vector((0, eps, 0)))
        gz = head_base_sdf(co + Vector((0, 0, eps))) - head_base_sdf(co - Vector((0, 0, eps)))
        g = Vector((gx, gy, gz))
        delta = -g.normalized() * clamp(d_s, -2.5, 2.5) if g.length > 1e-6 else Vector((0, 0, 0))

        if y > -19.5:
            return delta
        front = smoothstep(-19.5, -25.5, y)
        dx, dy, dz = delta.x, delta.y, delta.z

        # Open-eye orbital socket (-X)
        ex = (x - open_cx) / (open_rx * 1.14)
        ez = (z - open_cz) / (open_rz * 1.14)
        er = sqrt(ex * ex + ez * ez)
        if er < 1.38:
            dy += 4.7 * smoothstep(1.38, 0.40, er) * front

        # Continuous cheek lift directly beneath winking lower eyelid (+X)
        d_w, dz_w, _ = dist_polyline_2d(x, z, wink_curve)
        under_wink = (
            smoothstep(0.5, -1.6, dz_w)
            * ga(dz_w, -2.2, 2.4)
            * smoothstep(2.0, 4.8, x)
            * smoothstep(15.5, 11.8, x)
            * front
        )
        dy -= 1.45 * under_wink
        dz += 0.65 * under_wink

        # Crooked mouth cavity pocket & warm sculpted lower lip bolster!
        d_m, dz_m, t_m = dist_polyline_2d(x, z, mouth_curve)
        m_hh = 2.4 * sin(pi * clamp(t_m, 0.02, 0.98)) ** 0.60
        if d_m < m_hh + 1.6:
            dy += 5.5 * smoothstep(m_hh + 1.3, m_hh * 0.25, d_m) * front
        if dz_m < 0.0 and d_m < 4.8:
            lip = ga(d_m, m_hh + 1.25, 1.1) * sin(pi * clamp(t_m, 0.01, 0.99)) ** 0.45 * front
            dy -= 1.85 * lip
            dz += 0.40 * lip

        return Vector((dx, dy, dz))

    def head_l2(co, nor):
        x, y, z = co
        if y > -20.5:
            return Vector((0, 0, 0))
        front = smoothstep(-20.5, -26.0, y)
        dx, dy, dz = 0.0, 0.0, 0.0

        # Open eye (-X): silky-smooth plump upper eyelid hood & soft lower lid rim (wider smooth kernel!)
        ex = (x - open_cx) / open_rx
        ez = (z - open_cz) / open_rz
        er = sqrt(ex * ex + ez * ez)
        if er < 1.05:
            dy += 2.5 * smoothstep(1.05, 0.70, er) * front
        if ez > -0.15:
            up_rim = ga(er, 1.14, 0.24) * smoothstep(-0.15, 0.30, ez) * front
            dy -= 1.80 * up_rim
            dz -= 0.15 * up_rim
            up_crease = ga(er, 1.48, 0.18) * smoothstep(0.15, 0.55, ez) * front
            dy += 0.80 * up_crease
        if ez < 0.15:
            lo_rim = ga(er, 1.14, 0.26) * smoothstep(0.15, -0.35, ez) * front
            dy -= 1.20 * lo_rim
            dz += 0.32 * lo_rim

        # Joyful upward-arched wink (+X)
        d_w, dz_w, t_w = dist_polyline_2d(x, z, wink_curve)
        taper = sin(pi * clamp(t_w, 0.01, 0.99)) ** 0.42
        if d_w < 3.8:
            dy += 1.80 * ga(d_w, 0.0, 0.55) * (0.65 + 0.35 * taper) * front
            if dz_w < 0.0:
                lo_sq = ga(d_w, 1.25, 0.78) * taper * front
                dy -= 1.15 * lo_sq
                dz += 0.45 * lo_sq
            if dz_w > 0.0:
                up_sq = ga(d_w, 1.15, 0.62) * taper * front
                dy -= 0.95 * up_sq
                dy += 0.65 * ga(d_w, 2.35, 0.42) * taper * front

        # Glabella V-furrows
        glab = (ga(x, -1.05, 0.52) + ga(x, 1.05, 0.52)) * ga(z, 77.6, 1.55) * front
        dy += 0.75 * glab
        dy -= 0.42 * ga(x, 0.0, 0.62) * ga(z, 77.4, 1.35) * front

        # Recessed underside nostrils & alar creases
        for s in (-1, 1):
            d_pit = sqrt(((x - s * 2.9) / 1.25) ** 2 + ((y - (-34.6)) / 1.35) ** 2)
            if d_pit < 1.6 and z < 69.0:
                pit = smoothstep(1.5, 0.2, d_pit) * smoothstep(69.0, 66.8, z)
                dz += 1.45 * pit
                dy += 0.65 * pit
            d_ala = sqrt(((x - s * 5.2) / 0.85) ** 2 + ((z - 69.8) / 1.8) ** 2)
            if d_ala < 1.8 and y < -29.0:
                dy += 0.60 * ga(d_ala, 0.0, 0.8) * smoothstep(-29.0, -32.5, y)

        # Crisp smiling corner dimple & warm exposed lower lip rim!
        d_m, dz_m, t_m = dist_polyline_2d(x, z, mouth_curve)
        m_hh = 2.2 * sin(pi * clamp(t_m, 0.02, 0.98)) ** 0.60
        if d_m < m_hh + 0.45:
            dy += 1.6 * smoothstep(m_hh + 0.4, m_hh * 0.4, d_m) * front
        d_cor = sqrt(((x - 11.4) / 1.35) ** 2 + ((z - 69.2) / 1.55) ** 2)
        if d_cor < 1.9:
            dy += 0.95 * ga(d_cor, 0.0, 0.85) * front

        return Vector((dx, dy, dz))

    def head_l3(co, nor):
        x, y, z = co
        if y > -21.5:
            return Vector((0, 0, 0))
        front = smoothstep(-21.5, -26.5, y)
        dy = 0.0

        d_w, _, t_w = dist_polyline_2d(x, z, wink_curve)
        if d_w < 1.1:
            taper = sin(pi * clamp(t_w, 0.01, 0.99)) ** 0.35
            dy += 0.80 * ga(d_w, 0.0, 0.26) * (0.65 + 0.35 * taper) * front

        for c_pts, strength in [(crow_upper, 0.46), (crow_mid, 0.54), (crow_lower, 0.42)]:
            dc, _, tc = dist_polyline_2d(x, z, c_pts)
            if dc < 0.95:
                taper = smoothstep(0.0, 0.18, tc) * smoothstep(1.0, 0.18, tc)
                dy += strength * ga(dc, 0.0, 0.26) * taper * front

        d_ol, _, t_ol = dist_polyline_2d(x, z, [(-11.4, 74.7), (-13.4, 74.2), (-14.9, 73.6)])
        if d_ol < 0.9:
            dy += 0.34 * ga(d_ol, 0.0, 0.26) * smoothstep(0.0, 0.2, t_ol) * smoothstep(1.0, 0.2, t_ol) * front

        ex = (x - open_cx) / open_rx
        ez = (z - open_cz) / open_rz
        er = sqrt(ex * ex + ez * ez)
        if 0.90 < er < 1.25:
            dy -= 0.30 * ga(er, 1.09, 0.10) * front

        return Vector((0.0, dy, 0.0))

    apply_multires_sculpt(
        head_ob,
        [(1, head_l1), (2, head_l2), (3, head_l3)],
        smooth_iters={1: 1, 2: 1, 3: 0},
    )
    objs.append(head_ob)

    # --- Sculpted 3D Open Eyeball (reads warmly in BOTH unpainted clay AND glazed color!) ---
    # Uses a subtle sculpted iris ring & concave pupil dish (like fine ceramic/resin figurines!)
    # instead of a protruding BB-pellet pimple!
    eye_center = Vector((-7.7, -28.9, 75.15))
    eye_r = 3.55
    bpy.ops.mesh.primitive_uv_sphere_add(segments=40, ring_count=28, radius=eye_r, location=(0, 0, 0))
    eye_ob = bpy.context.object
    eye_ob.name = "Eye | open globe"
    me = eye_ob.data
    for k in ("eye", "iris", "pupil"):
        me.materials.append(mats[k])
    gaze = Vector((0.18, -0.98, 0.06)).normalized()
    # Sculpt subtle iris ring & gentle pupil concavity in local +Z pole coordinates!
    for v in me.vertices:
        d_dir = v.co.normalized()
        ang = math.acos(clamp(d_dir.z, -1.0, 1.0))
        # Crisp subtle recessed iris limbus groove at ang=0.56 + gentle concave pupil dish inside 0.30!
        limbus = -0.14 * ga(ang, 0.56, 0.045)
        pupil_dish = -0.22 * smoothstep(0.32, 0.14, ang)
        # Subtle catchlight bead carved right into upper-left iris edge (small, off-center, natural!)
        v.co = d_dir * (eye_r + limbus + pupil_dish)
    me.update()
    for p in me.polygons:
        p.use_smooth = True
        ang = math.acos(clamp(p.center.normalized().z, -1.0, 1.0))
        if ang < 0.30:
            p.material_index = 2  # pupil
        elif ang < 0.57:
            p.material_index = 1  # warm chestnut iris
        else:
            p.material_index = 0  # ivory sclera
    eye_ob.rotation_euler = Vector((0, 0, 1)).rotation_difference(gaze).to_euler()
    eye_ob.location = eye_center
    bpy.ops.object.select_all(action="DESELECT")
    eye_ob.select_set(True)
    bpy.context.view_layer.objects.active = eye_ob
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    objs.append(eye_ob)

    # Flush glossy white catchlight wafer perched OFF-CENTER at upper-left of iris
    # (barely raised 0.07 mm so it gleams in color WITHOUT reading as a weird bug-eye pimple in matte clay!)
    glint_dir = (gaze * 0.94 + Vector((-0.24, 0.0, 0.25))).normalized()
    glint_pos = eye_center + glint_dir * (eye_r - 0.18)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=14, ring_count=10, radius=0.46, location=(0, 0, 0))
    glint = bpy.context.object
    glint.name = "Eye | catchlight"
    glint.scale = (0.95, 0.95, 0.45)
    glint.rotation_euler = Vector((0, 0, 1)).rotation_difference(glint_dir).to_euler()
    glint.location = glint_pos
    glint.data.materials.append(mats["eye"])
    for p in glint.data.polygons:
        p.use_smooth = True
    bpy.ops.object.select_all(action="DESELECT")
    glint.select_set(True)
    bpy.context.view_layer.objects.active = glint
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    objs.append(glint)

    # Dark mouth cavity backing
    mb_rings = []
    for k_i in range(9):
        t = k_i / 8.0
        idx_f = t * (len(mouth_curve) - 1)
        i0 = min(len(mouth_curve) - 2, int(idx_f))
        f = idx_f - i0
        mx = mouth_curve[i0][0] * (1 - f) + mouth_curve[i0 + 1][0] * f
        mz = mouth_curve[i0][1] * (1 - f) + mouth_curve[i0 + 1][1] * f
        my = -27.2 + 0.045 * mx * mx
        rh = 2.8 * sin(pi * clamp(t, 0.05, 0.95)) ** 0.5
        mb_rings.append([(mx, my + 1.2 * cos(2 * pi * j / 12), mz + rh * sin(2 * pi * j / 12)) for j in range(12)])
    objs.append(build_loft("Mouth | dark cavity backing", mb_rings, "mouth", mats, cap_ends=True, subsurf=1))

    # Unified Curved Ceramic Upper Dental Arch (sweeping clearly up to x=+10.2 so it flashes in SIDE view too!)
    n_arch, n_prof = 46, 12
    dental_rings = []
    for k in range(n_arch + 1):
        u = k / n_arch
        tx = -2.0 + 12.2 * u
        tz = 64.1 + 0.11 * tx + 0.036 * tx * tx
        ty = -31.1 + 0.052 * (tx - 0.5) ** 2
        tooth_phase = u * 6.5
        tooth_sep = exp(-((tooth_phase - round(tooth_phase)) / 0.14) ** 2)
        th_h = (1.65 - 0.30 * u) * (1.0 - 0.10 * tooth_sep)
        th_d = 1.12 * (1.0 - 0.25 * tooth_sep)
        end_t = smoothstep(0.0, 0.07, u) * smoothstep(1.0, 0.92, u)
        th_h *= (0.45 + 0.55 * end_t)
        th_d *= (0.45 + 0.55 * end_t)
        ring = []
        for j in range(n_prof):
            a = 2.0 * pi * j / n_prof
            dy_p = th_d * cos(a)
            dz_p = th_h * sin(a)
            if sin(a) < -0.2:
                dz_p += 0.30 * tooth_sep * (-sin(a))
            ring.append((tx, ty + dy_p, tz + dz_p))
        dental_rings.append(ring)
    objs.append(build_loft("Teeth | crooked ceramic dental arch", dental_rings, "tooth", mats, cap_ends=True, subsurf=2))

    # Sculpted Ceramic Ears (tucked slightly snugger & angled naturally back!)
    for h in (-1, 1):
        ear_rings = []
        cnt = 20
        profile = [
            (0.95, 14.8, 0.0),
            (1.00, 16.2, 0.3),
            (0.98, 17.5, 0.5),
            (0.84, 18.0, 0.2),
            (0.68, 17.6, -0.1),
            (0.52, 16.5, -0.3),
            (0.28, 16.2, -0.4),
        ]
        for sc_e, x_d, y_o in profile:
            ring = []
            for i in range(cnt):
                t = 2.0 * pi * i / cnt
                ey = -14.2 + y_o + sc_e * (2.7 * cos(t) + 0.4 * sin(t))
                ez = 73.4 + sc_e * (4.5 * sin(t) - 0.3 * cos(t))
                ex = h * (x_d + 0.50 * cos(t))
                ring.append((ex, ey, ez))
            ear_rings.append(ring)
        objs.append(build_loft(f"Ear | {'left' if h > 0 else 'right'} sculpted pinna", ear_rings, "skin", mats, cap_ends=True, subsurf=2))

    return objs


# ==============================================================================
# 8. SCULPTED CERAMIC HAIR: BROWS, CURLED MOUSTACHE, LUSH BEARD & HORIZONTAL NAPE WAVES
# ==============================================================================
def build_hair(mats):
    objs = []

    # A. Expressive V-Angled Sculpted Eyebrows
    for h in (-1, 1):
        b_path = [
            (h * 1.4, -32.2, 77.1, 1.35, 1.20),
            (h * 3.8, -32.6, 78.6, 2.20, 1.75),
            (h * 7.2, -31.5, 80.1 + (0.2 if h > 0 else 0.0), 2.35, 1.90),
            (h * 10.8, -29.3, 79.6, 2.05, 1.65),
            (h * 13.8, -26.5, 77.7, 1.35, 1.20),
            (h * 15.2, -25.0, 76.4, 0.65, 0.65),
        ]
        def brow_prof(th, u, cx, cy):
            g = 1.0 + 0.07 * cos(3.0 * th + 2.0 * u) * smoothstep(0.1, 0.3, u) * smoothstep(1.0, 0.75, u)
            return cx * g, cy * g
        objs.append(build_sweep_tube(
            f"Brow | {'wink' if h > 0 else 'open'} side",
            b_path, "hair", mats, N=20, subsurf=2, profile_fn=brow_prof, up_hint=Vector((0, 0, 1)), resample=2
        ))

    # B. Lush, Gracefully Curled Asymmetric S-Curved Ceramic Moustache!
    #    Winking side (+X) lifts cleanly ABOVE the crooked teeth & curls gracefully UP into a fine ceramic flick!
    m_specs = [
        (-1, [
            (  0.6, -33.2, 67.8, 1.35, 1.20),
            ( -2.4, -34.2, 67.1, 2.35, 2.00),
            ( -6.4, -33.8, 65.8, 2.75, 2.30),
            (-10.8, -31.5, 65.7, 2.55, 2.15),
            (-14.6, -28.4, 67.3, 1.95, 1.70),
            (-16.4, -25.8, 69.5, 1.15, 1.05),
            (-15.2, -25.2, 70.9, 0.42, 0.42),
        ]),
        ( 1, [
            ( -0.6, -33.2, 67.9, 1.35, 1.20),
            (  2.5, -34.1, 67.9, 2.25, 1.95),
            (  6.5, -33.5, 68.5, 2.50, 2.10),  # lifted +0.6 mm to reveal joyful grin & teeth in FRONT & SIDE!
            ( 10.6, -31.1, 69.5, 2.35, 2.00),
            ( 14.0, -27.9, 70.8, 1.85, 1.60),
            ( 15.6, -25.2, 72.3, 1.05, 0.95),
            ( 14.3, -24.8, 73.3, 0.42, 0.42),  # graceful inward ceramic curl flick!
        ]),
    ]
    for h, m_path in m_specs:
        def must_prof(th, u, cx, cy):
            g = 1.0 + 0.095 * cos(3.0 * th - 1.5 * u) * smoothstep(0.08, 0.30, u) * smoothstep(1.0, 0.72, u)
            return cx * g, cy * g
        objs.append(build_sweep_tube(
            f"Moustache | {'wink' if h > 0 else 'open'} wing",
            m_path, "hair", mats, N=22, subsurf=2, profile_fn=must_prof, up_hint=Vector((0, 0, 1)), resample=3
        ))

    # C. Sculpted Overlapping S-Wave Ceramic Beard (pulled ~2 mm tighter to match SIDE overlay,
    #    and carved cleanly below the right-side upturned grin so teeth & lower lip shine!)
    N_b = 32
    core_levels = [
        (43.2,  2.0, -24.5, -22.4,  1.6),
        (45.5,  0.8, -26.8, -20.5,  5.0),
        (49.0,  0.0, -28.6, -18.8,  9.0),
        (53.5,  0.0, -29.4, -17.8, 12.8),
        (58.5,  0.0, -29.2, -17.2, 15.6),
        (63.0,  0.0, -28.2, -17.0, 16.2),
        (66.5,  0.0, -26.2, -17.4, 15.3),
        (69.5,  0.0, -24.0, -17.8, 13.6),
    ]
    c_rings = []
    for z, xc, yf, yb, hw in core_levels:
        yc, ry = 0.5 * (yf + yb), 0.5 * (yb - yf)
        ring = []
        for i in range(N_b):
            t = 2.0 * pi * i / N_b
            ct, st = cos(t), sin(t)
            x, y = xc + hw * ct, yc + ry * st
            if st < -0.2 and z > 59.5:
                smile_z = 61.5 + 0.18 * x + 0.032 * x * x
                mouth_w = smoothstep(12.2, 6.0, abs(x - 3.2))
                if z > smile_z - 1.2:
                    tuck = smoothstep(smile_z - 1.2, smile_z + 2.5, z) * mouth_w * smoothstep(-0.2, -0.8, st)
                    y += 4.8 * tuck
                    z_eff = z - 2.2 * tuck * smoothstep(69.5, 62.5, z)
                else:
                    z_eff = z
            else:
                z_eff = z
            ring.append((x, y, z_eff))
        c_rings.append(ring)
    objs.append(build_loft("Beard | sculpted inner core", c_rings, "hair", mats, cap_ends=True, subsurf=2))

    # 11 lush overlapping S-wave beard locks — top roots dropped cleanly beneath crooked lower lip on +X!
    lock_defs = [
        # (x_top, z_top, z_bot, x_bot, y_mid_off, w_mid, d_mid, wave_amp, wave_phase)
        (  0.0, 60.5, 42.2,  2.5, -1.4, 3.5, 2.5,  1.8,  0.4),
        ( -4.2, 61.8, 44.2, -0.6, -1.3, 3.4, 2.4,  1.9,  0.1),
        (  4.5, 61.6, 44.6,  4.4, -1.8, 3.5, 2.6, -1.7,  0.6),  # cleanly covers lower-lip junction without skin poke!
        ( -8.5, 64.2, 47.6, -4.8, -1.1, 3.5, 2.4,  2.1, -0.2),
        (  8.8, 63.6, 48.0,  7.4, -1.4, 3.5, 2.5, -2.0,  0.3),
        (-12.6, 66.0, 51.6, -9.2, -0.7, 3.3, 2.3,  1.8, -0.4),
        ( 12.6, 66.2, 52.0, 10.6, -0.7, 3.3, 2.3, -1.8,  0.0),
        (-15.7, 68.2, 55.8, -13.0, -0.2, 2.8, 2.1,  1.1, -0.5),
        ( 15.7, 69.0, 56.2,  13.6, -0.2, 2.8, 2.1, -1.1, -0.1),
        (-16.5, 69.2, 59.0, -14.5,  2.0, 2.4, 2.0,  0.6,  0.0),
        ( 16.5, 69.8, 59.5,  14.7,  2.0, 2.4, 2.0, -0.6,  0.0),
    ]
    for idx, (xt, zt, zb, xb, ymo, wm, dm, wamp, wph) in enumerate(lock_defs):
        pts = []
        n_st = 7
        for s in range(n_st):
            u = s / (n_st - 1)
            z = zt + (zb - zt) * u
            x = xt + (xb - xt) * (u ** 1.15) + wamp * sin(pi * 1.65 * u + wph) * sin(pi * u)
            if idx == 0 and u > 0.78:
                k = (u - 0.78) / 0.22
                x += 1.6 * k * k
                z += 0.7 * k * k
            x_norm = clamp(abs(x) / 17.8)
            y_base = -29.8 + 5.6 * (x_norm ** 1.7) + 5.2 * (max(0.0, (53.0 - z) / 11.0) ** 1.5)
            tuck_top = 0.85 if idx in (2, 4) else 1.45
            y = y_base + ymo * sin(pi * u) + tuck_top * smoothstep(0.22, 0.0, u)
            # Graceful ceramic tapering right to pointed lock tip!
            taper = smoothstep(0.0, 0.16, u) * (1.0 - 0.88 * (u ** 1.65))
            ra = max(0.35, wm * (0.28 + 0.72 * taper))
            rb = max(0.32, dm * (0.28 + 0.72 * taper))
            pts.append((x, y, z, ra, rb))
        def lock_prof(th, u, cx, cy):
            g = 1.0 + 0.06 * cos(2.0 * th)
            return cx * g, cy * g
        objs.append(build_sweep_tube(
            f"Beard | lock {idx + 1:02d}",
            pts, "hair", mats, N=14, subsurf=2, profile_fn=lock_prof, up_hint=Vector((0, 1, 0)), resample=2
        ))

    # D. Lush HORIZONTAL Rolling Ceramic Nape Hair Waves + Integrated Temple Curls!
    #    Eliminates BOTH the floating front-of-ear comma AND the visible smooth cylinder / braid look!
    #    Matches turnaround BACK (horizontal scalloped outward-curling ceramic waves under hat brim)
    #    and SIDE (flowing smoothly backward behind the ear onto the blue smock shoulders)!
    nc_rings = [
        [(rx * cos(2 * pi * i / 28), yc + ry * sin(2 * pi * i / 28), z) for i in range(28)]
        for z, rx, ry, yc in [
            (69.8, 16.5, 11.0, -9.8),
            (72.5, 18.2, 12.2, -9.5),
            (75.5, 17.8, 12.0, -10.0),
            (78.2, 16.8, 11.4, -11.0),
        ]
    ]
    objs.append(build_loft("Hair | nape base cushion", nc_rings, "hair", mats, cap_ends=True, subsurf=2))

    for h in (-1, 1):
        # 1. Integrated temple hair wave emerging smoothly from UNDER hat brim
        temple = [
            (h * 13.8, -20.5, 78.5, 1.9, 1.7),
            (h * 16.0, -19.6, 76.4, 2.3, 2.1),
            (h * 18.2, -18.8, 74.2, 2.1, 1.9),
            (h * 20.0, -18.2, 73.3, 1.5, 1.4),
            (h * 20.4, -17.9, 74.4, 0.7, 0.7),
        ]
        objs.append(build_sweep_tube(f"Hair | {'L' if h > 0 else 'R'} temple wave", temple, "hair", mats, N=14, subsurf=2, resample=2))

        # 2. Horizontal rolling nape waves sweeping OUTWARD left & right (2 lush stacked tiers!)
        horiz_waves = [
            # Center-back lush outward-scrolling horizontal wave
            [
                (h *  0.0,  1.2, 76.8, 2.6, 2.3),
                (h *  3.2,  3.2, 76.2, 3.0, 2.6),
                (h *  7.2,  3.8, 74.2, 3.0, 2.6),
                (h * 10.6,  2.8, 72.5, 2.5, 2.2),
                (h * 11.8,  2.0, 73.8, 1.4, 1.3),
                (h * 10.8,  1.8, 74.8, 0.6, 0.6),
            ],
            # Mid-back broad horizontal scroll sweeping wide to outer shoulders
            [
                (h *  4.5,  1.8, 77.2, 2.5, 2.2),
                (h *  8.8,  3.8, 76.0, 3.1, 2.7),
                (h * 13.4,  3.6, 73.6, 3.1, 2.7),
                (h * 17.0,  1.6, 71.8, 2.6, 2.3),
                (h * 18.2,  0.2, 73.2, 1.4, 1.3),
                (h * 17.2, -0.5, 74.4, 0.6, 0.6),
            ],
            # Rear-most side wave sweeping BACK behind ear to y=+5.2
            [
                (h * 10.5, -2.5, 77.0, 2.4, 2.2),
                (h * 14.5,  0.5, 75.5, 3.0, 2.6),
                (h * 18.0,  2.4, 73.0, 3.0, 2.6),
                (h * 20.4,  0.5, 71.4, 2.4, 2.2),
                (h * 21.0, -1.5, 72.8, 1.3, 1.2),
                (h * 20.0, -2.5, 74.0, 0.6, 0.6),
            ],
            # Behind-ear lush wave tucked cleanly BEHIND the ear helix (no overlap onto pinna!)
            [
                (h * 13.8, -8.2, 76.8, 2.3, 2.1),
                (h * 16.5, -7.0, 74.8, 2.8, 2.5),
                (h * 18.6, -5.0, 72.4, 2.7, 2.4),
                (h * 19.4, -3.4, 71.2, 2.2, 2.0),
                (h * 19.2, -2.5, 72.6, 1.1, 1.0),
            ],
            # Lower behind-ear curl tucking softly behind/below earlobe
            [
                (h * 14.4, -10.5, 73.6, 1.9, 1.8),
                (h * 17.0,  -9.5, 71.5, 2.4, 2.1),
                (h * 18.4,  -7.6, 70.4, 2.2, 1.9),
                (h * 18.2,  -5.8, 71.2, 1.3, 1.2),
                (h * 17.4,  -5.0, 72.2, 0.6, 0.6),
            ],
            # Lower center-back fill curl
            [
                (h *  1.2,  2.5, 73.2, 2.4, 2.1),
                (h *  5.5,  4.4, 72.0, 2.7, 2.3),
                (h * 10.5,  4.2, 71.2, 2.6, 2.3),
                (h * 14.5,  2.4, 71.0, 2.1, 1.9),
                (h * 15.6,  1.2, 72.2, 1.0, 1.0),
            ],
        ]
        for ci, cp in enumerate(horiz_waves):
            def nw_prof(th, u, cx, cy):
                g = 1.0 + 0.075 * cos(3.0 * th + 1.2 * u)
                return cx * g, cy * g
            objs.append(build_sweep_tube(
                f"Hair | {'L' if h > 0 else 'R'} nape wave {ci + 1}",
                cp, "hair", mats, N=16, subsurf=2, profile_fn=nw_prof, up_hint=Vector((0, 0, 1)), resample=2
            ))

    return objs


# ==============================================================================
# 9. SLOUCHY HOOKED RED GNOME CAP (ZERO BRIM PINCH, EXACT 107.3 MM HEIGHT!)
# ==============================================================================
def build_cap(mats):
    # Smooth, non-self-intersecting rolled brim + exact 107.3 mm total height match!
    # Tightened left shoulder ~1.4 mm to lock tightly onto turnaround FRONT, SIDE, BACK!
    spine_ctrl = [
        ( 0.0, -17.5, 76.6, 16.8, 16.2),  # inner brim base — wide Z step eliminates ring overlap!
        (-0.1, -17.2, 78.6, 18.2, 17.6),  # plump rolled brim crest
        (-0.3, -16.8, 80.7, 17.4, 16.8),  # top of rolled brim
        (-0.7, -16.4, 82.8, 16.0, 15.4),  # lower waist
        (-0.9, -15.9, 85.0, 15.9, 15.2),  # slouch bulge 1
        (-0.7, -15.4, 87.6, 14.0, 13.4),  # mid waist
        (-0.3, -14.9, 90.1, 13.7, 13.0),  # slouch bulge 2
        ( 0.5, -14.4, 93.2, 11.5, 11.0),  # upper cone
        ( 1.9, -13.9, 96.8,  9.3,  9.0),  # curving right (+X) and back
        ( 4.2, -13.4, 100.4, 7.5,  7.3),  # rising to high arch
        ( 7.5, -12.9, 102.6, 5.7,  5.7),  # crown apex (outer top hits z ~ 107.6 mm)
        (11.0, -12.6, 102.0, 4.6,  4.6),  # turning over hook
        (13.3, -12.4,  99.4, 3.7,  3.7),  # chunky rounded downward curl
        (13.5, -12.3,  96.5, 2.8,  2.8),  # juicy ceramic tip
        (12.4, -12.2,  95.2, 1.7,  1.7),
        (11.6, -12.2,  95.1, 0.55, 0.55),
    ]

    def cap_sculpt(lev):
        def fn(co, nor):
            x, y, z = co
            if z < 81.2 or z > 99.5:
                return Vector((0, 0, 0))
            ang = atan2(y + 16.0, x)
            mask = smoothstep(81.4, 83.4, z) * smoothstep(99.5, 95.8, z)
            if lev == 1:
                z1 = 84.4 + 1.05 * cos(ang - 0.55)
                c1 = -0.82 * ga(z, z1, 1.15) + 0.72 * ga(z, z1 + 1.9, 1.60)
                z2 = 89.8 + 1.15 * sin(ang + 0.35)
                c2 = -0.78 * ga(z, z2, 1.15) + 0.68 * ga(z, z2 + 1.8, 1.60)
                hook_pinch = -0.70 * ga(z, 95.2, 1.8) * smoothstep(2.5, 9.5, x)
                return nor * ((c1 + c2) * mask + hook_pinch)
            elif lev == 2:
                z1 = 84.4 + 1.05 * cos(ang - 0.55)
                z2 = 89.8 + 1.15 * sin(ang + 0.35)
                sharp = -0.25 * ga(z, z1, 0.52) - 0.22 * ga(z, z2, 0.52)
                return nor * (sharp * smoothstep(82.2, 84.0, z) * smoothstep(96.5, 93.8, z))
            return Vector((0, 0, 0))
        return fn

    return build_sweep_tube(
        "Cap | slouchy hooked gnome cap",
        spine_ctrl, "hat", mats, N=36, subsurf=0,
        multires_funcs=[(1, cap_sculpt(1)), (2, cap_sculpt(2))],
        up_hint=Vector((0, 1, 0)), resample=2, smooth_iters={1: 1}
    )


# ==============================================================================
# SCENE ASSEMBLY
# ==============================================================================
def build_scene(out_blend=None):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 0.001

    mats = make_materials()
    build_plinth(mats)
    build_boots(mats)
    build_seat(mats)
    build_trousers(mats)
    build_smock(mats)
    build_arms_and_hands(mats)
    head_objs = build_head_and_face(mats)
    build_hair(mats)
    build_cap(mats)

    bpy.ops.object.camera_add()
    cam = bpy.context.object
    sc.camera = cam
    cam.data.type = "ORTHO"
    cam.data.clip_start = 0.1
    cam.data.clip_end = 1000.0
    cam.data.ortho_scale = 119.0
    cam.location = Vector((33.0, -230.0, 76.0))
    cam.rotation_euler = (Vector((0.0, 0.0, 54.0)) - cam.location).to_track_quat("-Z", "Y").to_euler()

    sc.world = bpy.data.worlds.new("Studio")
    bg = sc.world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.58, 0.64, 0.74, 1.0)
    bg.inputs[1].default_value = 0.48

    for lname, power, size, pos in [
        ("Key softbox", 240000, 95, (-75, -145, 175)),
        ("Fill light",  110000, 90, ( 95,  -75, 105)),
        ("Rim light",   180000, 75, ( 30,   95, 135)),
    ]:
        bpy.ops.object.light_add(type="AREA", location=pos)
        lo = bpy.context.object
        lo.name = lname
        lo.data.energy = power
        lo.data.shape = "DISK"
        lo.data.size = size
        lo.rotation_euler = (Vector((0, 0, 54)) - lo.location).to_track_quat("-Z", "Y").to_euler()

    bpy.ops.object.select_all(action="DESELECT")
    head_objs[0].select_set(True)
    bpy.context.view_layer.objects.active = head_objs[0]

    if out_blend:
        Path(out_blend).parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(out_blend))
        print(f"Saved editable blend to {out_blend}")


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out_path = argv[0] if argv else str(Path(__file__).resolve().parent / "Clive-PoseFace.blend")
    build_scene(out_path)
