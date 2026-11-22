"""Render matched clay details or the painted studio views for turn 6."""
import argparse
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

CLAY = {
    "face": ((0, -24, 78), 65, 0, 0),
    "contact": ((0, -10, 86), 52, 123, 27),
    "low_face": ((0, -26, 70), 56, 42, -12),
    "boots": ((0, 1, 19.0), 44, 58, 13),
}
STUDIO = {
    "hero": ((0, -3.5, 54), 122, -27, 9),
    "profile": ((0, -3.0, 54), 122, 72, 4),
    "rear": ((0, -1.0, 55), 125, 132, 19),
}


def material(name, color, roughness, coat):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    shader = mat.node_tree.nodes.get("Principled BSDF")
    mat.diffuse_color = (*color, 1)
    shader.inputs["Base Color"].default_value = mat.diffuse_color
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Coat Weight"].default_value = coat
    shader.inputs["Coat Roughness"].default_value = .24
    return mat


def setup_studio(scene):
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 48
    scene.cycles.use_denoising = True
    prefs = bpy.context.preferences.addons["cycles"].preferences
    try:
        prefs.compute_device_type = "CUDA"
        prefs.refresh_devices()
        gpu_found = False
        for device in prefs.devices:
            device.use = device.type == "CUDA"
            gpu_found |= device.use
        if gpu_found:
            scene.cycles.device = "GPU"
    except (RuntimeError, TypeError, ValueError):
        scene.cycles.device = "CPU"
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 1100
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    bg = scene.world.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (.65, .76, 1, 1)
    bg.inputs[1].default_value = .29
    floor = material("Backdrop", (.082, .106, .129), .80, 0)
    bpy.ops.mesh.primitive_plane_add(size=2000, location=(0, 0, -.15))
    bpy.context.object.data.materials.append(floor)
    for obj in list(scene.objects):
        if obj.type == "LIGHT":
            bpy.data.objects.remove(obj, do_unlink=True)
    for location, size, power, color in [
        ((-85, -130, 170), 104, 345000, (1, .85, .70)),
        ((98, -79, 90), 82, 134000, (.72, .85, 1)),
        ((25, 83, 151), 73, 251000, (1, .88, .72)),
    ]:
        bpy.ops.object.light_add(type="AREA", location=location)
        light = bpy.context.object
        light.data.shape = "DISK"
        light.data.size = size
        light.data.energy = power
        light.data.color = color
        light.rotation_euler = (Vector((0, -3, 59)) - light.location).to_track_quat("-Z", "Y").to_euler()


def setup_clay(scene):
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = scene.render.resolution_y = 720
    sh = scene.display.shading
    sh.light, sh.studio_light, sh.color_type = "STUDIO", "paint.sl", "SINGLE"
    sh.single_color = (.68, .65, .60)
    sh.background_type, sh.background_color = "VIEWPORT", (.14, .15, .17)
    sh.show_shadows = sh.show_cavity = sh.show_specular_highlight = True
    sh.cavity_type, sh.cavity_valley_factor, sh.studiolight_rotate_z = "WORLD", 1, .45
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--studio", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    args.output.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    if args.studio:
        setup_studio(scene)
    else:
        setup_clay(scene)
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    bpy.ops.object.camera_add()
    cam = bpy.context.object
    scene.camera = cam
    cam.data.type = "ORTHO"
    cam.data.clip_start, cam.data.clip_end = .1, 2000
    for name, (center, scale, az, el) in (STUDIO if args.studio else CLAY).items():
        a, e = map(math.radians, (az, el))
        direction = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
        cam.location = Vector(center) + direction * 360
        cam.rotation_euler = (-direction).to_track_quat("-Z", "Y").to_euler()
        cam.data.ortho_scale = scale
        scene.render.filepath = str((args.output / (name + ".png")).resolve())
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
