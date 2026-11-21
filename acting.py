"""Facial expressions and body life for the MPFB cast. Usage at the END of build_scenes.py (all scenes exist):
    import acting; acting.init(globals()); acting.act()
Faces: shape keys (characters.py: FACE_KEYS on body, brows, lashes, teeth, tongue; look_* on the eyes). Shape-key values live on the mesh
datablock, which instances share, so every character that gets a face is given its own copy of those meshes first (_own).
Bodies: extra keys on bones pose()/walk() never touch (spine_01-03, neck_01, clavicles, fingers), expressed in the rest-axis frame of the
bone so they ride on top of whatever the parent bones do. Arm gestures key upperarm/lowerarm with pose()'s own maths, but only on
characters whose arms the builder does not animate. Direction convention for look/lean: yaw > 0 turns toward +X, pitch > 0 looks up."""
import bpy, json, math, random, re
from mathutils import Quaternion, Euler, Vector

G = {}
X_AXIS = Vector((1, 0, 0))
CH = re.compile(r"^(Marion|Cameron|Judge|Sheriff|Bride|Folk\d)(\.\d+)?$")
FACE = ["open", "wide", "smile", "frown", "press", "pucker", "snarl", "brow_up_L", "brow_up_R", "brow_dn_L", "brow_dn_R", "brow_in", "wide_eyes", "squint"]
EXPR = {   # key weights (shape keys go up to 2)
    "neutral": {},
    "fear": dict(open=.9, wide_eyes=1.8, brow_up_L=1.8, brow_up_R=1.8, brow_in=1.6, frown=.5),
    "plead": dict(open=.7, brow_in=2, brow_up_L=1, brow_up_R=1, frown=1, wide_eyes=1),
    "shout": dict(open=1.6, wide=.2, brow_dn_L=1.8, brow_dn_R=1.8, squint=.25, snarl=.25),
    "anger": dict(brow_dn_L=2, brow_dn_R=2, squint=.5, snarl=.8, press=.6, frown=.8),
    "smile": dict(smile=2, squint=.4, brow_up_L=.4, brow_up_R=.4),
    "grin": dict(smile=2, open=.5, squint=.5, brow_up_L=.6, brow_up_R=.6),
    "mild": dict(smile=.9, brow_up_L=.2, brow_up_R=.2),
    "uneasy": dict(brow_in=1.4, brow_up_L=.5, brow_up_R=.3, frown=.9, press=.6, squint=.3),
    "shock": dict(open=1.4, wide_eyes=2, brow_up_L=2, brow_up_R=2, brow_in=.4),
    "stern": dict(brow_dn_L=1.4, brow_dn_R=1.4, press=1.2, frown=.8, squint=.4),
    "puzzled": dict(brow_up_L=2, brow_dn_R=1.5, squint=.3, press=.8, pucker=.4, frown=.3),
}
FINGERS = [(n, c) for n, c in (("index", 1), ("middle", 1.1), ("ring", 1.2), ("pinky", 1.3))]

def init(g): G.update(g)
def _F(n, t): return round((t - G["SEGS"][n - 1]["start"]) * G["FPS"]) + 1
def _fend(scn): return scn.frame_end

# ---------- handles ----------
def handle(scn, root):
    rig = next(c for c in root.children if c.type == 'ARMATURE')
    P = {"root": root, "rig": rig, "meshes": [m for m in rig.children if m.type == 'MESH'], "scn": scn, "fx": None, "seed": sum(map(ord, root.name))}
    return P

def people(scn):
    return {o.name.split(".")[0]: handle(scn, o) for o in scn.objects if o.type == 'EMPTY' and CH.match(o.name) and any(c.type == 'ARMATURE' for c in o.children)}

def _own(P):
    """Private copies of the face-carrying meshes (with their own shape keys), so this instance can emote alone."""
    if P["fx"] is not None: return P["fx"]
    fx = []
    for o in P["meshes"]:
        if o.data.shape_keys and o.get("part") in ("body", "face"):
            o.data = o.data.copy(); fx.append((o, o.data.shape_keys.key_blocks))
    P["fx"] = fx; return fx

def _set(P, key, f, v):
    for o, kbs in _own(P):
        if key in kbs: kbs[key].value = v; kbs[key].keyframe_insert("value", frame=f)

# ---------- face ----------
def express(P, f, name, strength=1.0):
    """Key every expression channel at frame f for the named expression (lerps from the previous key)."""
    w = EXPR[name]
    for k in FACE: _set(P, k, f, min(2.0, w.get(k, 0) * strength))

def emote(P, seq, tr=7):
    """seq: [(frame, name[, strength]), ...] ascending. Each expression holds until `tr` frames before the next one."""
    prev = None
    for item in seq:
        f, n = item[0], item[1]; s = item[2] if len(item) > 2 else 1.0
        if prev: express(P, max(prev[0] + 1, f - tr), prev[1], prev[2])
        express(P, f, n, s); prev = (f, n, s)

def blink(P, f, dur=5):
    for d, v in ((0, 0), (dur // 2, 1), (dur, 0)): _set(P, "blink", f + d, v)

def blinks(P, f0, f1, seed=0):
    r = random.Random(P["seed"] + seed); f = f0 + r.randint(8, 50)
    _set(P, "blink", f0, 0)
    while f < f1 - 6: blink(P, f); f += r.randint(55, 110)
    _set(P, "blink", f1, 0)

def talk(P, f0, f1, amp=1.0, seed=0):
    """Jaw flaps like speech between f0 and f1 (separate `talk` channel, adds to any expression)."""
    r = random.Random(P["seed"] + seed + f0); f = f0
    _set(P, "talk", f0, 0)
    while f < f1 - 2: f += r.randint(3, 5); _set(P, "talk", f, amp * r.choice((.15, .5, 1, .8, .3)))
    _set(P, "talk", f1, 0)

def _eyes(P, f, yaw, pitch):
    _set(P, "look_r", f, max(0, yaw) / .5); _set(P, "look_l", f, max(0, -yaw) / .5)
    _set(P, "look_u", f, max(0, pitch) / .35); _set(P, "look_d", f, max(0, -pitch) / .35)

def look(P, f, yaw=0, pitch=0, eyes=None, neck=1.0):
    """Head (neck_01) plus eyeballs. eyes: (yaw, pitch) override, default follows the head."""
    _bone(P, f, "neck_01", x=-pitch * neck, z=yaw * neck)
    ey, ep = (yaw, pitch) if eyes is None else eyes
    _eyes(P, f, max(-.5, min(.5, ey)), max(-.35, min(.35, ep)))

# ---------- body ----------
def _bone(P, f, name, x=0.0, y=0.0, z=0.0):
    """Key bone `name` with an extra rotation (radians about the armature's X/Y/Z, in the parent's frame)."""
    rig = P["rig"]; pb = rig.pose.bones[name]; dp = f'pose.bones["{name}"].rotation_quaternion'
    ad = rig.animation_data
    if f != 1 and not (ad and ad.action and any(fc.data_path == dp for fc in _fcurves(ad.action))):
        pb.keyframe_insert("rotation_quaternion", frame=1)   # anchor the static pose so the first key does not rewrite earlier frames
    R = rig.data.bones[name].matrix_local.to_quaternion()
    pb.rotation_quaternion = R.inverted() @ Euler((x, y, z)).to_quaternion() @ R
    pb.keyframe_insert("rotation_quaternion", frame=f)

def _fcurves(action):
    try: return list(action.fcurves)
    except Exception:
        return [fc for l in action.layers for s in l.strips for b in s.channelbags for fc in b.fcurves]

def spine(P, f, fwd=0, side=0, twist=0):
    """Torso pose spread over spine_01..03. fwd > 0 leans forward, side > 0 leans toward +X, twist > 0 turns toward +X."""
    P["custom"] = True
    for b in ("spine_01", "spine_02", "spine_03"): _bone(P, f, b, x=fwd / 3, y=-side / 3, z=twist / 3)

def slump(P, f, amt=1.0, neck=True):
    """Shoulders drop, chest caves, head bows (neck=False when look() keys the neck too)."""
    spine(P, f, fwd=.22 * amt)
    for b, sg in (("clavicle_l", 1), ("clavicle_r", -1)): _bone(P, f, b, y=sg * .16 * amt)
    if neck: _bone(P, f, "neck_01", x=.35 * amt)

def shrug(P, f, amt=1.0):
    for b, sg in (("clavicle_l", 1), ("clavicle_r", -1)): _bone(P, f, b, y=-sg * .22 * amt)

def idle(P, f0, f1, amp=1.0, seed=0):
    """Breathing and a slow weight sway on the spine, shoulders and neck, keyed every 10 frames."""
    r = random.Random(P["seed"] + seed); ph = [r.uniform(0, 6.28) for _ in range(3)]
    for f in range(f0, f1 + 10, 10):
        f = min(f, f1); t = f / 30
        br = math.sin(t * 2 * math.pi / 3.0 + ph[0])
        spine(P, f, fwd=amp * (.012 * br + .015 * math.sin(t * .8 + ph[1])), side=amp * .035 * math.sin(t * .9 + ph[2]), twist=amp * .03 * math.sin(t * .6 + ph[1]))
        for b, sg in (("clavicle_l", 1), ("clavicle_r", -1)): _bone(P, f, b, y=sg * -amp * .02 * br)
        if f == f1: break

def curl(P, f, S, amt=1.0, point=False, key=True):
    """Finger curl on side S ('L' = -X, 'R' = +X, as pose()). amt 0 open .. 1 fist; point keeps the index straight."""
    s = "_r" if S == "L" else "_l"
    for n, c in FINGERS:
        a = (0 if (point and n == "index") else amt) * c
        for i, k in enumerate((1, 1.3, .9), 1):
            pb = P["rig"].pose.bones[f"{n}_0{i}{s}"]; pb.rotation_quaternion = Quaternion(X_AXIS, a * k * .8)
            if key: pb.keyframe_insert("rotation_quaternion", frame=f)

def relax_hands(P, amt=.35):
    for S in "LR": curl(P, 1, S, amt)   # keyed at 1 so later finger keys have an anchor

def arm(P, f, S, a=0, spread=0, wrap=0, elbow=0):
    """Key one arm exactly like pose() does (use only where the builder does not animate the arms)."""
    rig = P["rig"]; B, PB = rig.data.bones, rig.pose.bones
    s, sx = ("_r", -1) if S == "L" else ("_l", 1); sp = .12 + spread
    def rest(b): return (B[b].tail_local - B[b].head_local).normalized()
    Du = Quaternion(X_AXIS, a) @ rest("upperarm" + s).rotation_difference(Vector((sx * sp, 0, -1)).normalized())
    Dl = Quaternion(X_AXIS, a + elbow) @ rest("lowerarm" + s).rotation_difference(Vector((sx * (sp + wrap), 0, -1)).normalized())
    for b, D, Dp in (("upperarm" + s, Du, Quaternion()), ("lowerarm" + s, Dl, Du)):
        R = B[b].matrix_local.to_quaternion(); PB[b].rotation_quaternion = R.inverted() @ Dp.inverted() @ D @ R
        PB[b].keyframe_insert("rotation_quaternion", frame=f)

def _anchor_arms(P):
    for b in ("upperarm_l", "lowerarm_l", "upperarm_r", "lowerarm_r"): P["rig"].pose.bones[b].keyframe_insert("rotation_quaternion", frame=1)

# ---------- the script ----------
def act(scenes=None):
    S = {n: bpy.data.scenes[f"S{n:02d}"] for n in range(1, 10)}
    T = lambda n, t: max(1, min(S[n].frame_end, _F(n, t)))
    pp = {n: people(S[n]) for n in S}
    for n in S:
        for P in pp[n].values(): relax_hands(P)

    def face(n, who, blk=True):
        P = pp[n][who]; _own(P); blinks(P, 1, S[n].frame_end); return P

    # S01 Marion pleads then denies; crowd stern with a few jeers/points
    P = face(1, "Marion"); e = lambda t: T(1, t)
    emote(P, [(1, "fear"), (e(1.2), "plead", .8), (e(2.72), "plead", 1.2), (e(3.12), "shout", .8), (e(4.5), "plead", 1.1), (S[1].frame_end, "plead", 1)])
    talk(P, e(2.8), e(4.6), 1.0); slump(P, 1, .5, False); slump(P, e(2.4), .3, False); slump(P, e(4.5), .6, False)
    look(P, 1, -.2, .0); look(P, e(1.5), .25, -.1); look(P, e(2.9), 0, 0); look(P, S[1].frame_end, 0, -.05)
    for i in range(9):
        k = f"Folk{i}"
        if k not in pp[1]: continue
        P = pp[1][k]
        if i in (0, 1, 2, 5, 7):
            P = face(1, k)
            if i in (2, 7):
                emote(P, [(1, "stern"), (e(1.3), "anger", 1), (e(2.5), "shout", 1), (e(4.5), "shout", .8)]); talk(P, e(1.3), e(4.5), .8, i)
                _anchor_arms(P); arm(P, e(1.0), "R", 0, 0); arm(P, e(1.6), "R", -1.5, -.12, 0, -.1); arm(P, e(3.0), "R", -1.3, -.12, 0, -.1); arm(P, e(3.4), "R", -1.6, -.12, 0, -.1)
                curl(P, e(1.0), "R", .3); curl(P, e(1.6), "R", 1, point=True)
            else:
                emote(P, [(1, "stern"), (e(2.7), "anger", .8), (e(4.5), "stern", 1.2)])
            look(P, 1, 0, 0)

    # S02 riding off together: Marion (x -.32) and Cameron (x +.32) chat, smiling at each other
    M, C = face(2, "Marion"), face(2, "Cameron"); e = lambda t: T(2, t); Fe = S[2].frame_end
    for P, sg in ((M, 1), (C, -1)):
        emote(P, [(1, "smile", .8), (e(7.0), "grin", .8), (e(9.0), "smile", 1)])
        for t, y in ((5.2, .0), (6.0, .55), (7.2, .0), (8.0, .6), (9.0, .1)): look(P, e(t), sg * y, 0, eyes=(sg * .5, 0) if y > .3 else (0, 0))
    talk(M, e(5.2), e(7.0), .8, 1); talk(C, e(7.0), e(9.0), .8, 2)
    for t, v in ((5, 0), (6.5, .06), (8, 0), (9.5, .06)): spine(M, e(t), fwd=v, side=-v); spine(C, e(t), fwd=.03, side=v)

    # S03 Marion alone, uneasy, glancing at the empty seat (+X)
    M = face(3, "Marion"); e = lambda t: T(3, t)
    emote(M, [(1, "uneasy", .7), (e(10.3), "uneasy", 1.2), (e(12.0), "uneasy", 1.4)])
    for t, y, p in ((1, 0, 0), (10.1, .0, 0), (10.5, .75, -.25), (11.1, .75, -.25), (11.5, 0, 0), (12.2, .5, -.15), (13.0, 0, 0)):
        look(M, e(t), y, p, eyes=(y * 1.4, p))
    slump(M, e(11.0), .5, False)

    # S05 judge, gavel; Marion bows on "sentenced to hang"; sheriff grips his arm
    J = face(5, "Judge"); e = lambda t: T(5, t); h1, h2 = e(17.36), e(17.92)
    emote(J, [(1, "stern", 1.2), (e(17.2), "stern", 1.4)]); talk(J, e(16.4), e(18.0), .7, 5); look(J, 1, 0, -.1); look(J, h1, 0, -.15)
    base = -1.2; _anchor_arms(J); curl(J, 1, "R", .6)
    for f, a in ((1, base), (h1 - 8, -1.9), (h1, -.95), (h1 + 4, -1.3), (h2 - 7, -1.9), (h2, -.95), (h2 + 4, -1.2), (S[5].frame_end, base)): arm(J, f, "R", a, 0, 0, -.15)
    M = pp[5]["Marion"]; slump(M, 1, .1); slump(M, e(17.1), .15); slump(M, e(17.76), .2); slump(M, e(18.2), 1.0); slump(M, S[5].frame_end, 1.0)
    Sh = pp[5]["Sheriff"]; _anchor_arms(Sh); arm(Sh, 1, "L", -.6, -.2, -.3, -.2); curl(Sh, 1, "L", .9)
    spine(Sh, 1, 0, 0, .15)

    # S06 begging, then eyes wide as the trapdoor goes
    M = face(6, "Marion"); e = lambda t: T(6, t); Fe = S[6].frame_end; drop = e(21.12)
    emote(M, [(1, "plead", 1.3), (e(19.5), "plead", 1.6), (e(20.2), "plead", 1.5), (e(20.45), "shock", 1.1), (drop + 8, "shock", 1.3)])
    talk(M, 1, e(20.1), 1.1, 6)
    for t, y in ((1, .5), (e(18.9), -.5), (e(19.5), .45), (e(20.0), -.3)): look(M, t if t > 1 else 1, 0, .05, eyes=(y, .1))
    slump(M, 1, .3, False); slump(M, e(20.4), 0, False); spine(M, drop + 4, fwd=-.1)

    # S07 Cameron strolls, relaxed and curious; townsfolk turn to watch
    C = face(7, "Cameron"); e = lambda t: T(7, t); Fe = S[7].frame_end
    emote(C, [(1, "mild", .8), (e(24.0), "mild", 1.2), (e(25.6), "puzzled", .6)])
    for t, y, p in ((1, 0, 0), (e(22.2), .5, .1), (e(23.0), -.5, .05), (e(23.8), .3, .15), (e(24.6), 0, 0), (e(25.5), 0, 0)): look(C, t, y, p, eyes=(y * 1.2, p))
    for i, (k, P) in enumerate(sorted(pp[7].items())):
        if k == "Cameron": continue
        rig_front = P["root"].matrix_world.to_quaternion() @ Vector((0, -1, 0))   # where he faces
        f0 = T(7, 22.0 + i * .5); f1 = f0 + 24
        P["root"].keyframe_insert("rotation_euler", index=2, frame=1)
        want = Vector((P["root"].matrix_world.translation.x * -1, 0, 0)).normalized()   # street centre line is x = 0
        turn = (math.atan2(want.y, want.x) - math.atan2(rig_front.y, rig_front.x) + math.pi) % (2 * math.pi) - math.pi
        P["root"].keyframe_insert("rotation_euler", index=2, frame=f0)
        P["root"].rotation_euler.z += turn * .55; P["root"].keyframe_insert("rotation_euler", index=2, frame=f1)
        if i < 4: _own(P); emote(P, [(1, "neutral"), (f1, "puzzled" if i % 2 else "shock", .6)])
        look(P, 1, 0, 0); look(P, f1, math.copysign(min(abs(turn) * .45, .8), turn), 0)

    # S08 Cameron: oblivious half-smile -> puzzled; folk behind stagger back in shock
    C = face(8, "Cameron"); e = lambda t: T(8, t); Fe = S[8].frame_end
    emote(C, [(1, "mild", 1.0), (e(27.0), "mild", .9), (e(27.7), "puzzled", 1.1), (Fe, "puzzled", 1.3)])
    look(C, 1, .05, 0); look(C, e(27.1), -.1, .05); look(C, Fe, 0, .1)
    for i in range(3):
        P = face(8, f"Folk{i}"); P["root"].keyframe_insert("location", frame=1); f0 = e(26.7) + i * 2
        emote(P, [(1, "stern", .6), (f0, "shock", 1.1), (Fe, "shock", 1.4)])
        loc = P["root"].location.copy(); P["root"].keyframe_insert("location", frame=f0)
        P["root"].location = loc + Vector((0, .5, 0)); P["root"].keyframe_insert("location", frame=f0 + 12)
        spine(P, 1, 0); spine(P, f0 + 3, fwd=-.25); spine(P, f0 + 14, fwd=-.15); _bone(P, f0 + 3, "neck_01", x=-.2)
        look(P, 1, 0, 0)

    # S09 Cameron runs, panicked glances back; Bride screams
    C = face(9, "Cameron"); e = lambda t: T(9, t); Fe = S[9].frame_end; w1, w2 = e(29.2), e(30.24)
    emote(C, [(1, "uneasy", .8), (e(28.8), "fear", .7), (w2 - 4, "fear", 1.0), (w2 + 6, "puzzled", .8), (Fe, "puzzled", .9)])
    for t, y in ((1, 0), (e(28.3), 0), (e(28.6), 1.5), (e(29.0), 1.5), (e(29.3), 0), (e(29.9), 1.3), (e(30.3), 0)): look(C, t, y, 0, eyes=(.5 if y else 0, 0))
    spine(C, 1, .12); spine(C, Fe, .12)
    B = face(9, "Bride"); _anchor_arms(B); curl(B, 1, "R", 1)
    emote(B, [(1, "anger", 1.0), (e(28.8), "shout", .8), (w1, "shout", .9), (Fe, "shout", .9)]); talk(B, 1, Fe, 1.2, 9)
    for f in range(1, Fe + 6, 6): arm(B, min(f, Fe), "R", -2.4 + .25 * math.sin(f * .9), 0, 0, -.4)
    for f in range(1, Fe + 12, 12): spine(B, min(f, Fe), fwd=.08 + .04 * math.sin(f), twist=.1 * math.sin(f * .7))
    look(B, 1, 0, .1)
    for n in S:   # everyone whose torso nobody scripted breathes and sways
        for P in pp[n].values():
            if not P.get("custom"): idle(P, 1, S[n].frame_end, seed=n)
