# Original background track: soft synth pad + light arpeggio + gentle pulse. No samples, all generated.
import json, numpy as np, soundfile as sf

SR = 44100
dur = json.load(open("/home/claude/ep1/timeline.json"))["duration"]
n = int(dur * SR)
t = np.arange(n) / SR
bpm = 96
beat = 60 / bpm
bar = beat * 4

def midi(m): return 440 * 2 ** ((m - 69) / 12)

# A minor - F - C - G, two bars each
prog = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]
out = np.zeros(n)

def env_ad(x, a, d):
    return np.clip(x / a, 0, 1) * np.exp(-np.maximum(x - a, 0) / d)

chord_len = bar * 2
nchords = int(dur / chord_len) + 1
for i in range(nchords):
    ch = prog[i % 4]
    s = int(i * chord_len * SR)
    e = min(n, int((i + 1) * chord_len * SR + SR))
    if s >= n: break
    tt = t[s:e] - t[s]
    L = chord_len
    env = np.clip(tt / 1.2, 0, 1) * np.clip((L + 1 - tt) / 1.0, 0, 1)
    for m in ch + [ch[0] - 12]:
        f = midi(m)
        tone = sum(np.sin(2 * np.pi * f * (1 + dt) * tt) for dt in (-0.003, 0, 0.003)) / 3
        tone += 0.25 * np.sin(2 * np.pi * 2 * f * tt)
        out[s:e] += 0.09 * env * tone
    # arpeggio, 8th notes
    step = beat / 2
    for k in range(int(L / step)):
        m = ch[k % 3] + 12 + (12 if k % 8 >= 6 else 0)
        ns = s + int(k * step * SR)
        ne = min(n, ns + int(0.6 * SR))
        if ns >= n: break
        x = t[ns:ne] - t[ns]
        f = midi(m)
        out[ns:ne] += 0.045 * env_ad(x, 0.005, 0.18) * (np.sin(2 * np.pi * f * x) + 0.3 * np.sin(2 * np.pi * 3 * f * x))
    # soft pulse on beats
    for k in range(int(L / beat)):
        ns = s + int(k * beat * SR)
        ne = min(n, ns + int(0.3 * SR))
        if ns >= n: break
        x = t[ns:ne] - t[ns]
        fk = 55 * np.exp(-x * 18) + 40
        out[ns:ne] += 0.12 * np.exp(-x * 12) * np.sin(2 * np.pi * np.cumsum(fk) / SR)

# gentle low-pass via moving average, fades
k = 6
out = np.convolve(out, np.ones(k) / k, mode="same")
fade = np.clip(t / 2.0, 0, 1) * np.clip((dur - t) / 3.0, 0, 1)
out *= fade
out /= np.abs(out).max()
out *= 0.5
sf.write("/home/claude/ep1/music.wav", np.stack([out, out], 1).astype(np.float32), SR)
print("music", round(dur, 1), "s")
