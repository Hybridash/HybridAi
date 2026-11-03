"""Voiceover: speaks every line of a spec and records exact timings.

usage: python3 tts.py <spec.json> <outdir>
writes <outdir>/voice.wav and <outdir>/timeline.json

A line is a string (the bot speaks) or {"text", "who": "bot"|"human"} for two-character skits.
Toon Shorts use VoiceStudio (OmniVoice voice design) on the owner's Mac, at $VOICESTUDIO_URL
(default http://localhost:3900). If it isn't reachable, the build falls back to Kokoro and says so.
"""
import io, json, os, sys, urllib.request
import numpy as np, soundfile as sf

spec_path, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
spec = json.load(open(spec_path))
TOON = spec.get("style") == "toon"
SPEED = spec.get("voice_speed", 1.0)
SR = 24000
VS = os.environ.get("VOICESTUDIO_URL", "http://localhost:3900")

# Owner's pick (2026-11-02, "skit 1"): a young casual guy and a calm, lower, slower AI.
# The same instruct + seed gives the same voice on every line.
VS_VOICES = {"bot": {"instruct": "male, young adult, low pitch, american accent", "seed": 11, "speed": 0.9},
             "human": {"instruct": "male, young adult, moderate pitch, american accent", "seed": 7, "speed": 1.0}}
# Kokoro v1.0 speaker ids: 16 = am_michael (weekly videos), 12 = am_echo, 15 = am_liam (toon fallback).
KOKORO = ({"bot": {"sid": 12, "speed": 0.9}, "human": {"sid": 15}} if TOON else {"bot": {"sid": 16}, "human": {"sid": 15}})
if "voice_sid" in spec: KOKORO["bot"] = {"sid": spec["voice_sid"]}

def vs_up():
    try: return urllib.request.urlopen(f"{VS}/engines/tts", timeout=3).status == 200
    except OSError: return False

def vs_say(text, v):
    body = {"model": "omnivoice", "input": text, "instruct": v["instruct"], "seed": v["seed"],
            "speed": SPEED * v.get("speed", 1.0), "response_format": "wav"}
    req = urllib.request.Request(f"{VS}/v1/audio/speech", json.dumps(body).encode(), {"content-type": "application/json"})
    a, sr = sf.read(io.BytesIO(urllib.request.urlopen(req, timeout=300).read()), dtype="float32")
    assert sr == SR, f"VoiceStudio returned {sr} Hz, expected {SR}"
    return a

_kokoro = None
def kokoro_say(text, v):
    global _kokoro
    if _kokoro is None:
        import sherpa_onnx
        M = os.path.join(os.environ.get("MODELS_DIR", os.path.expanduser("~/hybridai-models")), "kokoro-multi-lang-v1_0")
        _kokoro = sherpa_onnx.OfflineTts(sherpa_onnx.OfflineTtsConfig(
            model=sherpa_onnx.OfflineTtsModelConfig(
                kokoro=sherpa_onnx.OfflineTtsKokoroModelConfig(
                    model=f"{M}/model.onnx", voices=f"{M}/voices.bin",
                    tokens=f"{M}/tokens.txt", data_dir=f"{M}/espeak-ng-data",
                    dict_dir=f"{M}/dict", lexicon=f"{M}/lexicon-us-en.txt"),
                num_threads=2)))
    return np.asarray(_kokoro.generate(text, sid=v["sid"], speed=SPEED * v.get("speed", 1.0)).samples, np.float32)

USE_VS = TOON and vs_up()
if TOON and not USE_VS: print(f"WARNING: VoiceStudio not reachable at {VS}; using Kokoro voices instead")
say, VOICES = (vs_say, {**VS_VOICES, **spec.get("voices", {})}) if USE_VS else (kokoro_say, KOKORO)

lead = spec.get("lead_in", 0.4)
gap = spec.get("line_gap", 0.25)
scene_gap = spec.get("scene_gap", 0.5)
chunks = [np.zeros(int(lead * SR), np.float32)]
t = lead
lines, scenes = [], []
for si, sc in enumerate(spec["scenes"]):
    start = t
    for ln in sc["lines"]:
        text, who = (ln, "bot") if isinstance(ln, str) else (ln["text"], ln.get("who", "bot"))
        a = say(text, VOICES[who])
        d = len(a) / SR
        lines.append({"scene": si, "text": text, "who": who, "start": t, "end": t + d})
        chunks += [a, np.zeros(int(gap * SR), np.float32)]
        t += d + gap
    chunks.append(np.zeros(int(scene_gap * SR), np.float32))
    t += scene_gap
    scenes.append({"start": start, "end": t})
tail = spec.get("tail", 1.2)
chunks.append(np.zeros(int(tail * SR), np.float32))
t += tail
sf.write(f"{out}/voice.wav", np.concatenate(chunks), SR)
json.dump({"duration": t, "scenes": scenes, "lines": lines}, open(f"{out}/timeline.json", "w"), indent=1)
print(f"voice {t:.1f}s, {len(lines)} lines ({'VoiceStudio' if USE_VS else 'Kokoro'})")
