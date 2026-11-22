"""Rebuild turn 6 from the committed PoseFace blend with Blender 5.2.1."""
import argparse
import math
import runpy
import sys
from pathlib import Path

import bpy
from mathutils import Quaternion, Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent / "2026-11-21-turnaround-pose-face"
loft = runpy.run_path(str(PARENT / "build_clive.py"))["build_loft"]

# Rim stations are read from the forehead clockwise toward Clive's left.
# Each station gives x, y and edge height in millimeters.
RIM = [
    (-1.1, -34.8, 83.3), (5.8, -33.4, 82.3), (11.8, -28.9, 79.8),
    (16.7, -23.2, 76.8), (18.1, -15.0, 76.5), (16.6, -7.6, 73.9),
    (12.8, -0.6, 75.1), (6.7, 2.1, 76.9), (-0.4, 3.3, 76.2),
    (-7.5, 2.0, 75.5), (-13.1, -1.3, 74.9), (-16.4, -7.1, 74.0),
    (-17.6, -14.4, 75.0), (-16.8, -22.0, 77.2), (-12.9, -28.6, 80.8),
    (-7.7, -33.4, 82.8),
]

# Sweep distance, center x/y/z, two section radii. The weight shifts toward
# the nape before the crown rolls toward the wink and back into the face plane.
CROWN = [
    (0, 0, -15.6, 77, 17.9, 19.2),
    (1.0, 0, -15.6, 78, 18.0, 19.2),
    (2.4, -0.2, -15.1, 79.4, 17.5, 18.6),
    (4.3, -0.5, -14.5, 81.3, 16.5, 17.2),
    (7.2, -1.3, -13.3, 84.2, 15.2, 15.8),
    (10.6, -2.0, -11.9, 87.6, 13.7, 14.0),
    (14.0, -1.6, -10.7, 91.0, 12.2, 12.3),
    (17.5, -0.3, -10.3, 94.0, 9.0, 9.7),
]
# Upper section widths and bend. The tangent directs both the centerline
# and the ring rotation, keeping the inside bend from doubling back.
HOOK = [
    (0, 0, 9.0, 9.7), (2.7, 8, 7.6, 8.0),
    (6.5, 34, 5.8, 6.2), (10.6, 68, 4.55, 4.8),
    (14.8, 106, 3.8, 4.0), (17.7, 137, 3.06, 3.24),
    (19.7, 158, 2.46, 2.65), (21.0, 171, 1.64, 1.83),
    (21.7, 181, .28, .32),
]

# Open diagonal folds on the cap surface: azimuth, sweep distance, height.
# Endpoints sink into the felt. The width of every fold changes on its path.
FOLDS = [
    [(-132, 2.0, 0), (-91, 3.9, 1.1), (-42, 5.7, 2.1), (8, 7.1, 2.08),
     (47, 8.0, 2.25), (85, 10.0, 1.7), (124, 15.8, 0.95), (151, 21.5, 0)],
    [(99, 3.6, 0), (132, 6.7, 1.0), (173, 8.8, 2.3), (219, 8.5, 2.05),
     (266, 10.8, 2.2), (301, 15.5, 1.5), (334, 21.9, 0.65), (363, 25.2, 0)],
    [(-57, 8.2, 0), (-36, 12.9, 1.13), (0, 14.4, 1.83), (39, 16.6, 1.74),
     (80, 20.8, 1.05), (106, 23.6, 0.48), (141, 25.4, 0)],
]

# Principal beard ribbons, from root to return. Width is measured across
# the lock and depth normal to the face. Most of the lower beard bends right.
BEARD = [
    [(-15.7,-24,73,1.3,1.0),(-17.4,-26.0,68.9,2.6,1.9),(-16.4,-28.2,64,3.1,2.1),
     (-16.2,-27.9,60,2.65,1.7),(-14.4,-26.0,57.3,1.8,1.5),(-12.3,-25.3,57.6,.5,.50)],
    [(-11.8,-28.2,66,1.0,1.1),(-13.45,-29.7,61.0,3.15,2.1),(-12.65,-31,56,3.3,2.1),
     (-10.3,-29.7,52.8,2.6,1.8),(-10.4,-27.7,49.3,1.95,1.4),(-8.0,-27.0,49.6,.62,.53)],
    [(-7.8,-28.1,62.4,1.2,1.25),(-8.6,-31.1,57.4,3.0,2.1),(-6.7,-32.1,53.6,3.25,2.05),
     (-5.6,-30.7,50.0,3.03,2.0),(-8.2,-28.6,46.5,1.88,1.45),(-7.1,-27.0,44.0,1.05,.95),
     (-4.9,-26.2,44.7,.42,.42)],
    [(-3.8,-29,60.4,1.7,1.2),(-3.6,-31.7,56.5,3.3,2.15),(-.8,-33.2,51.9,3.75,2.45),
     (-1.8,-31.6,47.5,3.45,2.2),(-5.0,-28.9,44.1,2.4,1.8),(-4.9,-26.2,41.0,1.85,1.34),
     (-2.9,-24.65,39.7,1.05,.85),(-1.65,-24.6,40.65,.40,.40)],
    [(1.0,-28.9,59.7,1.32,1.25),(1.0,-31.25,56.5,2.7,2.05),(3.7,-32.2,52.2,3.35,2.25),
     (3.25,-29.95,48.65,2.55,1.92),(1.65,-27.9,45.65,1.65,1.45),(3.6,-26.6,45.0,.53,.62)],
    [(6.0,-27.2,61.0,1.2,1.35),(6.55,-30.3,57.6,3.4,2.25),(8.05,-30.35,53.0,3.4,2.35),
     (6.7,-28.75,49.7,2.45,1.85),(7.6,-26.05,47.3,1.6,1.35),(9.55,-25.15,48.4,.57,.55)],
    [(11.5,-24.7,65.6,1.4,1.2),(12.6,-28.3,61.6,3.1,2.03),(13.6,-28.6,57.7,3.37,2.05),
     (12.9,-26.9,54.4,2.7,1.68),(11.7,-24.95,51.35,1.8,1.35),(12.9,-23.7,52.15,.49,.50)],
    [(16.8,-22.8,71.9,1.0,1.10),(16.0,-24.8,68.6,2.3,1.75),(17.6,-25.25,65.05,2.65,1.82),
     (17.7,-24.2,61.35,2.38,1.7),(16.9,-23,58.7,1.48,1.48),(15.7,-23.6,58.45,.48,.45)],
]

MOUSTACHE = [
    [(-.7,-34.2,67.6,1.0,1.05),(-4,-34.55,67.05,2.23,2),(-7.6,-34.65,65.5,2.95,2.1),
     (-11.1,-32.7,65.2,2.65,1.9),(-14.2,-29.6,66.1,2.1,1.7),
     (-15.8,-27.2,68.5,1.55,1.45),(-15.15,-26.5,70.1,.88,.88),(-13.5,-27.3,70.0,.40,.42)],
    [(0.65,-34.25,68.0,1.0,1.05),(3.8,-34.5,68.0,1.95,1.8),(7.25,-33.3,68.0,2.25,2.1),
     (10.45,-32.2,67.35,2.45,2.0),(13.85,-29.45,68.0,2.31,1.9),
     (16.0,-26.9,70.1,1.8,1.55),(15.65,-25.6,72.15,1.12,1.14),(13.95,-26.15,72.8,.45,.54)],
]

def clamp(value, lo=0.0, hi=1.0):
    return min(max(value, lo), hi)


def ease(value):
    t = clamp(value)
    return t * t * (3 - 2 * t)


def bell(value, center, width):
    return math.exp(-((value - center) / width) ** 2)


def interpolate(a, b, c, d, t):
    return b + 0.5 * t * (
        c - a + t * (2*a - 5*b + 4*c - d + t * (3*(b-c) + d-a))
    )


def sample(points, station, *, loop=False):
    i = math.floor(station)

    def point(offset):
        index = (i + offset) % len(points) if loop else min(max(i + offset, 0), len(points) - 1)
        return points[index]

    return tuple(interpolate(*coords, station - i) for coords in zip(*(point(k) for k in (-1, 0, 1, 2))))


def by_first(points, coordinate):
    for index, (a, b) in enumerate(zip(points, points[1:])):
        if coordinate <= b[0]:
            return sample(points, index + clamp((coordinate - a[0]) / (b[0] - a[0])))[1:]
    return points[-1][1:]


def rim_at(degrees):
    return Vector(sample(RIM, (degrees % 360) / 360 * len(RIM), loop=True))


def build_cap(mats):
    steps = 80
    last = CROWN[-1][0]
    lower = [last * i / 35 for i in range(36)]
    body = [(distance, *by_first(CROWN, distance), Quaternion()) for distance in lower]
    center = Vector(CROWN[-1][1:4])
    vertical = Vector((0, 0, 1))
    slouch = Vector((.66, -.75, 0)).normalized()
    bend_axis = vertical.cross(slouch)

    def turn(distance):
        bend, _, _ = by_first(HOOK, distance)
        return Quaternion(bend_axis, math.radians(bend))

    intervals = 55
    step = HOOK[-1][0] / intervals
    for i in range(1, intervals + 1):
        distance = i * step
        center += (turn(distance - step / 2) @ vertical) * step
        _, width, depth = by_first(HOOK, distance)
        body.append((last + distance, *center, width, depth, turn(distance)))

    rings = []
    for distance, x, y, z, width, depth, orientation in body:
        center = Vector((x, y, z))
        lateral = orientation @ Vector((1, 0, 0))
        front = orientation @ Vector((0, -1, 0))
        ring = []
        for j in range(steps):
            theta = 360 * j / steps
            angle = math.radians(theta)
            unit = math.sin(angle) * lateral + math.cos(angle) * front
            point = center + lateral * (width * math.sin(angle)) + front * (depth * math.cos(angle))
            rim = rim_at(theta)
            rim_ellipse = Vector((17.9 * math.sin(angle), -15.6 - 19.2 * math.cos(angle), 77))
            delta = rim - rim_ellipse
            point.x += delta.x * math.exp(-distance / 5.1)
            point.y += delta.y * math.exp(-distance / 5.1)
            point.z += delta.z * math.exp(-distance / 9.2)
            # The soft edge is cut from the flared hem. The fold relief dies
            # into the crown and has a wider ridge than its pinched valley.
            relief = 0.85 * bell(distance, 1.03, 1.18) - 0.31 * bell(distance, 2.95, 1.1)
            for curve in FOLDS:
                azimuth = (theta - curve[0][0]) % 360 + curve[0][0]
                if azimuth <= curve[-1][0]:
                    height, weight = by_first(curve, azimuth)
                    softness = 1.7 - 0.55 * ease((height - 7) / 17)
                    relief += weight * ease((28.0 - distance) / 8) * (
                        bell(distance, height, softness) - 0.43 * bell(distance, height + 1.8, 0.85)
                    )
            ring.append(point + unit * relief)
        rings.append(ring)
    # An inset under the edge makes the closure turn inward into the head.
    inside = []
    for p in rings[0]:
        v = p.copy()
        v.x *= 0.87
        v.y = -15.6 + (v.y + 15.6) * 0.87
        v.z -= 0.60
        inside.append(v)
    return loft("Cap | flared felt, three draped folds", [inside, *rings], "hat", mats, subsurf=1)


def ribbon(name, path, mats, *, nape=False, grooves=(-0.48, 0.23), carving=0.29):
    rings = []
    count = (len(path) - 1) * 5 + 1
    sections = [sample(path, i / 5) for i in range(count)]
    centers = [Vector(p[:3]) for p in sections]
    for i, (center, (_, _, _, width, depth)) in enumerate(zip(centers, sections)):
        tangent = (centers[min(i+1, count-1)] - centers[max(0, i-1)]).normalized()
        outward = Vector((center.x * .78, center.y + 13, .8)) if nape else Vector((center.x * .026, -1, .12))
        normal = (outward - tangent * tangent.dot(outward)).normalized()
        side = tangent.cross(normal)
        weight = ease(i / (count - 1) * 7) * ease((1 - i / (count - 1)) * 4.3)
        ring = []
        for j in range(40):
            angle = 2 * math.pi * j / 40
            across, out = math.sin(angle), math.cos(angle)
            incise = sum(bell(across, mark + .10 * math.sin(i / (count - 1) * 3.4), .115)
                         for mark in grooves)
            relief = carving * incise * weight * ease(out)
            ring.append(center + side * across * width + normal * (out * depth - relief))
        rings.append(ring)
    return loft(name, rings, "hair", mats, subsurf=1)


def make_nape(mats):
    # The roots use the cap rim as a datum. Each lip thickens below it,
    # bends around the head and returns into the neighboring carved mass.
    locks = []
    for i, (theta, sweep, length, width) in enumerate([
        (62, -8, 4.15, 2.8), (76, 5, 4.7, 2.65), (95, 16, 4.2, 2.95),
        (111, 23, 6.7, 3.65), (136, 30, 6.0, 3.6), (153, 41, 7.1, 4.25),
        (179, 27, 6.5, 3.61), (201, 23, 5.1, 3.24), (221, 31, 5.8, 3.45),
        (244, 18, 6.15, 3.4), (268, 12, 4.4, 2.9), (286, 8, 4.6, 2.75),
        (299, 6, 4.9, 3.0),
    ]):
        path = []
        for step, outset, drop, w, d in [
            (0, -2.65, -1.55, .75, .35), (.12, -1.85, 1.3, .96, .47),
            (.35, .12, length * .65, 1.1, .55), (.69, 1.3, length * .96, .94, .51),
            (1.02, 1.0, length * .88, .67, .44), (1.06, .5, length * .61, .48, .34),
            (.93, .25, length * .60, .19, .18),
        ]:
            azimuth = theta + sweep * step
            position = rim_at(azimuth)
            radial = Vector((position.x, position.y + 15.6, 0)).normalized()
            position += radial * outset
            position.z -= drop
            path.append((*position, width * w, width * d))
        locks.append(ribbon(f"Nape source | comma {i + 1:02}", path, mats, nape=True,
                            grooves=(-.43, .29) if i % 4 else (-.56, 0, .53), carving=.44))
    # Flatten the crown-facing roots against an inset of the brim.
    # The clamp fades by the shoulder of each lock, leaving the volutes round.
    for obj in locks:
        for v in obj.data.vertices:
            radial = Vector((v.co.x, v.co.y + 15.6))
            azimuth = math.degrees(math.atan2(radial.x, -radial.y))
            rim = rim_at(azimuth)
            limit = Vector((rim.x, rim.y + 15.6)).length
            push = max(0, radial.length - limit + 0.80) * ease((v.co.z - rim.z + 2.4) / 2.8)
            shift = radial.normalized() * push
            v.co.x -= shift.x
            v.co.y -= shift.y
    backing = []
    for theta in range(63, 304, 8):
        anchor = rim_at(theta)
        inward = Vector((anchor.x, anchor.y + 15.6, 0)).normalized()
        anchor -= inward * (3.15 + .55 * bell(theta, 180, 60))
        anchor.z -= 3.12
        width = 2.85 + .55 * bell(theta, 164, 58)
        fade = 0.5 + 0.5 * ease(min(theta - 61, 305 - theta) / 17)
        backing.append((*anchor, width * fade, 2.45 * fade))
    locks.append(ribbon("Nape source | connected collar", backing, mats, nape=True, grooves=()))
    return locks


def beard_backing(mats):
    profile = [
        (41.85, -4.1, -27.85, -23.55, 1.65),
        (44.0, -3.1, -30.1, -22.45, 4.6),
        (46.6, -2.4, -30.7, -20.8, 7.5),
        (49.8, -1.7, -32, -19.2, 10.1),
        (53.3, -1.05, -32.6, -17.7, 12.75),
        (57.0, -.35, -31.6, -17.1, 14.85),
        (60.4, -.2, -29.65, -16.8, 15.75),
        (63.4, 0, -27.5, -16.7, 15.45),
        (66.8, .28, -25.1, -17.2, 14.95),
        (70.1, .40, -23.30, -17.95, 13.5),
    ]
    rings = []
    for i in range(3 * (len(profile) - 1) + 1):
        z, x, front, rear, width = sample(profile, i / 3)
        rings.append([
            (x + width * math.sin(t), (front + rear) / 2 - (rear - front) / 2 * math.cos(t), z)
            for t in (j * math.tau / 56 for j in range(56))
        ])
    return loft("Beard source | chin and undercurl", rings, "hair", mats, subsurf=1)


def tuck_under_brim(cap, objects):
    graph = bpy.context.evaluated_depsgraph_get()
    surface = BVHTree.FromObject(cap, graph)
    for obj in objects:
        for v in obj.data.vertices:
            x, y, z = v.co
            radial = Vector((x, y + 15.6, 0))
            rim = rim_at(math.degrees(math.atan2(radial.x, -radial.y)))
            strength = ease((z - rim.z + 1.4) / 1.4)
            if strength == 0:
                continue
            unit = radial.normalized()
            origin = Vector((0, -15.6, z)) + unit * 30
            hit, normal, _, distance = surface.ray_cast(origin, -unit, 25)
            if hit is not None:
                margin = .48 if normal.dot(unit) > .35 else .10
                outside = max(0, radial.length - (30 - distance) + margin)
                v.co -= unit * outside * strength


def fuse_locks(name, sources, hidden, material):
    graph = bpy.context.evaluated_depsgraph_get()
    vertices, faces = [], []
    for obj in sources:
        mod = obj.evaluated_get(graph)
        mesh = mod.to_mesh()
        offset = len(vertices)
        vertices.extend(mod.matrix_world @ v.co for v in mesh.vertices)
        faces.extend(tuple(offset + i for i in face.vertices) for face in mesh.polygons)
        mod.to_mesh_clear()
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    mesh.remesh_voxel_size = 0.18
    mesh.use_remesh_fix_poles = True
    bpy.ops.object.voxel_remesh()
    smooth = obj.modifiers.new("Ease carved transitions", "SMOOTH")
    smooth.factor = 0.85
    smooth.iterations = 3
    obj.data.materials.clear()
    obj.data.materials.append(material)
    for p in obj.data.polygons:
        p.use_smooth = True
    for source in sources:
        for collection in list(source.users_collection):
            collection.objects.unlink(source)
        hidden.objects.link(source)
    return obj


def rebuild_boots(mats):
    # Profiles move from heel and welt, through a tall toe box, to the
    # narrower shaft. The upper's flank is deliberately flatter than hair.
    profile = [
        (10.42, -16.8, 14.55, 7.55), (10.60, -17.55, 15.1, 8.28),
        (11.18, -17.64, 15.2, 8.40), (11.92, -17.61, 15.21, 8.43),
        (12.22, -17.21, 14.96, 8.20), (12.48, -16.67, 14.69, 7.92),
        (13.08, -17.03, 14.70, 7.90), (14.40, -16.51, 14.62, 8.0),
        (15.77, -15.13, 14.32, 7.88), (17.15, -13.09, 14.00, 7.63),
        (18.40, -9.28, 13.77, 7.35), (19.68, -7.08, 13.63, 7.10),
        (21.12, -6.36, 13.87, 7.12), (22.55, -6.19, 14.09, 7.28),
        (24.04, -5.25, 14.26, 7.42), (25.25, -4.55, 14.0, 6.95),
    ]
    for hand in (-1, 1):
        rings = []
        length = (len(profile) - 1) * 3
        for i in range(length + 1):
            z, toe, heel, width = sample(profile, i / 3)
            center = (toe + heel) / 2
            ring = []
            for j in range(72):
                angle = 2 * math.pi * j / 72
                u, v = math.sin(angle), -math.cos(angle)
                y = center + (heel - toe) / 2 * v
                radius = width * (1 - .105 * bell(y, 1.6, 3.9) * ease((19 - z) / 6))
                tuck = 1.0 - .14 * ease((z - 22.7) / 2.6)
                y = center + (y - center) * tuck
                x = hand * (9.82 + 0.045 * (-y) + u * radius * tuck)
                arch = 1.60 * bell(y, 3, 3.55) * ease((13.5 - z) / 2.9)
                # Upper creases wrap diagonally from the compressed vamp,
                # with firm leather lying flat between the two bends.
                front = ease((.48 - v) / 1.25)
                z1 = 19.6 + 1.1 * u + .95 * v
                z2 = 22.6 - 1.25 * u + .40 * v
                relief = front * (
                    -.79 * bell(z, z1, .56) + .60 * bell(z, z1 - 1.05, .92)
                    -.56 * bell(z, z2, .50) + .46 * bell(z, z2 + .76, 1.0)
                )
                ring.append((x + hand * u * relief, y + v * relief, z + arch))
            rings.append(ring)
        name = "left" if hand > 0 else "right"
        obj = loft(f"Boot | {name} welt and buckled leather", rings, "boot", mats, subsurf=1)
        obj.data.materials.append(mats["welt"])
        for face in obj.data.polygons:
            if all(obj.data.vertices[i].co.z - 1.60 * bell(obj.data.vertices[i].co.y, 3, 3.55) < 12.33
                   for i in face.vertices):
                face.material_index = 1


def tune_palette(mats):
    # Glazed ceramic with broad highlights so the hand-cut forms stay visible.
    for key, (rgb, roughness, coat) in {
        "hat": ((.48, .027, .015), .24, .26),
        "hair": ((.89, .79, .63), .27, .25),
        "blue": ((.026, .113, .27), .26, .26),
        "boot": ((.17, .060, .023), .27, .22),
    }.items():
        mat = mats[key]
        shader = mat.node_tree.nodes["Principled BSDF"]
        mat.diffuse_color = (*rgb, 1)
        shader.inputs["Base Color"].default_value = mat.diffuse_color
        shader.inputs["Roughness"].default_value = roughness
        shader.inputs["Coat Weight"].default_value = coat
        shader.inputs["Coat Roughness"].default_value = .22


def rebuild(output):
    bpy.ops.wm.open_mainfile(filepath=str(PARENT / "Clive-PoseFace.blend"))
    for obj in list(bpy.context.scene.objects):
        if obj.name.startswith(("Cap |", "Hair |", "Moustache |", "Beard |", "Boot |")):
            bpy.data.objects.remove(obj, do_unlink=True)
    mats = {key: bpy.data.materials[key] for key in ("hat", "hair", "blue", "boot")}
    tune_palette(mats)
    welt = bpy.data.materials["boot"].copy()
    welt.name = "welt"
    welt.diffuse_color = (.095, .031, .011, 1)
    welt.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = welt.diffuse_color
    mats["welt"] = welt
    rebuild_boots(mats)
    cap = build_cap(mats)
    sources = bpy.data.collections.new("Hair sources | show to edit, hide to render")
    bpy.context.scene.collection.children.link(sources)
    beard = []
    for i, path in enumerate(BEARD):
        root = list(path[0])
        root[1] += 1.8
        root[2] += .3
        beard.append(ribbon(f"Beard source | lock {i+1:02}", [root, *path[1:]], mats, carving=.34))
    fuse_locks("Beard | carved flowing mass", [*beard, beard_backing(mats)], sources, mats["hair"])
    collar = fuse_locks("Hair | carved temple and nape", make_nape(mats), sources, mats["hair"])
    ears = [obj for obj in bpy.context.scene.objects if obj.name.startswith("Ear |")]
    tuck_under_brim(cap, [collar, *ears])
    for side, path in zip(("open", "wink"), MOUSTACHE):
        ribbon(f"Moustache | carved {side} wing", path, mats, grooves=(-.48, .21), carving=.34)
    sources.hide_render = sources.hide_viewport = True

    bpy.ops.object.select_all(action="DESELECT")
    cap.select_set(True)
    bpy.context.view_layer.objects.active = cap
    # Start in a front three-quarter view with material colors visible.
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                view = area.spaces.active
                view.shading.color_type = "MATERIAL"
                view.region_3d.view_distance = 159
                view.region_3d.view_location = (0, -3, 55)
                view.region_3d.view_rotation = Vector((.34, -.91, .22)).to_track_quat("Z", "Y")
                view.region_3d.view_perspective = "ORTHO"
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(output))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", nargs="?", type=Path, default=HERE / "Clive-FeltAndCarved.blend")
    rebuild(parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []).output.resolve())
