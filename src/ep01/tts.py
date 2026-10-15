import json, sys, numpy as np, soundfile as sf, sherpa_onnx

M = "/home/claude/models/kokoro-en-v0_19"
SID = int(sys.argv[1]) if len(sys.argv) > 1 else 6  # am_michael
cfg = sherpa_onnx.OfflineTtsConfig(
    model=sherpa_onnx.OfflineTtsModelConfig(
        kokoro=sherpa_onnx.OfflineTtsKokoroModelConfig(
            model=f"{M}/model.onnx", voices=f"{M}/voices.bin",
            tokens=f"{M}/tokens.txt", data_dir=f"{M}/espeak-ng-data"),
        num_threads=2),
)
tts = sherpa_onnx.OfflineTts(cfg)
script = json.load(open("/home/claude/ep1/script.json"))
sr = None
audio, timeline, t = [], [], 0.6
audio.append(np.zeros(int(0.6 * 24000), dtype=np.float32))
for si, sc in enumerate(script):
    start = t
    for line in sc["lines"]:
        g = tts.generate(line, sid=SID, speed=1.0)
        sr = g.sample_rate
        a = np.array(g.samples, dtype=np.float32)
        d = len(a) / sr
        timeline.append({"scene": si, "text": line, "start": t, "end": t + d})
        audio.append(a)
        gap = 0.28
        audio.append(np.zeros(int(gap * sr), dtype=np.float32))
        t += d + gap
    extra = 0.6
    audio.append(np.zeros(int(extra * sr), dtype=np.float32))
    t += extra
    sc["start"], sc["end"] = start, t
    print(si, sc["scene"], round(t - start, 1), flush=True)
audio.append(np.zeros(int(1.5 * sr), dtype=np.float32))
t += 1.5
full = np.concatenate(audio)
sf.write("/home/claude/ep1/voice.wav", full, sr)
json.dump({"duration": t, "scenes": [{"scene": s["scene"], "start": s["start"], "end": s["end"]} for s in script],
           "lines": timeline}, open("/home/claude/ep1/timeline.json", "w"), indent=1)
print("total", round(t, 1))
