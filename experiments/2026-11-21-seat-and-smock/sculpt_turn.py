"""Build the fitted smock, continuous pelvis and waistband on turn 6."""
import argparse
import math
import runpy
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent / "2026-11-21-felt-and-carved-hair"
helpers = runpy.run_path(str(PARENT / "sculpt_turn.py"))
loft = helpers["loft"]
mesh_object = loft.__globals__["create_mesh_obj"]
sample = helpers["sample"]
by_first = helpers["by_first"]
ease = helpers["ease"]
bell = helpers["bell"]

# z, half width, front, rear, depth of the midline cleft. The rear arc
# comes directly out of the upper thighs. Its lowest point is inside cloth.
PELVIS = [
    (32.8, 14.1, -6.8, 16.0, 2.0),
    (34.8, 15.9, -7.8, 18.35, 3.5),
    (36.6, 17.4, -8.0, 21.15, 4.5),
    (38.9, 18.6, -7.8, 24.85, 5.65),
    (41.3, 19.7, -7.9, 28.55, 6.05),
    (44.4, 20.8, -8.2, 32.57, 6.15),
    (47.5, 21.2, -8.25, 33.8, 5.80),
    (50.15, 20.85, -8.25, 33.48, 4.95),
    (53.25, 19.8, -8.55, 31.10, 3.35),
    (56.2, 17.9, -8.9, 27.4, 1.25),
    (59.3, 15.8, -9.4, 22.8, .36),
    (62.1, 11.7, -9.5, 16.0, 0),
    (64.2, 6.0, -9.3, 9.5, 0),
]
COUNT = 80
ANGLES = [math.tau * i / COUNT for i in range(COUNT)]


def skin_point(theta, z):
    width, front, rear, cleft = by_first(PELVIS, z)
    sine, cosine = math.sin(theta), math.cos(theta)
    center = front + .44 * (rear - front)
    x = width * sine
    if cosine < 0:
        # Flatten the dome above each upper thigh before cutting the cleft.
        lobe = math.sqrt(max(0, 1 - abs(sine) ** 2.35))
        y = center + (rear - center) * lobe
        y -= cleft * bell(x, .25, 2.50 + .025 * (z - 34)) * lobe
        y += lobe * (1.08 + .32 * sine) * bell(abs(sine), .42, .29) * bell(z, 45.6, 9.7)
    else:
        y = center - (center - front) * cosine
        y += 2.85 * bell(x, 0, 4.95) * ease((39.0 - z) / 5.0) * cosine
    return Vector((x, y, z))


def make_pelvis(mats):
    # One waist loop branches into two leg loops across a short crotch seam.
    # The lower leg branches terminate inside the cloth.
    start_height = 35.3
    heights = [start_height + (PELVIS[-1][0] - start_height) * i / 50 for i in range(51)]
    rings = [[skin_point(theta, z) for theta in ANGLES] for z in heights]
    vertices = [p for ring in rings for p in ring]
    faces = []
    for row in range(len(rings) - 1):
        for col in range(COUNT):
            a = row * COUNT + col
            b = row * COUNT + (col + 1) % COUNT
            faces.append((a, b, b + COUNT, a + COUNT))
    top = (len(rings) - 1) * COUNT
    faces.append(tuple(range(top, top + COUNT)))

    front, rear = rings[0][0], rings[0][COUNT // 2]
    bridge = []
    for i in range(1, 10):
        t = i / 10
        p = front.lerp(rear, t)
        p.z += 1.0 * math.sin(math.pi * t)
        bridge.append(len(vertices))
        vertices.append(p)

    loops = [
        list(range(COUNT // 2 + 1)) + bridge[::-1],
        list(range(COUNT // 2, COUNT)) + [0] + bridge,
    ]
    for side, loop in zip((1, -1), loops):
        roots = [vertices[index] for index in loop]
        center = Vector((side * 8.6, 4.0, 30.4))
        previous = loop
        for t in (.26, .58, 1.0):
            new = []
            for p in roots:
                unit = Vector(((p.x - center.x) / 8.7, (p.y - center.y) / 12.0)).normalized()
                target = center + Vector((5.25 * unit.x, 7.0 * unit.y, 0))
                new.append(len(vertices))
                vertices.append(p.lerp(target, t))
            for i in range(len(new)):
                j = (i + 1) % len(new)
                faces.append((previous[i], previous[j], new[j], new[i]))
            previous = new
        faces.append(tuple(previous))
    return mesh_object("Seat | continuous pelvis into thighs", vertices, faces, "skin", mats, subsurf=1)


def angular_direction(theta):
    return Vector((math.sin(theta), -math.cos(theta), 0))


def build_waistband(mats):
    # A wide cloth edge at the grips rolls into a lower, flatter band
    # behind. It stays attached to the under-seat contour in three dimensions.
    sections = [
        (-3.2, -.18), (-2.8, .74), (-1.92, 1.54), (-.83, 1.64),
        (-.09, 1.38), (.45, .80), (.46, .16), (-.38, -.72), (-1.28, -1.05),
    ]
    rings = []
    for dz, relief in sections:
        ring = []
        for theta in ANGLES:
            c, s = math.cos(theta), math.sin(theta)
            rear = ease((-c + .08) / .82)
            front = ease((c + .05) / 1.05)
            grip = bell(abs(s), .56, .24) * front
            # The back rises in the cleft and the outer hip, and gives
            # each glute a lower bowl directly over its own trouser leg.
            z = 36.55 + rear * (1.28 + 1.05 * bell(s, 0, .17) - 1.38 * bell(abs(s), .45, .24))
            z += .28 * s - .62 * grip
            z += dz * (1.0 - .17 * rear)
            p = skin_point(theta, z)
            p.x += s * (1.28 * front + .15) + .40 * s * bell(c, .23, .60)
            p.y -= 5.95 * front - .24 * grip
            p.y -= .9 * front * bell(s, 0, .28)
            p += angular_direction(theta) * relief
            ring.append(p)
        rings.append(ring)
    return loft("Waistband | fitted cloth between grips", rings, "blue", mats, subsurf=1)


def pelvis_clearance(p, tree, offset):
    lo, hi = PELVIS[0][0], PELVIS[-1][0]
    if not lo < p.z < hi:
        return p
    _, front, rear, _ = by_first(PELVIS, p.z)
    center = Vector((0, front + .44 * (rear - front), p.z))
    radial = p - center
    direction = radial.normalized()
    hit, _, _, distance = tree.ray_cast(center + direction * 46, -direction, 45)
    if hit is not None:
        target = 46 - distance + offset
        difference = target - radial.length
        if difference > 0:
            p += direction * difference
    return p


def build_smock(mats, pelvis, tailored):
    tree = BVHTree.FromObject(pelvis, bpy.context.evaluated_depsgraph_get())
    u_steps = [-.052, -.026, -.007, .016, .037, .065] + [.09 + .91 * k / 38 for k in range(39)]
    rings = []
    for raw_u in u_steps:
        u = max(0.0, raw_u)
        ring = []
        for theta in ANGLES:
            s, c = math.sin(theta), -math.cos(theta)
            back = .5 * (1 + c)
            fitted = ease((c + .72) / .85)
            legacy_z = 36.6 + 19.3 * back ** 1.05
            legacy_y = -13.8 + 43.2 * back ** 1.02
            hem_z = 37 + 19.15 * back ** 1.21
            hem_z += .52 * s * fitted - 1.85 * bell(c, .15, .40)
            hem_z += 1.55 * bell(c, .87, .33) + .36 * fitted
            edge = skin_point(theta, hem_z)
            outward = angular_direction(theta)
            if tailored:
                hem = Vector((20.8 * s, legacy_y, legacy_z)).lerp(edge + outward * .45, fitted)
            else:
                hem = Vector((20.8 * s, legacy_y, legacy_z))
            collar = Vector((12.2 * s, -10.5 + 11.8 * c, 66.8 + 3.2 * back))
            p = hem.lerp(collar, u)
            dome = math.sin(math.pi * u)
            shoulder = math.sin(math.pi * max(0, (u - .14) / .86))
            p.x += 3.85 * s * shoulder
            p.y += dome * (4.6 * back ** .72 - 2.4 * (1 - back))
            p.z += 9 * u ** .62 * (1 - u) ** .88 * (.30 + 1.15 * back)
            # Two irregular tension folds echo the hem and run out toward the
            # shoulder. The flank has a smaller crease where the cloth turns.
            fold_a = .13 + .060 * s + .045 * c
            fold_b = .28 - .075 * s + .032 * c
            fold = 0.98 * bell(u, fold_a, .073) - .47 * bell(u, fold_a + .083, .043)
            fold += (.81 + .30 * s) * bell(u, fold_b, .060) - .36 * bell(u, fold_b + .073, .046)
            pinch = .47 * bell(u, .25 + .09 * s, .075) * bell(c, -.13, .24)
            p += outward * (fitted * fold + pinch)
            lip = (.47 + .33 * fitted) * bell(raw_u, .016, .032)
            lip -= max(0, -raw_u / .052) * 1.63
            p += outward * lip
            p.z += .74 * max(0, -raw_u / .052) - .24 * bell(raw_u, .016, .032)
            if tailored and raw_u > -.014:
                p = pelvis_clearance(p, tree, .26 + .15 * bell(u, .04, .07))
            ring.append(p)
        rings.append(ring)
    return loft("Smock | arched hem fitted over seat", rings, "blue", mats, subsurf=1)


def fit_trouser_tops():
    # This local deformation supports the upper band. Lower pools and boots
    # keep the shape and landmarks of the parent.
    for obj in bpy.context.scene.objects:
        if obj.name.startswith("Trousers |") and "pooled folds" in obj.name:
            for v in obj.data.vertices:
                x, y, z = v.co
                upper = ease((z - 28.6) / 7.0)
                dorsal = ease((y - 2.6) / 11.4)
                v.co.y += 3.38 * upper * dorsal
                v.co.z += .86 * upper * dorsal - .36 * upper * ease((-y - 4) / 7)
                v.co.x *= 1.0 - .045 * upper * ease((abs(x) - 15) / 6)
    fill = bpy.data.objects["Trousers | inner seat fill"]
    for v in fill.data.vertices:
        pinch = bell(v.co.x, 0, 6.1) * ease((v.co.y - 7.8) / 7.8)
        v.co.y -= 3.1 * pinch
        v.co.z += .75 * pinch


def rebuild(output, mode):
    bpy.ops.wm.open_mainfile(filepath=str(PARENT / "Clive-FeltAndCarved.blend"))
    for obj in list(bpy.context.scene.objects):
        if obj.name.startswith(("Seat |", "Smock | hunched", "Waistband | unified")):
            bpy.data.objects.remove(obj, do_unlink=True)
    mats = {key: bpy.data.materials[key] for key in ("blue", "skin")}
    pelvis = make_pelvis(mats)
    smock = build_smock(mats, pelvis, mode != "unfitted")
    build_waistband(mats)
    fit_trouser_tops()
    bpy.ops.object.select_all(action="DESELECT")
    smock.select_set(True)
    bpy.context.view_layer.objects.active = smock
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                view = area.spaces.active.region_3d
                view.view_rotation = Vector((.94, .27, .22)).to_track_quat("Z", "Y")
    bpy.context.preferences.filepaths.save_version = 0
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", nargs="?", type=Path, default=HERE / "Clive-SeatAndSmock.blend")
    parser.add_argument("--unfitted", action="store_const", const="unfitted", dest="mode")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    rebuild(args.output.resolve(), args.mode)
