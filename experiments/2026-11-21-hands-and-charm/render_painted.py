"""Painted look with the file's own camera rig. blender -b file.blend -P paint.py -- outdir [samples] (never saves)"""
import sys, math
from pathlib import Path
import bpy
from mathutils import Vector
args = sys.argv[sys.argv.index("--") + 1:]
out = Path(args[0]); out.mkdir(parents=True, exist_ok=True)
samples = int(args[1]) if len(args) > 1 else 48
only = args[2].split(",") if len(args) > 2 else None
sc = bpy.context.scene
sc.render.engine = "CYCLES"
prefs = bpy.context.preferences.addons["cycles"].preferences
for kind in ("OPTIX", "CUDA"):
    try:
        prefs.compute_device_type = kind; prefs.get_devices()
        for d in prefs.devices: d.use = True
        sc.cycles.device = "GPU"; break
    except Exception: pass
sc.cycles.samples = samples; sc.cycles.use_denoising = True
sc.render.image_settings.file_format = "PNG"
cam = sc.camera
rig = [bpy.data.objects[n] for n in ("Key softbox", "Fill light", "Rim light")]
base = [(o.location.copy(), o.rotation_euler.copy()) for o in rig]
SHOTS = {  # name: (centre, ortho scale, azimuth, elevation, (w,h))
    "hero": ((0, -3, 55), 119, 8.2, 5.4, (1000, 1100)),
    "front": ((0, -3, 55), 119, 0, 0, (900, 1100)),
    "open34": ((0, -3, 55), 119, -38, 8, (1000, 1100)),
    "wink34": ((0, -3, 55), 119, 42, 8, (1000, 1100)),
    "side": ((0, -3, 55), 119, 90, 0, (1000, 1100)),
    "rear34": ((0, 0, 55), 119, 150, 12, (1000, 1100)),
    "back": ((0, -3, 55), 119, 180, 0, (1000, 1100)),
    "face": ((0, -27, 68), 50, -6, 2, (1000, 1000)),
    "face_wink": ((0, -27, 68), 50, 34, 4, (1000, 1000)),
    "hands": ((0, -12, 38), 46, 4, 6, (1000, 1000)),
    "hands_side": ((0, -12, 40), 46, 68, 4, (1000, 1000)),
}
cam.data.type = "ORTHO"
for name, (c, scale, az, el, res) in SHOTS.items():
    if only and name not in only: continue
    if (out / (name + ".png")).exists(): continue
    a, e = math.radians(az), math.radians(el)
    d = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
    cam.data.ortho_scale = scale
    cam.location = Vector(c) + d * 300
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    ca, sa = math.cos(a), math.sin(a)
    for o, (loc, rot) in zip(rig, base):                      # lights travel with the camera
        o.location = (loc.x * ca - loc.y * sa, loc.x * sa + loc.y * ca, loc.z)
        o.rotation_euler = (Vector((0, -5, 55)) - o.location).to_track_quat("-Z", "Y").to_euler()
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.filepath = str((out / (name + ".png")).resolve())
    bpy.ops.render.render(write_still=True)
