"""Real PBR textures and better lighting for the hanged-man scenes ("toy-box realism").
In build_scenes.py, before the save:  import sys; sys.path.insert(0, ROOT); import textures; textures.upgrade()
Re-download the texture set (skips files that exist):  python3 textures.py
Textures: Poly Haven, CC0. Meshes have no UVs, so every image is box-projected in Object space at its real-world size."""
import json, math, os, re, urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
TEXDIR = os.path.join(ROOT, "assets", "textures")
RES = "1k"
MAPS = {"diff": "Diffuse", "rough": "Rough", "nor_gl": "nor_gl"}  # file suffix -> Poly Haven map key
# Poly Haven id -> real-world tile size in metres (from /info dimensions)
ASSETS = {
    "weathered_planks": 2.0, "rough_wood": .5, "blue_painted_planks": 1.0, "white_planks_clean": 1.8,
    "brown_mud_dry": 1.3, "withered_grass": 2.0, "leafy_grass": 2.0, "gravel_stones": 2.0, "rock_boulder_dry": 1.8,
    "fabric_pattern_07": .4, "denim_fabric": .1, "poly_wool_herringbone": .27, "brown_leather": .4,
    "hessian_230": .27, "rough_linen": .27,
}
UA = {"User-Agent": "texture-fetch/1.0"}


def tex_path(asset, m):
    return os.path.join(TEXDIR, f"{asset}_{m}_{RES}.jpg")


def fetch(assets=ASSETS):
    """Download the 1k JPG diffuse/roughness/GL-normal maps once into assets/textures."""
    os.makedirs(TEXDIR, exist_ok=True)
    for a in assets:
        need = [m for m in MAPS if not os.path.exists(tex_path(a, m))]
        if not need:
            continue
        with urllib.request.urlopen(urllib.request.Request(f"https://api.polyhaven.com/files/{a}", headers=UA), timeout=30) as r:
            files = json.load(r)
        for m in need:
            key = MAPS[m] if MAPS[m] in files else sorted(k for k in files if k.startswith("col"))[0]  # fabrics ship colour variants only
            url = files[key][RES]["jpg"]["url"]
            assert url.startswith("https://dl.polyhaven.org/"), url
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                data = r.read()
            tmp = tex_path(a, m) + ".part"
            open(tmp, "wb").write(data); os.replace(tmp, tex_path(a, m))
            print("fetched", os.path.basename(tex_path(a, m)), len(data))


# ---------------- materials ----------------
# name -> spec. tex: Poly Haven id; size: tile size in m; gray: use the texture's luminance only, so the old flat colour sets the hue;
# hue: 0..1 how far a colour texture is pulled to the old hue (1 = fully); con: texture contrast; nrm: normal strength;
# rough: (multiply, add) on the roughness map; big: ground plane, two scales mixed by noise to hide tiling.
S = dict
SPECS = {
    "wood": S(tex="weathered_planks", size=1.6, hue=.6, con=1.2, nrm=1.0),
    "darkwood": S(tex="rough_wood", size=.9, hue=.7, nrm=1.2),
    "teal": S(tex="blue_painted_planks", size=1.2, gray=True, con=.7, nrm=1.0, rough=(.8, .1)),
    "darkteal": S(tex="blue_painted_planks", size=1.2, gray=True, con=.7, nrm=1.0, rough=(.8, .1)),
    "hat": S(tex="blue_painted_planks", size=1.2, gray=True, con=.6, nrm=.8),           # buildings, trapdoor, wheel spokes
    "white": S(tex="rough_linen", size=.12, gray=True, con=.8, nrm=.6),                  # shirts, dress, judge's hair
    "blackcloth": S(tex="rough_linen", size=.12, gray=True, con=.8, nrm=.6),
    "coat": S(tex="poly_wool_herringbone", size=.2, gray=True, con=.9, nrm=.8),
    "navy": S(tex="poly_wool_herringbone", size=.12, gray=True, con=.9, nrm=.8),
    "pants": S(tex="denim_fabric", size=.12, gray=True, con=1.0, nrm=.8),
    "boot": S(tex="brown_leather", size=.25, gray=True, con=1.0, nrm=1.0, rough=(.8, 0)),
    "rope": S(tex="hessian_230", size=.08, gray=True, con=1.2, nrm=1.5),
    "dirt": S(tex="brown_mud_dry", size=1.6, hue=1, nrm=1.2, big=True),
    "prairie": S(tex="withered_grass", size=2.0, hue=.6, nrm=1.0, big=True),
    "grass": S(tex="leafy_grass", size=2.0, hue=.7, nrm=1.0, big=True),
    "gravel": S(tex="gravel_stones", size=1.4, hue=.8, con=1.3, nrm=1.2, big=True),
    "rock": S(tex="rock_boulder_dry", size=.8, hue=.5, nrm=1.5),
    **{f"folk{i}": S(tex="fabric_pattern_07", size=.15, gray=True, con=.5, nrm=.6) for i in range(6)},
    # procedural (no image)
    "steel": S(proc="brushed"), "water": S(proc="water"), "paper": S(proc="paper"),
    "horse": S(proc="fur"), "horse2": S(proc="fur"), "hair": S(proc="fur"),
}
# (object-name pattern, material, variant): small worn items that share a set material get their own look
VARIANTS = [
    (r"brim|crown|hat", "hat", S(tex="brown_leather", size=.15, gray=True, con=.5, nrm=.4, rough=(.3, .65))),   # felt hats
    (r"brim|crown|hat", "darkwood", S(tex="brown_leather", size=.15, gray=True, con=.5, nrm=.4, rough=(.3, .65))),
    (r"torso|arm|skirt|leg|dress|sleeve", "hat", S(tex="rough_linen", size=.12, gray=True, con=.8, nrm=.6)),  # sheriff's shirt
    (r"tail", "darkwood", S(proc="fur")),
    (r"church|steeple", "white", S(tex="white_planks_clean", size=1.8, gray=True, con=1.0, nrm=1.0)),          # painted clapboard
]


def _orig_colour(m):
    """Flat colour M() gave the material, remembered so a second upgrade() tints from the same value."""
    if "tx_col" not in m:
        b = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None) if m.node_tree else None
        m["tx_col"] = list(b.inputs["Base Color"].default_value)[:3] if b else list(m.diffuse_color)[:3]
    return tuple(m["tx_col"])


_MEANS = {}
def _mean(img):
    """Mean linear RGB of an image (for tinting it to the old flat colour)."""
    if img.name not in _MEANS:
        import numpy as np
        px = np.empty(len(img.pixels), np.float32); img.pixels.foreach_get(px)
        rgb = px.reshape(-1, 4)[::7, :3]
        rgb = np.where(rgb <= .04045, rgb / 12.92, ((rgb + .055) / 1.055) ** 2.4)  # pixels are sRGB-encoded bytes
        _MEANS[img.name] = tuple(float(v) for v in rgb.mean(0))
    return _MEANS[img.name]


def _lum(c): return .2126 * c[0] + .7152 * c[1] + .0722 * c[2]


class _Tree:
    def __init__(s, m):
        m.use_nodes = True; s.nt = m.node_tree; s.nt.nodes.clear(); s.x = 0
    def n(s, kind, **props):
        node = s.nt.nodes.new(kind); s.x += 160; node.location = (s.x - 2000, 0)
        for k, v in props.items(): setattr(node, k, v)
        return node
    def ln(s, a, b): s.nt.links.new(a, b)
    def mix(s, fac, a, b, blend="MIX"):
        m = s.n("ShaderNodeMix", data_type="RGBA", blend_type=blend, clamp_factor=False)
        for i, v in ((0, fac), (6, a), (7, b)):
            (s.ln(v, m.inputs[i]) if hasattr(v, "links") else setattr(m.inputs[i], "default_value", v))
        return m.outputs[2]
    def math(s, op, a, b):
        m = s.n("ShaderNodeMath", operation=op)
        for i, v in ((0, a), (1, b)):
            (s.ln(v, m.inputs[i]) if hasattr(v, "links") else setattr(m.inputs[i], "default_value", v))
        return m.outputs[0]


def _load(asset, m):
    import bpy
    p = tex_path(asset, m)
    if not os.path.exists(p):
        return None
    img = bpy.data.images.load(p, check_existing=True)
    img.colorspace_settings.name = "sRGB" if m == "diff" else "Non-Color"
    return img


def _sample(t, img, vec):
    n = t.n("ShaderNodeTexImage", image=img, projection="BOX", projection_blend=.3)
    t.ln(vec, n.inputs["Vector"]); return n.outputs["Color"]


def _build(m, spec, tint):
    import bpy
    t = _Tree(m)
    out, b = t.n("ShaderNodeOutputMaterial"), t.n("ShaderNodeBsdfPrincipled")
    t.ln(b.outputs[0], out.inputs["Surface"]); out.location = (400, 0); b.location = (100, 0)
    obj = t.n("ShaderNodeTexCoord").outputs["Object"]
    imgs = {k: _load(spec.get("tex", ""), k) for k in MAPS} if "tex" in spec else {}
    if "proc" in spec or not imgs.get("diff"):
        return _procedural(t, b, obj, spec.get("proc", "plain"), tint)
    tile = t.n("ShaderNodeMapping"); tile.inputs["Scale"].default_value = (1 / spec["size"],) * 3; t.ln(obj, tile.inputs["Vector"])
    vecs = [tile.outputs[0]]
    if spec.get("big"):
        far = t.n("ShaderNodeMapping"); t.ln(obj, far.inputs["Vector"])
        far.inputs["Scale"].default_value = (1 / (spec["size"] * 3.3),) * 3; far.inputs["Rotation"].default_value[2] = .7
        far.inputs["Location"].default_value = (.37, .61, 0)
        vecs.append(far.outputs[0])
        nz = t.n("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = .06; nz.inputs["Detail"].default_value = 3; t.ln(obj, nz.inputs["Vector"])
        ramp = t.n("ShaderNodeMapRange"); ramp.inputs[1].default_value, ramp.inputs[2].default_value = .38, .62
        t.ln(nz.outputs["Fac"], ramp.inputs[0]); blend = ramp.outputs[0]
    def get(k):
        s = [_sample(t, imgs[k], v) for v in vecs]
        return t.mix(blend, s[0], s[1]) if len(s) > 1 else s[0]
    mean = _mean(imgs["diff"])
    col = get("diff")
    if spec.get("gray"):
        bw = t.n("ShaderNodeRGBToBW"); t.ln(col, bw.inputs[0]); col = bw.outputs[0]; mean = (_lum(mean),) * 3
    col = t.mix(spec.get("con", 1), (*mean, 1), col)                                # contrast around the mean
    h = 1 if spec.get("gray") else spec.get("hue", 1)
    k = _lum(tint) / max(_lum(mean), 1e-4)
    gain = [h * tint[i] / max(mean[i], 1e-4) + (1 - h) * k for i in range(3)]
    col = t.mix(1, col, (*gain, 1), "MULTIPLY")
    if spec.get("big"):                                                             # large soft patches, lighter/darker
        nz2 = t.n("ShaderNodeTexNoise"); nz2.inputs["Scale"].default_value = .015; t.ln(obj, nz2.inputs["Vector"])
        vr = t.n("ShaderNodeMapRange"); vr.inputs[3].default_value, vr.inputs[4].default_value = .82, 1.15
        t.ln(nz2.outputs["Fac"], vr.inputs[0])
        col = t.mix(1, col, vr.outputs[0], "MULTIPLY")
    t.ln(col, b.inputs["Base Color"])
    if imgs.get("rough"):
        rm, ra = spec.get("rough", (1, 0))
        t.ln(t.math("ADD", t.math("MULTIPLY", get("rough"), rm), ra), b.inputs["Roughness"])
    if imgs.get("nor_gl"):
        nm = t.n("ShaderNodeNormalMap"); nm.inputs["Strength"].default_value = spec.get("nrm", 1)
        t.ln(get("nor_gl"), nm.inputs["Color"]); t.ln(nm.outputs[0], b.inputs["Normal"])
    b.inputs["Specular IOR Level"].default_value = .4


def _procedural(t, b, obj, kind, tint):
    """Materials that need no image: brushed steel, water, paper, short fur/hair."""
    b.inputs["Base Color"].default_value = (*tint, 1)
    def noise(scale, detail=4, stretch=(1, 1, 1)):
        mp = t.n("ShaderNodeMapping"); mp.inputs["Scale"].default_value = stretch; t.ln(obj, mp.inputs["Vector"])
        nz = t.n("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = scale; nz.inputs["Detail"].default_value = detail
        t.ln(mp.outputs[0], nz.inputs["Vector"]); return nz.outputs["Fac"]
    def bump(h, strength, dist=.01):
        bp = t.n("ShaderNodeBump"); bp.inputs["Strength"].default_value = strength; bp.inputs["Distance"].default_value = dist
        t.ln(h, bp.inputs["Height"]); t.ln(bp.outputs[0], b.inputs["Normal"])
    if kind == "brushed":                                  # streaks along X (the rails run along X)
        f = noise(40, 6, (.05, 25, 25))
        b.inputs["Metallic"].default_value = 1
        t.ln(t.math("ADD", t.math("MULTIPLY", f, .3), .18), b.inputs["Roughness"]); bump(f, .15, .002)
        b.inputs["Base Color"].default_value = (*[min(1, c * 1.6) for c in tint], 1)
    elif kind == "water":
        b.inputs["Roughness"].default_value = .04; b.inputs["Coat Weight"].default_value = .5
        bump(noise(1.5, 6), .25, .05)
    elif kind == "paper":
        b.inputs["Roughness"].default_value = .85; bump(noise(250, 8), .08, .001)
    elif kind == "fur":                                    # fine strands + soft sheen + mottled colour
        b.inputs["Roughness"].default_value = .75
        b.inputs["Sheen Weight"].default_value = .6; b.inputs["Sheen Roughness"].default_value = .4
        b.inputs["Sheen Tint"].default_value = (*[min(1, c * 1.8 + .1) for c in tint], 1)
        mott = t.n("ShaderNodeMapRange"); mott.inputs[3].default_value, mott.inputs[4].default_value = .8, 1.15
        t.ln(noise(4, 3), mott.inputs[0])
        t.ln(t.mix(1, (*tint, 1), mott.outputs[0], "MULTIPLY"), b.inputs["Base Color"])
        bump(noise(300, 2, (1, 1, .05)), .35, .003)
    else:
        b.inputs["Roughness"].default_value = .7


def _material(name, spec, base=None):
    import bpy
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name); m["tx_col"] = list(_orig_colour(base))
    _build(m, spec, _orig_colour(m))
    return m


# ---------------- lighting ----------------
def _light(scn, key, kind, loc, aim, energy, size=1.0, colour=(1, 1, 1)):
    """Add (or update, on a second call) a light named TX_<scene>_<key> pointed from loc at aim."""
    import bpy
    from mathutils import Vector
    name = f"TX_{scn.name}_{key}"
    o = bpy.data.objects.get(name)
    if o is None:
        o = bpy.data.objects.new(name, bpy.data.lights.new(name, kind)); scn.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector(aim) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    d = o.data; d.energy, d.color = energy, colour
    if kind == "AREA": d.size = size
    else: d.shadow_soft_size = size
    return o


# per scene: sun (elevation deg, azimuth deg the light TRAVELS toward measured from +Y toward -X, energy) and extra lights.
# Cameras mostly look toward +Y, so the key comes from the camera's right and slightly behind the subject: it models shapes,
# throws shadows sideways across the frame and leaves the far sides of faces darker than the lit side.
WARM, COOL = (1, .93, .84), (.85, .93, 1)
SUN = {  # scene: (elevation, azimuth, strength)
    "S01": (34, 65, 5.5), "S02": (32, 75, 5.5), "S03": (34, 70, 5.5), "S04": (36, 60, 5.5), "S05": (50, 70, 1.8),
    "S06": (36, 65, 5.5), "S07": (30, 70, 5.5), "S08": (38, 35, 5.5), "S09": (34, 60, 4.3), "S10": (36, 50, 4.0),
}
RIM_NAMES = ("Marion", "Cameron", "Judge", "Bride")   # empties the character meshes hang under
RIM = {"S05": 2.5, "S10": 3.0}                         # rim strength override (default 3.5)
FILL = .45       # sky strength seen by surfaces (the camera still sees the full-strength sky)
CAM_FSTOP = 1.4  # shallower depth of field than the builder's f/2: soft background, subject on the track-to target stays sharp
LIGHTS = {
    "S05": [("ceiling", "AREA", (0, 1.5, 7), (0, 1.5, 0), 200, 8, WARM),
            ("judge", "AREA", (1.6, .4, 3.6), (0, 4.0, 2.2), 150, 1.5, WARM)],
    "S10": [("lamp", "AREA", (100.6, -.6, 2.4), (100, 0, .95), 40, 1.2, WARM),
            ("fill", "AREA", (98.5, -1.5, 2.0), (100, 0, .95), 20, 2, COOL)],
}


def _sun_rot(elev, az):
    """Euler rotation of a sun whose light travels toward azimuth az (0 = +Y, 90 = -X) and downward by elev degrees."""
    return (math.radians(90 - elev), 0, math.radians(az))


def _descendants(o):
    for c in o.children:
        yield c
        yield from _descendants(c)


def _rim(scn):
    """Cool back light linked only to the main characters (light linking), so the ground and sets are untouched."""
    import bpy
    roots = [o for o in scn.objects if o.type == 'EMPTY' and re.sub(r'\.\d+$', '', o.name) in RIM_NAMES]   # names carry .001 suffixes across scenes
    name = f"TX_{scn.name}_rim"
    o = bpy.data.objects.get(name)
    if not roots:
        if o: bpy.data.objects.remove(o)
        return
    if o is None:
        o = bpy.data.objects.new(name, bpy.data.lights.new(name, 'SUN')); scn.collection.objects.link(o)
    o.rotation_euler = (math.radians(62), 0, math.radians(-165))   # travels toward the camera (-Y) from behind, slightly from the left
    o.data.energy, o.data.color, o.data.angle = RIM.get(scn.name, 3.5), (.85, .93, 1), math.radians(6)
    cn = f"TX_{scn.name}_rimrecv"
    coll = bpy.data.collections.get(cn) or bpy.data.collections.new(cn)
    for ch in [m for r in roots for m in _descendants(r) if m.type == 'MESH']:
        if ch.name not in coll.objects: coll.objects.link(ch)
    o.light_linking.receiver_collection = coll


def _grade(scn, cams):
    """Contrast: a gentle S-curve on the display transform (Standard keeps the sky's saturated cyan), plus shallower DoF."""
    vs = scn.view_settings; vs.view_transform = 'Standard'; vs.use_curve_mapping = True
    c = vs.curve_mapping; cv = c.curves[3]       # combined RGB curve
    pts = [(0, 0), (.25, .2), (.5, .5), (.75, .8), (1, 1)]
    while len(cv.points) > 2: cv.points.remove(cv.points[1])
    cv.points[0].location, cv.points[1].location = pts[0], pts[-1]
    for p in pts[1:-1]: cv.points.new(*p)
    c.update()
    for cam in cams: cam.data.dof.aperture_fstop = CAM_FSTOP


def _eevee(scn):
    e = scn.eevee
    for k, v in (("use_raytracing", True), ("ray_tracing_method", "SCREEN"), ("use_fast_gi", True),
                 ("fast_gi_method", "GLOBAL_ILLUMINATION"), ("fast_gi_distance", 3.0), ("use_shadows", True),
                 ("shadow_ray_count", 2), ("shadow_step_count", 8)):
        if hasattr(e, k): setattr(e, k, v)
    if hasattr(e, "ray_tracing_options"): e.ray_tracing_options.resolution_scale = "2"


def upgrade(scenes=None):
    """Textured PBR materials, tuned sun, fill lights and Eevee quality options. Safe to call twice."""
    import bpy
    try:
        fetch()                                            # no network when the files already exist
    except Exception as ex:
        print("textures: fetch failed, missing maps fall back to procedural", ex)
    for name, spec in SPECS.items():
        if bpy.data.materials.get(name):
            _material(name, spec)
    scns = [bpy.data.scenes[n] for n in scenes] if scenes else [s for s in bpy.data.scenes if re.fullmatch(r"S\d\d", s.name)]
    for pat, base, spec in VARIANTS:
        bm = bpy.data.materials.get(base)
        if bm is None:
            continue
        var = None
        for scn in scns:
            for o in scn.objects:
                if o.type != "MESH" or not re.search(pat, o.name, re.I):
                    continue
                for i, mm in enumerate(o.data.materials):
                    if mm == bm:
                        var = var or _material(f"{base}__{pat.split('|')[0]}", spec, bm)
                        o.data.materials[i] = var
    for w in {s.world for s in scns if s.world and s.world.use_nodes}:   # sky: full strength to the camera, FILL as a light
        add = next((n for n in w.node_tree.nodes if n.type == "MATH" and n.operation != "MULTIPLY"), None)
        mul = next((n for n in w.node_tree.nodes if n.type == "MATH" and n.operation == "MULTIPLY"), None)
        if add and mul: mul.inputs[1].default_value = 1 - FILL; add.inputs[1].default_value = FILL
    for scn in scns:
        _eevee(scn)
        el, az, en = SUN.get(scn.name, (32, 70, 4.5))
        for o in scn.objects:
            if o.type == "LIGHT" and o.data.type == "SUN" and not o.name.startswith("TX_"):
                o.rotation_euler = _sun_rot(el, az)
                o.data.angle = math.radians(2.5); o.data.energy = en; o.data.color = (1, .92, .8)
        _rim(scn)
        _grade(scn, [o for o in scn.objects if o.type == "CAMERA"])
        for key, kind, loc, aim, w, size, col in LIGHTS.get(scn.name, []):
            _light(scn, key, kind, loc, aim, w, size, col)


if __name__ == "__main__":
    fetch()
