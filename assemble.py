"""Write the HyperFrames edit (edit/index.html + edit/compositions/captions.html) from segments.json and transcript.json."""
import json, re
from pathlib import Path

ROOT = Path(__file__).parent if "__file__" in locals() else Path(".")
FPS, MAXW = 30, 3

segs = json.loads((ROOT / "segments.json").read_text())
lines = json.loads((ROOT / "lines.json").read_text())
tw = json.loads((ROOT / "audio/transcript.json").read_text())

TOTAL = sum(s["frames"] for s in segs) / FPS

# Match script words with transcript timings
words = []
idx = 0
for li, line in enumerate(lines):
    for w in line.split():
        t = tw[idx]
        words.append(dict(text=w, start=t["start"], end=t["end"], line=li))
        idx += 1

assert idx == len(tw), f"Word count mismatch: {idx} vs {len(tw)}"

# Group words into 2-3 word caption chunks (Zack D style)
groups, cur = [], []
for k, w in enumerate(words):
    cur.append(w)
    nxt = words[k + 1] if k + 1 < len(words) else None
    if not nxt or len(cur) == MAXW or w["text"][-1] in ",." or (nxt and nxt["start"] - w["end"] >= 0.2) or (nxt and nxt["line"] != w["line"]):
        groups.append(cur)
        cur = []

caps = []
for g, grp in enumerate(groups):
    start = max(0.05, grp[0]["start"])
    end = groups[g + 1][0]["start"] if g + 1 < len(groups) else min(TOTAL, grp[-1]["end"] + 0.3)
    text = re.sub(r"[.,]", "", " ".join(w["text"] for w in grp))
    caps.append(f'    <div id="cap-{g}" class="clip cap" data-start="{start:.3f}" data-duration="{end - start:.3f}" data-track-index="0"><span>{text}</span></div>')

(ROOT / "edit/compositions").mkdir(parents=True, exist_ok=True)
(ROOT / "edit/compositions/captions.html").write_text(f"""<template>
  <style>
    #root {{ position: absolute; inset: 0; }}
    /* Zack D style: white bold, black outline, hard switch on the word */
    .cap {{ position: absolute; left: 80px; right: 80px; top: 1220px; text-align: center; overflow: visible;
      font-family: "Open Sans", "Montserrat", sans-serif; font-weight: 800; font-size: 78px; line-height: 1.1; color: #fff;
      -webkit-text-stroke: 10px #000; paint-order: stroke fill; text-shadow: 0 6px 16px rgba(0,0,0,.7); text-transform: uppercase; }}
  </style>
  <div id="root" data-composition-id="captions" data-width="1080" data-height="1920">
{chr(10).join(caps)}
  </div>
  <script>
    window.__timelines["captions"] = gsap.timeline({{ paused: true }});
  </script>
</template>
""")

vids, t = [], 0.0
for n, s in enumerate(segs, 1):
    d = s["frames"] / FPS
    vids.append(f'      <video id="scene-{n:02d}" class="clip" src="assets/scene_{n:02d}.mp4" muted playsinline data-start="{t:.4f}" data-duration="{d:.4f}" data-track-index="1" style="z-index:{n}"></video>')
    t += d

bgm = [f'      <audio id="bgm-{s["n"]:02d}" class="clip" src="assets/bgm_{s["n"]:02d}.mp3" data-start="{s["start"]:.3f}" data-duration="{s["end"] - s["start"]:.3f}" data-volume="0.22" data-track-index="4"></audio>' for s in segs]

(ROOT / "edit/index.html").write_text(f"""<!doctype html>
<html lang="en" data-resolution="portrait">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ margin: 0; width: 1080px; height: 1920px; overflow: hidden; background: #000; }}
      #root {{ position: relative; width: 100%; height: 100%; }}
      video {{ position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; object-fit: contain; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{TOTAL:.4f}" data-width="1080" data-height="1920">
{chr(10).join(vids)}
      <div id="captions" data-composition-id="captions" data-composition-src="compositions/captions.html" data-track-kind="captions"
        data-start="0" data-duration="{TOTAL:.4f}" data-track-index="2" data-width="1080" data-height="1920" style="z-index:20"></div>
      <audio id="vo" class="clip" src="assets/vo.wav" data-start="0" data-duration="{TOTAL:.4f}" data-volume="1" data-track-index="3"></audio>
{chr(10).join(bgm)}
    </div>
    <script>
      window.__timelines["main"] = gsap.timeline({{ paused: true }});
    </script>
  </body>
</html>
""")

print(f"Generated {len(caps)} captions across {TOTAL:.2f}s timeline.")
