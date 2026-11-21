"""Render scenes to renders/scene_NN.mp4. Usage: blender -b brain_myth.blend --python render_all.py"""
import bpy, sys, os

ROOT = os.path.dirname(os.path.abspath(__file__)) if "__file__" in locals() else os.getcwd()
os.makedirs(os.path.join(ROOT, "renders"), exist_ok=True)
names = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

scenes = [s for s in sorted(bpy.data.scenes, key=lambda s: s.name) if s.name.startswith("S")]
print(f"Found {len(scenes)} scenes to render: {[s.name for s in scenes]}", flush=True)

for sc in scenes:
    if not names or sc.name in names:
        sc_num = sc.name[1:] # e.g. "01" from "S01"
        sc.render.filepath = os.path.join(ROOT, f"renders/scene_{sc_num}.mp4")
        print(f"=== Rendering {sc.name} (Frames: {sc.frame_start}..{sc.frame_end}) to {sc.render.filepath} ===", flush=True)
        bpy.ops.render.render(animation=True, scene=sc.name)
        print(f"=== COMPLETED {sc.name} ===", flush=True)
