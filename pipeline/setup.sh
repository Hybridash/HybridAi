#!/usr/bin/env bash
# One-time setup for a fresh workspace. Safe to re-run.
set -e
MODELS="${MODELS_DIR:-$HOME/hybridai-models}"
mkdir -p "$MODELS"
pip install --break-system-packages -q sherpa-onnx soundfile numpy pillow 2>&1 | grep -v -i warning || true
if [ ! -f "$MODELS/kokoro-en-v0_19/model.onnx" ]; then
  echo "Downloading Kokoro voice model (~320 MB)..."
  curl -sSL -o "$MODELS/kokoro.tar.bz2" \
    https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/kokoro-en-v0_19.tar.bz2
  tar xjf "$MODELS/kokoro.tar.bz2" -C "$MODELS"
  rm -f "$MODELS/kokoro.tar.bz2"
fi
which ffmpeg >/dev/null || { echo "ffmpeg missing"; exit 1; }
echo "setup ok: $MODELS/kokoro-en-v0_19"
