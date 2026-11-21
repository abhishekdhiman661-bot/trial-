"""Props and set dressing for build_scenes.py: real-looking gallows/noose, buckboard wagon, storefronts, church, courtroom, river bed,
plus dress(scn) which fills each scene with rocks, grass, trees, fences, poles, mesas and background buildings.
Usage in build_scenes.py (after `from horses import horse, trot`):  import sets; sets.init(globals()); from sets import *
All geometry is built as plain Python lists (class G) and merged into a few objects per scene, so render cost stays low.
Names matter to textures.py: never put 'hat', 'tail', 'arm', 'leg', 'skirt', 'dress' in an object name that uses the hat/darkwood material.
shortcut: everything is procedural (no downloaded CC0 meshes), so no assets/props/SOURCE.txt is needed."""
import bpy, math, random as _rnd
from mathutils import Matrix, Vector, Euler, noise

pi = math.pi
R = _rnd.Random(1)


def init(g):
    gl = globals()
    for k in ("M", "kf", "empty", "box", "cyl", "sph", "horse", "pose", "SEATED", "WOOD", "DWOOD", "ROPE", "HAT", "TEAL", "DTEAL", "WHITE",
              "STEEL", "ROCK", "HORSE", "HORSE2", "GRASS", "PRAIRIE", "DIRT", "WATER", "PAPER", "INK", "BOOT", "BLACKM"):
        gl[k] = g[k]
    gl["GLASS"] = M("glass", (.45, .6, .7), .05)
    gl["CREAM"] = M("cream", (.82, .76, .6))
    gl["GOLD"] = M("gold", (.8, .6, .15), .3)
    gl["RED"] = M("red", (.5, .12, .1))
    gl["FLAGR"], gl["FLAGB"], gl["FLAGW"] = M("flagred", (.62, .08, .1)), M("flagblue", (.08, .12, .4)), M("flagwhite", (.9, .9, .88))
    gl["RUG"] = M("rug", (.35, .08, .08), .95)
    gl["PINE"] = M("pine", (.08, .22, .12), .9)
    gl["FARHILL"] = M("farhill", (.45, .58, .52), .95)
    gl["GRAVEL"] = M("gravel", (.45, .43, .38))
    gl["REED"] = M("reedmat", (.55, .52, .27), .8)
    gl["LIT"] = _emit_mat("windowlit", (1, .93, .75), 2.2)
    gl["SKYWIN"] = _emit_mat("skywindow", (.75, .9, 1), 3.0)
    gl["MESA"] = _mesa_mat()


def _emit_mat(name, col, strength):
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    e, o = nt.nodes.new("ShaderNodeEmission"), nt.nodes.new("ShaderNodeOutputMaterial")
    e.inputs["Color"].default_value = (*col, 1); e.inputs["Strength"].default_value = strength
    nt.links.new(e.outputs[0], o.inputs[0]); return m


def _mesa_mat():
    m = bpy.data.materials.get("mesa")
    if m: return m
    m = bpy.data.materials.new("mesa"); m.use_nodes = True; nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'); b.inputs["Roughness"].default_value = .95
    tc, wv, ramp = nt.nodes.new("ShaderNodeTexCoord"), nt.nodes.new("ShaderNodeTexWave"), nt.nodes.new("ShaderNodeValToRGB")
    wv.wave_type, wv.bands_direction = 'BANDS', 'Z'
    wv.inputs["Scale"].default_value, wv.inputs["Distortion"].default_value, wv.inputs["Detail"].default_value = .12, 3, 3
    ramp.color_ramp.elements[0].color, ramp.color_ramp.elements[1].color = (.5, .28, .2, 1), (.72, .45, .32, 1)
    nt.links.new(tc.outputs["Object"], wv.inputs["Vector"]); nt.links.new(wv.outputs["Color"], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], b.inputs["Base Color"]); return m


# ====================================================================== geometry accumulator
CUBE_V = [(-.5, -.5, -.5), (.5, -.5, -.5), (.5, .5, -.5), (-.5, .5, -.5), (-.5, -.5, .5), (.5, -.5, .5), (.5, .5, .5), (-.5, .5, .5)]
CUBE_F = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
AXM = {'Z': Matrix.Identity(3), 'X': Matrix.Rotation(pi / 2, 3, 'Y'), 'Y': Matrix.Rotation(-pi / 2, 3, 'X')}
_ICO = {}


def ico(sub):
    if sub not in _ICO:
        import bmesh
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1)
        idx = {v: i for i, v in enumerate(bm.verts)}
        _ICO[sub] = ([tuple(v.co) for v in bm.verts], [tuple(idx[v] for v in f.verts) for f in bm.faces]); bm.free()
    return _ICO[sub]


class G:
    """Pure-python mesh: vertices, faces, per-face material and smooth flag. Merge many props into one object."""
    def __init__(s): s.v, s.f, s.m, s.s = [], [], [], []

    def _emit(s, pts, faces, mat, smooth, loc=(0, 0, 0), rot=(0, 0, 0), sc=None):
        Rm = rot if isinstance(rot, Matrix) else Euler(rot, 'XYZ').to_matrix()
        if sc is not None:
            Rm = Rm @ Matrix.Diagonal(sc if hasattr(sc, "__len__") else (sc, sc, sc))
        loc = Vector(loc); n = len(s.v)
        s.v += [tuple(Rm @ Vector(p) + loc) for p in pts]
        s.f += [tuple(i + n for i in f) for f in faces]; s.m += [mat] * len(faces); s.s += [smooth] * len(faces)

    def add(s, o, loc=(0, 0, 0), rot=(0, 0, 0), sc=None):
        Rm = rot if isinstance(rot, Matrix) else Euler(rot, 'XYZ').to_matrix()
        if sc is not None: Rm = Rm @ Matrix.Diagonal(sc if hasattr(sc, "__len__") else (sc, sc, sc))
        loc = Vector(loc); n = len(s.v)
        s.v += [tuple(Rm @ Vector(p) + loc) for p in o.v]
        s.f += [tuple(i + n for i in f) for f in o.f]; s.m += o.m; s.s += o.s

    def box(s, size, loc, mat, rot=(0, 0, 0)):
        s._emit([(x * size[0], y * size[1], z * size[2]) for x, y, z in CUBE_V], CUBE_F, mat, False, loc, rot)

    def beam(s, a, b, w, h, mat):
        a, b = Vector(a), Vector(b); d = b - a
        q = d.to_track_quat('Y', 'X' if abs(d.normalized().z) > .95 else 'Z')
        s.box((w, d.length, h), (a + b) / 2, mat, q.to_euler())

    def poly(s, pts, mat, smooth=False):
        s._emit(pts, [tuple(range(len(pts)))], mat, smooth)

    def lathe(s, prof, loc, mat, axis='Z', seg=12, rot=(0, 0, 0), smooth=True, sc=None, closed=False, jitter=0, caps=True):
        """prof: [(radius, height)] bottom to top; radius 0 makes an apex; closed joins last to first (ring/torus)."""
        pts, rings = [], []
        for r, z in prof:
            if r < 1e-6: rings.append([len(pts)]); pts.append((0, 0, z))
            else:
                rings.append(list(range(len(pts), len(pts) + seg)))
                for i in range(seg):
                    a = 2 * pi * i / seg; p = Vector((r * math.cos(a), r * math.sin(a), z))
                    if jitter:
                        k = 1 + jitter * noise.noise(p * 1.5 + loc_seed(loc)); p = Vector((p.x * k, p.y * k, z))
                    pts.append(tuple(p))
        faces = []
        pairs = list(zip(rings, rings[1:])) + ([(rings[-1], rings[0])] if closed else [])
        for a, b in pairs:
            for i in range(seg):
                j = (i + 1) % seg
                if len(a) == 1: faces.append((a[0], b[j], b[i]))
                elif len(b) == 1: faces.append((a[i], a[j], b[0]))
                else: faces.append((a[i], a[j], b[j], b[i]))
        sm = [smooth] * len(faces)
        if caps and not closed:
            for ring, up in ((rings[0], False), (rings[-1], True)):
                if len(ring) > 1:
                    base = len(pts); pts += [pts[i] for i in ring]; ids = list(range(base, base + seg))
                    faces.append(tuple(ids if up else ids[::-1])); sm.append(False)
        Rm = (rot if isinstance(rot, Matrix) else Euler(rot, 'XYZ').to_matrix()) @ AXM[axis]
        n = len(s.v); M3 = Rm @ (Matrix.Diagonal(sc if hasattr(sc, "__len__") else (sc, sc, sc)) if sc is not None else Matrix.Identity(3))
        s.v += [tuple(M3 @ Vector(p) + Vector(loc)) for p in pts]
        s.f += [tuple(i + n for i in f) for f in faces]; s.m += [mat] * len(faces); s.s += sm

    def cyl(s, r, h, loc, mat, r2=None, axis='Z', seg=12, rot=(0, 0, 0), smooth=True):
        s.lathe([(r, -h / 2), (r if r2 is None else r2, h / 2)], loc, mat, axis, seg, rot, smooth)

    def tube(s, pts, r, mat, sides=6, radii=None, closed=False, smooth=True, cap=True):
        P = [Vector(p) for p in pts]; n = len(P)
        T = []
        for i in range(n):
            a, b = P[(i - 1) % n] if closed else P[max(i - 1, 0)], P[(i + 1) % n] if closed else P[min(i + 1, n - 1)]
            T.append((b - a).normalized())
        up = Vector((0, 0, 1)) if abs(T[0].z) < .9 else Vector((1, 0, 0))
        N = T[0].cross(up).normalized(); frames = []
        for t in T:
            N = (N - t * N.dot(t)).normalized(); frames.append((N.copy(), t.cross(N)))
        pts_o, base = [], len(s.v)
        for i, p in enumerate(P):
            rr = r * (radii[i] if radii else 1); nn, bb = frames[i]
            for k in range(sides):
                a = 2 * pi * k / sides; pts_o.append(tuple(p + rr * (math.cos(a) * nn + math.sin(a) * bb)))
        faces = []
        for i in range(n if closed else n - 1):
            i2 = (i + 1) % n
            for k in range(sides):
                k2 = (k + 1) % sides
                faces.append((i * sides + k, i * sides + k2, i2 * sides + k2, i2 * sides + k))
        sm = [smooth] * len(faces)
        if cap and not closed:
            faces.append(tuple(range(sides - 1, -1, -1))); sm.append(False)
            faces.append(tuple(range((n - 1) * sides, n * sides))); sm.append(False)
        s.v += pts_o; s.f += [tuple(i + base for i in f) for f in faces]; s.m += [mat] * len(faces); s.s += sm

    def prism(s, prof, y0, y1, mat):
        """Polygon in (x, z), counter-clockwise seen from -Y, extruded from y0 to y1."""
        n = len(prof); front = [(x, y0, z) for x, z in prof]; back = [(x, y1, z) for x, z in prof]
        faces = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))] + [(i, n + i, n + (i + 1) % n, (i + 1) % n) for i in range(n)]
        s._emit(front + back, faces, mat, False)

    def blob(s, r, loc, mat, seed=0, sq=(1, 1, 1), rot=(0, 0, 0), sub=2, rough=.3, flat=None, smooth=False):
        v, f = ico(sub); sd = Vector((seed * 7.13 + .3, seed * 3.7 + .1, seed * 1.9 + .7)); pts = []
        for x, y, z in v:
            p = Vector((x, y, z)); q = p * (1 + noise.noise(p * 1.4 + sd) * rough + noise.noise(p * 3.5 + sd) * rough * .4)
            if flat is not None and q.z < flat: q.z = flat + (q.z - flat) * .1
            pts.append((q.x * sq[0] * r, q.y * sq[1] * r, q.z * sq[2] * r))
        s._emit(pts, f, mat, smooth, loc, rot)

    def arch(s, face, pos, w, h, mat, off=0.0, nseg=8):
        """Flat arched-top polygon (rect + semicircle) standing on z=pos[1]; face S(-Y) E(+X) W(-X); pos=(centre along face, base z, wall coord)."""
        u0, z0, c = pos; r = w / 2; pts2 = [(-r, 0), (r, 0)]
        pts2 += [(r * math.cos(pi * i / nseg), h - r + r * math.sin(pi * i / nseg)) for i in range(nseg + 1)]
        pts3 = []
        for u, z in pts2:
            if face == 'S': pts3.append((u0 + u, c - off, z0 + z))
            elif face == 'E': pts3.append((c + off, u0 + u, z0 + z))
            else: pts3.append((c - off, u0 - u, z0 + z))
        s.poly(pts3, mat)

    def grid(s, nx, ny, fn, mats):
        """Flag-like quad grid; fn(i, j) -> point; mats(i, j) -> material per quad."""
        base = len(s.v); s.v += [fn(i, j) for j in range(ny + 1) for i in range(nx + 1)]
        for j in range(ny):
            for i in range(nx):
                a = base + j * (nx + 1) + i
                s.f.append((a, a + 1, a + nx + 2, a + nx + 1)); s.m.append(mats(i, j)); s.s.append(True)

    def build(s, scn, name, loc=(0, 0, 0), rot=(0, 0, 0), parent=None):
        me = bpy.data.meshes.new(name); me.from_pydata(s.v, [], s.f)
        mats = []
        for m in s.m:
            if m not in mats: mats.append(m)
        for m in mats: me.materials.append(m)
        me.polygons.foreach_set("material_index", [mats.index(m) for m in s.m])
        me.polygons.foreach_set("use_smooth", s.s); me.update()
        o = bpy.data.objects.new(name, me); o.location, o.rotation_euler, o.parent = loc, rot, parent
        scn.collection.objects.link(o); return o


def loc_seed(loc): return Vector((loc[0] * .13, loc[1] * .17, 0))


def text3d(scn, name, txt, size, loc, rot, mat, extrude=.015, parent=None):
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = txt; cu.size = size; cu.align_x = cu.align_y = 'CENTER'; cu.extrude = extrude
    cu.materials.append(mat)
    o = bpy.data.objects.new(name, cu); o.location, o.rotation_euler, o.parent = loc, rot, parent
    scn.collection.objects.link(o); return o


# ====================================================================== small props (prototypes)
_P = {}


def proto(key, fn):
    if key not in _P:
        g = G(); fn(g); _P[key] = g
    return _P[key]


def p_barrel(g):
    prof = [(0, 0), (.21, 0)] + [(.27 - .07 * ((z - .45) / .45) ** 2, z) for z in (.05, .2, .45, .7, .85)] + [(.21, .9), (0, .9)]
    g.lathe(prof, (0, 0, 0), WOOD, seg=14)
    for z in (.12, .3, .6, .78):
        r = .27 - .07 * ((z - .45) / .45) ** 2 + .008
        g.lathe([(r, z - .018), (r, z + .018)], (0, 0, 0), STEEL, seg=14, caps=False)


def p_crate(g):
    g.box((.6, .6, .5), (0, 0, .25), WOOD)
    for sx in (-1, 1):
        for sy in (-1, 1): g.box((.07, .07, .52), (sx * .27, sy * .27, .26), DWOOD)
    for z in (.06, .44):
        g.box((.62, .62, .06), (0, 0, z), DWOOD)
    g.beam((-.3, -.3, .08), (.3, -.3, .46), .05, .02, DWOOD)


def p_bale(g):
    g.box((.9, .45, .45), (0, 0, .225), PRAIRIE)
    for x in (-.25, .25): g.box((.03, .47, .47), (x, 0, .225), STEEL)


def p_trough(g):
    for sy in (-1, 1): g.box((1.6, .06, .4), (0, sy * .22, .4), WOOD)
    for sx in (-1, 1): g.box((.06, .5, .4), (sx * .77, 0, .4), WOOD)
    g.box((1.5, .4, .04), (0, 0, .22), DWOOD); g.box((1.5, .38, .02), (0, 0, .5), WATER)
    for sx in (-.6, .6): g.box((.08, .5, .22), (sx, 0, .11), DWOOD)


def p_bench(g):
    g.box((1.4, .35, .05), (0, 0, .45), WOOD); g.box((1.4, .05, .3), (0, .17, .65), WOOD)
    for sx in (-.6, .6): g.box((.06, .3, .45), (sx, 0, .22), DWOOD)


def p_sack(g):
    g.blob(.22, (0, 0, .18), CREAM, 3, (1, .8, .85), sub=1, rough=.15, smooth=True)


def p_rock(g, seed=0):
    g.blob(1, (0, 0, .45), ROCK, seed, (1, 1, .8), sub=2, rough=.32, flat=-.55)


def p_tuft(g, mat=None, h=.3, n=12, seed=0):
    rr = _rnd.Random(seed)
    for _ in range(n):
        a, d, hh, t = rr.random() * 2 * pi, .06 * rr.random(), h * (.6 + .8 * rr.random()), .15 + .4 * rr.random()
        g.lathe([(.011, 0), (0, hh)], (d * math.cos(a), d * math.sin(a), 0), mat, seg=3,
                rot=Matrix.Rotation(t, 3, Vector((-math.sin(a), math.cos(a), 0))), smooth=False, caps=False)


def p_bush(g, seed=0):
    rr = _rnd.Random(seed)
    for i in range(4):
        g.blob(.35 + .2 * rr.random(), (rr.uniform(-.4, .4), rr.uniform(-.4, .4), .3 + .15 * i * rr.random()), GRASS, seed + i, (1, 1, .8), sub=1, rough=.25, flat=-.5)


def p_tree(g, seed=0):
    rr = _rnd.Random(seed)
    g.lathe([(.28, 0), (.2, 1.2), (.14, 2.6), (.08, 3.6)], (0, 0, 0), DWOOD, seg=7)
    for i in range(5):
        a = i * 1.26 + rr.random(); g.blob(1.3 + .5 * rr.random(), (1.1 * math.cos(a) * (i > 0), 1.1 * math.sin(a) * (i > 0), 4.2 + .6 * (i % 3)), GRASS, seed + i, (1, 1, .85), sub=1, rough=.2)


def p_pine(g, seed=0):
    g.lathe([(.2, 0), (.12, 1.5)], (0, 0, 0), DWOOD, seg=6)
    for i, (r, z, h) in enumerate(((1.6, 1.0, 2.2), (1.25, 2.2, 2.0), (.85, 3.4, 1.8))):
        g.lathe([(r, z), (0, z + h)], (0, 0, 0), PINE, seg=8, smooth=False)


def p_post_rail(g, L=3.0):
    for x in (-L / 2, L / 2): g.box((.12, .12, 1.2), (x, 0, .6), DWOOD)
    for z in (.45, .85): g.box((L, .06, .12), (0, 0, z), WOOD)


def p_picket(g, L=2.4):
    for z in (.25, .65): g.box((L, .04, .07), (0, .03, z), WHITE)
    for x in (-L / 2, L / 2): g.box((.1, .1, .95), (x, 0, .47), WHITE)
    n = int(L / .16)
    for i in range(1, n):
        x = -L / 2 + i * L / n; g.prism([(x - .035, 0), (x + .035, 0), (x + .035, .78), (x, .86), (x - .035, .78)], -.01, .01, WHITE)


def p_stone(g, seed=0):
    g.box((.5, .1, .6), (0, 0, .3), ROCK); g.lathe([(.25, -.05), (.25, .05)], (0, 0, .6), ROCK, axis='Y', seg=10, rot=(0, 0, 0))
    g.box((.7, .35, .1), (0, -.05, .05), ROCK)


def p_cross(g):
    g.box((.08, .06, .9), (0, 0, .45), WOOD); g.box((.45, .06, .08), (0, 0, .7), WOOD)


def p_pole(g):
    g.lathe([(.14, 0), (.1, 7.4)], (0, 0, 0), DWOOD, seg=7); g.box((.09, 1.8, .12), (0, 0, 7.0), DWOOD)
    for y in (-.8, 0, .8): g.cyl(.04, .14, (0, y, 7.14), GLASS, seg=6)
    g.beam((0, -.1, 6.2), (0, -.9, 7.0), .06, .06, DWOOD); g.beam((0, .1, 6.2), (0, .9, 7.0), .06, .06, DWOOD)


def p_lamp(g):
    g.lathe([(.08, 0), (.05, 2.4)], (0, 0, 0), BLACKM, seg=6); g.box((.3, .04, .04), (.15, 0, 2.35), BLACKM)
    g.lathe([(.07, 2.1), (.12, 2.3), (.07, 2.5)], (.3, 0, 0), GLASS, seg=6)


def p_wheel(g):
    g.lathe([(.5, -.05), (.5, .05), (.485, .05), (.485, -.05)], (0, 0, 0), STEEL, axis='X', seg=28, closed=True)
    g.lathe([(.485, -.05), (.485, .05), (.42, .05), (.42, -.05)], (0, 0, 0), DWOOD, axis='X', seg=14, closed=True, smooth=False)
    for k in range(12):
        a = 2 * pi * k / 12; g.box((.045, .35, .04), (0, .265 * math.cos(a), .265 * math.sin(a)), WOOD, (a, 0, 0))
    g.lathe([(0, -.13), (.055, -.13), (.09, -.08), (.09, .08), (.055, .13), (0, .13)], (0, 0, 0), DWOOD, axis='X', seg=12)
    g.lathe([(.1, -.02), (.1, .02)], (0, 0, 0), STEEL, axis='X', seg=12, caps=False)


# ====================================================================== gallows
def gallows(scn, noose_axis='Z'):
    g = G()
    # planked deck 4 x 3 m, top at z=2, 1 m trap hole in the middle
    for x0, x1 in ((-2, -.5), (.5, 2)):
        n = 6; w = (x1 - x0) / n
        for i in range(n): g.box((w - .012, 3, .1), (x0 + w * (i + .5), 0, 1.95), WOOD)
    for y0 in (-1.5, .5):
        for i in range(4): g.box((1, .24, .1), (0, y0 + .25 * (i + .5) + .0, 1.95), WOOD)
    for y in (-1.45, -.55, .55, 1.45): g.box((4, .14, .18), (0, y, 1.81), DWOOD)          # joists
    for x in (-.55, .55): g.box((.1, 1.1, .16), (x, 0, 1.82), DWOOD)
    for x in (-1.8, 1.8):
        for y in (-1.3, 1.3): g.box((.2, .2, 1.8), (x, y, .9), DWOOD)                    # posts
    for x in (-1.8, 1.8):                                                               # braces in the end frames
        g.beam((x, -1.3, .2), (x, 0, 1.75), .08, .1, DWOOD); g.beam((x, 1.3, .2), (x, 0, 1.75), .08, .1, DWOOD)
    for y in (-1.38, 1.38):                                                             # plank skirt front/back
        for i in range(12): g.box((.29, .04, 1.5), (-1.74 + i * .316, y, .85), WOOD)
        g.beam((-1.8, y - .04 * (1 if y < 0 else -1), .15), (1.8, y - .04 * (1 if y < 0 else -1), 1.75), .09, .04, DWOOD)
    for i in range(10): g.box((.04, .29, 1.5), (-1.88, -1.3 + i * .29, .85), WOOD)
    # upright, beam, braces
    g.box((.22, .22, 3.5), (-1.7, 0, 3.75), DWOOD); g.box((2.3, .2, .2), (-.7, 0, 5.4), DWOOD)
    g.beam((-1.7, 0, 4.2), (-.55, 0, 5.3), .1, .12, DWOOD); g.beam((-1.7, 0, 4.2), (-2.5, 0, 5.1), .08, .1, DWOOD)
    for sy in (-1, 1): g.beam((-1.7, sy * 1.15, 2.0), (-1.7, sy * .11, 3.7), .1, .12, DWOOD)
    g.box((.2, 1.0, .12), (-1.7, 0, 2.7), DWOOD)
    for z in (2.7, 4.0, 5.4): g.cyl(.04, .26, (-1.7, 0, z), STEEL, axis='Y', seg=8)    # through-bolts
    # back and left rails
    for y in (1.45,):
        for x in (-1.9, -.6, .7, 1.95): g.box((.08, .08, .9), (x, y, 2.45), DWOOD)
        g.box((4, .08, .08), (0, y, 2.9), WOOD)
    # stairs on +X: 10 steps rising to the deck edge, width 1.1
    rise, run = .2, .33
    for i in range(10):
        x = 2.0 + run * (9 - i) + run / 2
        g.box((run + .02, 1.1, .06), (x, 0, rise * (i + 1) - .03), WOOD); g.box((.03, 1.1, rise), (x - run / 2 + .0, 0, rise * (i + .5)), DWOOD)
    for sy in (-.58, .58):
        g.beam((5.3, sy, .0), (2.0, sy, 2.0), .06, .3, DWOOD)
        for t in (0, .45, .9):
            xp = 5.2 - t * 3.2; zp = (5.2 - xp) * (2 / 3.3) + .2
            g.box((.07, .07, 1.0), (xp, sy, zp + .3), DWOOD)
        g.beam((5.2, sy, 1.2), (2.2, sy, 3.1), .06, .06, DWOOD)
    trap = G()
    for i in range(4): trap.box((.98, .24, .08), (0, -.125 - .25 * i, 0), HAT)
    for x in (-.3, .3): trap.box((.08, .9, .05), (x, -.5, -.065), DWOOD)
    for x in (-.3, .3): trap.box((.1, .32, .012), (x, -.18, .046), STEEL)
    trap.box((.6, .05, .02), (0, -.96, .045), STEEL)
    tr = trap.build(scn, "g_trap", (0, .5, 1.96))   # origin on the hinge
    g.build(scn, "g_frame")
    # rope: origin at the beam so it can sway
    rope = _noose(scn, noose_axis)
    return {"trap": tr, "rope": rope}


def _noose(scn, axis):
    L = 1.75
    rg = G()
    if axis == 'Z':   # worn: loop horizontal at neck height 3.55, knot behind the neck
        zc, ry, rx, ky = -L, .19, .17, .19
        top = zc + .22
        path = [(0, 0, 0), (0, .02, -.4), (0, .08, -.9), (0, .14, -1.25), (0, ky, top)]
        loop = [(rx * math.sin(t), ky - (ky + ry) * (1 - math.cos(t)) / 2 + 0, zc + (.02 * math.cos(t) - .03)) for t in [2 * pi * i / 28 for i in range(28)]]
        kn, kdir = (0, ky, zc), (0, 0, 1)
    else:             # free: vertical loop facing the camera, knot at the top
        rz, rx = .21, .15; zc = -L - .16
        top = zc + rz + .22
        path = [(0, 0, 0), (0, 0, -.5), (0, 0, -1.0), (0, 0, top)]
        loop = [(rx * math.sin(t), 0, zc + rz * math.cos(t)) for t in [2 * pi * i / 28 for i in range(28)]]
        kn, kdir = (0, 0, zc + rz), (0, 0, 1)
    rad = lambda n: [1 + .12 * math.sin(i * 1.3) + .05 * math.sin(i * 3.1) for i in range(n)]
    # dense standing part
    dense = []
    for a, b in zip(path, path[1:]):
        for k in range(6): dense.append(tuple(Vector(a).lerp(Vector(b), k / 6)))
    dense.append(path[-1])
    rg.tube(dense, .026, ROPE, 8, rad(len(dense)))
    rg.tube(loop, .027, ROPE, 8, [1 + .15 * math.sin(i * .9) + .06 * math.sin(i * 2.3) for i in range(len(loop))], closed=True)
    kx, ky_, kz = kn
    rg.tube([(kx, ky_, kz - .03), (kx, ky_, kz + .22)], .036, ROPE, 8)     # core of the knot
    helix = [(kx + .036 * math.cos(2 * pi * i / 9), ky_ + .036 * math.sin(2 * pi * i / 9), kz + .005 + i * .0028) for i in range(8 * 9 + 1)]
    rg.tube(helix, .016, ROPE, 5)                                           # eight wraps
    rg.tube([(kx, ky_, kz - .03), (kx + .01, ky_, kz - .11)], .02, ROPE, 6, [1, 1.25])   # frayed tail end
    for dx in (-.04, 0, .04):
        rg.tube([(dx, .13 * math.sin(2 * pi * i / 14), .1 - .13 * math.cos(2 * pi * i / 14)) for i in range(14)], .02, ROPE, 5, closed=True)
    return rg.build(scn, "g_rope", (0, 0, 5.3))


# ====================================================================== wagon
def _wagon_body(scn, root, parked=False):
    g = G()
    for y in (-.2, 1.4):
        g.box((1.5, .09, .09), (0, y, .5), STEEL)
        for sx in (-.5, .5): g.box((.12, .2, .45), (sx, y, .775), DWOOD)
    g.box((.07, 1.8, .09), (0, .6, .58), DWOOD)
    for sx in (-.55, .55): g.box((.1, 2.4, .15), (sx, .6, 1.075), DWOOD)
    for i in range(5): g.box((.256, 2.4, .08), (-.52 + i * .26, .6, 1.185), WOOD)
    g.box((1.3, .06, .5), (0, -.6, 1.05), DWOOD)                                   # kickboard
    for sx in (-.675, .675):
        for z in (1.32, 1.54): g.box((.05, 1.9, .19), (sx, .85, z), WOOD)
        for y in (-.1, .8, 1.8): g.box((.07, .07, .56), (sx, y, 1.5), DWOOD)
    for z in (1.4, 1.6): g.box((1.4, .05, .18), (0, 1.8, z), WOOD)
    g.box((1.3, .38, .08), (0, -.5, 1.31), DWOOD)                                  # seat plank on springs
    for sx in (-.58, .58):
        for k, (ln, z) in enumerate(((.6, 1.235), (.48, 1.25), (.36, 1.263))): g.box((.06, ln, .012), (sx, -.5, z), STEEL)
    for sx in (-.62, .62): g.box((.05, .05, .5), (sx, -.27, 1.6), DWOOD)
    g.box((1.3, .05, .06), (0, -.27, 1.85), DWOOD); g.box((1.24, .04, .05), (0, -.27, 1.5), DWOOD)
    for i in range(7): g.box((.025, .025, .33), (-.45 + i * .15, -.27, 1.67), DWOOD)
    g.box((1.3, .45, .05), (0, -1.02, .475), DWOOD)                                 # footboard
    for sx in (-.6, .6): g.beam((sx, -.55, 1.0), (sx, -1.2, .47), .06, .06, DWOOD)
    g.box((.09, 2.8, .09), (0, -1.6, .9), DWOOD)                                    # tongue, tip at y=-3
    g.cyl(.07, .03, (0, -3.02, .9), STEEL, axis='Y', seg=10)
    g.box((.2, .06, .12), (0, -.35, .88), STEEL)
    g.box((.04, .04, .5), (.72, .2, 1.55), STEEL)                                   # brake lever
    for x, y, h in ((-.3, 1.2, .0), (.3, 1.35, .0)): g.box((.55, .55, .45), (x, y, 1.225 + .225), WOOD)
    g.add(proto("barrel", p_barrel), (.3, .5, 1.225), (0, 0, 0), .9)
    g.add(proto("sack", p_sack), (-.3, .45, 1.225)); g.add(proto("sack", p_sack), (-.35, .8, 1.225), (0, 0, .7))
    if parked: g.box((.1, .1, .85), (0, -2.6, .42), DWOOD)
    return g.build(scn, "w_body", parent=root)


def wagon(scn, loc, rz, riders):
    """riders: list of (builder, seat x). Returns the rig root, wheels and horses."""
    root = empty(scn, "Wagon", loc, rot=(0, 0, rz)); k = dict(parent=root)
    _wagon_body(scn, root)
    wmesh = None; wheels = []
    for x in (-.72, .72):
        for y in (-.2, 1.4):
            w = G() if wmesh is None else None
            if w is not None:
                p_wheel(w); o = w.build(scn, "w_wheel", (x, y, .5), parent=root); wmesh = o.data
            else:
                o = bpy.data.objects.new("w_wheel", wmesh); o.location, o.parent = (x, y, .5), root; scn.collection.objects.link(o)
            wheels.append(o)
    horses = [horse(scn, f"Horse{i}", root, (x, -2.7, 0), c) for i, (x, c) in enumerate(((-.45, HORSE), (.45, HORSE2)))]
    for build, x in riders:
        pose(build(scn, loc=(x, -.5, .5), parent=root), **SEATED)
    return root, wheels, horses


# ====================================================================== storefronts and town
SIGNS = ["SALOON", "HOTEL", "BANK", "GENERAL STORE", "BARBER", "LIVERY", "SHERIFF", "UNDERTAKER", "HARDWARE", "ASSAY OFFICE", "CAFE", "STABLE"]


def _store(h, body, with_porch=True):
    """Storefront in local space: footprint 4.6 x 4.5 centred on the origin, street face toward -Y."""
    g = G(); w, d = 4.6, 4.5; yf = -d / 2; yc = yf - .16; H = h + .9
    g.box((w, d, h), (0, 0, h / 2), body); g.box((w + .1, .16, H), (0, yf - .08, H / 2), body)
    g.box((w + .3, .3, .22), (0, yf - .15, H + .05), DWOOD); g.box((w + .2, .2, .1), (0, yf - .1, 3.3), DWOOD)
    for sx in (-1, 1): g.box((.14, .14, H), (sx * (w / 2 + .02), yf - .1, H / 2), WHITE)
    g.box((1.2, .06, 2.2), (0, yc - .03, 1.1), WHITE); g.box((1.0, .05, 2.05), (0, yc - .06, 1.03), DWOOD)
    g.box((.6, .02, .7), (0, yc - .09, 1.55), GLASS); g.box((.05, .05, .05), (.38, yc - .1, 1.0), STEEL)
    for sx in (-1.55, 1.55):
        g.box((1.1, .06, 1.4), (sx, yc - .03, 1.7), WHITE); g.box((.92, .03, 1.22), (sx, yc - .06, 1.7), GLASS)
        g.box((.04, .04, 1.22), (sx, yc - .08, 1.7), WHITE); g.box((.92, .04, .04), (sx, yc - .08, 1.7), WHITE)
        g.box((1.25, .14, .06), (sx, yc - .1, 1.0), WHITE)
    if h >= 4.6:
        for sx in (-1.85, 1.85):
            g.box((.8, .06, 1.0), (sx, yc - .03, 3.95), WHITE); g.box((.64, .03, .84), (sx, yc - .06, 3.95), GLASS)
    g.box((2.9, .06, .8), (0, yc - .03, h + .35), WHITE); g.box((2.8, .1, .7), (0, yc - .06, h + .35), INK)
    g.box((.5, .5, 1.2), (1.4, 1.0, h + .6), DWOOD)
    if with_porch:
        g.box((w + .6, .6, .12), (0, yf - .3, .06), WOOD)
        for sx in (-1.6, 1.6): g.box((.12, .12, 3.0), (sx, yf - .45, 1.5), WOOD)
        g.box((w + .2, .85, .1), (0, yf - .82, 3.08), DWOOD, (.08, 0, 0)); g.box((w + .2, .06, .22), (0, yf - 1.2, 2.96), DWOOD)
        for sx in (-1.6, 1.6): g.beam((sx, yf - .45, 2.4), (sx, yf - .15, 3.0), .07, .07, WOOD)
    return g


def _rotz(v, a):
    c, s = math.cos(a), math.sin(a); return (v[0] * c - v[1] * s, v[0] * s + v[1] * c, v[2])


def building(g, texts, pos, rz, h, body, idx, items=True, rail=False):
    g.add(_store(h, body), (pos[0], pos[1], 0), (0, 0, rz))
    W = lambda p: tuple(Vector(_rotz(p, rz)) + Vector((pos[0], pos[1], 0)))
    txt = SIGNS[idx % len(SIGNS)]
    texts.append((txt, W((0, -2.25 - .16 - .13, h + .35)), (pi / 2, 0, rz), min(.42, 2.6 / (len(txt) * .62))))
    if rail:
        g.add(proto("rail", lambda q: p_post_rail(q, 3.0)), W((0, -3.15, 0)), (0, 0, rz))
        g.add(proto("trough", p_trough), W((1.0, -3.55, 0)), (0, 0, rz))
    elif items:
        for sx in (-1.05, 1.05):
            k = R.choice(("barrel", "crate", "bench", "sack"))
            if k == "barrel": g.add(proto("barrel", p_barrel), W((sx, -2.58, .12)), (0, 0, 0), .85)
            elif k == "crate": g.add(proto("crate", p_crate), W((sx, -2.58, .12)), (0, 0, rz + R.uniform(-.2, .2)))
            elif k == "bench": g.add(proto("bench", p_bench), W((sx, -2.5, .12)), (0, 0, rz))
            else:
                g.add(proto("sack", p_sack), W((sx, -2.58, .12))); g.add(proto("sack", p_sack), W((sx + .15, -2.5, .12)), (0, 0, 1))


def _signs(scn, texts):
    for t, loc, rot, size in texts: text3d(scn, "dec_sign", t, size, loc, rot, PAPER)


def town(scn):
    rr = _rnd.Random(11); g = G(); texts = []
    mats = [TEAL, WOOD, DTEAL, HAT]
    for i in range(6):
        for side in (-1, 1):
            y = -3 + i * 5.2; rz = pi / 2 if side < 0 else -pi / 2
            rail = (i == 0) or (i == 4 and side < 0) or (i == 5 and side > 0)
            building(g, texts, (side * 6, y), rz, rr.uniform(4.2, 6.4), mats[(i * 2 + (side > 0)) % 4], i * 2 + (side > 0), rail=rail)
    g.build(scn, "t_town"); _signs(scn, texts)


# ====================================================================== church
def church(scn):
    g = G(); Y0, Y1 = 6.5, 13.5
    g.box((6.2, 7.2, .25), (0, 10, .125), ROCK)
    g.prism([(-3, .25), (3, .25), (3, 4.5), (0, 6.9), (-3, 4.5)], Y0, Y1, WHITE)
    for sx in (-1, 1):
        for y in (Y0, Y1): g.box((.16, .16, 4.3), (sx * 3.02, y, 2.4), WHITE)
    phi = math.atan2(2.4, 3.0); L = 4.35
    for sx in (-1, 1): g.box((L, 7.6, .12), (sx * 1.74, 10, 5.64), DWOOD, (0, sx * phi, 0))
    g.box((.22, 7.7, .16), (0, 10, 7.02), DWOOD)
    g.box((1.9, .38, .25), (0, 6.31, .125), ROCK)
    g.arch('S', (0, .25, Y0), 1.7, 2.65, WHITE, .02); g.arch('S', (0, .25, Y0), 1.3, 2.4, DWOOD, .045)
    for sx in (-.3, .3): g.box((.55, .03, 1.7), (sx, Y0 - .07, 1.15), DTEAL)
    g.box((.04, .04, .3), (.5, Y0 - .09, 1.3), STEEL)
    for sx in (-2, 2):
        g.arch('S', (sx, .9, Y0), 1.2, 2.2, WHITE, .02); g.arch('S', (sx, 1.0, Y0), .9, 2.0, GLASS, .035)
        g.box((.05, .04, 1.2), (sx, Y0 - .05, 1.5), WHITE); g.box((.9, .04, .05), (sx, Y0 - .05, 1.6), WHITE)
    for sg, c in ((-1, -3), (1, 3)):
        for y in (8.0, 10.0, 12.0):
            f = 'E' if sg > 0 else 'W'
            g.arch(f, (y, .9, c), 1.2, 2.2, WHITE, .02); g.arch(f, (y, 1.0, c), .9, 2.0, GLASS, .035)
            g.box((.04, .05, 1.2), (c + sg * .05, y, 1.5), WHITE); g.box((.04, .9, .05), (c + sg * .05, y, 1.6), WHITE)
    g.box((1.7, 1.7, 2.8), (0, 7.5, 7.6), WHITE)
    for f, cx, cy in (('S', 0, 6.65), ('E', .85, 7.5), ('W', -.85, 7.5)):
        if f == 'S': g.arch(f, (0, 7.0, cy), .9, 1.5, BLACKM, .012)
        else: g.arch(f, (7.5, 7.0, cx), .9, 1.5, BLACKM, .012)
        for k in range(10):
            z = 7.12 + k * .13
            if f == 'S': g.box((.84, .06, .04), (0, 6.64, z), WHITE, (-.5, 0, 0))
            else: g.box((.06, .84, .04), (cx + (.01 if f == 'E' else -.01), 7.5, z), WHITE, (0, .5 if f == 'E' else -.5, 0))
    g.box((2.0, 2.0, .15), (0, 7.5, 9.02), WHITE)
    g.lathe([(1.25, 9.05), (0, 12.2)], (0, 7.5, 0), DWOOD, seg=8, smooth=False, rot=(0, 0, pi / 8))
    g.box((.1, .1, 1.1), (0, 7.5, 12.5), DWOOD); g.box((.55, .1, .1), (0, 7.5, 12.65), DWOOD)
    g.build(scn, "church_main")
    fe = G(); seg = proto("picket", p_picket)       # yard fence; gate gap |x|<4.6 at the front, the action runs through it
    for sx in (-1, 1):
        for xc in (5.8, 8.2): fe.add(seg, (sx * xc, 3.0, 0))
        for k in range(6): fe.add(seg, (sx * 9.4, 4.2 + 2.4 * k, 0), (0, 0, pi / 2))
    for k in range(8): fe.add(seg, (-8.2 + 2.4 * k, 18.0, 0))
    for sx in (-4.6, 4.6): fe.box((.2, .2, 1.3), (sx, 3.0, .65), WHITE); fe.box((.28, .28, .06), (sx, 3.0, 1.32), WHITE)
    fe.build(scn, "church_fence")
    gs = G(); rr = _rnd.Random(4)
    for i in range(11):
        x = rr.choice((-1, 1)) * rr.uniform(5.4, 8.4); y = rr.uniform(6.5, 16)
        gs.add(proto("stone", p_stone) if rr.random() < .75 else proto("cross", p_cross), (x, y, 0), (rr.uniform(-.06, .06), rr.uniform(-.06, .06), rr.uniform(-.15, .15)), rr.uniform(.8, 1.2))
    gs.build(scn, "church_graves")


# ====================================================================== courtroom
def courtroom(scn):
    g = G(); H = 9.0
    g.box((12, .2, H), (0, 5.5, H / 2), DTEAL)
    for sx in (-6, 6): g.box((.2, 12, H), (sx, -.35, H / 2), TEAL)
    g.box((12.2, .2, H), (0, -6.4, H / 2), DTEAL)
    for sy, ln in ((5.39, 11.8), (-6.29, 11.8)):     # wainscot on back and front walls
        for i in range(14): g.box((.14, .05, 1.5), (-ln / 2 + .45 + i * (ln - .9) / 13, sy, .75), DWOOD)
        g.box((ln, .1, .1), (0, sy, 1.55), WOOD); g.box((ln, .06, .16), (0, sy, .08), DWOOD)
    for sx in (-5.89, 5.89):
        for i in range(14): g.box((.05, .14, 1.5), (sx, -6.2 + i * 11.6 / 13, .75), DWOOD)
        g.box((.1, 11.8, .1), (sx, -.35, 1.55), WOOD); g.box((.06, 11.8, .16), (sx, -.35, .08), DWOOD)
    for sx, f, inw in ((-5.9, 'E', 1), (5.9, 'W', -1)):         # windows with light, facing into the room
        for y in (-4.6, -2.0, .6, 3.2):
            g.arch(f, (y, 2.2, sx), 1.3, 3.2, WHITE, .02); g.arch(f, (y, 2.35, sx), 1.05, 2.9, SKYWIN, .035)
            g.box((.04, .05, 2.6), (sx + inw * .05, y, 3.5), WHITE); g.box((.04, 1.05, .05), (sx + inw * .05, y, 3.8), WHITE); g.box((.04, 1.05, .05), (sx + inw * .05, y, 3.0), WHITE)
    for x in (-3.6, 0, 3.6): g.arch('S', (x, 2.2, -6.3), 1.3, 3.2, WHITE, .02); g.arch('S', (x, 2.35, -6.3), 1.05, 2.9, SKYWIN, .035)
    g.box((12, .3, .3), (0, 5.3, 7.4), DWOOD)
    g.box((5, 3.2, .015), (0, .5, .008), RUG)
    g.box((5.6, 1.85, .55), (0, 4.575, .275), DWOOD)                          # dais under the judge
    g.box((3.4, .9, 1.5), (0, 3.2, .75), DWOOD)                               # bench
    for sx in (-1.15, 0, 1.15):
        g.box((1.0, .04, 1.1), (sx, 2.73, .8), WOOD); g.box((.8, .02, .8), (sx, 2.71, .8), DWOOD)
    g.box((3.6, 1.1, .08), (0, 3.2, 1.54), WOOD); g.box((3.7, .08, .06), (0, 2.63, 1.52), DWOOD)
    g.cyl(.1, .035, (.5, 3.1, 1.5975), DWOOD, seg=16)                         # sound block under the gavel head
    g.box((.3, .06, .1), (-.5, 2.85, 1.65), GOLD)
    g.box((.9, .5, .02), (-1.1, 3.3, 1.59), PAPER); g.box((.25, .17, .08), (-1.35, 3.1, 1.62), DTEAL); g.box((.22, .16, .07), (-1.35, 3.1, 1.7), RED)
    g.cyl(.07, .02, (1.3, 3.4, 1.6), STEEL, seg=10); g.cyl(.012, .3, (1.3, 3.4, 1.75), STEEL, seg=6); g.cyl(.1, .1, (1.3, 3.4, 1.93), M("OF_shade", (.05, .35, .15), .4), r2=.05, seg=10)
    g.box((1.0, .12, 1.3), (0, 5.2, 1.2), DWOOD); g.box((.9, .5, .08), (0, 4.85, 1.0), DWOOD); g.box((1.1, .14, .12), (0, 5.2, 1.9), DWOOD)
    g.cyl(.45, .05, (0, 5.35, 3.4), GOLD, axis='Y', seg=24); g.cyl(.36, .06, (0, 5.34, 3.4), DWOOD, axis='Y', seg=24)
    for sx, kind in ((-2.55, 'state'), (2.55, 'us')):
        g.cyl(.035, 3.2, (sx, 5.0, 2.15), DWOOD, seg=8); g.cyl(.06, .08, (sx, 5.0, 3.78), GOLD, seg=8)
        d = -1 if sx > 0 else 1; fw, fh = 1.3, .9
        wave = lambda i, j, sx=sx, d=d: (sx + d * (.04 + i * fw / 8), 5.0 + .06 * math.sin(i * .9), 3.4 - j * fh / 6)
        if kind == 'us': g.grid(8, 6, wave, lambda i, j: FLAGB if (i < 3 and j < 3) else (FLAGR if j % 2 == 0 else FLAGW))
        else: g.grid(8, 6, wave, lambda i, j: FLAGB)
    for i in range(24):                                                       # bar railing with a gate gap
        x = -5.7 + i * .5
        if abs(x) >= .7: g.box((.04, .04, .8), (x, -1.2, .6), DWOOD)
    for x in (-5.8, -.7, .7, 5.8): g.box((.12, .12, 1.1), (x, -1.2, .55), DWOOD)
    for x0, x1 in ((-5.8, -.7), (.7, 5.8)): g.box((x1 - x0, .09, .07), ((x0 + x1) / 2, -1.2, 1.08), WOOD); g.box((x1 - x0, .07, .06), ((x0 + x1) / 2, -1.2, .2), DWOOD)
    for y in (-2.6, -3.7, -4.8):                                              # gallery benches
        for x0, x1 in ((-5.4, -1.1), (1.1, 5.4)):
            xc, ln = (x0 + x1) / 2, x1 - x0
            g.box((ln, .42, .06), (xc, y, .45), WOOD); g.box((ln, .05, .55), (xc, y - .22, .8), WOOD); g.box((ln, .05, .1), (xc, y - .22, .55), DWOOD)
            for x in (x0, x1): g.box((.06, .5, 1.0), (x, y - .1, .5), DWOOD)
    g.box((1.8, .8, .08), (-3.6, 3.4, 1.0), WOOD); g.box((1.7, .7, .9), (-3.6, 3.4, .45), DWOOD); g.box((.9, .5, .02), (-3.6, 3.3, 1.05), PAPER)
    g.box((1.2, 1.0, 1.1), (3.4, 3.4, .55), DWOOD); g.box((1.3, 1.1, .06), (3.4, 3.4, 1.12), WOOD); g.box((.06, 1.0, .35), (2.78, 3.4, 1.3), DWOOD)
    g.build(scn, "c_room")


def gavel(scn):
    g = empty(scn, "Gavel", (.5, 3.55, 1.68)); m = G()
    m.lathe([(.016, .05), (.022, .0), (.02, -.1), (.017, -.2), (.016, -.45)], (0, 0, 0), WOOD, axis='Y', seg=10)
    m.lathe([(0, -.1), (.044, -.1), (.065, -.05), (.065, .05), (.044, .1), (0, .1)], (0, -.45, 0), DWOOD, axis='X', seg=16)
    for sx in (-.075, .075): m.lathe([(.067, sx - .007), (.067, sx + .007)], (0, -.45, 0), STEEL, axis='X', seg=16, caps=False)
    m.build(scn, "gavel_body", parent=g); return g


# ====================================================================== river bed (S04)
def river(scn):
    box(scn, "river", (120, 6, .04), (0, 7, .02), WATER)
    g = G(); rr = _rnd.Random(9)
    g.blob(1, (0, 3.55, -.02), GRAVEL, 2, (70, .6, .2), sub=3, rough=.12, flat=-.5, smooth=True)
    g.blob(1, (0, 13.0, -.4), GRASS, 5, (70, 3.2, 1.1), sub=3, rough=.12, flat=-.3, smooth=True)
    g.build(scn, "r_banks")
    r = G(); n = 0
    while n < 30:
        x, y, s = rr.uniform(-9, 9), rr.uniform(-6, 3.3), rr.uniform(.12, .45)
        if -1.9 < x < 2.8 and -1.6 < y < 3.3: continue
        r.add(proto(f"rock{n % 6}", lambda q, k=n % 6: p_rock(q, k)), (x, y, 0), (0, 0, rr.random() * 6.28), (s * rr.uniform(.9, 1.3), s * rr.uniform(.8, 1.2), s * rr.uniform(.6, .95))); n += 1
    for i in range(4):
        x = rr.choice((-1, 1)) * rr.uniform(6, 10); y = rr.uniform(-5, 2); s = rr.uniform(.8, 1.1)
        r.add(proto(f"rock{i}", lambda q, k=i: p_rock(q, k)), (x, y, 0), (0, 0, rr.random() * 6.28), (s, s * .9, s * .8))
    for i in range(160):
        x, y = rr.uniform(-8, 8), rr.uniform(-5, 3.4)
        if -1.2 < x < 2.1 and -1.2 < y < 2.8: continue
        s = rr.uniform(.03, .08); r.blob(s, (x, y, s * .25), ROCK, i, (1, rr.uniform(.7, 1.2), .6), (0, 0, rr.random() * 6), sub=1, rough=.3)
    r.build(scn, "r_rocks")
    d = G()
    for (x0, y0, a, ln) in ((3.6, 2.6, .25, 2.6), (-3.8, 3.0, -.3, 3.0), (6.5, -1.5, 1.1, 2.2)):
        pts = [(x0 + math.cos(a) * ln * t, y0 + math.sin(a) * ln * t + .15 * math.sin(t * 6), .1 + .05 * math.sin(t * 9)) for t in [i / 8 for i in range(9)]]
        d.tube(pts, .1, DWOOD, 7, [1.2 - .5 * i / 8 + .1 * math.sin(i * 2) for i in range(9)])
        d.tube([pts[3], (pts[3][0] + .1, pts[3][1] + .3, .35)], .035, DWOOD, 5, [1, .5])
    d.build(scn, "r_driftwood")
    rd = G(); rs = proto("reed", lambda q: p_tuft(q, REED, 1.1, 20, 3))
    for i in range(22): rd.add(rs, (rr.uniform(-12, 12), rr.uniform(3.7, 4.2), 0), (0, 0, rr.random() * 6), rr.uniform(.8, 1.5))
    for i in range(16): rd.add(rs, (rr.uniform(-12, 12), rr.uniform(9.6, 10.4), 0), (0, 0, rr.random() * 6), rr.uniform(.8, 1.5))
    rd.build(scn, "r_reeds")


# ====================================================================== dress(scn)
def parked_wagon(scn, loc, rz):
    root = empty(scn, "dec_wagon", loc, rot=(0, 0, rz)); _wagon_body(scn, root, parked=True); wm = None
    for x in (-.72, .72):
        for y in (-.2, 1.4):
            if wm is None:
                gg = G(); p_wheel(gg); o = gg.build(scn, "w_wheel", (x, y, .5), parent=root); wm = o.data
            else:
                o = bpy.data.objects.new("w_wheel", wm); o.location, o.parent = (x, y, .5), root; scn.collection.objects.link(o)


class D:
    def __init__(s, scn, seed, keep=(), xmax=1e9):
        s.scn, s.keep, s.xmax, s.g = scn, list(keep), xmax, {}; R.seed(seed)

    def G(s, k): return s.g.setdefault(k, G())

    def ok(s, x, y, h=0, rad=0):
        if x > s.xmax: return False
        return not any(x0 - rad <= x <= x1 + rad and y0 - rad <= y <= y1 + rad and h > hm for x0, y0, x1, y1, hm in s.keep)

    def pts(s, n, samp, h=0, rad=0):
        out, t = [], 0
        while len(out) < n and t < n * 30:
            t += 1; x, y = samp()
            if s.ok(x, y, h, rad): out.append((x, y))
        return out

    def rect(s, x0, y0, x1, y1): return lambda: (R.uniform(x0, x1), R.uniform(y0, y1))

    def ring(s, r0, r1, a0=0, a1=2 * pi, cx=0, cy=0):
        def f():
            a, r = R.uniform(a0, a1), R.uniform(r0, r1); return cx + r * math.cos(a), cy + r * math.sin(a)
        return f

    def rocks(s, n, samp, r0, r1, key="rocks"):
        for x, y in s.pts(n, samp, r1 * .8, r1):
            r = R.uniform(r0, r1)
            s.G(key).add(_rk(R.randrange(6)), (x, y, 0), (0, 0, R.random() * 6.28), (r * R.uniform(.9, 1.3), r * R.uniform(.8, 1.2), r * R.uniform(.55, .9)))

    def tufts(s, n, samp, mat, h0=.2, h1=.4, key="tufts"):
        for x, y in s.pts(n, samp, h1):
            s.G(key).add(_tf(mat, R.randrange(4)), (x, y, 0), (0, 0, R.random() * 6.28), R.uniform(h0, h1) / .3)

    def bushes(s, n, samp):
        for x, y in s.pts(n, samp, .8, .6): s.G("bush").add(_bk(R.randrange(3)), (x, y, 0), (0, 0, R.random() * 6.28), R.uniform(.9, 1.6))

    def trees(s, n, samp, scale=(.9, 1.3), pine=.4):
        for x, y in s.pts(n, samp, 6, 2):
            k = R.randrange(3)
            if R.random() < pine: s.G("pines").add(_pk(k), (x, y, 0), (0, 0, R.random() * 6), R.uniform(*scale))
            else: s.G("trees").add(_tk(k), (x, y, 0), (0, 0, R.random() * 6), R.uniform(*scale))

    def mesas(s, n, samp):
        for x, y in s.pts(n, samp):
            rad, h = R.uniform(14, 34), R.uniform(10, 30)
            s.G("mesa").lathe([(0, 0), (1, 0), (.86, .3), (.9, .45), (.72, .7), (.7, 1), (0, 1)], (x, y, 0), MESA, seg=18, jitter=.2, sc=(rad, rad * R.uniform(.7, 1), h), smooth=False)

    def hills(s, n, samp):
        for x, y in s.pts(n, samp):
            r = R.uniform(10, 24); s.G("hill").blob(1, (x, y, -.5), FARHILL, R.randrange(99), (r * 1.7, r, r * .3), sub=2, rough=.18, flat=-.3, smooth=True)

    def line(s, x0, y0, x1, y1, step=3.0, key="fence", fn=None):
        L = math.hypot(x1 - x0, y1 - y0); a = math.atan2(y1 - y0, x1 - x0); n = max(1, int(L / step))
        for i in range(n):
            t = (i + .5) / n; x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            if s.ok(x, y, 1.2): s.G(key).add(proto("rail3", lambda q: p_post_rail(q, step)), (x, y, 0), (0, 0, a))

    def poles(s, pts, along='x'):
        pg = s.G("poles")
        for x, y in pts: pg.add(proto("pole", p_pole), (x, y, 0), (0, 0, 0 if along == 'x' else pi / 2))
        for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
            for off in (-.8, 0, .8):
                n = 12; w = []
                for i in range(n + 1):
                    t = i / n; sag = .55 * 4 * t * (1 - t)
                    if along == 'x': w.append((xa + (xb - xa) * t, ya + off, 7.14 - sag))
                    else: w.append((xa + off, ya + (yb - ya) * t, 7.14 - sag))
                pg.tube(w, .012, BLACKM, 4)

    def done(s):
        for k, g in s.g.items(): g.build(s.scn, "dec_" + k)


def _rk(k): return proto(f"rock{k}", lambda q: p_rock(q, k))
def _bk(k): return proto(f"bush{k}", lambda q: p_bush(q, k))
def _pk(k): return proto(f"pine{k}", lambda q: p_pine(q, k))
def _tk(k): return proto(f"tree{k}", lambda q: p_tree(q, k))
def _tf(mat, k): return proto(f"tuft{mat.name}{k}", lambda q: p_tuft(q, mat, .3, 14, k))


def _horizon(d, n_mesa=9, n_hill=10, n_tl=14, a0=0, a1=2 * pi):
    d.mesas(n_mesa, d.ring(105, 140, a0, a1)); d.hills(n_hill, d.ring(60, 100, a0, a1))
    d.trees(n_tl, d.ring(28, 75, a0, a1), (1, 1.6), .5)


def _square(scn):
    d = D(scn, 21, [(-3.2, -11, 6.5, 2.6, .4)], xmax=70)
    texts = []; g = d.G("bldg"); rr = _rnd.Random(5); mats = [TEAL, WOOD, DTEAL, HAT]
    for i in range(7): building(g, texts, (-15.6 + i * 5.2, 14), 0, rr.uniform(4.5, 6.4), mats[i % 4], i + 3, rail=(i == 1))
    for k, y in enumerate((-3.2, 2.0)):
        building(g, texts, (-13, y), pi / 2, rr.uniform(4.2, 5.8), mats[(k + 1) % 4], k + 1, rail=(k == 0))
        building(g, texts, (13, y), -pi / 2, rr.uniform(4.2, 5.8), mats[(k + 2) % 4], k + 5)
    _signs(scn, texts)
    _horizon(d, 9, 10, 16)
    for x, y, rz in ((-3.6, 3.0, .3), (-4.3, 3.7, 1.0), (3.4, 3.2, -.4), (-3.9, 2.9, 0)): d.G("crates").add(proto("crate", p_crate), (x, y, 0), (0, 0, rz))
    for x, y in ((3.8, 3.1), (-3.3, 4.2), (4.5, 3.9)): d.G("crates").add(proto("barrel", p_barrel), (x, y, 0), (0, 0, 0))
    for x, y in ((-7.8, 5.6), (-8.6, 4.6), (7.6, 6)): d.G("crates").add(proto("bale", p_bale), (x, y, 0), (0, 0, R.uniform(-.5, .5)))
    parked_wagon(scn, (-6.8, 5.6, 0), .5)
    d.rocks(70, d.rect(-30, -14, 30, 40), .1, .4); d.rocks(8, lambda: (R.choice((-1, 1)) * R.uniform(7.2, 11), R.uniform(-12, -3)), .5, .9, "boulders")
    d.tufts(260, d.rect(-30, -14, 30, 40), PRAIRIE, .15, .4); d.bushes(10, lambda: (R.choice((-1, 1)) * R.uniform(8, 16), R.uniform(-12, 8)))
    d.done()


def _prairie(scn, road_along):
    wag = scn.name == "S03"
    keep = [(-9, -14, 9, 20, .35)] if wag else [(-22, -14, 16, 3.8, .35), (-32, 8.6, -12, 14.5, .35)]
    d = D(scn, 31 if wag else 32, keep)
    if wag: box(scn, "dec_road", (2.6, 150, .02), (0, 30, .01), DIRT)
    else: box(scn, "dec_road", (130, 2.6, .02), (0, 0, .01), DIRT)
    _horizon(d, 10, 12, 22)
    d.rocks(90, d.rect(-40, -20, 40, 60), .1, .45); d.tufts(520, d.rect(-35, -14, 35, 60) if wag else d.rect(-50, -14, 50, 40), PRAIRIE, .2, .5)
    d.bushes(16, lambda: (R.choice((-1, 1)) * R.uniform(10, 40), R.uniform(-4, 60)) if wag else (R.uniform(-50, 50), R.choice((R.uniform(14, 40), R.uniform(-40, -14)))))
    if wag:
        d.line(-9.5, -14, -9.5, 70); d.line(9.5, -14, 9.5, 70)
        d.poles([(12.5, y) for y in (-25, 0, 25, 50, 75)], 'y')
        b = d.G("barn"); b.prism([(-4, 0), (4, 0), (4, 3.5), (0, 6), (-4, 3.5)], -5, 5, RED); b.box((8.6, 10.6, .15), (0, 0, 3.5), DWOOD)
        b.box((2.4, .1, 2.6), (0, -5.05, 1.3), WHITE)
        d.g["barn"] = _moved(b, (16, 48, 0), .4)
        for x, y in ((24, 44), (24, 52)): d.G("barn").add(proto("bale", p_bale), (x, y, 0))
    else:
        d.poles([(x, 8.4) for x in (-52, -8, 14, 36, 58)], 'x'); d.line(-60, 16, 60, 16)
    d.done()


def _moved(g, loc, rz):
    o = G(); o.add(g, loc, (0, 0, rz)); return o


def _bed(scn):
    d = D(scn, 41, [(-1.7, -1.5, 2.7, 3.2, .12), (0, -3, 3.4, 1.5, .45)])
    _horizon(d, 8, 8, 0)
    d.trees(18, d.rect(-30, 14, 30, 26), (1, 1.5), .35); d.bushes(16, d.rect(-25, 11, 25, 20))
    d.rocks(70, d.rect(-14, -9, 14, 3.5), .1, .45); d.tufts(160, d.rect(-14, -9, 14, 3.5), PRAIRIE, .12, .3)
    d.rocks(25, d.rect(-30, -14, 30, -6), .3, .9, "boulders")
    d.done()


def _street(scn):
    d = D(scn, 51, [(-2.6, -8, 2.6, 33, .4)])
    texts = []; g = d.G("bldg"); rr = _rnd.Random(8)
    building(g, texts, (-2.8, 31), 0, 6.8, TEAL, 0, items=False); building(g, texts, (2.8, 31), 0, 6.0, WOOD, 2, items=False)
    for i in range(3):
        building(g, texts, (-14, 2 + i * 8), pi / 2, rr.uniform(4.5, 6.2), [DTEAL, HAT, WOOD][i], i + 4, items=False)
        building(g, texts, (14, 4 + i * 8), -pi / 2, rr.uniform(4.5, 6.2), [WOOD, TEAL, DTEAL][i], i + 7, items=False)
    _signs(scn, texts)
    _horizon(d, 9, 8, 14)
    parked_wagon(scn, (3.3, 19, 0), .04); parked_wagon(scn, (-3.3, 22.5, 0), -.05)
    for x, y in ((3.6, 16.4), (-3.6, 25.8)): d.G("props").add(proto("barrel", p_barrel), (x, y, 0), (0, 0, 0))
    for x, y in ((6, 27), (-6.5, 28)): d.G("props").add(proto("bale", p_bale), (x, y, 0))
    d.rocks(40, d.rect(-30, -10, 30, 60), .1, .35); d.tufts(120, d.rect(-30, 26, 30, 70), PRAIRIE, .2, .4)
    d.trees(12, d.rect(-30, 36, 30, 60), (1, 1.5), .4)
    d.done()


def _yard(scn):
    d = D(scn, 61, [(-2.6, -9, 4.6, 7, .4), (-1.5, 2.5, 1, 7, .4)])
    box(scn, "dec_path", (1.8, 14.2, .02), (0, -1, .01), DIRT)
    _horizon(d, 8, 10, 0)
    d.trees(10, lambda: (R.choice((-1, 1)) * R.uniform(10.5, 22), R.uniform(2, 24)), (1, 1.4), .3)
    d.trees(14, d.rect(-35, 24, 35, 45), (1, 1.6), .5)
    d.bushes(14, lambda: (R.choice((-1, 1)) * R.uniform(6, 12), R.uniform(0, 14)))
    d.rocks(30, d.rect(-14, -10, 14, 22), .1, .3); d.tufts(360, d.rect(-18, -12, 18, 24), GRASS, .2, .5)
    d.done()


def dress(scn):
    fn = {"S01": _square, "S06": _square, "S10": _square, "S02": lambda s: _prairie(s, 'x'), "S03": lambda s: _prairie(s, 'y'),
          "S04": _bed, "S07": _street, "S08": _street, "S09": _yard}.get(scn.name)
    if fn: fn(scn)
