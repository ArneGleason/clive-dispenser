"""Wrap the fused PLY in a Blender scene: blender -b -P blend_clive.py -- in.ply out.blend [decimate_ratio]"""
import sys

import bpy

args = sys.argv[sys.argv.index("--") + 1:]
ply, out = args[0], args[1]
ratio = float(args[2]) if len(args) > 2 else 1.0
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.ply_import(filepath=ply)
obj = bpy.context.object
obj.name = obj.data.name = "Clive | fused clay"
# marching cubes leaves slivers that break shadow volumes: weld and dissolve them
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.remove_doubles(threshold=0.03)
bpy.ops.mesh.dissolve_degenerate(threshold=0.01)
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.object.mode_set(mode="OBJECT")
if ratio < 1:
    mod = obj.modifiers.new("Decimate", "DECIMATE")
    mod.ratio = ratio
    bpy.ops.object.modifier_apply(modifier=mod.name)
bpy.ops.object.shade_smooth()
attr = obj.data.color_attributes[0].name
mat = bpy.data.materials.new("Glazed ceramic (vertex paint)")
mat.use_nodes = True
nt = mat.node_tree
bsdf = nt.nodes["Principled BSDF"]
col = nt.nodes.new("ShaderNodeVertexColor")
col.layer_name = attr
nt.links.new(col.outputs["Color"], bsdf.inputs["Base Color"])
bsdf.inputs["Roughness"].default_value = 0.32
bsdf.inputs["Coat Weight"].default_value = 0.7
bsdf.inputs["Coat Roughness"].default_value = 0.08
obj.data.materials.append(mat)
bpy.context.scene.unit_settings.scale_length = 0.001
bpy.context.scene.unit_settings.length_unit = "MILLIMETERS"
bpy.ops.wm.save_as_mainfile(filepath=out, compress=True)
print("saved", out, len(obj.data.vertices), "verts", len(obj.data.polygons), "faces")
