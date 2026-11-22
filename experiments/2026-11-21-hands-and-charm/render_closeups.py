"""Clay close-ups in the review_views.py Workbench look. blender -b file.blend -P shots.py -- outdir [res]   (never saves)"""
import math, sys
from pathlib import Path
import bpy
from mathutils import Vector

SHOTS = {  # name: (centre, ortho scale mm, azimuth, elevation)
    "face_front": ((0, -28, 70), 46, 0, 0),
    "face_open34": ((0, -26, 70), 46, -42, 6),
    "face_wink34": ((0, -26, 70), 46, 48, 6),
    "face_low": ((0, -26, 68), 46, 22, -24),
    "hands_front": ((0, -12, 38), 44, 0, 4),
    "hands_low": ((0, -12, 38), 44, 30, -14),
    "hands_open34": ((0, -12, 38), 44, -40, 10),
    "hands_side": ((0, -12, 40), 44, 90, 0),
    "hands_top": ((0, -12, 38), 44, 0, 62),
}

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    out = Path(args[0]); out.mkdir(parents=True, exist_ok=True)
    res = int(args[1]) if len(args) > 1 else 640
    scene = bpy.context.scene
    bpy.ops.object.camera_add()
    cam = bpy.context.object
    scene.camera = cam
    cam.data.type = "ORTHO"
    cam.data.clip_start, cam.data.clip_end = 0.1, 2000
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.film_transparent = False
    scene.render.use_compositing = False
    scene.render.use_sequencer = False
    scene.render.resolution_x = scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    sh = scene.display.shading
    sh.light, sh.studio_light, sh.color_type = "STUDIO", "paint.sl", "SINGLE"
    sh.single_color = (.68, .65, .60)
    sh.background_type, sh.background_color = "VIEWPORT", (.14, .15, .17)
    sh.show_shadows = sh.show_cavity = sh.show_specular_highlight = True
    sh.cavity_type, sh.cavity_valley_factor, sh.studiolight_rotate_z = "WORLD", 1, .45
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1
    for name, (centre, scale, az, el) in SHOTS.items():
        a, e = math.radians(az), math.radians(el)
        d = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
        cam.data.ortho_scale = scale
        cam.location = Vector(centre) + d * 400
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = str((out / (name + ".png")).resolve())
        bpy.ops.render.render(write_still=True)

main()
