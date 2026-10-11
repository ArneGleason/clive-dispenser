"""Render PLY parts with Blender (bpy, headless Cycles).

Usage: python3 render.py scene.json
scene.json = {
  "objects": [{"ply": "...", "gloss": 0.25, "alpha": 1.0}, ...],
  "camera": {"loc": [x,y,z], "target": [x,y,z], "lens": 60},
  "out": "file.png", "size": [1200, 1500], "samples": 64,
  "text": [{"body": "CLIVE", "loc": [...], "rot": [...], "size": 9, "depth": 0.6, "color": [r,g,b]}]
}
Units: scene is authored in mm; we scale by 0.001 so Blender works in metres.
"""
import json
import math
import sys

import bpy
from mathutils import Vector

S = 0.001

cfg = json.load(open(sys.argv[-1]))
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = cfg.get("samples", 64)
scene.cycles.use_denoising = True
scene.render.resolution_x, scene.render.resolution_y = cfg.get("size", [1200, 1500])
scene.render.film_transparent = False
scene.view_settings.view_transform = "Standard"
scene.view_settings.exposure = cfg.get("exposure", -2.0)


def plastic(name, gloss, alpha, flat=None):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    if flat is None:
        attr = nt.nodes.new("ShaderNodeVertexColor")
        nt.links.new(attr.outputs["Color"], bsdf.inputs["Base Color"])
    else:
        bsdf.inputs["Base Color"].default_value = (*flat, 1)
    bsdf.inputs["Roughness"].default_value = gloss
    bsdf.inputs["Coat Weight"].default_value = 0.25
    bsdf.inputs["Coat Roughness"].default_value = 0.15
    if alpha < 1:
        bsdf.inputs["Alpha"].default_value = alpha
    return mat


for i, o in enumerate(cfg["objects"]):
    bpy.ops.wm.ply_import(filepath=o["ply"])
    ob = bpy.context.selected_objects[0]
    ob.scale = (S, S, S)
    bpy.ops.object.shade_auto_smooth(angle=math.radians(o.get("smooth_angle", 35)))
    ob.data.materials.append(plastic(f"m{i}", o.get("gloss", 0.3), o.get("alpha", 1.0), o.get("flat")))

for i, t in enumerate(cfg.get("text", [])):
    bpy.ops.object.text_add(location=[c * S for c in t["loc"]], rotation=[math.radians(a) for a in t["rot"]])
    ob = bpy.context.object
    ob.data.body = t["body"]
    ob.data.size = t["size"] * S
    ob.data.extrude = t["depth"] * S
    ob.data.align_x = "CENTER"
    ob.data.align_y = "CENTER"
    font = t.get("font")
    if font:
        ob.data.font = bpy.data.fonts.load(font)
    ob.data.materials.append(plastic(f"t{i}", 0.5, 1.0, t["color"]))

# Floor + soft studio lighting.
bpy.ops.mesh.primitive_plane_add(size=4, location=(0, 0, -0.0002))
floor = bpy.context.object
fm = bpy.data.materials.new("floor")
fm.use_nodes = True
fm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = cfg.get("floor", (0.93, 0.89, 0.80, 1))
fm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.8
floor.data.materials.append(fm)

world = bpy.data.worlds.new("w")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.95, 0.92, 0.85, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.25


def area(name, loc, energy, size):
    light = bpy.data.lights.new(name, "AREA")
    light.energy = energy
    light.size = size
    ob = bpy.data.objects.new(name, light)
    scene.collection.objects.link(ob)
    ob.location = loc
    d = Vector((0, 0, 0.07)) - Vector(loc)
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


area("key", (0.25, -0.30, 0.35), 14, 0.30)
area("fill", (-0.30, -0.15, 0.20), 6, 0.40)
area("rim", (0.05, 0.35, 0.30), 10, 0.25)

cam_cfg = cfg["camera"]
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
scene.collection.objects.link(cam)
cam.location = [c * S for c in cam_cfg["loc"]]
d = Vector([c * S for c in cam_cfg["target"]]) - cam.location
cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
cam.data.lens = cam_cfg.get("lens", 60)
cam.data.clip_start = 0.001
scene.camera = cam

scene.render.filepath = cfg["out"]
bpy.ops.render.render(write_still=True)
print("wrote", cfg["out"])
