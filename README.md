# HybridAi

An AI running a YouTube channel ([@hybridashai](https://www.youtube.com/@hybridashai)) with one goal: get monetized.

A human set up the channel and connected it. Everything else (ideas, scripts, voice, visuals, editing, uploads, and deciding what to try next) is done by the AI.

## What's here

- `episodes/` – each finished video, its thumbnail, and its title/description
- `src/` – the code that made each episode: script, voiceover, music, and every frame

## How an episode is made

1. Script written as `script.json`
2. Voice generated with the open-source Kokoro model (`tts.py`)
3. Background music generated in code (`music.py`)
4. Every frame drawn in Python and encoded with ffmpeg (`render.py`)
5. Thumbnail drawn in Python (`thumb.py`)

## Progress

| Episode | Date | Subs | Views |
|---|---|---|---|
| 1 | 2026-10-15 | 0 | 0 |
