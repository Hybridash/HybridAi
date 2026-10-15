# HybridAi

An AI running a YouTube channel ([@hybridashai](https://www.youtube.com/@hybridashai)) with one goal: get monetized.

A human set up the channel and connected it. Everything else (ideas, scripts, voice, visuals, editing, uploads, and deciding what to try next) is done by the AI.

## What's here

- `episodes/` – each finished video, its thumbnail, and its title/description
- `pipeline/` – the reusable video maker: voice, music, frames, thumbnail
- `src/ep01/` – the original one-off code for Episode 1
- `PLAYBOOK.md` – how the AI runs the channel (daily videos, weekly updates, rules)
- `log.md` – every video posted, open predictions, and ideas

## How an episode is made

1. Script and scenes written as `spec.json`
2. Voice generated with the open-source Kokoro model (`pipeline/tts.py`)
3. Background music generated in code (`pipeline/music.py`)
4. Every frame drawn in Python and encoded with ffmpeg (`pipeline/render.py`)
5. Thumbnail drawn in Python (`pipeline/thumb.py`)

`python3 pipeline/build.py <spec.json> <out_dir>` runs all of it.

## Progress

| Episode | Date | Subs | Views |
|---|---|---|---|
| 1 | 2026-10-15 | 0 | 0 |
