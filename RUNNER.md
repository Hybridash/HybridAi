# Daily runs on the owner's Mac

Since 2026-11-02 the daily Short is made on the owner's Mac (a local scheduled task), because its voices come from VoiceStudio, which only runs there. The weekly video still runs in the cloud.

Layout (already set up, reuse it):
- `~/hybridai-runner/HybridAi`: this repo. Start every run with `git pull`.
- `~/hybridai-runner/venv`: Python 3.12 with the pipeline's packages. Build with `~/hybridai-runner/venv/bin/python pipeline/build.py ...`.
- `~/hybridai-models/kokoro-multi-lang-v1_0`: the fallback voice model.
- Fonts are bundled in `pipeline/fonts/`.

Before building, make sure VoiceStudio is running: `curl -s localhost:3900/engines/tts` should answer. If it doesn't, run `open -a VoiceStudio`, wait about 30 seconds, and check again.

Commits are authored as Hybridash: `git -c user.name=Hybridash -c user.email=286233097+Hybridash@users.noreply.github.com commit ...`, with no AI co-author or attribution lines.

If the venv is missing: `/opt/homebrew/bin/python3.12 -m venv ~/hybridai-runner/venv && ~/hybridai-runner/venv/bin/pip install "sherpa-onnx<2" soundfile numpy pillow`.
