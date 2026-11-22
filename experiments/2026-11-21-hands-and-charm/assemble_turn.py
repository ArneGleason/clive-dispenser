"""Turn 10 · Fable 2: fit the new fists and bust into turn 9's Clive.

    blender -b experiments/2026-11-21-garment-anatomy-carved-hair/Clive-GarmentAndHair.blend
        -P experiments/2026-11-21-hands-and-charm/assemble_turn.py -- partsdir out.blend [--keep-beard] [--decimate 0.4]

Opens the turn 9 file (the parent is never saved over), removes the parts this turn
replaces, imports the PLY parts written by sculpt_parts.py, and saves the result under
a new name. --decimate thins the dense marching-cubes parts to keep the file light.
"""
import sys
from pathlib import Path

import bpy
import numpy as np

args = sys.argv[sys.argv.index("--") + 1:]
parts, out = Path(args[0]), args[1]
keep_beard = "--keep-beard" in args
decimate = float(args[args.index("--decimate") + 1]) if "--decimate" in args else 1.0

REPLACED_BY_HANDS = ["Hand | left sculpted forearm and hand", "Hand | right sculpted forearm and hand"]
REPLACED_BY_BUST = ["Head | continuous quad sculpt", "Eye | open globe", "Eye | catchlight", "Brow | open side",
                    "Brow | wink side", "Moustache | carved open wing", "Moustache | carved wink wing",
                    "Mouth | dark cavity backing", "Teeth | crooked ceramic dental arch"]
BEARD = ["Beard | carved 360 mass"]
GROUP_MATERIALS = ["skin_blush", "hair", "eye", "iris", "pupil", "tooth", "mouth", "lash"]   # red channel / 25


def retire(names):
    """Remove the turn 9 parts this turn replaces. They stay untouched in the parent file."""
    for n in names:
        ob = bpy.data.objects.get(n)
        if ob is not None:
            me = ob.data
            bpy.data.objects.remove(ob, do_unlink=True)
            if me.users == 0:
                bpy.data.meshes.remove(me)


def blush_material():
    """Turn 8's skin glaze, with rosy areas and freckles driven by vertex attributes instead of fixed points."""
    if "skin_blush" in bpy.data.materials:
        return bpy.data.materials["skin_blush"]
    mat = bpy.data.materials["skin"].copy()
    mat.name = "skin_blush"
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    base = bsdf.inputs["Base Color"].links[0].from_socket
    blush = nt.nodes.new("ShaderNodeAttribute")
    blush.attribute_name = "blush"
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["B"].default_value = (0.78, 0.16, 0.14, 1)
    nt.links.new(base, mix.inputs["A"])
    nt.links.new(blush.outputs["Fac"], mix.inputs["Factor"])
    # freckles: small darker flecks, only where the freckle mask says so
    frk = nt.nodes.new("ShaderNodeAttribute")
    frk.attribute_name = "freckle"
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = 1.15
    geo = nt.nodes["Geometry"]
    nt.links.new(geo.outputs["Position"], vor.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeMapRange")
    ramp.inputs["From Min"].default_value = 0.10
    ramp.inputs["From Max"].default_value = 0.22
    ramp.inputs["To Min"].default_value = 1.0
    ramp.inputs["To Max"].default_value = 0.0
    nt.links.new(vor.outputs["Distance"], ramp.inputs["Value"])
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    nt.links.new(ramp.outputs["Result"], mul.inputs[0])
    nt.links.new(frk.outputs["Fac"], mul.inputs[1])
    mix2 = nt.nodes.new("ShaderNodeMix")
    mix2.data_type = "RGBA"
    mix2.inputs["B"].default_value = (0.55, 0.20, 0.12, 1)
    nt.links.new(mix.outputs["Result"], mix2.inputs["A"])
    nt.links.new(mul.outputs["Value"], mix2.inputs["Factor"])
    nt.links.new(mix2.outputs["Result"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.24
    bsdf.inputs["Coat Weight"].default_value = 0.45
    bsdf.inputs["Coat Roughness"].default_value = 0.11
    return mat


def lash_material():
    if "lash" in bpy.data.materials:
        return bpy.data.materials["lash"]
    mat = bpy.data.materials["pupil"].copy()
    mat.name = "lash"
    mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.045, 0.022, 0.012, 1)
    return mat


def bring_in(ply, name):
    bpy.ops.wm.ply_import(filepath=str(ply))
    ob = bpy.context.object
    ob.name = ob.data.name = name
    me = ob.data
    # marching cubes leaves slivers that streak Workbench shadows: weld and dissolve them
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=0.02)
    bpy.ops.mesh.dissolve_degenerate(threshold=0.005)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    col = me.color_attributes[0]
    n = len(me.vertices)
    raw = np.empty(len(col.data) * 4, dtype=np.float32)
    col.data.foreach_get("color_srgb", raw)
    raw = raw.reshape(-1, 4)
    if col.domain == "CORNER":
        per_vert = np.zeros((n, 4), np.float32)
        loops = np.empty(len(me.loops), dtype=np.int32)
        me.loops.foreach_get("vertex_index", loops)
        per_vert[loops] = raw
        raw = per_vert
    group = np.rint(raw[:, 0] * 255 / 25).astype(int)
    for attr, ch in (("blush", 1), ("freckle", 2)):
        a = me.attributes.new(attr, "FLOAT", "POINT")
        a.data.foreach_set("value", raw[:, ch].astype(np.float32))
    me.color_attributes.remove(me.color_attributes[0])
    used = sorted(set(group.tolist()))
    blush_material()
    lash_material()
    for g in used:
        me.materials.append(bpy.data.materials[GROUP_MATERIALS[g]])
    slot = {g: i for i, g in enumerate(used)}
    start = np.empty(len(me.polygons), dtype=np.int32)
    me.polygons.foreach_get("loop_start", start)
    corner = np.empty(len(me.loops), dtype=np.int32)
    me.loops.foreach_get("vertex_index", corner)
    tri = group[np.stack([corner[start], corner[start + 1], corner[start + 2]], 1)]
    # a face takes the group two of its corners agree on, else its first corner's
    pick = np.where(tri[:, 1] == tri[:, 2], tri[:, 1], tri[:, 0])
    me.polygons.foreach_set("material_index", np.vectorize(slot.get)(pick).astype(np.int32))
    if decimate < 1:
        mod = ob.modifiers.new("Decimate", "DECIMATE")
        mod.ratio = decimate
        bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.ops.object.shade_smooth()
    me.update()
    return ob


if (parts / "hand_L.ply").exists():
    retire(REPLACED_BY_HANDS)
    bring_in(parts / "hand_L.ply", "Hand | left chubby fist over the waistband")
    bring_in(parts / "hand_R.ply", "Hand | right chubby fist over the waistband")
if (parts / "bust.ply").exists():
    retire(REPLACED_BY_BUST + ([] if keep_beard else BEARD))
    bring_in(parts / "bust.ply", "Bust | face, grin, moustache and beard as one glazed piece")
bpy.ops.object.select_all(action="DESELECT")
bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=False, do_recursive=True)
bpy.ops.wm.save_as_mainfile(filepath=out, compress=True)
print("saved", out)
