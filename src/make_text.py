"""Make the embossed CLIVE nameplate lettering as an STL (uses bpy).

    python3 make_text.py OUT.stl
"""
import os
import sys

import bpy

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SIZE, DEPTH, Y, Z = 14.0, 1.3, -24.0, 8.5   # letters stand 0.8 mm proud of the base top (z = 9)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.object.text_add(location=(0, Y, Z))
ob = bpy.context.object
ob.data.body = "CLIVE"
ob.data.size = SIZE
ob.data.extrude = DEPTH / 2
ob.data.align_x = "CENTER"
ob.data.align_y = "CENTER"
if os.path.exists(FONT):
    ob.data.font = bpy.data.fonts.load(FONT)
ob.location.z = Z + DEPTH / 2
bpy.ops.object.convert(target="MESH")
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.remove_doubles(threshold=0.001)
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.object.mode_set(mode="OBJECT")
bpy.ops.wm.stl_export(filepath=sys.argv[-1], export_selected_objects=True, global_scale=1.0)
print("wrote", sys.argv[-1])
