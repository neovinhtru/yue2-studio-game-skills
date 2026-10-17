---
name: yue2-studio-core
description: Connect Codex, Pi or Paseo agents to a local YuE2 Studio (ianiv/YuE2) FastAPI server on macOS Apple Silicon; check models/LoRAs, submit music jobs, monitor jobs, retrieve FLAC/ABC/plan, and manage soundtrack projects. Use whenever the user asks to operate YuE2 Studio through an agent.
license: MIT
compatibility: Python 3.10+ CLI; YuE2 Studio listening locally at 127.0.0.1:8765. No Python package installation needed for client.
---
# YuE2 Studio: Core API Skill

> Use the **ianiv/YuE2 Studio REST API**, not the NVIDIA-centric `scripts/run_yue2.py` from the upstream YuE skill. This skill does not run the MLX model itself.

## Mandatory routine

1. From the agent shell, run `python3 <absolute-path-to-this-skill>/scripts/yue2.py doctor` (e.g. `python3 ~/.agents/skills/yue2-studio-core/scripts/yue2.py doctor`). Resolve paths relative to this `SKILL.md`, never assume the shell current directory.
2. If `models_ready=false`, stop; do not claim generation occurred. If `fake_mode=true`, the result is silent demo output, NOT generated music.
3. Confirm whether user's request is **music**, not a one-shot sound effect (YuE2 is built for music). Choose the matching game skill.
4. Use `--preset fast` for first drafts, `--preset quality` for final passes. These are performance-quality tradeoffs, not guarantees of better audio.
5. For requested **instrumental**, pass explicit instrumental style, sectioned lyric scaffolding and preferably a compatible valid LoRA. Verify by listening; prompts alone do not guarantee no vocals.
6. Save prompts, seed, LoRA names, job IDs, and an archived FLAC/ABC/plan. Do not say an audio file sounds good unless actually listened to / analyzed with an available tool.
7. Do not delete jobs or overwrite outputs without explicit permission. Use loopback address; Studio has no built-in authentication.

## CLI (runs from any directory)

```bash
YUE2="$HOME/.agents/skills/yue2-studio-core/scripts/yue2.py"
python3 "$YUE2" doctor
python3 "$YUE2" loras
python3 "$YUE2" jobs --status done --limit 10
python3 "$YUE2" job JOB_ID
python3 "$YUE2" wait JOB_ID --interval 5 --timeout 7200
python3 "$YUE2" download JOB_ID --format flac --out ./outputs/main.flac
python3 "$YUE2" download JOB_ID --format abc --out ./outputs/main.abc
python3 "$YUE2" download JOB_ID --format zip --out ./outputs/main-artifacts.zip
```

For **project-level** install, substitute `<project>/.agents/skills/...` for `$HOME/.agents/skills/...`.

`YUE2_STUDIO_URL=http://127.0.0.1:8765` overrides the default. Script rejects non-loopback servers unless explicitly passed `--allow-remote` (not recommended; unauthenticated API).

## Setup YuE2 Studio if missing

```bash
brew install uv ffmpeg
# In an already-cloned ianiv/YuE2 repository:
uv sync
uv run python scripts/setup.py --with-cover  # optional cover models, uses ~2.7GB extra
uv run yue2-studio --open
```

Check Studio's own latest README before changing setup. On 24 GiB Mac, Studio auto-enables low-memory mode; do not disable by default. Server serializes model generation jobs.

## Studio endpoint map

- `GET /api/status` — engine, model readiness, memory, LoRAs and cover availability.
- `GET /api/loras` — adapter names, parts and validation.
- `POST /api/jobs` — create, variations, regenerate, cover or hum.
- `GET /api/jobs/{id}` — job status and artifacts. `GET /api/jobs/{id}/events` — optional SSE.
- `GET /api/songs/{id}/audio.flac|audio.mp3|score.abc|plan.json|artifacts.zip` — available files.
- `/api/projects` and `/api/tracks` — album/project/take selection.

Full contract: https://github.com/ianiv/YuE2/blob/main/docs/API.md

## Guardrails and licensing

YuE2 Studio app code is MIT; **model weights are separately licensed**, and the YuE2 authors state that individual creators may monetize outputs under additional permission, while commercial model-weight use by companies requires a separate license. Check the current official MODEL_LICENSE and attribution/third-party input rights before publication; do not assume a game sold by a company is licensed just because Studio runs. Review the actual model checkpoints' terms before publishing. Uploaded cover audio needs separate rights clearance. Keep reproducible asset metadata; avoid leaking local prompts/audio to remote servers.
