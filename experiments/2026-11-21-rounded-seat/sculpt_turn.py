"""Round the seat on the turn 7 cage and refit the shirt and waistband."""
import argparse
import math
import runpy
import sys
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent / "2026-11-21-seat-and-smock"
tailoring = runpy.run_path(str(PARENT / "sculpt_turn.py"))
builders = tailoring["build_smock"].__globals__
parent_skin = builders["skin_point"]
ease = builders["ease"]
bell = builders["bell"]

# Glaze colours are linear RGB. The two tones produce subdued variation
# across the ceramic instead of baking photographed highlights into paint.
GLAZES = {
    "hat": ((.365, .018, .010), (.57, .051, .024), .24, .30),
    "blue": ((.014, .056, .178), (.028, .125, .31), .26, .28),
    "hair": ((.78, .667, .476), (.96, .863, .682), .29, .23),
    "skin": ((.85, .465, .256), (.96, .621, .388), .28, .21),
    "boot": ((.102, .033, .012), (.24, .099, .036), .28, .22),
    "base": ((.66, .49, .287), (.86, .735, .515), .34, .14),
}


def seat_skin(theta, z):
    p = parent_skin(theta, z)
    _, _, original, _ = builders["by_first"](builders["PELVIS"], z)

    # The reference holds its rear projection for several millimetres
    # above and below the apex. Use an oval arc there, feathered into
    # the waist and the thighs rather than pulling the apex forward.
    q = (z - 48.45) / 13.80
    oval = 33.76 - 14.75 * (1 - math.sqrt(max(0, 1 - q*q)))
    blend = ease((z - 35.90) / 5.25) * ease((61.2 - z) / 4.9)
    back = ease((-math.cos(theta) - .06) / .69)
    p.y += (oval - original) * blend * back

    # Carry the lower fullness around the outer cheek in the rear view,
    # keeping the cleft and the original leg sockets on the same cage.
    side = math.sin(theta)
    p.x += 1.05 * side * back * bell(abs(side), .68, .24) * bell(z, 42.8, 4.45)
    return p


def shave_tip(theta, z):
    p = parent_skin(theta, z)
    p.y -= 2.5 * bell(z, 48.2, 4.15) * ease((-math.cos(theta) - .06) / .69)
    return p


def color_materials():
    for name, (low, high, roughness, coat) in GLAZES.items():
        mat = bpy.data.materials[name]
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        shader = nodes.get("Principled BSDF")
        mat.diffuse_color = (*(0.5*(a+b) for a,b in zip(low, high)), 1)
        shader.inputs["Roughness"].default_value = roughness
        shader.inputs["Coat Weight"].default_value = coat
        shader.inputs["Coat Roughness"].default_value = .23
        geometry = nodes.new("ShaderNodeNewGeometry")
        geometry.location = (-660, 290)
        texture = nodes.new("ShaderNodeTexNoise")
        texture.label = "Subtle shade in the glaze"
        texture.location = (-440, 290)
        texture.inputs["Scale"].default_value = .32
        texture.inputs["Detail"].default_value = 2.1
        links.new(geometry.outputs["Position"], texture.inputs["Vector"])
        blend = nodes.new("ShaderNodeMixRGB")
        blend.location = (-200, 290)
        blend.inputs[1].default_value = (*low, 1)
        blend.inputs[2].default_value = (*high, 1)
        links.new(texture.outputs["Fac"], blend.inputs[0])
        links.new(blend.outputs["Color"], shader.inputs["Base Color"])

    # Keep Neon's painted blush placement and bring the face into the same warm palette.
    face = bpy.data.materials["skin_face"]
    tint = next(node for node in face.node_tree.nodes if node.bl_idname == "ShaderNodeMix")
    tint.inputs[6].default_value = (.91, .55, .33, 1)
    tint.inputs[7].default_value = (.87, .255, .151, 1)


def rebuild(output, apex_only):
    bpy.ops.wm.open_mainfile(filepath=str(PARENT / "Clive-SeatAndSmock.blend"))
    for obj in list(bpy.context.scene.objects):
        if obj.name.startswith(("Seat |", "Smock | arched", "Waistband | fitted")):
            bpy.data.objects.remove(obj, do_unlink=True)
    mats = {name: bpy.data.materials[name] for name in ("skin", "blue")}
    # Keep the same branched cage and fit functions. Give all three builders
    # the revised skin surface so the contact edits agree at every station.
    builders["skin_point"] = shave_tip if apex_only else seat_skin
    pelvis = builders["make_pelvis"](mats)
    builders["build_smock"](mats, pelvis, tailored=True)
    builders["build_waistband"](mats)
    color_materials()

    bpy.ops.object.select_all(action="DESELECT")
    pelvis.select_set(True)
    bpy.context.view_layer.objects.active = pelvis
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                view = area.spaces.active.region_3d
                view.view_rotation = Vector((.81, .55, .12)).to_track_quat("Z", "Y")
    bpy.context.preferences.filepaths.save_version = 0
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", nargs="?", type=Path, default=HERE / "Clive-RoundedSeat.blend")
    parser.add_argument("--apex-only", action="store_true", help="Replay the rejected apex subtraction trial")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    rebuild(args.output.resolve(), args.apex_only)
