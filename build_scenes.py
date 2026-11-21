"""Builds the 8 scenes of the "10% Brain Myth" 3D short in Blender.
Run inside Blender:
    exec(open("build_scenes.py").read())
or from command line:
    blender -b --python build_scenes.py

Frame counts come directly from segments.json (calibrated to the user narration audio).
Total duration: 39.84s (1,196 frames @ 30 fps).
"""
import bpy, bmesh, json, math, random, os
from mathutils import Matrix, Quaternion, Vector

ROOT = os.path.dirname(os.path.abspath(__file__)) if "__file__" in locals() else os.getcwd()
SEGS = json.load(open(os.path.join(ROOT, "segments.json")))
FPS, pi = 30, math.pi
random.seed(42)

# ---------- reset scenes & datablocks ----------
_old = list(bpy.data.scenes)
for o in _old: o.name = "old_" + o.name
for coll in (bpy.data.objects, bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights, bpy.data.actions, bpy.data.worlds):
    for b in list(coll):
        try: coll.remove(b)
        except: pass

# ---------- materials ----------
def _bsdf(m):
    m.use_nodes = True
    return next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)

def M(name, col, rough=0.6, metallic=0.0):
    m = bpy.data.materials.get(name)
    if not m:
        m = bpy.data.materials.new(name)
        b = _bsdf(m)
        if b:
            b.inputs["Base Color"].default_value = (*col, 1)
            b.inputs["Roughness"].default_value = rough
            b.inputs["Metallic"].default_value = metallic
    return m

def Memit(name, col, strength=5.0):
    m = bpy.data.materials.get(name)
    if not m:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        nt = m.node_tree
        nt.nodes.clear()
        e = nt.nodes.new("ShaderNodeEmission")
        o = nt.nodes.new("ShaderNodeOutputMaterial")
        e.inputs["Color"].default_value = (*col, 1)
        e.inputs["Strength"].default_value = strength
        nt.links.new(e.outputs[0], o.inputs[0])
    return m

def Mglass(name, col=(0.8, 0.9, 1.0), ior=1.45):
    m = bpy.data.materials.get(name)
    if not m:
        m = bpy.data.materials.new(name)
        b = _bsdf(m)
        if b:
            b.inputs["Base Color"].default_value = (*col, 1)
            b.inputs["Roughness"].default_value = 0.1
            if "Transmission Weight" in b.inputs:
                b.inputs["Transmission Weight"].default_value = 0.9
            elif "Transmission" in b.inputs:
                b.inputs["Transmission"].default_value = 0.9
            b.inputs["IOR"].default_value = ior
    return m

# Color palette
BRAIN_MAT = M("brain_tissue", (0.85, 0.65, 0.70), rough=0.4)
BRAIN_DORMANT = M("brain_dormant", (0.25, 0.25, 0.28), rough=0.8)
NEURAL_GLOW = Memit("neural_glow", (0.1, 0.85, 1.0), strength=8.0)
GOLD_GLOW = Memit("gold_glow", (1.0, 0.75, 0.1), strength=6.0)
RED_LASER = Memit("red_laser", (1.0, 0.05, 0.05), strength=12.0)
RED_STAMP = M("red_stamp", (0.85, 0.1, 0.1), rough=0.7)
SKULL_GLASS = Mglass("skull_glass", (0.7, 0.85, 1.0))
STEEL = M("steel", (0.4, 0.42, 0.45), rough=0.3, metallic=0.9)
BRASS = M("brass", (0.75, 0.60, 0.25), rough=0.35, metallic=0.8)
PAPER = M("paper", (0.95, 0.94, 0.90), rough=0.8)
DARK_ROOM = M("dark_room", (0.05, 0.05, 0.07), rough=0.9)
WALL_MAT = M("wall_mat", (0.15, 0.18, 0.22), rough=0.7)
COUCH_MAT = M("couch_mat", (0.2, 0.35, 0.45), rough=0.6)

def sky(col1=(0.02, 0.03, 0.06), col2=(0.08, 0.12, 0.2)):
    w = bpy.data.worlds.new("Sky")
    w.use_nodes = True
    nt = w.node_tree
    bg = next(n for n in nt.nodes if n.type == 'BACKGROUND')
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[0].color = 0.2, (*col1, 1)
    ramp.color_ramp.elements[1].position, ramp.color_ramp.elements[1].color = 0.8, (*col2, 1)
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.8
    return w

WORLD = sky()

# ---------- procedural meshes ----------
def _obj(scn, name, bm, mat, loc=(0,0,0), rot=(0,0,0), scale=(1,1,1), parent=None, smooth=False):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if smooth:
        for p in me.polygons: p.use_smooth = True
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me)
    o.location, o.rotation_euler, o.scale, o.parent = loc, rot, scale, parent
    scn.collection.objects.link(o)
    return o

def box(scn, name, size, loc, mat, **k):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    return _obj(scn, name, bm, mat, loc, **k)

def cyl(scn, name, r, h, loc, mat, seg=24, **k):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=h)
    return _obj(scn, name, bm, mat, loc, smooth=True, **k)

def sph(scn, name, r, loc, mat, seg=24, **k):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg//2, radius=r)
    return _obj(scn, name, bm, mat, loc, smooth=True, **k)

def empty(scn, name, loc=(0,0,0), parent=None, rot=(0,0,0)):
    e = bpy.data.objects.new(name, None)
    e.location, e.rotation_euler, e.parent = loc, rot, parent
    e.empty_display_size = 0.2
    scn.collection.objects.link(e)
    return e

def make_procedural_brain(scn, name, loc=(0,0,0), scale=(1,1,1), lit_mode="full"):
    """Creates a stylized 3D brain with left/right hemispheres and gyri lobes."""
    root = empty(scn, name, loc=loc)
    root.scale = scale
    
    # Left and Right hemispheres
    for side, sign in [("L", -1), ("R", 1)]:
        # Frontal, Parietal, Occipital, Temporal lobe clusters
        clusters = [
            ((sign * 0.35,  0.30,  0.25), (0.45, 0.55, 0.40)),
            ((sign * 0.38, -0.25,  0.20), (0.42, 0.48, 0.38)),
            ((sign * 0.30, -0.65, -0.05), (0.35, 0.38, 0.32)),
            ((sign * 0.42, -0.10, -0.22), (0.38, 0.45, 0.30)),
            ((sign * 0.22, -0.45, -0.40), (0.30, 0.30, 0.28)),  # Cerebellum
        ]
        for i, (cloc, cscale) in enumerate(clusters):
            # Select material based on lit_mode
            if lit_mode == "10percent":
                mat = NEURAL_GLOW if (side == "L" and i == 0) else BRAIN_DORMANT
            elif lit_mode == "laser_target":
                mat = RED_LASER if (side == "L" and i == 1) else BRAIN_MAT
            elif lit_mode == "active_burst":
                mat = GOLD_GLOW if i % 2 == 0 else NEURAL_GLOW
            else:
                mat = BRAIN_MAT
                
            sph(scn, f"{name}_{side}_{i}", r=1.0, loc=cloc, mat=mat, parent=root, scale=cscale)
            
    # Brainstem
    cyl(scn, f"{name}_stem", r=0.14, h=0.6, loc=(0, -0.3, -0.6), mat=BRAIN_DORMANT if lit_mode == "10percent" else BRAIN_MAT, parent=root)
    return root

# ---------- animation helpers ----------
def kf(o, f, loc=None, rot=None, scale=None):
    if loc is not None: o.location = loc; o.keyframe_insert("location", frame=f)
    if rot is not None: o.rotation_euler = rot; o.keyframe_insert("rotation_euler", frame=f)
    if scale is not None: o.scale = scale; o.keyframe_insert("scale", frame=f)

EASE = {
    "io": lambda u: u * u * (3 - 2 * u),
    "out": lambda u: 1 - (1 - u) ** 3,
    "in": lambda u: u ** 3,
    "lin": lambda u: u
}

def camera(scn, keys, lens=28, name="Cam"):
    """Creates a tracking camera animated along path keys: [(frame, cam_pos, target_pos, ease)]"""
    cd = bpy.data.cameras.new(name); cd.lens = lens
    cam = bpy.data.objects.new(name, cd); scn.collection.objects.link(cam)
    tgt = empty(scn, name + "_tgt")
    c = cam.constraints.new('TRACK_TO')
    c.target, c.track_axis, c.up_axis = tgt, 'TRACK_NEGATIVE_Z', 'UP_Y'
    
    for (f0, p0, t0, _), (f1, p1, t1, e) in zip(keys, keys[1:]):
        for f in range(f0, f1):
            u = EASE[e or "io"]((f - f0) / (f1 - f0))
            kf(cam, f, loc=Vector(p0).lerp(Vector(p1), u))
            kf(tgt, f, loc=Vector(t0).lerp(Vector(t1), u))
            
    f_last, p_last, t_last, _ = keys[-1]
    kf(cam, f_last, loc=p_last); kf(tgt, f_last, loc=t_last)
    scn.camera = cam
    return cam, tgt

def new_scene(n):
    seg = SEGS[n - 1]
    scn = bpy.data.scenes.new(f"S{n:02d}")
    r = scn.render
    r.engine = 'BLENDER_EEVEE'
    r.resolution_x, r.resolution_y, r.fps = 1080, 1920, FPS
    scn.frame_start, scn.frame_end = 1, seg["frames"]
    scn.world = WORLD
    
    # Lighting: Key light + Rim light + Fill
    key_l = bpy.data.lights.new(f"Key_L_{n}", 'SUN')
    key_l.energy = 3.5; key_l.color = (1.0, 0.95, 0.9)
    key_o = bpy.data.objects.new(f"Key_{n}", key_l)
    key_o.rotation_euler = (math.radians(50), 0, math.radians(35))
    scn.collection.objects.link(key_o)
    
    rim_l = bpy.data.lights.new(f"Rim_L_{n}", 'AREA')
    rim_l.energy = 120.0; rim_l.size = 2.0; rim_l.color = (0.2, 0.7, 1.0)
    rim_o = bpy.data.objects.new(f"Rim_{n}", rim_l)
    rim_o.location = (0, 2.5, 1.5)
    rim_o.rotation_euler = (math.radians(-40), 0, math.radians(180))
    scn.collection.objects.link(rim_o)
    
    return scn

# ==============================================================================
# SCENE 01: The 10% Myth Anomaly (0.00s - 5.20s, 156 frames)
# Transparent head silhouette, only a small 10% frontal node glows cyan.
# ==============================================================================
s1 = new_scene(1)
sph(s1, "GlassHead", r=1.35, loc=(0, 0, 0), mat=SKULL_GLASS, scale=(1.0, 1.25, 1.4))
cyl(s1, "Neck", r=0.45, h=1.0, loc=(0, -0.1, -1.2), mat=SKULL_GLASS)
brain1 = make_procedural_brain(s1, "Brain10pct", loc=(0, 0, 0.1), scale=(0.7, 0.7, 0.7), lit_mode="10percent")

# Subtle floating idle animation
kf(brain1, 1, loc=(0, 0, 0.10))
kf(brain1, 78, loc=(0, 0, 0.14))
kf(brain1, 156, loc=(0, 0, 0.10))

# Camera slow push-in from wide to the 10% glowing node
camera(s1, [
    (1,   (0, -4.2, 0.4), (0, 0, 0.1), "out"),
    (156, (0.2, -2.6, 0.35), (0.2, 0.1, 0.25), "io")
], lens=35)

# ==============================================================================
# SCENE 02: Full Neural Explosion (5.20s - 10.40s, 156 frames)
# Massive electric pulses surge across the entire brain.
# ==============================================================================
s2 = new_scene(2)
brain2 = make_procedural_brain(s2, "BrainBurst", loc=(0, 0, 0), scale=(0.85, 0.85, 0.85), lit_mode="active_burst")

# Camera rotating around the glowing cerebrum
camera(s2, [
    (1,   (-2.5, -2.5, 1.2), (0, 0, 0), "out"),
    (156, (2.8, -2.2, 0.8),  (0, 0, 0), "io")
], lens=28)

# Dynamic pulse scale
kf(brain2, 1, scale=(0.82, 0.82, 0.82))
kf(brain2, 40, scale=(0.88, 0.88, 0.88))
kf(brain2, 80, scale=(0.83, 0.83, 0.83))
kf(brain2, 120, scale=(0.89, 0.89, 0.89))
kf(brain2, 156, scale=(0.85, 0.85, 0.85))

# ==============================================================================
# SCENE 03: The Weight vs Energy Scale (10.40s - 15.45s, 152 frames)
# Left pan: Tiny 2% brain. Right pan: Heavy 20% energy battery.
# ==============================================================================
s3 = new_scene(3)
# Scale balance frame
cyl(s3, "ScalePillar", r=0.08, h=2.5, loc=(0, 0, 0), mat=BRASS)
cyl(s3, "ScaleBase", r=0.8, h=0.1, loc=(0, 0, -1.25), mat=BRASS)
beam = cyl(s3, "Beam", r=0.05, h=2.6, loc=(0, 0, 1.2), mat=BRASS, rot=(0, math.radians(90), 0))

# Left Pan (Brain 2% mass)
left_pan = cyl(s3, "LeftPan", r=0.6, h=0.04, loc=(-1.2, 0, 0.5), mat=BRASS)
make_procedural_brain(s3, "TinyBrain", loc=(-1.2, 0, 0.75), scale=(0.35, 0.35, 0.35))

# Right Pan (20% Energy Battery)
right_pan = cyl(s3, "RightPan", r=0.6, h=0.04, loc=(1.2, 0, -0.1), mat=BRASS)
cyl(s3, "BatteryBody", r=0.25, h=0.8, loc=(1.2, 0, 0.35), mat=STEEL)
cyl(s3, "BatteryCore", r=0.22, h=0.7, loc=(1.2, 0, 0.35), mat=RED_LASER)

# Keyframe tilt showing battery weighing down heavily
kf(beam, 1, rot=(0, 0, 0))
kf(beam, 60, rot=(0, math.radians(-15), 0))
kf(beam, 152, rot=(0, math.radians(-18), 0))

camera(s3, [
    (1,   (0, -4.5, 0.8), (0, 0, 0.4), "out"),
    (152, (0, -3.6, 0.5), (0.2, 0, 0.3), "io")
], lens=32)

# ==============================================================================
# SCENE 04: Evolutionary Logic (15.45s - 22.25s, 204 frames)
# Human skull silhouette expanding in volume.
# ==============================================================================
s4 = new_scene(4)
skull = sph(s4, "EvoSkull", r=1.0, loc=(0, 0, 0), mat=M("bone", (0.9, 0.88, 0.8)), scale=(0.8, 1.0, 0.9))
brain4 = make_procedural_brain(s4, "EvoBrain", loc=(0, 0, 0.1), scale=(0.5, 0.5, 0.5))

# Morph expansion
kf(brain4, 1, scale=(0.5, 0.5, 0.5))
kf(brain4, 120, scale=(0.85, 0.85, 0.85))
kf(brain4, 204, scale=(0.9, 0.9, 0.9))

camera(s4, [
    (1,   (-2.8, -2.8, 0.5), (0, 0, 0.1), "out"),
    (204, (-1.8, -2.0, 0.2), (0, 0, 0.1), "io")
], lens=30)

# ==============================================================================
# SCENE 05: The 1% Micro-Damage (22.25s - 25.20s, 89 frames)
# Macro camera zooms into gyri, red laser targets 1% spot.
# ==============================================================================
s5 = new_scene(5)
brain5 = make_procedural_brain(s5, "CortexZoom", loc=(0, 0, 0), scale=(1.2, 1.2, 1.2), lit_mode="laser_target")
# Red target indicator line
cyl(s5, "TargetBeam", r=0.015, h=3.0, loc=(-0.4, -1.0, 0.3), mat=RED_LASER, rot=(math.radians(45), 0, 0))

camera(s5, [
    (1,  (-1.2, -1.8, 0.8), (-0.4, 0.1, 0.2), "out"),
    (89, (-0.6, -1.0, 0.4), (-0.4, 0.1, 0.2), "in")
], lens=45)

# ==============================================================================
# SCENE 06: Consequence - Soundwaves Shatter (25.20s - 30.65s, 163 frames)
# Character profile, soundwave arcs crumbling.
# ==============================================================================
s6 = new_scene(6)
sph(s6, "PersonSilhouette", r=1.0, loc=(-1.0, 0, 0), mat=M("dark_char", (0.1, 0.12, 0.15)), scale=(0.9, 1.1, 1.3))
# Soundwave rings
for i in range(4):
    w = cyl(s6, f"SoundRing_{i}", r=0.4 + i*0.25, h=0.03, loc=(-0.1 + i*0.4, 0, 0), mat=NEURAL_GLOW, rot=(0, math.radians(90), 0))
    kf(w, 1, scale=(1, 1, 1), loc=(-0.1 + i*0.4, 0, 0))
    kf(w, 80 + i*15, scale=(0.8, 0.8, 0.8), loc=(-0.1 + i*0.4, 0, -0.3 * i))

camera(s6, [
    (1,   (0, -3.8, 0.1), (0.2, 0, 0), "out"),
    (163, (0.5, -2.8, -0.1), (0.4, 0, -0.1), "io")
], lens=35)

# ==============================================================================
# SCENE 07: Vintage Myth Newspaper (30.65s - 34.45s, 114 frames)
# Newspaper spins in with big headline, red DEBUNKED stamp hits.
# ==============================================================================
s7 = new_scene(7)
paper = box(s7, "Newspaper", size=(1.8, 2.4, 0.02), loc=(0, 0, 0), mat=PAPER)
stamp = box(s7, "StampMark", size=(1.4, 0.4, 0.04), loc=(0, -0.05, 0.03), mat=RED_STAMP, rot=(0, 0, math.radians(-15)))

# Spinning in animation
kf(paper, 1, loc=(0, -6.0, 2.0), rot=(math.radians(30), 0, math.radians(180)))
kf(paper, 45, loc=(0, 0, 0), rot=(0, 0, 0))

# Stamp slam down at frame 50
kf(stamp, 1, scale=(0.001, 0.001, 0.001))
kf(stamp, 49, scale=(0.001, 0.001, 0.001))
kf(stamp, 52, scale=(1.2, 1.2, 1.2))
kf(stamp, 56, scale=(1.0, 1.0, 1.0))

camera(s7, [
    (1,   (0, -3.5, 0), (0, 0, 0), "out"),
    (114, (0, -2.8, 0), (0, 0, 0), "io")
], lens=28)

# ==============================================================================
# SCENE 08: Loop Payoff (34.45s - 39.84s, 162 frames)
# Living room: Person scrolling phone on sofa, 100% glowing radiant brain aura overhead.
# ==============================================================================
s8 = new_scene(8)
# Living room set
box(s8, "Floor", size=(6.0, 6.0, 0.1), loc=(0, 0, -1.0), mat=DARK_ROOM)
box(s8, "BackWall", size=(6.0, 0.1, 4.0), loc=(0, 2.5, 1.0), mat=WALL_MAT)
# Sofa
box(s8, "SofaBase", size=(2.6, 1.2, 0.6), loc=(0, 0.8, -0.6), mat=COUCH_MAT)
box(s8, "SofaBack", size=(2.6, 0.4, 1.2), loc=(0, 1.3, -0.1), mat=COUCH_MAT)
# Person silhouette sitting
sph(s8, "PersonHead", r=0.35, loc=(0, 0.7, 0.65), mat=M("char", (0.2, 0.22, 0.25)))
# 100% Glowing Radiant Brain floating above head
make_procedural_brain(s8, "FullActiveBrain", loc=(0, 0.7, 1.35), scale=(0.45, 0.45, 0.45), lit_mode="active_burst")

# Smartphone with screen light
phone = box(s8, "Phone", size=(0.2, 0.35, 0.02), loc=(0, 0.3, 0.35), mat=Memit("screen", (0.8, 0.9, 1.0), strength=4.0))

camera(s8, [
    (1,   (0, -3.2, 0.8), (0, 0.6, 0.9), "out"),
    (162, (0, -4.8, 1.2), (0, 0.6, 0.8), "io")  # Slow pull out loop
], lens=26)

print("Successfully configured all 8 scenes for 10% Brain Myth Short.")

# Save blend file if running in background
if bpy.app.background:
    blend_path = os.path.join(ROOT, "brain_myth.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"Saved mainfile to {blend_path}")
