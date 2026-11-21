"""ElevenLabs voiceover for lines.json -> audio/vo.mp3. Key is scoped (no voices_read), so the voice id is fixed."""
import json, sys, urllib.request, urllib.error
from pathlib import Path
env = {k.strip(): v.strip() for k, v in (l.split("=", 1) for l in Path("../.env.local").read_text().splitlines() if "=" in l)}
VOICE = sys.argv[1] if len(sys.argv) > 1 else "nPczCjzI2devNBz1zQrb"  # Brian (premade)
body = {"text": "\n\n".join(json.loads(Path("lines.json").read_text())), "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.45, "similarity_boost": 0.75, "style": 0.2, "speed": 1.1}}
req = urllib.request.Request(f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE}?output_format=mp3_44100_128", json.dumps(body).encode(),
                             {"xi-api-key": env["ELEVENLABS_API_KEY"], "Content-Type": "application/json"})
try: Path("audio/vo.mp3").write_bytes(urllib.request.urlopen(req, timeout=120).read())
except urllib.error.HTTPError as e: sys.exit(f"{e.code} {e.read()[:400]}")
