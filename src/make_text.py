"""Make the raised CLIVE lettering for the front edge of the base, as an STL (uses bpy).

    python3 make_text.py OUT.stl
"""
import math
import os
import sys

import bpy

FONTS = ["/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", "C:/Windows/Fonts/georgiab.ttf"]
SIZE = 14.5              # cap height ends up about 7 mm
FACE_Y = -36.0           # gnome.BASE_FRONT_Y: the plinth face the viewer sees, behind Clive
Z_MID = 3.0              # middle of the plinth's flat face
PROUD, SUNK = 1.0, 0.6   # letters stand 1 mm proud and are anchored 0.6 mm into the stone

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.object.text_add(rotation=(math.radians(90), 0, 0))
ob = bpy.context.object
ob.data.body = "CLIVE"
ob.data.size = SIZE
ob.data.extrude = (PROUD + SUNK) / 2
ob.data.align_x = "CENTER"
ob.data.align_y = "CENTER"
for f in FONTS:
    if os.path.exists(f):
        ob.data.font = bpy.data.fonts.load(f)
        break
bpy.ops.object.convert(target="MESH")
bpy.context.view_layer.update()
zs = [(ob.matrix_world @ v.co).z for v in ob.data.vertices]
ob.location = (0, FACE_Y - (PROUD - SUNK) / 2, Z_MID - (max(zs) + min(zs)) / 2)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.mesh.remove_doubles(threshold=0.001)
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.object.mode_set(mode="OBJECT")
bpy.ops.wm.stl_export(filepath=sys.argv[-1], export_selected_objects=True, global_scale=1.0)
print("wrote", sys.argv[-1])
