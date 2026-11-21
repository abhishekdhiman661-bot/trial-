"""Builds the cast once with MPFB (MakeHuman for Blender) and caches it in assets/characters.blend.
Run: Blender -b --python characters.py   (build_scenes.py runs this itself when the cache is missing).
Needs the mpfb extension plus the asset packs in assets/packs/ unzipped into MPFB's user data folder.
Each character is a collection CH_<name>: one game_engine armature (faces -Y, feet at z=0, origin between the feet)
with skinned child meshes. Clothes are recoloured from their own textures (luminance x tint), two-tone garments
split at a rest-pose height so one MakeHuman outfit can read as e.g. white shirt + dark trousers."""
import bpy, os, gzip, math, numpy as np
from mathutils import Vector

ROOT = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else __import__("os").getcwd()
LIB = ROOT + "/assets/characters.blend"

# colours (linear), kept close to the old blockout palette so scenes read the same
WHITE, DARK, BROWN, TAN, DWOOD, BLACK = (1.0, 1.0, .97), (.06, .065, .09), (.40, .22, .09), (.75, .62, .40), (.20, .12, .07), (.025, .025, .03)
HAIR_BROWN, HAIR_DARK, HAIR_GREY, HAIR_BLOND = (.16, .08, .035), (.06, .035, .02), (.62, .62, .6), (.55, .4, .2)
BOOTS, BOWLER, TRILBY, WIDE = "culturalibre_male_boots", "culturalibre_cl_bowler_hat", "elvs_male_trilby_hat", "mindfront_fishing_hat_01"
SUIT, JACKET, STRIPES, GOWN = "male_casualsuit01", "male_casualsuit05", "male_casualsuit03", "maciekg_wizard_robe"

def man(skin, hair, hair_col, outfit, top, bottom, split=1.0, hat=None, hat_col=None, shoes=BOOTS, age=.5, weight=.5, height=1.8):
    return dict(gender=1.0, age=age, weight=weight, skin=skin, hair=hair, hair_col=hair_col, height=height,
                clothes=[(outfit, top, bottom, split), (shoes, None, None, 0)] + ([(hat, hat_col, None, 0)] if hat else []))

def woman(skin, hair, hair_col, gown_col, age=.5, height=1.68):
    return dict(gender=0.0, age=age, weight=.5, skin=skin, hair=hair, hair_col=hair_col, height=height,
                clothes=[(GOWN, gown_col, None, 0), ("toigo_ankle_boots_female", (.12, .08, .05), None, 0)])

CAST = {
    "Marion":  man("young_caucasian_male", "short02", HAIR_BROWN, SUIT, WHITE, DARK, split=1.0),
    "Cameron": man("young_caucasian_male2", "short04", HAIR_BROWN, JACKET, BROWN, (.10, .08, .06), split=.82, hat=TRILBY, hat_col=TAN),
    "Judge":   man("old_caucasian_male", "short01", HAIR_GREY, "male_elegantsuit01", BLACK, BLACK, shoes="shoes03", age=.9, weight=.6),
    "Sheriff": man("middleage_caucasian_male", "short03", HAIR_DARK, SUIT, TAN, (.14, .09, .05), split=1.0, hat=WIDE, hat_col=DWOOD, age=.7),
    "Bride":   woman("young_caucasian_female", "ponytail01", HAIR_DARK, (.9, .9, .87), age=.4),
    # townsfolk: shirt colours from the old FOLK palette, hats on the odd ones as before
    "Folk0": man("middleage_caucasian_male", "short02", HAIR_DARK, SUIT, (.6, .3, .3), (.12, .1, .08), age=.65),
    "Folk1": man("young_african_male", "short01", HAIR_DARK, JACKET, (.3, .45, .6), (.15, .12, .1), split=.82, hat=BOWLER, hat_col=(.05, .04, .035)),
    "Folk2": woman("middleage_caucasian_female", "braid01", HAIR_BROWN, (.55, .5, .3), age=.6),
    "Folk3": man("young_caucasian_male", "short03", HAIR_BLOND, STRIPES, None, (.25, .17, .1), split=1.0, hat=WIDE, hat_col=(.55, .45, .3)),
    "Folk4": woman("young_caucasian_female2", "bob02", HAIR_DARK, (.5, .4, .55), age=.45),
    "Folk5": man("old_caucasian_male", "short04", HAIR_GREY, SUIT, (.65, .6, .55), (.1, .1, .12), hat=BOWLER, hat_col=(.12, .1, .08), age=.85),
    "Folk6": man("middleage_african_male", "short02", HAIR_DARK, SUIT, (.4, .55, .4), (.2, .15, .1), age=.6),
    "Folk7": man("young_caucasian_male2", "short01", HAIR_BLOND, JACKET, (.3, .3, .32), (.12, .1, .08), split=.82, hat=TRILBY, hat_col=(.3, .22, .14)),
    "Folk8": woman("old_caucasian_female", "bob01", HAIR_GREY, (.25, .3, .4), age=.85, height=1.62),
}

def _mean_lum(img):
    """Alpha-weighted mean luminance of a texture, so tinting keeps the fabric detail but hits the target colour."""
    px = np.empty(len(img.pixels), np.float32); img.pixels.foreach_get(px); px = px.reshape(-1, 4)[::7]
    lum = px[:, :3] @ np.array([.2126, .7152, .0722], np.float32); w = px[:, 3] > .5
    return max(float(lum[w].mean()) if w.any() else float(lum.mean()), .05)

def recolor(obj, top, bottom=None, split=0.0, detail=.6):
    """Base colour = tint x (texture luminance / mean, flattened to `detail`); with bottom, rest-pose z < split (metres) gets the bottom tint."""
    for slot in obj.material_slots:
        m = slot.material; nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
        tex = next((n for n in nt.nodes if n.type == 'TEX_IMAGE' and n.name == 'diffuseTexture'), None)
        if tex is None or not bsdf.inputs["Base Color"].is_linked: continue
        src = bsdf.inputs["Base Color"].links[0].from_socket
        bw, gain, mix = nt.nodes.new("ShaderNodeRGBToBW"), nt.nodes.new("ShaderNodeMath"), nt.nodes.new("ShaderNodeMix")
        gain.operation, gain.inputs[1].default_value, gain.inputs[2].default_value = 'MULTIPLY_ADD', detail / _mean_lum(tex.image), 1 - detail
        mix.data_type, mix.blend_type, mix.inputs["Factor"].default_value = 'RGBA', 'MULTIPLY', 1
        nt.links.new(src, bw.inputs[0]); nt.links.new(bw.outputs[0], gain.inputs[0]); nt.links.new(gain.outputs[0], mix.inputs["B"])
        if bottom is None:
            mix.inputs["A"].default_value = (*top, 1)
        else:   # Generated coords are the undeformed bbox (0..1), so the split stays put when the rig moves
            zmin, zmax = min(v.co.z for v in obj.data.vertices), max(v.co.z for v in obj.data.vertices)
            tc, sep, step, two = nt.nodes.new("ShaderNodeTexCoord"), nt.nodes.new("ShaderNodeSeparateXYZ"), nt.nodes.new("ShaderNodeMath"), nt.nodes.new("ShaderNodeMix")
            step.operation, step.inputs[1].default_value = 'GREATER_THAN', (split - zmin) / (zmax - zmin)
            two.data_type = 'RGBA'; two.inputs["A"].default_value, two.inputs["B"].default_value = (*bottom, 1), (*top, 1)
            nt.links.new(tc.outputs["Generated"], sep.inputs[0]); nt.links.new(sep.outputs["Z"], step.inputs[0])
            nt.links.new(step.outputs[0], two.inputs["Factor"]); nt.links.new(two.outputs["Result"], mix.inputs["A"])
        nt.links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
        bsdf.inputs["Roughness"].default_value = .85

# ---------- facial shape keys (animated per instance by acting.py) ----------
# key -> {MPFB face-unit target: weight}; every key is a delta on the body mesh, and the small face meshes (brows, lashes,
# teeth, tongue) get the same keys derived from the nearest body vertices so they follow the skin. Eyes get look_* keys.
FACE_KEYS = {
    "open": {"mouth-open": 1}, "wide": {"mouth-part-later": 1}, "smile": {"mouth-corner-puller": 1}, "frown": {"mouth-depression": 1},
    "press": {"mouth-compression": 1}, "pucker": {"mouth-pursing": 1}, "snarl": {"mouth-upward-retraction": 1}, "talk": {"mouth-open": .5},
    "brow_up_L": {"eyebrows-left-up": 1, "eyebrows-left-extern-up": .4}, "brow_up_R": {"eyebrows-right-up": 1, "eyebrows-right-extern-up": .4},
    "brow_dn_L": {"eyebrows-left-down": 1}, "brow_dn_R": {"eyebrows-right-down": 1},
    "brow_in": {"eyebrows-left-inner-up": 1, "eyebrows-right-inner-up": 1},
    "wide_eyes": {"eye-left-opened-up": 1, "eye-right-opened-up": 1}, "squint": {"eye-left-slit": 1, "eye-right-slit": 1},
    "blink": {"eye-left-closure": 1, "eye-right-closure": 1},
}
LOOK_KEYS = {"look_l": (2, .5), "look_r": (2, -.5), "look_u": (0, -.35), "look_d": (0, .35)}   # eye mesh: axis, radians
_UNITS = {}

def _coords(me): a = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("co", a); return a.reshape(-1, 3)

def _unit(race, name, n, scale):
    k = (race, name)
    if k not in _UNITS:
        d = np.zeros((n, 3), np.float32)
        d0 = os.path.expanduser("~/Library/Application Support/Blender/5.2/extensions/blender_org/mpfb/data/targets/expression/units/")
        for l in gzip.open(f"{d0}{race}/{name}.target.gz", "rt"):
            p = l.split()
            if p and not p[0].startswith("#") and int(p[0]) < n: d[int(p[0])] = (float(p[1]), -float(p[3]), float(p[2]))   # MPFB's axis swap
        _UNITS[k] = d * scale
    return _UNITS[k]

def _add_key(obj, name, delta):
    me = obj.data
    if me.shape_keys is None: obj.shape_key_add(name="Basis", from_mix=False)
    kb = obj.shape_key_add(name=name, from_mix=False); kb.slider_max, kb.value = 2.0, 0.0
    kb.data.foreach_set("co", (_coords_basis(me) + delta).ravel()); return kb

def _coords_basis(me):
    a = np.empty(len(me.vertices) * 3, np.float32); me.shape_keys.reference_key.data.foreach_get("co", a); return a.reshape(-1, 3)

def add_face_keys(body, parts, eyes, race):
    from mathutils import kdtree
    from bl_ext.blender_org.mpfb.entities.objectproperties import GeneralObjectProperties as G
    sc = G.get_value("scale_factor", entity_reference=body); n = len(body.data.vertices)
    ref = _coords_basis(body.data); mix = ref.copy()
    for kb in body.data.shape_keys.key_blocks[1:]:
        if kb.value: mix += kb.value * (np.array([v.co[:] for v in kb.data], np.float32) - ref)
    body_d = {}
    for key, units in FACE_KEYS.items():
        body_d[key] = sum(w * _unit(race, u, n, sc) for u, w in units.items())
        _add_key(body, key, body_d[key])
    tree = kdtree.KDTree(n)
    for i, co in enumerate(mix): tree.insert(co, i)
    tree.balance()
    Mb = np.array(body.matrix_world.inverted())
    for o in parts:
        M = Mb @ np.array(o.matrix_world); co = _coords(o.data) @ M[:3, :3].T + M[:3, 3]
        bind = []
        for c in co:
            hit = tree.find_n(c, 4); w = np.array([1 / (d * d + 1e-8) for _, _, d in hit]); bind.append(([i for _, i, _ in hit], w / w.sum()))
        R = np.linalg.inv(M[:3, :3])
        for key, d in body_d.items():
            pd = np.array([(d[i] * w[:, None]).sum(0) for i, w in bind], np.float32) @ R.T
            if np.abs(pd).max() > 1e-5: _add_key(o, key, pd)
    co = _coords(eyes.data)   # two eyeballs, split at x=0; rotate each about its own centre
    for key, (ax, ang) in LOOK_KEYS.items():
        out = co.copy(); c, s = math.cos(ang), math.sin(ang)
        for side in (co[:, 0] > 0, co[:, 0] <= 0):
            ctr = co[side].mean(0); p = co[side] - ctr; a, b = [(1, 2), (0, 2), (0, 1)][ax][0], [(1, 2), (0, 2), (0, 1)][ax][1]
            q = p.copy(); q[:, a] = p[:, a] * c - p[:, b] * s; q[:, b] = p[:, a] * s + p[:, b] * c; out[side] = q + ctr
        _add_key(eyes, key, out - co)

def bake_body(body):
    """Fold the macro (age/gender/weight) shape keys into the basis and drop the invisible helper verts, so each per-instance copy
    of the body mesh only carries the face keys."""
    import bmesh
    me, ref = body.data, _coords_basis(body.data); mix = ref.copy(); kbs = me.shape_keys.key_blocks
    for kb in kbs[1:]:
        if kb.value: mix += kb.value * (np.array([v.co[:] for v in kb.data], np.float32) - ref)
    for kb in kbs[1:]:
        if kb.name in FACE_KEYS: kb.data.foreach_set("co", (np.array([v.co[:] for v in kb.data], np.float32) + mix - ref).ravel())
    kbs[0].data.foreach_set("co", mix.ravel()); me.vertices.foreach_set("co", mix.ravel())
    for kb in list(kbs[1:]):
        if kb.name not in FACE_KEYS: body.shape_key_remove(kb)
    bm = bmesh.new(); bm.from_mesh(me); gi = body.vertex_groups["body"].index; dl = bm.verts.layers.deform.active
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if gi not in v[dl]], context='VERTS'); bm.to_mesh(me); bm.free()

def build(name, c):
    from bl_ext.blender_org.mpfb.services.humanservice import HumanService
    info = HumanService._create_default_human_info_dict()
    info["phenotype"].update(gender=c["gender"], age=c["age"], weight=c["weight"], muscle=.55, height=.5)
    info.update(name=name, rig="game_engine", eyes="low-poly/low-poly.mhclo", eyebrows="eyebrow001/eyebrow001.mhclo",
                eyelashes="eyelashes01/eyelashes01.mhclo", teeth="teeth_base/teeth_base.mhclo", tongue="tongue01/tongue01.mhclo", hair=f"{c['hair']}/{c['hair']}.mhclo",
                skin_mhmat=f"{c['skin']}/{c['skin']}.mhmat", skin_material_type="ENHANCED_SSS",
                clothes=[f"{n}/{n}.mhclo" for n, *_ in c["clothes"]])
    st = HumanService.get_default_deserialization_settings(); st["subdiv_levels"] = 0
    body = HumanService.deserialize_from_dict(info, st)
    arm = body.parent
    kids = [o for o in bpy.data.objects if o.parent == arm]
    by_src = {o.name.split(".", 1)[1]: o for o in kids}
    hair = next(o for k, o in by_src.items() if k.startswith(c["hair"]))
    recolor(hair, c["hair_col"])
    for n, top, bottom, split in c["clothes"]:
        o = next(o for k, o in by_src.items() if k.startswith(n) or n.startswith(k))
        if top is not None or bottom is not None:
            recolor(o, top or (1, 1, 1), bottom, split, .25 if n == GOWN else .6)   # top None: keep the texture's own pattern but tint the bottom half
    for k, o in by_src.items():   # build_scenes uses these tags (glow on clothes, corpse drops hair/hat/eyes)
        o["part"] = ("body" if o is body else "hair" if o is hair else "face" if k.startswith(("low-poly", "eyebrow", "eyelash", "teeth", "tongue"))
                     else "hat" if k in (BOWLER, TRILBY, WIDE) else "clothes")
    for k, o in by_src.items():   # the shipped teeth texture renders near-black: plain ivory instead
        if k.startswith("teeth"):
            for slot in o.material_slots:
                b = next(n for n in slot.material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
                for l in list(b.inputs["Base Color"].links): slot.material.node_tree.links.remove(l)
                b.inputs["Base Color"].default_value = (.85, .8, .68, 1)
    face = [o for o in by_src.values() if o["part"] == "face"]
    add_face_keys(body, [o for o in face if not o.name.split(".", 1)[1].startswith("low-poly")], next(o for o in face if o.name.split(".", 1)[1].startswith("low-poly")),
                  "african" if "african" in c["skin"] else "caucasian")
    bake_body(body)
    # normalise height to the old blockout's ~1.8 m and put the boot soles on z=0
    dg = bpy.context.evaluated_depsgraph_get()
    def zs(o): e = o.evaluated_get(dg); return [(e.matrix_world @ v.co).z for v in e.data.vertices]
    top = max(zs(body)); arm.scale = (c["height"] / top,) * 3; bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
    arm.location.z -= min(min(zs(o)) for o in kids if o.type == 'MESH')
    col = bpy.data.collections.new("CH_" + name); bpy.context.scene.collection.children.link(col)
    for o in [arm] + kids:
        for uc in list(o.users_collection): uc.objects.unlink(o)
        col.objects.link(o)
    print("CHAR", name, round(c["height"] / top, 3), sum(len(o.data.polygons) for o in kids), flush=True)

def build_all(names=None):
    for o in list(bpy.data.objects): bpy.data.objects.remove(o)
    for name, c in CAST.items():
        if names is None or name in names: build(name, c)
    os.makedirs(os.path.dirname(LIB), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=LIB)

if __name__ == "__main__":
    build_all()
