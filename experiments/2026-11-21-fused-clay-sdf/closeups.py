"""Close-up clay views in the same Workbench look as character-sculpt/tools/review_views.py.

blender -b model.blend -P closeups.py -- outdir            (never saves the scene)
"""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

SHOTS = {  # name: (centre, ortho scale mm, azimuth, elevation)
    "face_front": ((0, -28, 70), 50, 0, 0),
    "face_open34": ((0, -26, 70), 50, -42, 6),
    "face_wink34": ((0, -26, 70), 50, 48, 6),
    "face_low": ((0, -26, 68), 50, 22, -24),
    "hands_low": ((0, -12, 34), 50, 30, -14),
    "nape_high": ((0, -6, 72), 56, 150, 24),
    "trousers_rear": ((0, 6, 32), 56, 160, 4),
    "trousers_front": ((0, -6, 30), 56, -24, 8),
}


def main():
    out = Path(sys.argv[sys.argv.index("--") + 1])
    out.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    bpy.ops.object.camera_add()
    cam = bpy.context.object
    scene.camera = cam
    cam.data.type = "ORTHO"
    cam.data.clip_start, cam.data.clip_end = 0.1, 2000
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    sh = scene.display.shading
    sh.light, sh.studio_light, sh.color_type = "STUDIO", "paint.sl", "SINGLE"
    sh.single_color = (.68, .65, .60)
    sh.background_type, sh.background_color = "VIEWPORT", (.14, .15, .17)
    sh.show_shadows = sh.show_cavity = sh.show_specular_highlight = True
    sh.cavity_type, sh.cavity_valley_factor, sh.studiolight_rotate_z = "WORLD", 1, .45
    scene.view_settings.view_transform = "Standard"
    for name, (centre, scale, az, el) in SHOTS.items():
        a, e = math.radians(az), math.radians(el)
        d = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
        cam.data.ortho_scale = scale
        cam.location = Vector(centre) + d * 400
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = str((out / (name + ".png")).resolve())
        bpy.ops.render.render(write_still=True)


main()
