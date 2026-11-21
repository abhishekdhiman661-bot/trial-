# 3D Story Short: 10% Brain Myth 🧠

A 3D vertical story short in **Zack D Films style** narrated in Hinglish, fully built via code with Blender and HyperFrames.

- **Audio Narration**: 39.84s custom voice narration (`audio/vo.wav`)
- **Visuals**: 8 Procedural 3D scenes built in Blender (`build_scenes.py`)
- **Captions**: 52 dynamic text-stroke cues (`captions.srt` / `edit/compositions/captions.html`)
- **Cloud Rendering**: Automated GitHub Actions CI workflow in `.github/workflows/render.yml`

## Cloud Render Instructions

Pushing to `main` branch automatically triggers the `.github/workflows/render.yml` pipeline:
1. Downloads Blender 4.2 LTS on Ubuntu Linux runner.
2. Builds all 8 3D scenes from `build_scenes.py` into `brain_myth.blend`.
3. Renders animation frames into 8 MP4 scene videos.
4. Combines video layers with custom voiceover and burnt-in Zack D captions into `final_short.mp4`.
5. Uploads `final_short.mp4` to GitHub Actions **Artifacts** tab for instant download.
