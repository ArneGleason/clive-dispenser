"""Render the painted comparison with common cameras and studio light."""
import math
from pathlib import Path
import runpy
import sys

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
lighting = HERE.parent / "2026-11-21-felt-and-carved-hair" / "render_details.py"
setup_studio = runpy.run_path(str(lighting))["setup_studio"]
VIEWS = {
    "front": (-28, 9),
    "side": (90, 4),
    "rear": (131, 15),
    "back": (180, 6),
}


def main(output):
    output.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    setup_studio(scene)
    for obj in scene.objects:
        if obj.type == "MESH" and obj.data.materials and obj.data.materials[0].name == "Backdrop":
            obj.scale = (15, 15, 1)
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"

    bpy.ops.object.camera_add()
    camera = bpy.context.object
    scene.camera = camera
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 121
    camera.data.clip_start = .1
    camera.data.clip_end = 35000
    center = Vector((0, -2.5, 54))
    for name, (az, el) in VIEWS.items():
        a, e = math.radians(az), math.radians(el)
        direction = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
        camera.location = center + direction * 360
        camera.rotation_euler = (-direction).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = str((output / f"{name}.png").resolve())
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main(Path(sys.argv[sys.argv.index("--") + 1]))
