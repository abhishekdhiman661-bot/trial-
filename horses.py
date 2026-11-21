"""Rigged, animated horses for build_scenes.py (drop-in for horse() / swing(h["legs"])).

Model: Quaternius "Horse" (CC0), cached in assets/horse/horse.blend (see SOURCE.txt, prep_horse.py).
Usage:  from horses import horse, trot     then   horse(scn, name, parent, loc, col)   and   trot(h, f0, f1, speed)
"""
import bpy, os, math
from mathutils import Vector

DIR = os.path.dirname(os.path.abspath(__file__)) + "/assets/horse"
K = .45                      # must equal K in prep_horse.py (size baked into the mesh); withers ~1.5 m
Y0 = -.3                     # model shifted forward in the root: keeps the tail swing off the driver, chest just ahead of the tongue tip
SHIFT = (0, Y0, 0)
# ground speed of the stance foot per frame at action scale 1 (template units * K), measured from the Walk/Gallop actions
GAIT = {"Walk": .047, "Gallop": .18}
_cache = {}


def _tpl():
    if "t" not in _cache:
        if "HORSE_TPL" not in bpy.data.collections:
            with bpy.data.libraries.load(DIR + "/horse.blend") as (src, dst):
                dst.collections, dst.actions = ["HORSE_TPL"], list(src.actions)
        c = bpy.data.collections["HORSE_TPL"]
        _cache["t"] = (c.objects["AnimalArmature"], c.objects["Horse"])
    return _cache["t"]


def _mat(key, base, mul=1., rough=.6):
    """Flat-colour copy of material `base` (any colour source), darkened by mul."""
    k = f"{base.name}_{key}"
    if k not in bpy.data.materials:
        c = base.get("tx_col") or list(base.diffuse_color)[:3]
        m = bpy.data.materials.new(k); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (c[0] * mul, c[1] * mul, c[2] * mul, 1); b.inputs["Roughness"].default_value = rough
    return bpy.data.materials[k]


def _link(scn, parent, name, a, b, r, mat):
    """Thin cylinder between points a, b given in `parent` space."""
    a, b = Vector(a), Vector(b); d = b - a
    me = bpy.data.meshes.new(name); import bmesh
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=r, radius2=r, depth=1)
    bm.to_mesh(me); bm.free(); me.materials.append(mat)
    o = bpy.data.objects.new(name, me); scn.collection.objects.link(o)
    o.parent, o.location, o.scale = parent, (a + b) / 2, (1, 1, d.length)
    o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = d.to_track_quat('Z', 'Y'); return o


def horse(scn, name, parent, loc, col, leather=None):
    """Returns {root, arm, body:[mesh], legs:[], ...}. root faces -Y, hooves on z=0. col: material (e.g. HORSE / HORSE2)."""
    tarm, tmesh = _tpl()
    root = bpy.data.objects.new(name, None); root.location, root.parent, root.empty_display_size = loc, parent, .2
    scn.collection.objects.link(root)
    arm = tarm.copy(); arm.name = name + "_rig"; arm.parent = root; arm.location = SHIFT
    arm.scale = tarm.scale * K; scn.collection.objects.link(arm)
    me = tmesh.copy(); me.name = name + "_body"; me.parent, me.location = root, SHIFT; scn.collection.objects.link(me)   # unit-scale mesh, skinned to arm
    for md in me.modifiers:
        if md.type == 'ARMATURE': md.object = arm
    sub = me.modifiers.new("smooth", 'SUBSURF'); sub.levels = sub.render_levels = 1    # rounds off the low-poly facets
    dark = _mat("dark", col, .45); mane = _mat("mane", col, .3, .5)
    remap = {"Main": col, "Main_Light": col, "Main_Dark": dark, "Hair": mane}
    for sl, m in zip(me.material_slots, tmesh.data.materials):
        sl.link = 'OBJECT'; sl.material = remap.get(m.name, m)
    H = {"root": root, "arm": arm, "body": [me], "legs": []}
    # harness: padded collar on the neck base, two traces back to the wagon bed front corners (x +-.6, y -.6, z .85 in
    # wagon space) and a strap to the tongue tip (0, -3, .9); points are relative to this root, so loc is subtracted
    lea = leather or bpy.data.materials.get("boot") or _mat("leather", col, .2)
    import bmesh
    me_c = bpy.data.meshes.new(name + "_collar"); bm = bmesh.new()
    R, r, N, M = .25, .07, 20, 8
    vs = [[bm.verts.new(((R + r * math.cos(b)) * math.cos(a), (R + r * math.cos(b)) * math.sin(a), r * math.sin(b)))
           for b in (2 * math.pi * j / M for j in range(M))] for a in (2 * math.pi * i / N for i in range(N))]
    for i in range(N):
        for j in range(M): bm.faces.new((vs[i][j], vs[(i + 1) % N][j], vs[(i + 1) % N][(j + 1) % M], vs[i][(j + 1) % M]))
    bm.to_mesh(me_c); bm.free(); me_c.shade_smooth(); me_c.materials.append(lea)
    col_o = bpy.data.objects.new(name + "_collar", me_c); scn.collection.objects.link(col_o)
    from mathutils import Matrix, Euler
    Mc = Matrix.Translation((0, Y0 - .72, 1.28)) @ Euler((.42, 0, 0)).to_matrix().to_4x4() @ Matrix.Diagonal((1, .8, 1, 1))
    bone = tarm.data.bones["Neck1"]    # collar rides the neck bone so it follows the body bob; parent inverse bakes the rest placement
    col_o.parent, col_o.parent_type, col_o.parent_bone = arm, 'BONE', bone.name
    col_o.matrix_parent_inverse = (arm.matrix_basis @ bone.matrix_local @ Matrix.Translation((0, bone.length, 0))).inverted() @ Mc
    ox, oy = -loc[0], -loc[1]
    for sx in (-1, 1):
        _link(scn, root, name + "_trace", (sx * .3, Y0 - .6, 1.2), (sx * .6 + ox, -.6 + oy, .85), .018, lea)
    _link(scn, root, name + "_strap", (-.2 * (ox / abs(ox or 1)), Y0 - .6, 1.2), (ox, -3 + oy, .9), .02, lea)
    return H


def trot(H, f0, f1, speed=None, phase=0, gait=None):
    """Loop a walk (or gallop when speed is high) over frames f0..f1 on an NLA strip. speed: ground speed in m/frame
    (the strip is time-scaled so the hooves match it); phase: frames to offset this horse's cycle."""
    arm = H["arm"]; gait = gait or ("Gallop" if speed and speed > .1 else "Walk")
    act = bpy.data.actions[gait]; sc = max(.4, min(2., GAIT[gait] / speed)) if speed else 1.
    ad = arm.animation_data or arm.animation_data_create()
    st = ad.nla_tracks.new().strips.new(gait, int(f0 - phase), act)
    st.scale = sc; st.repeat = (f1 - f0 + phase) / (act.frame_range[1] * sc) + 1; st.extrapolation = 'NOTHING'
    return st
