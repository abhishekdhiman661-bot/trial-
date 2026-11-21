"""Sentence timings from the Parakeet transcript -> segments.json, then one ElevenLabs music clip per segment -> audio/bgm_NN.mp3."""
import json, subprocess, sys, urllib.request, urllib.error
from pathlib import Path
env = {k.strip(): v.strip() for k, v in (l.split("=", 1) for l in Path("../.env.local").read_text().splitlines() if "=" in l)}
FPS, MIN_MS = 30, 10000  # shortcut: assumes the music API rejects clips under 10 s; we generate 10 s and trim
lines, words = json.loads(Path("lines.json").read_text()), json.loads(Path("audio/transcript.json").read_text())
total = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", "audio/vo.mp3"]))
MOODS = ["ominous low drone with a slow heartbeat drum", "warm hopeful fingerpicked acoustic guitar", "the same acoustic guitar turning uneasy and hollow",
         "dark low string swell, a cold discovery", "heavy solemn drum hits, judgement", "strings rising in tension to an abrupt cut-off",
         "sparse mysterious piano notes, curiosity", "one shocking low piano and string hit that rings out", "wry pizzicato strings with a faint church organ",
         "melancholic slow piano resolving softly to silence"]
segs, i = [], 0
for n, line in enumerate(lines):
    k = len(line.split())
    start = words[i]["start"]; i += k
    segs.append({"n": n + 1, "text": line, "start": start, "mood": MOODS[n]})
# "hanged man" was heard as one word, so every index after it is checked by the assert below instead of trusted
for a, b in zip(segs, segs[1:] + [{"start": total}]):
    a["end"] = b["start"]; a["frames"] = round((a["end"] - a["start"]) * FPS)
assert abs(segs[-1]["start"] - 32.4) < 0.5 and all(s["frames"] > 20 for s in segs), segs
Path("segments.json").write_text(json.dumps(segs, indent=1))
for s in segs:
    out = Path(f"audio/bgm_{s['n']:02d}.mp3"); dur = s["end"] - s["start"]
    if not out.exists() or "--force" in sys.argv:
        body = {"prompt": f"Instrumental only, no vocals. Dark old-west cinematic underscore in D minor at 80 BPM, sparse and quiet so a narrator can speak over it. This cue: {s['mood']}.",
                "music_length_ms": max(MIN_MS, int(dur * 1000)), "model_id": "music_v1"}
        req = urllib.request.Request("https://api.elevenlabs.io/v1/music?output_format=mp3_44100_128", json.dumps(body).encode(),
                                     {"xi-api-key": env["ELEVENLABS_API_KEY"], "Content-Type": "application/json"})
        try: raw = urllib.request.urlopen(req, timeout=300).read()
        except urllib.error.HTTPError as e: sys.exit(f"seg {s['n']}: {e.code} {e.read()[:400]}")
        Path("audio/_raw.mp3").write_bytes(raw)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", "audio/_raw.mp3", "-t", f"{dur:.3f}",
                        "-af", f"afade=t=in:d=0.08,afade=t=out:st={max(0, dur - 0.25):.3f}:d=0.25", str(out)], check=True)
    print(s["n"], f"{s['start']:.2f}-{s['end']:.2f}", s["frames"], "f", out.name)
Path("audio/_raw.mp3").unlink(missing_ok=True)
