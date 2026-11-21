"""Render matched clay views from an upright Blender scene. Never saves the scene."""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

VIEWS = {
    "front": (0, 0), "side": (90, 0), "rear": (180, 0),
    "front_high": (-42, 24), "wink_side": (48, 12),
    "rear_high": (123, 27), "rear_low": (-134, -7),
    "front_low": (58, -10), "overhead": (-25, 65),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--frame-from", type=Path, help="Parent review's frame.json")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    scene = bpy.context.scene
    if args.frame_from:
        frame = json.loads(args.frame_from.read_text(encoding="utf-8"))
    else:
        dg = bpy.context.evaluated_depsgraph_get()
        corners = []
        for obj in scene.objects:
            if obj.type == "MESH" and obj.visible_get() and not obj.hide_render:
                evaluated = obj.evaluated_get(dg)
                corners.extend(evaluated.matrix_world @ Vector(v) for v in evaluated.bound_box)
        if not corners:
            raise ValueError("Expected visible figure meshes in the active view layer")
        lo = Vector([min(v[i] for v in corners) for i in range(3)])
        hi = Vector([max(v[i] for v in corners) for i in range(3)])
        frame = {"center": list((lo + hi) / 2), "scale": (hi - lo).length * 1.08}
    center, scale = Vector(frame["center"]), float(frame["scale"])
    if len(center) != 3 or not all(math.isfinite(v) for v in center) or not math.isfinite(scale) or scale <= 0:
        raise ValueError("Invalid camera framing")
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "frame.json").write_text(json.dumps(frame, indent=2))
    bpy.ops.object.camera_add()
    cam = bpy.context.object
    scene.camera = cam
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = scale
    cam.data.clip_start = scale / 1000
    cam.data.clip_end = scale * 8
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.film_transparent = False
    scene.render.use_border = False
    scene.render.use_compositing = False
    scene.render.use_sequencer = False
    scene.render.resolution_x = scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.pixel_aspect_x = scene.render.pixel_aspect_y = 1
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    sh = scene.display.shading
    sh.light = "STUDIO"
    sh.studio_light = "paint.sl"
    sh.color_type = "SINGLE"
    sh.single_color = (.68, .65, .60)
    sh.background_type = "VIEWPORT"
    sh.background_color = (.14, .15, .17)
    sh.show_shadows = True
    sh.show_cavity = True
    sh.cavity_type = "WORLD"
    sh.cavity_valley_factor = 1
    sh.show_specular_highlight = True
    sh.studiolight_rotate_z = .45
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1
    for name, (azimuth, elevation) in VIEWS.items():
        az, el = map(math.radians, (azimuth, elevation))
        direction = Vector((math.sin(az)*math.cos(el), -math.cos(az)*math.cos(el), math.sin(el)))
        cam.location = center + direction * scale * 3
        cam.rotation_euler = (-direction).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = str((args.output / (name + ".png")).resolve())
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
