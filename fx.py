"""Edge-only yellow highlight for build_scenes.py: inverted-hull shells (front faces culled in the shader, so only
the rim outside the silhouette shows) in a tight bright line plus a wide soft halo. The object's own material stays visible.
In build_scenes.py replace the `def glow(...)` block with:  import fx; glow = fx.glow
Shared mesh data is never modified: shells are new objects on the same data, with a Displace modifier (after the Armature
modifier for skinned meshes, so the shell follows the pose)."""
import bpy

# (thickness in object units, peak alpha, emission strength, colour)
EDGE = (.55, .8)   # Layer Weight facing range that fades the shell in
LAYERS = ((.005, 1.0, 10.0, (1, .78, .05, 1)), (.014, .55, 5.0, (1, .8, .1, 1)), (.035, .16, 3.0, (1, .85, .15, 1)))


def _mat(scn, i, strength, col):
    m = bpy.data.materials.new(f"{scn.name}_glow{i}"); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    n = nt.nodes.new
    geo, mul, em, tr, mix, out, fade = (n("ShaderNodeNewGeometry"), n("ShaderNodeMath"), n("ShaderNodeEmission"),
        n("ShaderNodeBsdfTransparent"), n("ShaderNodeMixShader"), n("ShaderNodeOutputMaterial"), n("ShaderNodeObjectInfo"))
    mul.operation = 'MULTIPLY'     # only the inside of the shell's far wall (backfaces) is visible, times the fade
    em.inputs["Color"].default_value, em.inputs["Strength"].default_value = col, strength
    lw, rng, gate = n("ShaderNodeLayerWeight"), n("ShaderNodeMapRange"), n("ShaderNodeMath")
    rng.inputs[1].default_value, rng.inputs[2].default_value = EDGE   # grazing only: keeps pockets and seams inside the silhouette dark
    gate.operation = 'MULTIPLY'; nt.links.new(lw.outputs["Facing"], rng.inputs[0])
    nt.links.new(geo.outputs["Backfacing"], gate.inputs[0]); nt.links.new(rng.outputs[0], gate.inputs[1])
    nt.links.new(gate.outputs[0], mul.inputs[0]); nt.links.new(fade.outputs["Alpha"], mul.inputs[1])
    nt.links.new(mul.outputs[0], mix.inputs[0]); nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    m.surface_render_method = 'BLENDED'; m.use_transparency_overlap = True   # no depth write: the near wall must not hide the far wall
    return m


def glow(scn, objs, f_on, f_off):
    for i, (thick, alpha, strength, col) in enumerate(LAYERS):
        m = _mat(scn, i, strength, col)
        for o in objs:
            g = bpy.data.objects.new(f"{o.name}_glow{i}", o.data)
            scn.collection.objects.link(g)
            g.parent, g.matrix_parent_inverse = o.parent, o.matrix_parent_inverse
            g.location, g.rotation_euler, g.scale = o.location, o.rotation_euler, o.scale
            if o.animation_data and o.animation_data.action:   # follow the object's own animation (plain meshes)
                g.parent, g.matrix_parent_inverse = o, g.matrix_parent_inverse.__class__.Identity(4)
                g.location, g.rotation_euler, g.scale = (0, 0, 0), (0, 0, 0), (1, 1, 1)
            for md in o.modifiers:
                if md.type == 'ARMATURE':
                    a = g.modifiers.new("arm", 'ARMATURE'); a.object, a.use_vertex_groups = md.object, True
            d = g.modifiers.new("shell", 'DISPLACE'); d.strength, d.mid_level = thick, 0
            for sl in g.material_slots: sl.link, sl.material = 'OBJECT', m
            g.visible_shadow = False
            for f, a in ((f_on, 0), (f_on + 6, alpha), (f_off - 6, alpha), (f_off, 0)):   # fade rides on the object colour alpha (Object Info)
                g.color = (1, 1, 1, a); g.keyframe_insert("color", frame=f)
