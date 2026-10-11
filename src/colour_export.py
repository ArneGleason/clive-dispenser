"""Writers for colour 3D printing.

* 3MF with per-vertex colour (3MF Materials extension colour groups): for
  full-colour printers and their slicers.
* OBJ + MTL with one flat colour per face from a small filament palette: for
  multi-filament FDM printers (AMS-style changers, tool changers).
"""
import zipfile

import numpy as np

# Eight filaments cover Clive. Merge gold into stone and brown into black for a 6-colour printer.
FILAMENTS = {
    "red": (0.80, 0.10, 0.08), "blue": (0.13, 0.28, 0.72), "skin": (0.97, 0.80, 0.68),
    "white": (0.96, 0.95, 0.92), "brown": (0.45, 0.26, 0.13), "black": (0.08, 0.07, 0.06),
    "stone": (0.80, 0.74, 0.62), "gold": (0.90, 0.72, 0.25),
}

_CT = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
 <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
 <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>
</Types>"""
_RELS = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>
</Relationships>"""


def write_3mf(path, verts, faces, colours, name="Clive", bits=5):
    """3MF with per-vertex colours, quantised to `bits` per channel to keep files small."""
    q = np.round(np.clip(colours, 0, 1) * (2 ** bits - 1)).astype(np.int64)
    key = (q[:, 0] << (2 * bits)) | (q[:, 1] << bits) | q[:, 2]
    uniq, idx = np.unique(key, return_inverse=True)
    rgb = np.stack([(uniq >> (2 * bits)) & (2 ** bits - 1), (uniq >> bits) & (2 ** bits - 1), uniq & (2 ** bits - 1)], 1)
    rgb = np.round(rgb * 255 / (2 ** bits - 1)).astype(int)
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<model unit="millimeter" xml:lang="en-US" '
           'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
           'xmlns:m="http://schemas.microsoft.com/3dmanufacturing/material/2015/02">',
           f' <metadata name="Title">{name}</metadata>', ' <resources>', '  <m:colorgroup id="1">']
    out += [f'   <m:color color="#{r:02X}{g:02X}{b:02X}"/>' for r, g, b in rgb]
    out += ['  </m:colorgroup>', f'  <object id="2" name="{name}" type="model" pid="1" pindex="0">', '   <mesh>',
            '    <vertices>']
    out += [f'     <vertex x="{x:.4f}" y="{y:.4f}" z="{z:.4f}"/>' for x, y, z in verts]
    out += ['    </vertices>', '    <triangles>']
    out += [f'     <triangle v1="{a}" v2="{b}" v3="{c}" pid="1" p1="{idx[a]}" p2="{idx[b]}" p3="{idx[c]}"/>'
            for a, b, c in faces]
    out += ['    </triangles>', '   </mesh>', '  </object>', ' </resources>', ' <build>', '  <item objectid="2"/>',
            ' </build>', '</model>']
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _CT)
        z.writestr("_rels/.rels", _RELS)
        z.writestr("3D/3dmodel.model", "\n".join(out))


def _lab(rgb):
    """sRGB 0..1 -> CIE Lab, so 'nearest colour' matches what eyes see."""
    c = np.where(rgb > 0.04045, ((rgb + 0.055) / 1.055) ** 2.4, rgb / 12.92)
    xyz = c @ np.array([[0.4124, 0.2126, 0.0193], [0.3576, 0.7152, 0.1192], [0.1805, 0.0722, 0.9505]])
    xyz /= np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[:, 1] - 16, 500 * (f[:, 0] - f[:, 1]), 200 * (f[:, 1] - f[:, 2])], 1)


def nearest_filament(colours):
    names = list(FILAMENTS)
    pal = _lab(np.array([FILAMENTS[n] for n in names]))
    d = ((_lab(np.asarray(colours))[:, None, :] - pal[None, :, :]) ** 2).sum(-1)
    return [names[i] for i in d.argmin(1)]


def write_obj_palette(path, verts, faces, vertex_colours):
    """OBJ + MTL, each face assigned the nearest of the FILAMENTS colours."""
    face_rgb = vertex_colours[faces].mean(axis=1)
    names = np.array(nearest_filament(face_rgb))
    mtl = path[:-4] + ".mtl"
    with open(mtl, "w") as f:
        for n, (r, g, b) in FILAMENTS.items():
            f.write(f"newmtl {n}\nKd {r:.3f} {g:.3f} {b:.3f}\n\n")
    with open(path, "w") as f:
        f.write(f"mtllib {mtl.split('/')[-1]}\n")
        f.writelines(f"v {x:.4f} {y:.4f} {z:.4f}\n" for x, y, z in verts)
        for n in FILAMENTS:
            sel = faces[names == n]
            if len(sel):
                f.write(f"usemtl {n}\n")
                f.writelines(f"f {a + 1} {b + 1} {c + 1}\n" for a, b, c in sel)
    return {n: int((names == n).sum()) for n in FILAMENTS}
