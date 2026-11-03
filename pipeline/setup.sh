#!/usr/bin/env bash
# One-time setup for a fresh workspace. Safe to re-run.
set -e
MODELS="${MODELS_DIR:-$HOME/hybridai-models}"
mkdir -p "$MODELS"
pip install --break-system-packages -q "sherpa-onnx<2" soundfile numpy pillow 2>&1 | grep -v -i warning || true
if [ ! -f "$MODELS/kokoro-multi-lang-v1_0/model.onnx" ]; then
  echo "Downloading Kokoro v1.0 voice model..."
  curl -sSL -o "$MODELS/kokoro.tar.bz2" \
    https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/kokoro-multi-lang-v1_0.tar.bz2
  tar xjf "$MODELS/kokoro.tar.bz2" -C "$MODELS"
  rm -f "$MODELS/kokoro.tar.bz2"
fi
which ffmpeg >/dev/null || { echo "ffmpeg missing"; exit 1; }
echo "setup ok: $MODELS/kokoro-multi-lang-v1_0"
