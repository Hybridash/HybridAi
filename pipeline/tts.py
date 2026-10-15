"""Voiceover: speaks every line of a spec and records exact timings.

usage: python3 tts.py <spec.json> <outdir>
writes <outdir>/voice.wav and <outdir>/timeline.json
"""
import json, os, sys
import numpy as np, soundfile as sf, sherpa_onnx

spec_path, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
spec = json.load(open(spec_path))
M = os.path.join(os.environ.get("MODELS_DIR", os.path.expanduser("~/hybridai-models")), "kokoro-en-v0_19")
SID = spec.get("voice_sid", 6)  # 6 = am_michael, the channel's voice
SPEED = spec.get("voice_speed", 1.0)

tts = sherpa_onnx.OfflineTts(sherpa_onnx.OfflineTtsConfig(
    model=sherpa_onnx.OfflineTtsModelConfig(
        kokoro=sherpa_onnx.OfflineTtsKokoroModelConfig(
            model=f"{M}/model.onnx", voices=f"{M}/voices.bin",
            tokens=f"{M}/tokens.txt", data_dir=f"{M}/espeak-ng-data"),
        num_threads=2)))

SR = 24000
lead = spec.get("lead_in", 0.4)
gap = spec.get("line_gap", 0.25)
scene_gap = spec.get("scene_gap", 0.5)
chunks = [np.zeros(int(lead * SR), np.float32)]
t = lead
lines, scenes = [], []
for si, sc in enumerate(spec["scenes"]):
    start = t
    for text in sc["lines"]:
        g = tts.generate(text, sid=SID, speed=SPEED)
        a = np.asarray(g.samples, np.float32)
        d = len(a) / g.sample_rate
        lines.append({"scene": si, "text": text, "start": t, "end": t + d})
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
print(f"voice {t:.1f}s, {len(lines)} lines")
