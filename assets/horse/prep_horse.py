# Run once: Blender -b --python prep_horse.py  -> horse.blend (collection HORSE_TPL: AnimalArmature + Horse, actions with fake users)
import bpy, os
D = os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=D + "/horse_q.glb")
O = bpy.data.objects
keep = {"AnimalArmature", "Horse"}
for o in list(O):
    if o.name not in keep: O.remove(o)
arm, h = O["AnimalArmature"], O["Horse"]
bpy.context.view_layer.objects.active = h
if h.data.has_custom_normals: bpy.ops.mesh.customdata_custom_splitnormals_clear()
import bmesh   # glTF import splits every face's verts (flat look): weld them so smooth shading + subsurf work
bm = bmesh.new(); bm.from_mesh(h.data); print("verts", len(bm.verts))
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4); print("welded", len(bm.verts))
bm.to_mesh(h.data); bm.free()
h.data.shade_smooth()
if "sharp_edge" in h.data.attributes: h.data.attributes.remove(h.data.attributes["sharp_edge"])
# bake the armature's world matrix (scale 100 + glTF axis rotation) and the size K into the mesh so the mesh object has unit scale (glow()'s displace shell is in object units = metres);
# the armature keeps scale 100*K (its bones are in cm-like units); horses.py must use the same K
import mathutils
K = .45
h.data.transform(mathutils.Matrix.Scale(K, 4) @ h.matrix_world); h.parent = None; h.matrix_world = mathutils.Matrix.Identity(4); h["K"] = K
arm.parent = None; arm.location = (0, 0, 0)
c = bpy.data.collections.new("HORSE_TPL")
for o in (arm, h):
    for k in o.users_collection: k.objects.unlink(o)
    c.objects.link(o)
bpy.context.scene.collection.children.link(c)
for a in list(bpy.data.actions):
    if a.name.startswith("AnimalArmature|"): bpy.data.actions.remove(a)   # glTF duplicates (NLA copies)
    else: a.use_fake_user = True
arm.animation_data_clear()
bpy.ops.wm.save_as_mainfile(filepath=D + "/horse.blend")
