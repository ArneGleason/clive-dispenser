"""Turn vertex-coloured PLYs into textured OBJs (UV unwrap + bake), with bpy.

    python3 bake_texture.py OUT_DIR part1.ply [part2.ply ...]

Full-colour printers and print services want OBJ + MTL + PNG texture.
"""
import os
import sys

import bpy

out_dir = sys.argv[1]
SIZE = 4096
for ply in sys.argv[2:]:
    name = os.path.splitext(os.path.basename(ply))[0]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.engine = "CYCLES"
    bpy.context.scene.cycles.device = "CPU"
    bpy.context.scene.cycles.samples = 1
    bpy.ops.wm.ply_import(filepath=ply)
    ob = bpy.context.selected_objects[0]
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.002)
    bpy.ops.object.mode_set(mode="OBJECT")
    img = bpy.data.images.new(f"{name}_colour", SIZE, SIZE)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    attr = nt.nodes.new("ShaderNodeVertexColor")
    emit = nt.nodes.new("ShaderNodeEmission")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    nt.links.new(attr.outputs["Color"], emit.inputs["Color"])
    nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    nt.nodes.active = tex
    ob.data.materials.clear()
    ob.data.materials.append(mat)
    bpy.context.scene.render.bake.margin = 8
    bpy.ops.object.bake(type="EMIT")
    png = os.path.join(out_dir, f"{name}_colour.png")
    img.filepath_raw = png
    img.file_format = "PNG"
    img.save()
    # Swap to a plain textured material for export.
    nt.nodes.clear()
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bpy.ops.wm.obj_export(filepath=os.path.join(out_dir, f"{name}.obj"), export_selected_objects=False,
                          export_materials=True, path_mode="RELATIVE", export_colors=False, forward_axis="Y", up_axis="Z")
    print("baked", name, flush=True)
