"""Turn 9 · Continuous trousers, 360-degree Greek-carved hair, soft garment rims,
anatomical arms/hands, and stiff-leather boots built on the Turn 8 parent.
"""
import argparse
import math
import runpy
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Quaternion, Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parent
PARENT_TURN8 = EXPERIMENTS / "2026-11-21-rounded-seat"
PARENT_TURN7 = EXPERIMENTS / "2026-11-21-seat-and-smock"
PARENT_TURN6 = EXPERIMENTS / "2026-11-21-felt-and-carved-hair"
PARENT_TURN4 = EXPERIMENTS / "2026-11-21-turnaround-pose-face"

t8 = runpy.run_path(str(PARENT_TURN8 / "sculpt_turn.py"))
seat_skin = t8["seat_skin"]
t7 = t8["tailoring"]
t6 = t7["helpers"]
t4 = runpy.run_path(str(PARENT_TURN4 / "build_clive.py"))

clamp = t6["clamp"]
ease = t6["ease"]
bell = t6["bell"]
sample = t6["sample"]
by_first = t6["by_first"]
loft = t6["loft"]
create_mesh_obj = t7["mesh_object"]
build_sweep_tube = t4["build_sweep_tube"]
smoothstep = t4["smoothstep"]
ga = t4["ga"]

RIM = t6["RIM"]
CROWN = t6["CROWN"]
HOOK = t6["HOOK"]
FOLDS = t6["FOLDS"]
rim_at = t6["rim_at"]
tuck_under_brim = t6["tuck_under_brim"]
BEARD = t6["BEARD"]
MOUSTACHE = t6["MOUSTACHE"]

PELVIS = t7["PELVIS"]
COUNT = t7["COUNT"]
ANGLES = t7["ANGLES"]
angular_direction = t7["angular_direction"]

# Keep Turn 7/8's seat_skin active inside Turn 7's helpers too.
t7["skin_point"] = seat_skin


def closest_bvh_distance(tree, p):
    """Return distance to closest surface point in BVHTree and the hit point/normal."""
    loc, normal, _, dist = tree.find_nearest(p)
    return loc, normal, dist


def pelvis_clearance_vec(p, tree, offset):
    """Push p radially outward from the pelvis centerline so it clears Turn 8 skin."""
    lo, hi = PELVIS[0][0] - 0.5, PELVIS[-1][0]
    if not (lo < p.z < hi):
        return p
    _, front, rear, _ = by_first(PELVIS, clamp(p.z, PELVIS[0][0], PELVIS[-1][0]))
    center = Vector((0.0, front + 0.44 * (rear - front), p.z))
    radial = p - center
    if radial.length < 1e-6:
        return p
    direction = radial.normalized()
    hit, _, _, distance = tree.ray_cast(center + direction * 46.0, -direction, 45.0)
    if hit is not None:
        target = 46.0 - distance + offset
        diff = target - radial.length
        if diff > 0.0:
            return p + direction * diff
    return p


def bvh_clear_from_center(p, tree, center, min_offset, max_ray=30.0):
    """Push point radially outward from leg/boot center if inside BVH + min_offset."""
    radial = Vector((p.x - center.x, p.y - center.y, 0.0))
    if radial.length < 1e-5:
        return p
    d = radial.normalized()
    orig = Vector((center.x, center.y, p.z)) + d * max_ray
    hit, _, _, dist = tree.ray_cast(orig, -d, max_ray - 0.5)
    if hit is not None:
        # Guard against hitting the opposite leg across x = 0 when center is offset laterally
        if abs(center.x) > 3.0 and hit.x * center.x < 0.5:
            return p
        target_r = max_ray - dist + min_offset
        if radial.length < target_r:
            delta = target_r - radial.length
            return Vector((p.x + d.x * delta, p.y + d.y * delta, p.z))
    return p


# ==============================================================================
# 1. THICKENED SOFT WORN-FELT CAP (nonplanar Turn 6 curve + soft bullnose hem)
# ==============================================================================
def build_soft_cap(mats):
    steps = 80
    last = CROWN[-1][0]
    lower = [last * i / 35 for i in range(36)]
    body = [(distance, *by_first(CROWN, distance), Quaternion()) for distance in lower]
    center = Vector(CROWN[-1][1:4])
    vertical = Vector((0.0, 0.0, 1.0))
    slouch = Vector((0.66, -0.75, 0.0)).normalized()
    bend_axis = vertical.cross(slouch)

    def turn(distance):
        bend, _, _ = by_first(HOOK, distance)
        return Quaternion(bend_axis, math.radians(bend))

    intervals = 55
    step = HOOK[-1][0] / intervals
    for i in range(1, intervals + 1):
        distance = i * step
        center += (turn(distance - step * 0.5) @ vertical) * step
        _, width, depth = by_first(HOOK, distance)
        # Slightly widen the inner concave hook section to keep the crease open and organic.
        width_adj = width * (1.0 + 0.08 * bell(distance, 10.5, 5.5))
        depth_adj = depth * (1.0 + 0.08 * bell(distance, 10.5, 5.5))
        body.append((last + distance, *center, width_adj, depth_adj, turn(distance)))

    rings = []
    rim_outward = []
    for r_idx, (distance, x, y, z, width, depth, orientation) in enumerate(body):
        c_vec = Vector((x, y, z))
        lateral = orientation @ Vector((1.0, 0.0, 0.0))
        front = orientation @ Vector((0.0, -1.0, 0.0))
        ring = []
        for j in range(steps):
            theta = 360.0 * j / steps
            angle = math.radians(theta)
            unit = math.sin(angle) * lateral + math.cos(angle) * front
            point = c_vec + lateral * (width * math.sin(angle)) + front * (depth * math.cos(angle))
            rim = rim_at(theta)
            rim_ellipse = Vector((17.9 * math.sin(angle), -15.6 - 19.2 * math.cos(angle), 77.0))
            delta = rim - rim_ellipse
            point.x += delta.x * math.exp(-distance / 5.1)
            point.y += delta.y * math.exp(-distance / 5.1)
            point.z += delta.z * math.exp(-distance / 9.2)

            # Fade fold relief cleanly near the brim edge and inside the tight hook turn
            # so the underside of the spiral hook stays smooth with zero pinch spike.
            edge_fade = ease((distance - 0.30) / 1.40)
            hook_clear = ease((20.8 - distance) / 5.5)
            relief = (0.72 * bell(distance, 1.55, 1.35) - 0.24 * bell(distance, 3.35, 1.25)) * edge_fade
            for curve in FOLDS:
                azimuth = (theta - curve[0][0]) % 360.0 + curve[0][0]
                if azimuth <= curve[-1][0]:
                    height, weight = by_first(curve, azimuth)
                    softness = 1.78 - 0.50 * ease((height - 7.0) / 17.0)
                    relief += weight * hook_clear * ease((21.5 - distance) / 7.0) * (
                        bell(distance, height, softness) - 0.40 * bell(distance, height + 1.85, 0.92)
                    )
            final_pt = point + unit * relief
            ring.append(final_pt)
            if r_idx == 0:
                # True flared outward direction perpendicular to rim curve in XY
                rim_outward.append(Vector((math.sin(angle), -math.cos(angle), 0.0)).normalized())
        rings.append(ring)

    # C1-continuous semicircular worn-felt brim turn starting smoothly from rings[0] (offset 0,0)
    # Lifting inner brow roll subtly over forehead arch so eyes/brows stay framed cleanly.
    lip_stations = [
        (-0.26, -0.30),
        (-0.66, -0.68),
        (-1.22, -0.76),
        (-1.86, -0.50),
        (-2.45, +0.16),
        (-2.88, +1.30),
    ]
    hem_rings = []
    for d_rad, d_z in reversed(lip_stations):
        hring = []
        for j, (p, u_rad) in enumerate(zip(rings[0], rim_outward)):
            angle = math.radians(360.0 * j / steps)
            brow_lift = 0.28 * ease((math.cos(angle) - 0.35) / 0.65)
            v = p + u_rad * d_rad
            v.z += d_z + brow_lift * (abs(d_rad) / 2.88)
            hring.append(v)
        hem_rings.append(hring)

    return loft("Cap | thick felt, draped folds", [*hem_rings, *rings], "hat", mats, subsurf=1)


# ==============================================================================
# 2. SEAT-FITTED SOFT-HEM SMOCK WITH NATURAL SHOULDER / DELTOID FULLNESS
# ==============================================================================
def build_soft_smock(mats, pelvis):
    graph = bpy.context.evaluated_depsgraph_get()
    tree = BVHTree.FromObject(pelvis, graph)

    # Exact tangent start at u_start = 0.020 so the folded hem roll shares zero step/crease!
    u_start = 0.020
    u_body = [0.020, 0.042, 0.068, 0.098] + [0.10 + 0.90 * k / 38 for k in range(1, 39)]

    def smock_surface_point(u, theta):
        s, c = math.sin(theta), -math.cos(theta)
        back = 0.5 * (1.0 + c)
        fitted = ease((c + 0.72) / 0.85)
        legacy_z = 36.6 + 19.3 * (back ** 1.05)
        legacy_y = -13.8 + 43.2 * (back ** 1.02)
        hem_z = 37.0 + 19.15 * (back ** 1.21)
        hem_z += 0.52 * s * fitted - 1.85 * bell(c, 0.15, 0.40)
        hem_z += 1.55 * bell(c, 0.87, 0.33) + 0.36 * fitted
        edge = seat_skin(theta, hem_z)
        outward = angular_direction(theta)
        # Keep front smock hem softly tucked onto belly/hips behind wrists (no bar jutting forward!)
        hem_front = Vector((18.8 * s, legacy_y + 1.45 * (1.0 - back), legacy_z + 0.85 * (1.0 - back)))
        hem = hem_front.lerp(edge + outward * 0.65, fitted)
        collar = Vector((12.4 * s, -10.5 + 11.8 * c, 66.8 + 3.2 * back))
        p = hem.lerp(collar, u)

        dome = math.sin(math.pi * u)
        shoulder = math.sin(math.pi * max(0.0, (u - 0.14) / 0.86))
        deltoid_swell = 3.25 * s * shoulder + 0.95 * s * bell(abs(s), 0.78, 0.25) * bell(u, 0.66, 0.24)
        p.x += deltoid_swell
        p.y += dome * (4.85 * (back ** 0.72) - 2.35 * (1.0 - back))
        p.z += 9.20 * (u ** 0.62) * ((1.0 - u) ** 0.88) * (0.30 + 1.15 * back)

        # Diagonal cloth tension folds sweeping smoothly down into a soft woven cloth hem
        fold_a = 0.14 + 0.060 * s + 0.045 * c
        fold_b = 0.29 - 0.075 * s + 0.032 * c
        fold = 0.96 * bell(u, fold_a, 0.075) - 0.44 * bell(u, fold_a + 0.084, 0.045)
        fold += (0.80 + 0.30 * s) * bell(u, fold_b, 0.062) - 0.35 * bell(u, fold_b + 0.074, 0.048)
        pinch = 0.45 * bell(u, 0.25 + 0.09 * s, 0.075) * bell(c, -0.13, 0.24)
        hem_bead = (0.15 + 0.65 * fitted) * bell(u, 0.032, 0.038)
        p += outward * (fitted * fold + pinch + hem_bead)
        return p, outward, fitted

    hem_pts, hem_tangents, hem_outwards = [], [], []
    for theta in ANGLES:
        p0, out_d, _ = smock_surface_point(u_start, theta)
        p1, _, _ = smock_surface_point(u_start + 0.025, theta)
        p0 = pelvis_clearance_vec(p0, tree, 0.48)
        p1 = pelvis_clearance_vec(p1, tree, 0.48)
        tang = (p0 - p1).normalized()
        hem_pts.append(p0)
        hem_tangents.append(tang)
        hem_outwards.append(out_d)

    # Smooth C1 semicircular hem turn ending right BEFORE u_start=(0,0) with zero seam step!
    hem_roll_stations = [
        (-2.15, +0.85),
        (-1.60, +0.00),
        (-1.05, -0.58),
        (-0.42, -0.72),
        (-0.08, -0.38),
    ]
    rings = []
    for r_idx, (off_out, off_tan) in enumerate(hem_roll_stations):
        ring = []
        for idx, theta in enumerate(ANGLES):
            p = hem_pts[idx] + hem_outwards[idx] * off_out + hem_tangents[idx] * off_tan
            if r_idx >= 1:
                p = pelvis_clearance_vec(p, tree, 0.28 + 0.16 * (r_idx / 4.0))
            ring.append(p)
        rings.append(ring)

    for u in u_body:
        ring = []
        for theta in ANGLES:
            p, _, _ = smock_surface_point(u, theta)
            p = pelvis_clearance_vec(p, tree, 0.36 + 0.10 * bell(u, 0.03, 0.06))
            ring.append(p)
        rings.append(ring)

    smock = loft("Smock | fitted soft-hem tunic", rings, "blue", mats, subsurf=1)

    # Ensure brass tunic button hugs the front smock placket cleanly.
    btn = bpy.data.objects.get("Smock | brass tunic button")
    if btn is not None:
        sg = bpy.context.evaluated_depsgraph_get()
        sm_tree = BVHTree.FromObject(smock, sg)
        loc, nor, _, _ = sm_tree.ray_cast(Vector((0.0, -30.0, 39.8)), Vector((0.0, 1.0, 0.0)), 30.0)
        if loc is not None:
            # Current button sits centered near (0, -15.45, 39.85)
            cur_y = sum(v.co.y for v in btn.data.vertices) / len(btn.data.vertices)
            dy = (loc.y - 0.35) - cur_y
            for v in btn.data.vertices:
                v.co.y += dy
    return smock


# ==============================================================================
# 3. ANATOMICAL SLEEVES, FOREARMS & ARTICULATED HANDS (voxel-fused per side)
# ==============================================================================
def build_anatomical_tube(name, sections, mat_name, mats, N=24, subsurf=1,
                          axis_mod_fn=None, smooth_iters=0):
    """Build closed lofted limb/finger with directional cross-section modulation."""
    pts = [Vector(s[:3]) for s in sections]
    n_pts = len(pts)
    tans = []
    for j in range(n_pts):
        d = pts[min(n_pts - 1, j + 1)] - pts[max(0, j - 1)]
        tans.append(d.normalized() if d.length > 1e-8 else Vector((0.0, 0.0, -1.0)))

    # Parallel transport frame
    up_hint = Vector((0.0, -1.0, 0.0))
    n0 = up_hint - tans[0] * up_hint.dot(tans[0])
    if n0.length < 1e-4:
        n0 = Vector((1.0, 0.0, 0.0)) - tans[0] * tans[0].x
    n0.normalize()
    b0 = tans[0].cross(n0).normalized()
    normals, binorms = [n0], [b0]
    for j in range(1, n_pts):
        ax = tans[j - 1].cross(tans[j])
        if ax.length > 1e-6:
            ang = math.acos(clamp(tans[j - 1].dot(tans[j]), -1.0, 1.0))
            nj = (Matrix_Rot(ang, ax.normalized()) @ normals[-1]).normalized()
        else:
            nj = normals[-1].copy()
        nj = (nj - tans[j] * nj.dot(tans[j])).normalized()
        bj = tans[j].cross(nj).normalized()
        normals.append(nj)
        binorms.append(bj)

    rings = []
    for j, sec in enumerate(sections):
        c = pts[j]
        ra, rb = sec[3], sec[4]
        u = j / max(1, n_pts - 1)
        nj, bj = normals[j], binorms[j]
        ring = []
        for i in range(N):
            th = math.tau * i / N
            cx, cy = math.cos(th), math.sin(th)
            if axis_mod_fn is not None:
                dx_s, dy_s, dz_s, r_mul = axis_mod_fn(u, th, cx, cy, c)
            else:
                dx_s, dy_s, dz_s, r_mul = 0.0, 0.0, 0.0, 1.0
            p = c + bj * (ra * cx * r_mul) + nj * (rb * cy * r_mul)
            p.x += dx_s
            p.y += dy_s
            p.z += dz_s
            ring.append(p)
        rings.append(ring)

    obj = create_mesh_obj_rings(name, rings, mat_name, mats, cap_ends=True, subsurf=subsurf)
    if smooth_iters > 0:
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.smooth_vert(bm, verts=bm.verts, factor=0.35, use_axis_x=True, use_axis_y=True, use_axis_z=True)
        bm.to_mesh(obj.data)
        bm.free()
    return obj


def Matrix_Rot(angle, axis):
    return Quaternion(axis, angle).to_matrix()


def create_mesh_obj_rings(name, rings, mat_name, mats, cap_ends=True, subsurf=1):
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
    return create_mesh_obj(name, verts, faces, mat_name, mats, subsurf=subsurf)


def fuse_sources(name, sources, hidden, material, voxel_size=0.15, smooth_factor=0.62, smooth_iters=2):
    graph = bpy.context.evaluated_depsgraph_get()
    vertices, faces = [], []
    for obj in sources:
        ev = obj.evaluated_get(graph)
        me = ev.to_mesh()
        offset = len(vertices)
        vertices.extend(ev.matrix_world @ v.co for v in me.vertices)
        faces.extend(tuple(offset + i for i in f.vertices) for f in me.polygons)
        ev.to_mesh_clear()
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    mesh.remesh_voxel_size = voxel_size
    mesh.use_remesh_fix_poles = True
    bpy.ops.object.voxel_remesh()
    if smooth_iters > 0:
        sm = obj.modifiers.new("Ease fused joints", "SMOOTH")
        sm.factor = smooth_factor
        sm.iterations = smooth_iters
    obj.data.materials.clear()
    obj.data.materials.append(material)
    for p in obj.data.polygons:
        p.use_smooth = True
    for src in sources:
        for col in list(src.users_collection):
            col.objects.unlink(src)
        hidden.objects.link(src)
    return obj


def build_anatomy_arms_and_hands(mats):
    anat_sources = bpy.data.collections.get("Anatomy sources | show to edit, hide to render")
    if anat_sources is None:
        anat_sources = bpy.data.collections.new("Anatomy sources | show to edit, hide to render")
        bpy.context.scene.collection.children.link(anat_sources)

    hands = []
    for h in (-1, 1):
        side = "left" if h > 0 else "right"

        # A. Draped anatomical sleeve flowing smoothly from hunched smock shoulder
        sl_sections = [
            (h * 10.2, -2.5, 65.5, 5.5, 6.8),
            (h * 13.6, -3.7, 64.0, 6.5, 7.6),
            (h * 16.6, -4.8, 61.2, 7.1, 8.0),   # broad deltoid cap sitting organically above armhole
            (h * 18.2, -6.1, 57.8, 6.6, 7.5),
            (h * 18.7, -7.2, 54.4, 6.2, 7.0),
            (h * 18.7, -8.2, 50.9, 5.8, 6.5),
            (h * 18.3, -8.8, 48.3, 5.5, 6.0),
            (h * 18.0, -9.1, 46.5, 5.0, 5.4),
        ]

        def sleeve_mod(u, th, cx, cy, c, s_sign=h):
            medial = max(0.0, -s_sign * cx)
            posterior = max(0.0, -cy)
            shoulder_mask = ease((0.44 - u) / 0.44)
            dx_in = -s_sign * medial * 1.9 * shoulder_mask
            dy_in = -posterior * 1.5 * shoulder_mask
            crease = (
                0.42 * bell(u, 0.62 + 0.07 * cy, 0.095)
                - 0.34 * bell(u, 0.72 + 0.06 * cy, 0.062)
                + 0.30 * bell(u, 0.46 - 0.05 * cy, 0.10)
            ) * (0.45 + 0.55 * max(0.0, cy))
            r_scale = 1.0 - (0.06 * posterior + 0.05 * medial) * shoulder_mask + crease * 0.075
            return dx_in, dy_in, 0.0, r_scale

        sl_dense = [sample(sl_sections, k / 2.5) for k in range(int((len(sl_sections) - 1) * 2.5) + 1)]
        build_anatomical_tube(
            f"Sleeve | {side} draped sleeve",
            sl_dense, "blue", mats, N=32, subsurf=2, axis_mod_fn=sleeve_mod
        )

        cuff = bpy.data.objects.get(f"Cuff | {side} rolled cuff")
        if cuff is not None:
            for v in cuff.data.vertices:
                v.co.y += 0.20

        # B. Articulated anatomical Forearm + Wrist + Dorsal Hand + 4 Distinct Fingers + Thumb
        arm_parts = []

        fp_sections = [
            (h * 17.9, -8.8, 48.2, 4.6, 4.9),   # inside cuff
            (h * 17.0, -9.4, 45.2, 4.4, 4.7),   # forearm muscle belly
            (h * 15.2, -10.5, 42.3, 3.8, 3.7),  # forearm taper
            (h * 12.6, -12.0, 39.9, 3.45, 2.55),# narrowed flattened wrist
            (h * 10.1, -13.1, 38.3, 4.75, 2.55),# wide dorsal metacarpal palm
            (h *  8.7, -13.7, 37.0, 4.70, 2.15),# arched knuckle ridge swallowing all finger roots
            (h *  8.1, -14.0, 36.4, 4.10, 1.55),
        ]
        fp_dense = [sample(fp_sections, k / 2.5) for k in range(int((len(fp_sections) - 1) * 2.5) + 1)]

        def palm_mod(u, th, cx, cy, c, s_sign=h):
            palm_zone = ease((u - 0.55) / 0.35)
            dorsal_flat = 1.0 - 0.14 * palm_zone * max(0.0, cy)
            thenar = 0.25 * ease((u - 0.50) / 0.22) * ease((0.92 - u) / 0.20) * max(0.0, -s_sign * cx)
            return 0.0, 0.0, 0.0, dorsal_flat + thenar * 0.22

        arm_parts.append(build_anatomical_tube(
            f"Anatomy source | {side} forearm palm", fp_dense, "skin", mats, N=26, subsurf=1, axis_mod_fn=palm_mod
        ))

        finger_specs = [
            (0, 5.2, 37.2, 0.98, 1.24,  0.42),
            (1, 7.2, 37.5, 1.08, 1.32,  0.18),
            (2, 9.1, 37.8, 0.97, 1.18, -0.04),
            (3, 10.4, 37.8, 0.78, 0.96, -0.22),
        ]
        for idx, fx, fz, fl, fr, ang_s in finger_specs:
            inw = -h * (1.05 + ang_s) * fl
            # Sink MCP root deeply inside dorsal palm so ZERO knuckle pea protrudes!
            fpath = [
                (h * (fx - 0.80), -12.60, fz - 0.10, fr * 0.50, fr * 0.45),
                (h * (fx - 0.15), -13.65, fz - 0.15, fr * 0.90, fr * 0.85),
                (h * fx + inw * 0.48, -14.85, fz - 1.50 * fl, fr * 1.02, fr * 0.96),
                (h * fx + inw * 0.88, -14.25, fz - 3.05 * fl, fr * 0.89, fr * 0.84),
                (h * fx + inw * 1.00, -12.75, fz - 3.78 * fl, fr * 0.70, fr * 0.64),
            ]
            f_dense = [sample(fpath, k / 2.0) for k in range(int((len(fpath) - 1) * 2.0) + 1)]
            arm_parts.append(build_anatomical_tube(
                f"Anatomy source | {side} F{idx + 1}", f_dense, "skin", mats, N=18, subsurf=1
            ))

        thumb_path = [
            (h * 8.4, -12.5, 38.6, 1.40, 1.25),
            (h * 6.3, -12.9, 37.7, 1.45, 1.32),
            (h * 4.5, -13.35, 36.6, 1.28, 1.20),
            (h * 3.8, -12.25, 35.6, 0.94, 0.86),
        ]
        t_dense = [sample(thumb_path, k / 2.0) for k in range(int((len(thumb_path) - 1) * 2.0) + 1)]
        arm_parts.append(build_anatomical_tube(
            f"Anatomy source | {side} thumb", t_dense, "skin", mats, N=18, subsurf=1
        ))

        fused_hand = fuse_sources(
            f"Hand | {side} sculpted forearm and hand",
            arm_parts, anat_sources, mats["skin"], voxel_size=0.15, smooth_factor=0.60, smooth_iters=2
        )
        hands.append(fused_hand)

    anat_sources.hide_viewport = True
    anat_sources.hide_render = True
    return hands


# ==============================================================================
# 4. STIFF-LEATHER SCULPTED BOOTS (sole welt, heel block, toe cap, buckled creases)
# ==============================================================================
def build_sculpted_boots(mats):
    profile = [
        (10.42, -17.3,  14.85, 7.85, 2.30),
        (10.65, -17.90, 15.45, 8.60, 2.42),  # sharper sole edge
        (11.45, -17.92, 15.50, 8.66, 2.48),  # firm vertical sole wall
        (12.05, -17.65, 15.20, 8.42, 2.42),
        (12.35, -17.05, 14.70, 8.05, 2.30),  # crisp recessed welt seam
        (12.80, -17.45, 14.88, 8.15, 2.30),
        (14.30, -17.00, 14.75, 8.20, 2.38),  # stiffer quarter plane
        (15.85, -15.50, 14.40, 8.05, 2.42),
        (17.35, -13.10, 14.00, 7.75, 2.36),
        (18.70,  -9.05, 13.75, 7.42, 2.30),
        (20.10,  -6.85, 13.65, 7.15, 2.24),
        (21.55,  -6.25, 13.90, 7.20, 2.18),
        (23.10,  -6.00, 14.15, 7.45, 2.15),
        (24.50,  -5.30, 14.30, 7.60, 2.10),
        (25.60,  -4.60, 13.85, 6.90, 2.05),
    ]
    boots = []
    steps_n = 76
    for hand in (-1, 1):
        rings = []
        length = (len(profile) - 1) * 3
        for i in range(length + 1):
            z, toe, heel, width, sq_p = sample(profile, i / 3.0)
            center = (toe + heel) * 0.5
            ring = []
            for j in range(steps_n):
                angle = math.tau * j / steps_n
                u, v = math.sin(angle), -math.cos(angle)
                sup_s = math.copysign(abs(u) ** (2.0 / sq_p), u)
                sup_v = math.copysign(abs(v) ** (2.0 / (sq_p - 0.15)), v)
                y = center + (heel - toe) * 0.5 * sup_v

                radius = width * (1.0 - 0.135 * bell(y, 1.9, 3.7) * ease((19.5 - z) / 6.2))
                tuck = 1.0 - 0.12 * ease((z - 23.8) / 2.2)
                y = center + (y - center) * tuck
                x = hand * (9.82 + 0.045 * (-y) + sup_s * radius * tuck)

                arch = 1.90 * bell(y, 2.6, 3.05) * ease((13.6 - z) / 2.8)
                heel_block = 0.56 * ease((y - 5.2) / 1.8) * ease((13.5 - z) / 1.2) * ease((z - 10.6) / 0.7)

                front = ease((0.52 - v) / 1.15)
                asym_phase = 0.28 * hand
                z1 = 19.35 + (1.25 + asym_phase) * u + 0.95 * v
                z2 = 22.35 - (1.35 - asym_phase) * u + 0.45 * v
                creases = front * (
                    -0.98 * bell(z, z1, 0.50) + 0.75 * bell(z, z1 - 0.95, 0.85)
                    - 0.70 * bell(z, z2, 0.46) + 0.56 * bell(z, z2 + 0.72, 0.92)
                )
                toe_cap_y = -9.6 - 1.4 * (u * u)
                toe_ridge = 0.36 * bell(y, toe_cap_y, 0.65) * ease((17.8 - z) / 3.5) * ease((z - 12.6) / 1.2)
                heel_seam = 0.32 * bell(u, 0.0, 0.14) * ease((v - 0.65) / 0.3) * ease((z - 12.8) / 2.0) * ease((23.5 - z) / 2.0)
                collar_slouch = 0.38 * bell(z, 23.8 + 0.5 * u * hand, 0.85)

                relief = heel_block + creases + toe_ridge + heel_seam + collar_slouch
                ring.append((x + hand * u * relief, y + v * relief, z + arch))
            rings.append(ring)

        name = "left" if hand > 0 else "right"
        obj = loft(f"Boot | {name} sculpted leather", rings, "boot", mats, subsurf=1)
        obj.data.materials.append(mats["welt"])
        for face in obj.data.polygons:
            verts = [obj.data.vertices[k].co for k in face.vertices]
            is_sole = all(v.z - 1.90 * bell(v.y, 2.6, 3.05) < 12.42 for v in verts)
            is_heel_block = all(v.y > 4.6 and v.z < 13.25 for v in verts)
            if is_sole or is_heel_block:
                face.material_index = 1
        boots.append(obj)
    return boots


# ==============================================================================
# 5. CONTINUOUS BIFURCATED TWO-LEG TROUSERS (WAISTBAND + FLY + POOLS + HANDS GRIP)
# ==============================================================================
def build_continuous_trousers(mats, pelvis, hands, boots):
    graph = bpy.context.evaluated_depsgraph_get()
    pelvis_tree = BVHTree.FromObject(pelvis, graph)
    hand_trees = [BVHTree.FromObject(h_ob, graph) for h_ob in hands]
    boot_trees = [BVHTree.FromObject(b_ob, graph) for b_ob in boots]  # [-1]=right, [+1]=left

    N = COUNT  # 80
    # Strictly monotonic semicircular waistband roll -> upper hip skirt -> crotch loop
    # (zero z_off reversals, zero overhanging saucer flange!).
    # Each tuple: (raw_t_vertical_progress, rad_out, z_off, hand_compress_factor)
    skirt_t_steps = [
        (-0.18, -2.00, -0.35, 0.35),  # tucked cleanly inside pelvis
        (-0.12, -1.35, +0.45, 0.65),
        (-0.06, -0.45, +0.85, 0.90),  # rounded top crest where thumbs & fingers wrap!
        (0.00,  +0.35, +0.52, 1.00),  # outer-upper curve of waistband
        (0.06,  +0.72, +0.10, 1.00),  # waistband outer face
        (0.14,  +0.68,  0.00, 0.85),  # continuous flow into hip/upper thigh
        (0.28,  +0.78,  0.00, 0.60),
        (0.46,  +0.90,  0.00, 0.35),
        (0.68,  +0.80,  0.00, 0.15),
        (0.86,  +0.62,  0.00, 0.05),
        (1.00,  +0.48,  0.00, 0.00),  # bifurcation loop at crotch saddle z~31.4
    ]

    def apply_hand_compression(p, compress_w):
        """Physically indent trouser cloth beneath gripping fingers/thumbs across full crest."""
        if compress_w <= 0.0:
            return p
        best_dist = 99.0
        for ht in hand_trees:
            _, _, _, dist = ht.find_nearest(p)
            if dist < best_dist:
                best_dist = dist
        if best_dist < 1.85:
            press = ease((1.85 - best_dist) / 1.85) * 1.45 * compress_w
            p = p + Vector((0.0, 0.90, -0.42)) * press
        return p

    def skirt_point(theta, raw_t, bulge_out, z_off, comp_w):
        s, c = math.sin(theta), math.cos(theta)
        t = clamp(raw_t, 0.0, 1.0)
        rear = ease((-c + 0.12) / 0.80)
        front = ease((c + 0.15) / 1.05)
        grip_zone = bell(abs(s), 0.45, 0.25) * front

        # Front sits higher where hands hold it up (~36.2..36.6); rear drops snugly UNDER the
        # lower curve of the buttocks (~34.7..35.3) so it NEVER flares out onto the overhanging cheek!
        z_top_front = 36.20 + 0.55 * grip_zone + 0.20 * s
        z_top_rear = 34.75 + 0.72 * bell(s, 0.0, 0.18) - 0.52 * bell(abs(s), 0.44, 0.24)
        z_top = z_top_front * (1.0 - rear) + z_top_rear * rear
        z_bot = 31.35 - 0.50 * abs(s) + 0.20 * rear
        z = z_top * (1.0 - t) + z_bot * t + z_off * (1.0 - 0.20 * rear)

        p = seat_skin(theta, clamp(z, 33.0, 38.5))

        # Front pulled slightly forward by hands; rear hugs beneath cheeks smoothly
        front_pull = (5.0 - 2.3 * t) * front + 0.70 * bell(s, 0.0, 0.30) * front
        p.x += s * (1.65 * front + 0.85 * (1.0 - rear)) + 0.35 * s * bell(c, 0.20, 0.55)
        p.y -= front_pull
        p.y += rear * (0.20 + 1.05 * t) * (1.0 - 0.25 * bell(abs(s), 0.0, 0.22))

        fly = 0.48 * bell(s, -0.02, 0.09) * front * ease((t - 0.08) / 0.25)
        seam_grooves = (
            -0.42 * bell(s, 0.0, 0.08) * rear * ease((t - 0.12) / 0.30)
            - 0.16 * bell(t, 0.14, 0.05) * front  # gentle stitched waistband detail at front only
        )
        diag_tension = (
            0.55 * bell(t - 0.45 * (abs(s) - 0.42), 0.40, 0.13) * front * ease((abs(s) - 0.15) / 0.3)
            - 0.25 * bell(t - 0.45 * (abs(s) - 0.42), 0.56, 0.10) * front * ease((abs(s) - 0.15) / 0.3)
        )

        # Keep rear outer bulge compact so top roll cups neatly into under-seat fold
        bulge_adj = bulge_out * (1.0 - 0.35 * rear * ease((0.35 - t) / 0.35))
        out_dir = angular_direction(theta)
        p += out_dir * (bulge_adj + fly + seam_grooves + diag_tension)

        p = apply_hand_compression(p, comp_w)
        # Apply pelvis clearance ONLY once outside the inner rolled lip (raw_t >= 0.05)
        # so the top rear edge stays softly rolled inward beneath the cheeks!
        if raw_t >= 0.04:
            p = pelvis_clearance_vec(p, pelvis_tree, 0.38 if rear < 0.5 else 0.28)
        return p

    skirt_rings = [[skirt_point(theta, rt, bo, zo, cw) for theta in ANGLES]
                   for rt, bo, zo, cw in skirt_t_steps]

    verts = [p.copy() for ring in skirt_rings for p in ring]
    faces = []
    for row in range(len(skirt_rings) - 1):
        for col in range(N):
            a = row * N + col
            b = row * N + (col + 1) % N
            faces.append((a, b, b + N, a + N))

    top_cap_c = sum(skirt_rings[0], Vector()) / N
    top_cap_c.z += 0.5
    i_top_cap = len(verts)
    verts.append(top_cap_c)
    for col in range(N):
        faces.append((i_top_cap, (col + 1) % N, col))

    # Clean smooth crotch bridge (NO pelvis_clearance_vec around x=0 where Turn 8 thighs already split!)
    bot_row = len(skirt_rings) - 1
    front_i = bot_row * N + 0
    rear_i = bot_row * N + (N // 2)
    p_front, p_rear = verts[front_i], verts[rear_i]
    bridge = []
    n_bridge = 10
    for k in range(1, n_bridge):
        u = k / n_bridge
        pb = p_front.lerp(p_rear, u)
        pb.z += 0.90 * math.sin(math.pi * u)
        bridge.append(len(verts))
        verts.append(pb)

    left_loop = [bot_row * N + i for i in range(N // 2 + 1)] + bridge[::-1]
    right_loop = [bot_row * N + i for i in range(N // 2, N)] + [bot_row * N + 0] + bridge

    n_leg_rings = 32
    leg_boot_targets = {1: (9.65, 2.5), -1: (-9.65, 2.5)}
    for side, loop in zip((1, -1), (left_loop, right_loop)):
        boot_tree = boot_trees[1 if side > 0 else 0]
        cx_b, cy_b = leg_boot_targets[side]
        boot_c = Vector((cx_b, cy_b, 24.0))
        roots = [verts[idx].copy() for idx in loop]
        c_root = sum(roots, Vector()) / len(roots)
        rx0 = max(4.0, max(abs(p.x - c_root.x) for p in roots))
        ry0 = max(5.0, max(abs(p.y - c_root.y) for p in roots))
        # Monotonic normalized radial direction around each branched loop (prevents crotch twists!)
        units_leg = []
        for p in roots:
            dv = Vector(((p.x - c_root.x) / rx0, (p.y - c_root.y) / ry0))
            units_leg.append(dv.normalized() if dv.length > 1e-6 else Vector((side, 0.0)))
        prev_ring = loop

        for step in range(1, n_leg_rings + 1):
            t_leg = step / n_leg_rings
            z_ring = 31.30 * (1.0 - t_leg) + 22.35 * t_leg
            knee_forward = -2.0 * math.sin(math.pi * clamp(t_leg / 0.85))
            c_target = Vector((cx_b + side * 0.25 * math.sin(math.pi * t_leg),
                               cy_b + knee_forward, z_ring))

            inward_tuck = 1.0 - 0.35 * ease((t_leg - 0.87) / 0.13)
            base_rx = (8.3 + 1.15 * math.sin(math.pi * t_leg)) * inward_tuck
            base_ry = (9.8 + 1.35 * math.sin(math.pi * t_leg)) * inward_tuck

            new_ring = []
            for p0, unit in zip(roots, units_leg):
                ca, sa = unit.x, unit.y
                ang = math.atan2(sa, ca)
                blend = ease(t_leg / 0.36)
                p_ell = Vector((
                    c_target.x + base_rx * ca,
                    c_target.y + base_ry * sa,
                    z_ring - 0.55 * sa * ease((0.85 - t_leg) / 0.85)
                ))
                p = p0.lerp(p_ell, blend)
                p.z = p0.z * (1.0 - t_leg) + p_ell.z * t_leg

                slant = 0.08 * sa - 0.05 * side * ca
                twist = 0.06 * math.sin(ang * 2.0 + side * 0.8)
                u_f = t_leg + slant + twist
                phase_s = 0.030 if side > 0 else -0.025

                fold_rope = (
                    + 1.35 * bell(u_f, 0.24 + phase_s, 0.125)
                    - 0.45 * bell(u_f, 0.40 + phase_s, 0.085)
                    + 1.48 * bell(u_f, 0.54 - phase_s, 0.115) * (0.85 + 0.22 * math.cos(ang + side))
                    - 0.42 * bell(u_f, 0.69 - phase_s, 0.080)
                    + 1.65 * bell(u_f, 0.80 + phase_s * 0.5, 0.105)
                ) * ease(t_leg / 0.18) * ease((0.93 - t_leg) / 0.14)

                radial_out = Vector((p.x - c_target.x, p.y - c_target.y, 0.0))
                r_unit = radial_out.normalized() if radial_out.length > 1e-5 else Vector((ca, sa, 0.0))
                p += r_unit * fold_rope
                p.z -= 0.35 * max(0.0, fold_rope) * (0.35 + 0.65 * abs(sa))

                # Per-thigh radial skin clearance (prevents crossing rays across x=0 crotch!)
                if t_leg < 0.36 and abs(p.x) > 1.8:
                    p = bvh_clear_from_center(p, pelvis_tree, Vector((side * 8.6, 4.0, p.z)), 0.42, max_ray=13.5)
                if 0.40 <= t_leg <= 0.88:
                    p = bvh_clear_from_center(p, boot_tree, boot_c, 0.60)

                new_ring.append(len(verts))
                verts.append(p)

            for i in range(len(new_ring)):
                j = (i + 1) % len(new_ring)
                faces.append((prev_ring[i], prev_ring[j], new_ring[j], new_ring[i]))
            prev_ring = new_ring

        cap_c = sum((verts[k] for k in prev_ring), Vector()) / len(prev_ring)
        i_cap = len(verts)
        verts.append(cap_c)
        for i in range(len(prev_ring)):
            j = (i + 1) % len(prev_ring)
            faces.append((i_cap, prev_ring[i], prev_ring[j]))

    trousers = create_mesh_obj(
        "Trousers | continuous lowered pants",
        verts, faces, "blue", mats, subsurf=1
    )

    tr_tree = BVHTree.FromObject(trousers, bpy.context.evaluated_depsgraph_get())
    loc, _, _, _ = tr_tree.ray_cast(Vector((0.35, -30.0, 34.7)), Vector((0.0, 1.0, 0.0)), 30.0)
    y_btn = loc.y - 0.55 if loc is not None else -14.2
    btn_rings = [
        [(0.35 + r * math.cos(math.tau * i / 14),
          y_btn - 0.58 * (1.0 - abs(dz) / 1.25) + 0.22 * math.sin(math.tau * i / 14),
          34.70 + dz) for i in range(14)]
        for dz, r in [(-1.05, 0.52), (-0.62, 1.12), (0.0, 1.26), (0.62, 1.12), (1.05, 0.52)]
    ]
    create_mesh_obj_rings("Waistband | fly button", btn_rings, "blue", mats, cap_ends=True, subsurf=1)
    return trousers


# ==============================================================================
# 6. 360-DEGREE GREEK-SCULPTED CARVED BEARD, MOUSTACHE & NAPE HAIR
# ==============================================================================
BEARD_SPINE = [
    (0.0, -22.5, 66.0),
    (-0.2, -23.5, 61.5),
    (-0.5, -24.8, 56.5),
    (-1.4, -26.2, 51.0),
    (-3.2, -26.4, 45.8),
    (-3.0, -25.0, 41.8),
]


def closest_spine_pt(p):
    best = Vector(BEARD_SPINE[0])
    best_d2 = 1e18
    for a, b in zip(BEARD_SPINE, BEARD_SPINE[1:]):
        va, vb = Vector(a), Vector(b)
        ab = vb - va
        l2 = ab.length_squared
        t = clamp((p - va).dot(ab) / max(l2, 1e-8))
        q = va + ab * t
        d2 = (p - q).length_squared
        if d2 < best_d2:
            best_d2 = d2
            best = q
    return best


def carved_lock(name, path, mats, *, mode="beard", grooves=(-0.46, 0.24), carving=0.40):
    """Sculpt a Greek/Roman carved hair ribbon whose grooves follow true 3D outward surface normals."""
    count = (len(path) - 1) * 5 + 1
    sections = [sample(path, i / 5.0) for i in range(count)]
    centers = [Vector(p[:3]) for p in sections]
    rings = []
    for i, (center, (_, _, _, width, depth)) in enumerate(zip(centers, sections)):
        u = i / max(1, count - 1)
        tangent = (centers[min(i + 1, count - 1)] - centers[max(0, i - 1)]).normalized()
        if mode == "nape":
            outward = Vector((center.x * 0.78, center.y + 13.5, 0.75))
        elif mode == "moustache":
            outward = Vector((center.x * 0.04, -1.0, 0.14))
        else:
            spine = closest_spine_pt(center)
            radial = Vector((center.x - spine.x, center.y - spine.y, (center.z - spine.z) * 0.45))
            if radial.length < 0.4:
                radial = Vector((center.x * 0.2, -1.0, -0.3))
            tip_down = ease((u - 0.72) / 0.25)
            outward = radial.normalized().lerp(Vector((0.0, 0.20, -1.0)), tip_down * 0.35)
        normal = (outward - tangent * tangent.dot(outward))
        if normal.length < 1e-5:
            normal = Vector((0.0, -1.0, 0.0))
        normal.normalize()
        side = tangent.cross(normal).normalized()
        weight = ease(u * 7.0) * ease((1.0 - u) * 4.5)
        ring = []
        for j in range(44):
            angle = math.tau * j / 44
            across, out = math.sin(angle), math.cos(angle)
            incise = 0.0
            for mark in grooves:
                d = (across - (mark + 0.09 * math.sin(u * 3.5))) / 0.115
                incise += math.exp(-(abs(d) ** 1.45))
            relief = carving * incise * weight * ease(out)
            ring.append(center + side * (across * width) + normal * (out * depth - relief))
        rings.append(ring)
    return loft(name, rings, "hair", mats, subsurf=1)


def recessed_beard_core(mats):
    """Inner solid core buried 2.6+ mm strictly INSIDE the 360-deg carved locks to prevent internal pinholes."""
    profile = [
        (43.2, -2.8, -26.2, -24.0, 1.4),
        (46.2, -2.2, -27.4, -23.2, 4.2),
        (49.5, -1.6, -28.6, -22.0, 7.0),
        (53.2, -0.9, -29.2, -21.0, 9.5),
        (57.2, -0.3, -28.8, -20.2, 11.6),
        (61.0, -0.1, -27.0, -19.8, 12.4),
        (64.5,  0.1, -25.2, -19.9, 12.2),
        (68.0,  0.3, -23.5, -20.4, 10.8),
    ]
    rings = []
    for i in range(3 * (len(profile) - 1) + 1):
        z, x, front, rear, width = sample(profile, i / 3.0)
        rings.append([
            (x + width * math.sin(t), (front + rear) * 0.5 - (rear - front) * 0.5 * math.cos(t), z)
            for t in (j * math.tau / 48 for j in range(48))
        ])
    return loft("Beard source | recessed inner core", rings, "hair", mats, subsurf=1)


def build_greek_hair(mats, cap):
    sources = bpy.data.collections.get("Hair sources | show to edit, hide to render")
    if sources is None:
        sources = bpy.data.collections.new("Hair sources | show to edit, hide to render")
        bpy.context.scene.collection.children.link(sources)
    else:
        for obj in list(sources.objects):
            bpy.data.objects.remove(obj, do_unlink=True)

    beard_locks = []

    # Tier A: Primary Front 8 S-locks (softened lip-root taper + integrated side locks)
    for i, path in enumerate(BEARD):
        root = list(path[0])
        root[1] += 2.6
        root[2] += 0.8
        root[3] *= 0.55
        root[4] *= 0.55
        mod_path = [tuple(root)]
        for k, sec in enumerate(path[1:], start=1):
            p = list(sec)
            if 1 <= k <= len(path) - 2:
                p[3] *= 1.07
                p[4] *= 1.05
            # Pull outermost side locks gently inward along lower jaw contour
            if i in (0, 7) and k >= 3:
                p[0] *= 0.93
            mod_path.append(tuple(p))
        gr = (-0.48, 0.23) if i % 2 == 0 else (-0.54, 0.04, 0.52)
        beard_locks.append(carved_lock(
            f"Beard source | front {i + 1:02}", mod_path,
            mats, mode="beard", grooves=gr, carving=0.40
        ))

    # Tier B: Flank Jaw-Wrap Locks (tapered roots deeply buried under cheek & ear!)
    flank_paths = [
        [(-14.2, -19.8, 69.2, 0.35, 0.35), (-17.5, -21.2, 64.5, 2.35, 1.85), (-17.0, -23.0, 59.5, 2.85, 2.15),
         (-15.0, -23.6, 54.5, 2.35, 1.85), (-11.6, -24.2, 50.2, 1.65, 1.40), (-9.2, -25.2, 50.8, 0.55, 0.55)],
        [(-13.8, -18.5, 66.8, 0.35, 0.35), (-16.2, -19.5, 61.5, 2.45, 2.00), (-14.8, -21.4, 55.2, 2.65, 2.05),
         (-11.8, -22.5, 49.4, 2.15, 1.75), (-8.5, -23.8, 44.8, 1.45, 1.25), (-6.2, -25.0, 44.4, 0.52, 0.52)],
        [(14.2, -19.8, 69.2, 0.35, 0.35), (17.5, -21.0, 64.5, 2.30, 1.85), (17.0, -22.2, 59.5, 2.80, 2.10),
         (15.2, -22.8, 54.6, 2.30, 1.80), (11.8, -23.6, 50.8, 1.60, 1.35), (9.5, -24.8, 51.6, 0.52, 0.52)],
        [(13.8, -18.3, 66.8, 0.35, 0.35), (16.0, -19.0, 61.5, 2.40, 1.95), (14.6, -20.8, 55.2, 2.60, 2.00),
         (11.6, -21.8, 49.5, 2.05, 1.70), (7.8, -23.2, 45.4, 1.40, 1.22), (5.5, -24.6, 45.2, 0.50, 0.50)],
    ]
    for i, path in enumerate(flank_paths):
        beard_locks.append(carved_lock(
            f"Beard source | flank {i + 1:02}", path,
            mats, mode="beard", grooves=(-0.44, 0.25), carving=0.39
        ))

    # Tier C: Rear & Underside Beard Locks (roots tucked under jaw, bottoms sealing forward into chin tip!)
    rear_paths = [
        [(-10.8, -19.8, 63.8, 0.38, 0.38), (-13.0, -17.4, 58.2, 2.95, 2.25), (-11.6, -18.0, 52.8, 3.10, 2.35),
         (-8.8, -20.2, 47.4, 2.50, 2.00), (-5.8, -23.2, 43.2, 1.70, 1.45), (-3.8, -25.4, 43.2, 0.55, 0.55)],
        [(-5.0, -20.2, 63.2, 0.40, 0.40), (-5.8, -17.4, 57.5, 3.45, 2.50), (-4.8, -18.0, 51.8, 3.55, 2.55),
         (-5.2, -20.8, 46.2, 2.85, 2.20), (-4.0, -24.2, 42.0, 1.85, 1.55), (-2.6, -26.2, 41.8, 0.55, 0.55)],
        [(0.2, -20.0, 63.0, 0.40, 0.40), (0.5, -17.2, 57.2, 3.55, 2.55), (0.8, -18.0, 51.5, 3.50, 2.50),
         (-1.2, -21.0, 46.0, 2.80, 2.20), (-2.6, -24.4, 41.8, 1.80, 1.50), (-1.8, -26.2, 41.5, 0.52, 0.52)],
        [(5.5, -19.8, 63.2, 0.40, 0.40), (6.6, -17.4, 57.6, 3.35, 2.40), (6.4, -18.2, 52.2, 3.30, 2.35),
         (3.4, -20.8, 47.2, 2.55, 2.00), (-0.4, -23.6, 43.4, 1.65, 1.40), (-1.6, -25.6, 43.2, 0.52, 0.52)],
        [(10.6, -19.8, 63.8, 0.38, 0.38), (12.4, -17.6, 58.6, 2.90, 2.20), (11.2, -18.6, 53.5, 2.90, 2.20),
         (8.2, -20.6, 48.6, 2.30, 1.85), (4.6, -22.8, 45.2, 1.45, 1.30), (2.4, -24.6, 45.2, 0.50, 0.50)],
    ]
    for i, path in enumerate(rear_paths):
        gr = (-0.50, 0.22) if i % 2 == 0 else (-0.55, 0.02, 0.53)
        beard_locks.append(carved_lock(
            f"Beard source | rear {i + 1:02}", path,
            mats, mode="beard", grooves=gr, carving=0.42
        ))

    beard_locks.append(recessed_beard_core(mats))
    beard_fused = fuse_sources(
        "Beard | carved 360 mass", beard_locks, sources, mats["hair"],
        voxel_size=0.16, smooth_factor=0.58, smooth_iters=2
    )

    nape_locks = []
    nape_specs = [
        (60,  -9, 4.35, 2.9), (74,   6, 4.95, 2.75), (94,  18, 4.65, 3.10),
        (110, 25, 7.05, 3.80), (135, 31, 6.45, 3.70), (153, 42, 7.45, 4.35),
        (179, 28, 6.85, 3.75), (201, 24, 5.45, 3.35), (221, 32, 6.15, 3.55),
        (244, 19, 6.40, 3.50), (268, 12, 4.65, 3.00), (286,  8, 4.80, 2.85),
        (300,  6, 5.10, 3.10),
    ]
    for i, (theta, sweep, length, width) in enumerate(nape_specs):
        path = []
        for step, outset, drop, w, d in [
            (0.00, -2.55, -1.45, 0.78, 0.36), (0.12, -1.75, 1.35, 0.98, 0.49),
            (0.35,  0.22, length * 0.65, 1.12, 0.56), (0.69, 1.38, length * 0.96, 0.96, 0.52),
            (1.00,  1.02, length * 0.86, 0.70, 0.46), (1.12, 0.58, length * 0.68, 0.50, 0.40),
        ]:
            az = theta + sweep * step
            pos = rim_at(az)
            radial = Vector((pos.x, pos.y + 15.6, 0.0)).normalized()
            pos += radial * outset
            pos.z -= drop
            path.append((*pos, width * w, width * d))
        gr = (-0.43, 0.29) if i % 4 else (-0.56, 0.0, 0.53)
        nape_locks.append(carved_lock(
            f"Nape source | comma {i + 1:02}", path,
            mats, mode="nape", grooves=gr, carving=0.48
        ))

    for obj in nape_locks:
        for v in obj.data.vertices:
            radial = Vector((v.co.x, v.co.y + 15.6))
            az = math.degrees(math.atan2(radial.x, -radial.y))
            rim = rim_at(az)
            limit = Vector((rim.x, rim.y + 15.6)).length
            push = max(0.0, radial.length - limit + 0.85) * ease((v.co.z - rim.z + 2.4) / 2.8)
            shift = radial.normalized() * push
            v.co.x -= shift.x
            v.co.y -= shift.y

    backing = []
    for theta in range(62, 305, 8):
        anchor = rim_at(theta)
        inward = Vector((anchor.x, anchor.y + 15.6, 0.0)).normalized()
        anchor -= inward * (3.10 + 0.55 * bell(theta, 180, 60))
        anchor.z -= 3.15
        w_col = 2.90 + 0.55 * bell(theta, 164, 58)
        fade = 0.5 + 0.5 * ease(min(theta - 60, 306 - theta) / 17.0)
        backing.append((*anchor, w_col * fade, 2.50 * fade))
    nape_locks.append(carved_lock("Nape source | connected collar", backing, mats, mode="nape", grooves=()))

    collar_fused = fuse_sources(
        "Hair | carved temple and nape", nape_locks, sources, mats["hair"],
        voxel_size=0.16, smooth_factor=0.60, smooth_iters=2
    )
    ears = [obj for obj in bpy.context.scene.objects if obj.name.startswith("Ear |")]
    tuck_under_brim(cap, [collar_fused, *ears])

    for side, path in zip(("open", "wink"), MOUSTACHE):
        carved_lock(f"Moustache | carved {side} wing", path, mats,
                    mode="moustache", grooves=(-0.48, 0.21), carving=0.38)

    sources.hide_viewport = True
    sources.hide_render = True
    return beard_fused, collar_fused


# ==============================================================================
# 7. MAIN REBUILD ENTRY POINT
# ==============================================================================
def rebuild(output):
    bpy.ops.wm.open_mainfile(filepath=str(PARENT_TURN8 / "Clive-RoundedSeat.blend"))

    remove_prefixes = (
        "Cap |",
        "Smock | arched", "Smock | hunched",
        "Waistband |", "Trousers |",
        "Sleeve |", "Forearm |", "Finger |", "Thumb |", "Hand |",
        "Boot |",
        "Beard |", "Hair |", "Moustache |",
        "Beard source |", "Nape source |", "Anatomy source |",
    )
    for obj in list(bpy.context.scene.objects):
        if obj.name.startswith(remove_prefixes):
            bpy.data.objects.remove(obj, do_unlink=True)

    mats = {
        key: bpy.data.materials[key]
        for key in ("hat", "blue", "skin", "hair", "boot", "welt")
    }

    pelvis = bpy.data.objects["Seat | continuous pelvis into thighs"]

    cap = build_soft_cap(mats)
    smock = build_soft_smock(mats, pelvis)
    hands = build_anatomy_arms_and_hands(mats)
    boots = build_sculpted_boots(mats)
    build_continuous_trousers(mats, pelvis, hands, boots)
    build_greek_hair(mats, cap)

    # Purge orphaned meshes from removed legacy objects to keep the .blend compact
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)

    bpy.ops.object.select_all(action="DESELECT")
    pelvis.select_set(True)
    bpy.context.view_layer.objects.active = pelvis
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                view = area.spaces.active
                view.shading.color_type = "MATERIAL"
                view.region_3d.view_distance = 159
                view.region_3d.view_location = (0, -3, 55)
                view.region_3d.view_rotation = Vector((0.34, -0.91, 0.22)).to_track_quat("Z", "Y")
                view.region_3d.view_perspective = "ORTHO"

    bpy.context.preferences.filepaths.save_version = 0
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", nargs="?", type=Path, default=HERE / "Clive-GarmentAndHair.blend")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    rebuild(args.output.resolve())
