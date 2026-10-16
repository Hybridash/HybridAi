"""Builds a finished video from a spec. Runs voice, music, frames, mix, and checks.

usage: python3 build.py <spec.json> <out_dir> [--stills]
  --stills  only make the voice + a contact sheet of sample frames (fast preview)
output: <out_dir>/final.mp4 (+ thumbnail.jpg if the spec has one), contact.png
"""
import json, os, subprocess, sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
spec_path, out = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
os.makedirs(out, exist_ok=True)
spec = json.load(open(spec_path))
py = sys.executable
def run(*a): subprocess.run([py, *a], check=True)

run(f"{HERE}/tts.py", spec_path, out)
tl = json.load(open(f"{out}/timeline.json"))
dur = tl["duration"]
short = spec.get("format") == "short"
if short and dur > 175:
    print(f"WARNING: short is {dur:.0f}s; YouTube Shorts must be 3 minutes or less")

# contact sheet: middle of every scene
ts = [round((s["start"] + s["end"]) / 2, 2) for s in tl["scenes"]]
run(f"{HERE}/render.py", spec_path, out, "still", *map(str, ts))
ims = [Image.open(f"{out}/still_{t}.png") for t in ts]
tw, th = (270, 480) if short else (480, 270)
cols = 4 if short else 3
rows = (len(ims) + cols - 1) // cols
sheet = Image.new("RGB", (tw * cols, th * rows))
for i, im in enumerate(ims):
    sheet.paste(im.resize((tw, th)), ((i % cols) * tw, (i // cols) * th))
sheet.save(f"{out}/contact.png")
for t in ts: os.remove(f"{out}/still_{t}.png")
print("contact sheet:", f"{out}/contact.png")
if "--stills" in sys.argv: sys.exit()

seed = abs(hash(spec.get("label", "") + spec.get("title", ""))) % 1000
run(f"{HERE}/music.py", out, str(seed))
n = 2
procs = [subprocess.Popen([py, f"{HERE}/render.py", spec_path, out, "part", str(i), str(n)]) for i in range(n)]
for p in procs:
    if p.wait() != 0: sys.exit("frame render failed")
with open(f"{out}/parts.txt", "w") as f:
    for i in range(n): f.write(f"file '{out}/part{i}.mp4'\n")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", f"{out}/parts.txt",
                "-c", "copy", f"{out}/video_only.mp4"], check=True)
mvol = spec.get("music_volume", 0.16)
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{out}/video_only.mp4", "-i", f"{out}/voice.wav",
                "-i", f"{out}/music.wav", "-filter_complex",
                f"[1:a]aresample=48000,aformat=channel_layouts=stereo,volume=1.6,asplit=2[v1][vsc];"
                f"[2:a]aresample=48000,volume={mvol}[m];[m][vsc]sidechaincompress=threshold=0.04:ratio=5:attack=20:release=500[md];"
                f"[md][v1]amix=inputs=2:duration=longest:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]",
                "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
                f"{out}/final.mp4"], check=True)
for i in range(n): os.remove(f"{out}/part{i}.mp4")
os.remove(f"{out}/video_only.mp4")
if spec.get("thumbnail"):
    run(f"{HERE}/thumb.py", spec_path, f"{out}/thumbnail.jpg")
    # Opening frame = the thumbnail, so whatever frame YouTube shows (and Shorts feeds) carries the hook.
    # Held for cover_seconds (default 0.6) with silence, then the video starts.
    cover = f"{out}/cover.png"
    if short: run(f"{HERE}/thumb.py", spec_path, cover, "vertical")
    else: Image.open(f"{out}/thumbnail.jpg").resize((1920, 1080)).save(cover)
    hold = spec.get("cover_seconds", 0.6)
    os.rename(f"{out}/final.mp4", f"{out}/body.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", "30", "-t", str(hold), "-i", cover,
                    "-f", "lavfi", "-t", str(hold), "-i", "anullsrc=r=48000:cl=stereo", "-i", f"{out}/body.mp4",
                    "-filter_complex", "[0:v]format=yuv420p,setsar=1[cv];[2:v]setsar=1[bv];[cv][1:a][bv][2:a]concat=n=2:v=1:a=1[v][a]",
                    "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", f"{out}/final.mp4"], check=True)
    os.remove(f"{out}/body.mp4")
    dur += hold
size = os.path.getsize(f"{out}/final.mp4")
print(f"final: {out}/final.mp4  {dur:.1f}s  {size/1e6:.1f} MB")
if size > 99e6: print("WARNING: over 99 MB; GitHub cannot host it, compress before pushing")
