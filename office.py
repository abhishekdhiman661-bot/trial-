"""Office half of scene S10: a 1987 official signs the pardon. Built at x = X so it can share a scene with the gallows.
Usage from build_scenes.py:  sys.path.insert(0, ROOT); import office; camA = office.build_office(s, X, cut, globals())
The official is the cached MPFB "Judge" (dark suit); his right arm is IK-driven, the fingers are posed into a pen grip, the pen is
parented to the hand bone, and the signature is a bevelled curve whose end factor is keyed in sync with the pen tip.
shortcut: Judge is an old man; add a younger "Official" to characters.py CAST when a 1980s look matters."""
import bpy, math
from mathutils import Matrix, Quaternion, Vector, Euler

pi = math.pi
# signature strokes in page units (1 unit = 1.1 mm, x right, y up from the signature line); Catmull-Rom smoothed
def _sig_path():
    """Cursive signature in page units (1 unit = 1.1 mm, x right, y up from the signature line): slanted looping baseline wave
    with a big first capital and two ascenders, then an underline swoop back to the left."""
    G = lambda t, c, w: math.exp(-((t - c) / w) ** 2)
    out = []
    for i in range(401):
        t = i / 400; ph = 2 * pi * 7 * t
        amp = (9 + 26 * G(t, .06, .06) + 12 * G(t, .36, .05) + 10 * G(t, .64, .05) - 3 * t) * (.7 + .3 * math.sin(ph * .37 + 1.3))
        y = amp * (.5 - .5 * math.cos(ph)); x = 92 * t + 5.5 * math.sin(ph) + .45 * y
        out.append((x, y - 4))
    return out + [(104, 6), (112, 0), (96, -6), (66, -9), (34, -10), (8, -8)]


def _catmull(pts, per=14):
    P = [Vector(p) for p in pts]; P = [P[0] * 2 - P[1]] + P + [P[-1] * 2 - P[-2]]
    out = []
    for i in range(1, len(P) - 2):
        a, b, c, d = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(per):
            t = k / per
            out.append(.5 * ((2 * b) + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t * t + (-a + 3 * b - 3 * c + d) * t ** 3))
    out.append(P[-2]); return out


def _resample(pts, n):
    """n+1 points equally spaced by arc length, so curve factor and pen tip share one parameter."""
    L = [0.0]
    for a, b in zip(pts, pts[1:]): L.append(L[-1] + (b - a).length)
    out, j = [], 0
    for i in range(n + 1):
        s = L[-1] * i / n
        while j < len(L) - 2 and L[j + 1] < s: j += 1
        t = (s - L[j]) / max(L[j + 1] - L[j], 1e-9); out.append(pts[j].lerp(pts[j + 1], t))
    return out


def build_office(scn, X, cut, h):
    box, cyl, sph, empty, kf, interp, M, person, pose, camera, fr = (h[k] for k in "box cyl sph empty kf interp M person pose camera fr".split())
    SEATED = h["SEATED"]; F1 = cut - 1
    col = scn.collection
    # ---------- materials (OF_ names cannot collide with textures.py specs) ----------
    DWOOD, PAPER, INK, STEEL = M("darkwood", (.2, .12, .07)), M("paper", (.95, .95, .92)), M("ink", (.02, .02, .05)), M("steel", (.35, .37, .4), .4)
    LEATHER, PEN, BRASS = M("OF_blotter", (.06, .12, .08), .55), M("OF_pen", (.012, .012, .02), .18), M("OF_brass", (.75, .55, .2), .3)
    SEAL, SHADE, WALL, RUG = M("OF_seal", (.5, .03, .03), .35), M("OF_shade", (.05, .35, .15), .4), M("OF_wall", (.2, .27, .27), .8), M("OF_rug", (.3, .1, .09), .9)
    for m in (BRASS, PEN):
        m.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = 1 if m is BRASS else 0
    # ---------- room: walls all round (the camera looks -Y at the far wall), floor over the scene's dirt, ceiling against the sun ----------
    zt = .76                                                    # desk top
    box(scn, "OF_floor", (6, 5, .02), (X, -.5, .01), RUG)
    box(scn, "OF_wall_f", (6, .1, 3), (X, -2.0, 1.5), WALL); box(scn, "OF_wall_b", (6, .1, 3), (X, 2.0, 1.5), WALL)
    box(scn, "OF_wall_l", (.1, 5, 3), (X - 3, -.5, 1.5), WALL); box(scn, "OF_wall_r", (.1, 5, 3), (X + 3, -.5, 1.5), WALL)
    box(scn, "OF_ceil", (6, 5, .1), (X, -.5, 3.05), WALL)
    box(scn, "OF_wains", (6, .06, 1.0), (X, -1.95, .5), DWOOD)                                   # panelling under the far wall
    box(scn, "OF_shelf", (1.4, .3, 1.8), (X - 1.1, -1.8, .9), DWOOD)
    for i in range(4): box(scn, "OF_shelf_b", (1.3, .28, .03), (X - 1.1, -1.78, .3 + i * .42), BRASS)
    box(scn, "OF_frame", (.7, .04, .9), (X + 1.0, -1.93, 1.7), DWOOD); box(scn, "OF_pic", (.6, .02, .8), (X + 1.0, -1.915, 1.7), M("OF_pic", (.35, .4, .3), .8))
    # ---------- desk, blotter, chair ----------
    box(scn, "OF_desk", (1.9, .9, .05), (X, -.1, zt - .025), DWOOD)
    for sx in (-.85, .85): box(scn, "OF_desk_leg", (.08, .8, zt - .05), (X + sx, -.1, (zt - .05) / 2), DWOOD)
    box(scn, "OF_blot", (.48, .38, .008), (X - .2, .08, zt + .004), LEATHER)
    box(scn, "OF_chair_seat", (.5, .5, .06), (X + .1, .52, .45), M("OF_blotter", (.06, .12, .08)))
    box(scn, "OF_chair_back", (.5, .06, .6), (X + .1, .8, .78), M("OF_blotter", (.06, .12, .08)))
    # ---------- the document ----------
    ztop = zt + .0085 + .0005
    doc = empty(scn, "OF_doc", (X - .2, .08, ztop), rot=(0, 0, pi + .1))   # +x_local runs toward the official's right (world -X), +y_local away from him
    box(scn, "OF_paper", (.23, .31, .001), (0, 0, 0), PAPER, parent=doc, off=(0, 0, -.0005))
    TNR = "/System/Library/Fonts/Supplemental/Times New Roman.ttf"
    fnt = bpy.data.fonts.load(TNR) if __import__("os").path.exists(TNR) else None   # serif on macOS, Blender's default font elsewhere

    def text(s, x, y, size, align='LEFT', mat=INK):
        c = bpy.data.curves.new("OF_t", 'FONT'); c.body, c.size, c.align_x = s, size, align
        if fnt: c.font = fnt
        o = bpy.data.objects.new("OF_t", c); o.data.materials.append(mat); o.parent, o.location = doc, (x, y, .0003)
        col.objects.link(o); return o
    text("OFFICE OF THE GOVERNOR", 0, .125, .0105, 'CENTER'); text("STATE EXECUTIVE DEPARTMENT", 0, .108, .0062, 'CENTER')
    box(scn, "OF_rule", (.19, .0012, .0004), (0, .097, 0), INK, parent=doc); box(scn, "OF_rule", (.19, .0006, .0004), (0, .094, 0), INK, parent=doc)
    text("POSTHUMOUS PARDON", 0, .067, .0165, 'CENTER')
    body = ["WHEREAS, in the year 1887, a man was", "convicted of murder in this State and put", "to death by hanging; and WHEREAS the said",
            "conviction has since been found to rest", "upon no sufficient proof of guilt;", "NOW, THEREFORE, I do hereby grant a full",
            "and unconditional pardon, effective this", "day, to the man so condemned."]
    for i, s_ in enumerate(body): text(s_, -.088, .035 - i * .0135, .0073)
    text("Given under my hand and the Great Seal", -.088, -.082 + .0, .0058); text("of this State, this 14th day of March, 1987.", -.088, -.0905, .0058)
    box(scn, "OF_hr", (.16, .0007, .0004), (.04, -.1, 0), INK, parent=doc)
    text("Governor", .04, -.1086, .0062, 'CENTER')
    seal = cyl(scn, "OF_seal", .0185, .0016, (-.088, -.098, .0008), SEAL, parent=doc, seg=24)
    cyl(scn, "OF_seal_ring", .0135, .0022, (-.088, -.098, .0009), SEAL, parent=doc, seg=24)
    for dx in (-.004, .004): box(scn, "OF_ribbon", (.006, .03, .0006), (-.088 + dx, -.118, .0003), M("OF_gold", (.7, .5, .1), .4), parent=doc, rot=(0, 0, dx * 30))
    # ---------- desk props ----------
    box(scn, "OF_name", (.2, .035, .045), (X + .35, -.3, zt + .02), BRASS, rot=(0, 0, .15))
    cyl(scn, "OF_lamp_base", .08, .02, (X - .8, -.25, zt + .01), BRASS); cyl(scn, "OF_lamp_stem", .012, .3, (X - .8, -.25, zt + .17), BRASS)
    cyl(scn, "OF_lamp_shade", .1, .1, (X - .8, -.25, zt + .38), SHADE, r2=.05, rot=(0, 0, 0))
    cyl(scn, "OF_inkwell", .03, .04, (X + .3, .05, zt + .02), M("OF_ink_glass", (.02, .02, .06), .1))
    cyl(scn, "OF_pen2", .005, .15, (X + .15, .25, zt + .006), PEN, axis='X', rot=(0, 0, .5))
    # ---------- the official ----------
    P = person(scn, "OF_official", (X + .12, .52, -.5), "Judge"); pose(P, **SEATED)
    rig, root = P["rig"], P["root"]


    VL = scn.view_layers[0]

    def ev():
        VL.update(); return rig.evaluated_get(VL.depsgraph)

    def wb(name, tail=False):          # world position of a bone head/tail in the evaluated pose
        E = ev(); pb = E.pose.bones[name]; return E.matrix_world @ (pb.tail if tail else pb.head)

    # ---------- the signature: path in page space, curve + pen-tip positions share one arc-length parameter ----------
    pts = _resample(_catmull(_sig_path(), 3), 500)
    loc = [Vector((-.05 + p.x * .00135, -.09 + p.y * .00135, 0)) for p in pts]
    sig = bpy.data.curves.new("OF_sig", 'CURVE'); sig.dimensions, sig.bevel_depth, sig.bevel_resolution, sig.use_fill_caps = '3D', .0009, 3, True
    sig.bevel_factor_mapping_end = 'SPLINE'
    sp = sig.splines.new('POLY'); sp.points.add(len(loc) - 1)
    for p, v in zip(sp.points, loc): p.co = (v.x, v.y, 0, 1)
    sob = bpy.data.objects.new("OF_signature", sig); sob.data.materials.append(INK); sob.parent, sob.location = doc, (0, 0, .0006)
    col.objects.link(sob)
    VL.update(); DOCM = doc.matrix_world.copy()
    world = [DOCM @ Vector((v.x, v.y, .0006)) for v in loc]
    f0, f1 = fr(10, 33.0) - 5, cut - 12        # pen lands just before "pardon", signature done a little before the cut
    def path(f):                                # pen tip on the paper at frame f (clamped)
        t = min(max((f - f0) / (f1 - f0), 0), 1) * (len(world) - 1); i = min(int(t), len(world) - 2)
        return world[i].lerp(world[i + 1], t - i)

    # ---------- arms: IK on the forearms, hand orientation copied from a control empty ----------
    for pbn in rig.pose.bones: pbn.rotation_mode = 'QUATERNION'
    R0 = {}
    for S, sfx in (("R", "_r"), ("L", "_l")):
        R0[S] = rig.matrix_world.to_quaternion() @ rig.data.bones["hand" + sfx].matrix_local.to_quaternion()
    ctl, pole = empty(scn, "OF_wrist_R"), empty(scn, "OF_pole_R", (X - .3, .75, .7))
    ctlL, poleL = empty(scn, "OF_wrist_L"), empty(scn, "OF_pole_L", (X + .5, .5, .85))
    for T, PO, sfx in ((ctl, pole, "_r"), (ctlL, poleL, "_l")):
        ik = rig.pose.bones["lowerarm" + sfx].constraints.new('IK'); ik.target, ik.pole_target, ik.pole_angle, ik.chain_count = T, PO, -pi / 2, 2
        cr = rig.pose.bones["hand" + sfx].constraints.new('COPY_ROTATION'); cr.target = T
        T.rotation_mode = 'QUATERNION'

    def hand_q(S, d, roll):
        """World orientation of the hand bone: fingers along d, rolled about d from the rest palm-inward pose."""
        d = Vector(d).normalized(); rest = R0[S] @ Vector((0, 1, 0))
        return Quaternion(d, roll) @ rest.rotation_difference(d) @ R0[S]

    # finger curls about each bone's local X (radians); fingers: base, mid, tip joint
    FING = h.get("OF_FING") or {"index": (.6, .7, .4), "middle": (.9, 1.0, .6), "ring": (1.3, 1.3, .9), "pinky": (1.4, 1.4, 1.0),
                                "thumb": (.3, .4, .3)}
    def curl(sfx, spec, extra=0.0):
        for fn, ang in spec.items():
            for j, a in enumerate(ang):
                pb = rig.pose.bones[f"{fn}_0{j + 1}{sfx}"]; pb.rotation_mode = 'XYZ'; pb.rotation_euler = (a + (extra if fn in ("index", "middle", "thumb") else 0), 0, 0)
    curl("_r", FING); curl("_l", {k: (.15, .2, .15) for k in FING})
    # reference pose: pen tip on the start of the signature, hand aimed along the stroke direction
    DIRR, ROLLR = Vector((.1, -1, -.12)), -1.15
    ctl.rotation_quaternion = hand_q("R", DIRR, ROLLR)
    ctl.location = path(f0) + Vector((0, .1, .05)); ctlL.location = (X + .02, .0, ztop + .035)
    ctlL.rotation_quaternion = hand_q("L", (0, -1, -.05), pi / 2)
    # ---------- pen: built along +Z with the tip at the origin, placed between thumb and index pads, parented to the hand bone ----------
    Tt, Ti = wb("thumb_03_r", True), wb("index_03_r", True)
    C = (Tt + Ti) / 2; a = Vector(h.get("OF_PENAXIS") or (-.3, .45, .84)).normalized()
    tip0 = C - a * h.get("OF_GRIPD", .035)
    pen = empty(scn, "OF_pen", tip0); pen.rotation_mode = 'QUATERNION'; pen.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(a)
    k = dict(parent=pen)
    cyl(scn, "OF_pen_nib", .0012, .016, (0, 0, 0), STEEL, r2=.0042, off=(0, 0, .008), **k)
    cyl(scn, "OF_pen_grip", .0046, .028, (0, 0, 0), PEN, r2=.0058, off=(0, 0, .03), **k)
    cyl(scn, "OF_pen_barrel", .0058, .085, (0, 0, 0), PEN, off=(0, 0, .0865), **k)
    cyl(scn, "OF_pen_band", .0061, .004, (0, 0, 0), BRASS, off=(0, 0, .1), **k)
    cyl(scn, "OF_pen_end", .0058, .018, (0, 0, 0), PEN, r2=.0042, off=(0, 0, .1415), **k)
    box(scn, "OF_pen_clip", (.0014, .0035, .042), (0, 0, 0), BRASS, off=(.0066, 0, .105), **k)
    sph(scn, "OF_pen_clipball", .0022, (.0066, 0, .0835), BRASS, **k)
    VL.update(); E_ = ev(); pbh = E_.pose.bones["hand_r"]
    pen.parent, pen.parent_type, pen.parent_bone = rig, 'BONE', "hand_r"
    pen.matrix_parent_inverse = (E_.matrix_world @ pbh.matrix @ Matrix.Translation((0, pbh.length, 0))).inverted()
    # tip offset from the wrist (hand bone head) in the control frame: lets us solve the wrist from the wanted tip position
    Lt = ctl.rotation_quaternion.inverted() @ (tip0 - wb("hand_r"))

    # ---------- animation: the pen tip is the master; wrist drifts smoothly, the residual is wrist rotation + finger flex ----------
    def ease(u): u = min(max(u, 0), 1); return u * u * (3 - 2 * u)
    p0, pN = path(f0), path(f1)
    H0 = p0 + Vector(h.get("OF_HOVER") or (-.07, -.07, .09))
    def tip_at(f):
        if f < f0: return H0.lerp(p0, ease((f - 1) / (f0 - 1)))
        if f <= f1: return path(f)
        return pN + Vector((0, 0, .04 * ease((f - f1) / 6))) + (DOCM.to_3x3() @ Vector((.02, .0, 0))) * ease((f - f1) / (F1 - f1 + 1))
    frames = list(range(1, F1 + 1)); T = {f: tip_at(f) for f in frames}
    Q0 = ctl.rotation_quaternion.copy(); LW = Q0 @ Lt; W = 7
    Dinv = DOCM.to_3x3().inverted()
    for f in frames:
        lo = sum((T[min(max(g, 1), F1)] for g in range(f - W, f + W + 1)), Vector()) / (2 * W + 1)
        w0 = lo - LW; e = T[f] - (w0 + LW)
        Rq = LW.rotation_difference(LW + e) @ Q0
        ctl.rotation_quaternion = Rq; ctl.location = T[f] - Rq @ Lt
        ctl.keyframe_insert("location", frame=f); ctl.keyframe_insert("rotation_quaternion", frame=f)
        dy = (Dinv @ (T[f] - lo)).y; fx = -h.get("OF_FLEX", .1) * max(-1, min(1, dy / .008))
        for fn in ("index", "middle", "thumb"):
            for j in (1, 2):
                pb = rig.pose.bones[f"{fn}_0{j}_r"]; pb.rotation_euler.x = FING[fn][j - 1] + fx * (1 if j == 1 else .6); pb.keyframe_insert("rotation_euler", index=0, frame=f)
    with interp('LINEAR'):
        for f, v in ((1, 0), (f0, 0), (f1, 1), (F1, 1)): sig.bevel_factor_end = v; sig.keyframe_insert("bevel_factor_end", frame=f)
    for cb in (cb for l in sig.animation_data.action.layers for st in l.strips for cb in st.channelbags):   # 5.x layered action: force linear
        for fc in cb.fcurves:
            for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'

    # ---------- lights (the scene's TX_S10_* lights sit at x=100; these are tied to X) ----------
    def light(name, kind, loc, aim, watt, size, colour=(1, .93, .82)):
        o = bpy.data.objects.new(name, bpy.data.lights.new(name, kind)); col.objects.link(o); o.location = loc
        o.rotation_euler = (Vector(aim) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); o.data.energy, o.data.color = watt, colour
        if kind == 'AREA': o.data.size = size
        return o
    light("OF_key", 'AREA', (X + .45, .35, 1.6), (X - .2, .05, .78), 55, .8)
    light("OF_rim", 'AREA', (X - 1.2, -.9, 1.5), (X - .1, .3, .9), 60, 1.0, (.8, .9, 1))
    light("OF_lampL", 'POINT', (X - .8, -.25, zt + .36), (X - .8, -.25, zt), 25, .08, (1, .75, .45))

    # ---------- camera: from behind his right shoulder, low and close, wide at first, pushing in to the pen tip ----------
    fp = fr(10, 33.28)
    keys = [(1, (X - 1.1, .95, 1.3), (X - .1, .3, .85)), (fp + 6, (X - .6, .38, .95), (X - .27, .14, .8)),
            (f1, (X - .52, .32, .9), (X - .28, .13, .795)), (F1, (X - .5, .33, .91), (X - .25, .13, .795))]
    cam, tgt = camera(scn, keys, lens=30, name="CamOffice")
    cd = cam.data; cd.dof.aperture_fstop = 5.0; cd.dof.focus_object = tgt; cd.shift_y = -.1
    for f, ln in ((1, 26), (fp + 6, 38), (F1, 44)): cd.lens = ln; cd.keyframe_insert("lens", frame=f)
    scn.frame_set(1)
    return cam
