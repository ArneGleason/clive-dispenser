"""Painted studio renders of the fused Clive (Cycles). Never saves the scene.

blender -b Clive-FusedClay.blend -P render_painted.py -- outdir [samples]

Writes hero.png, rear.png, portrait.png and the orthographic front/side/back
trio used for the side-by-side against character-sculpt/references/clive-turnaround.png.
"""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
out = Path(args[0])
samples = int(args[1]) if len(args) > 1 else 96
out.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
prefs = bpy.context.preferences.addons["cycles"].preferences
for kind in ("OPTIX", "CUDA"):
    try:
        prefs.compute_device_type = kind
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        scene.cycles.device = "GPU"
        break
    except Exception:
        pass
scene.cycles.samples = samples
scene.cycles.use_denoising = True
scene.view_settings.view_transform = "Standard"
scene.render.film_transparent = True
scene.render.image_settings.file_format = "PNG"

world = bpy.data.worlds.new("Studio")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.80, 0.80, 0.82, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.35

# seamless backdrop
bpy.ops.mesh.primitive_plane_add(size=4000, location=(0, 0, 0))
floor = bpy.context.object
mat = bpy.data.materials.new("Backdrop")
mat.use_nodes = True
mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.78, 0.78, 0.80, 1)
mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.9
floor.data.materials.append(mat)
floor.is_shadow_catcher = True


GAIN = 0.035


def area(name, loc, size, power, target=(0, -5, 55)):
    light = bpy.data.lights.new(name, "AREA")
    light.size = size
    light.energy = power
    ob = bpy.data.objects.new(name, light)
    scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return ob


rig = [area("Key", (-160, -230, 240), 200, 9.0e6 * GAIN), area("Fill", (230, -170, 90), 260, 2.5e6 * GAIN),
       area("Rim", (60, 260, 200), 180, 5.0e6 * GAIN), area("Top", (0, -20, 380), 300, 2.0e6 * GAIN)]

bpy.ops.object.camera_add()
cam = bpy.context.object
scene.camera = cam
cam.data.clip_start, cam.data.clip_end = 1, 5000


def shoot(name, centre, az, el, res, ortho=None, lens=85, dist=560, spin_lights=True):
    if (out / name).exists():                              # lets a crashed run resume
        return
    a, e = math.radians(az), math.radians(el)
    d = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
    if ortho:
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = ortho
    else:
        cam.data.type = "PERSP"
        cam.data.lens = lens
    cam.location = Vector(centre) + d * dist
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    for ob, base in zip(rig, RIG0):                       # lights travel with the camera
        x, y, z = base
        ca, sa = math.cos(a), math.sin(a)
        ob.location = (x * ca - y * sa, x * sa + y * ca, z) if spin_lights else base
        ob.rotation_euler = (Vector((0, -5, 55)) - ob.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.resolution_x, scene.render.resolution_y = res
    raw = out / ("raw_" + name)
    scene.render.filepath = str(raw.resolve())
    bpy.ops.render.render(write_still=True)
    flatten(raw, out / name)
    raw.unlink()


def flatten(path, final):
    """Composite the transparent render over a soft studio grey."""
    img = bpy.data.images.load(str(path))
    w, h = img.size
    px = __import__("numpy").array(img.pixels[:], dtype="float32").reshape(h, w, 4)
    grad = __import__("numpy").linspace(0.70, 0.86, h, dtype="float32")[:, None, None]
    px[..., :3] = px[..., :3] + (1 - px[..., 3:4]) * grad
    px[..., 3] = 1
    img.pixels[:] = px.ravel()
    img.filepath_raw = str(final)
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


RIG0 = [tuple(ob.location) for ob in rig]
shoot("hero.png", (0, -3, 55), -32, 9, (1100, 1400), lens=90, dist=330)
shoot("wink.png", (0, -3, 55), 40, 6, (1100, 1400), lens=90, dist=330)
shoot("rear.png", (0, 0, 54), 148, 14, (1100, 1400), lens=90, dist=330)
shoot("portrait.png", (0, -27, 70), -14, 2, (1200, 1200), lens=110, dist=190)
for name, az in (("ortho_front.png", 0), ("ortho_side.png", 90), ("ortho_back.png", 180)):
    shoot(name, (0, -3, 54.5), az, 0, (900, 1200), ortho=118)
