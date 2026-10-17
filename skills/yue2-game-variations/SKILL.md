---
name: yue2-game-variations
description: Produce several reproducible YuE2 Studio music candidates, compare their seeds/presets/LoRAs, archive results, select and rate finished takes in a soundtrack project. Use when iterating on background music, evaluating combat cues, or curating game albums.
license: MIT
compatibility: Requires sibling yue2-studio-core skill and local YuE2 Studio API.
---
# Variations and human-in-the-loop selection

Use `../yue2-studio-core/scripts/yue2.py` relative to this SKILL.md.

## Process

1. Fix the **exact prompt, preset, `cot` and adapter stack** before comparing seeds. For seed-only A/B, do not change two independent variables at once.
2. Start with 2–3 variants; YuE2 Studio queues generation serially. Batch only as much as time/energy allows.
3. `variations --count 3 --seed 4200` creates 3 jobs with seeds 4200, 4201, 4202. Use `--random-seeds` only when deliberately abandoning adjacency.
4. Wait for each returned `jobs[].id`, download FLAC and full artifact ZIP; report failures/truncation from `job.truncated`. Do not fabricate auditions. User or a real audio-listening tool should evaluate dynamics, hooks, vocal leakage, artifacts, and loop suitability.
5. Shortlist; use Studio projects/tracks, add job IDs, rate 1–5, and **explicitly** choose the final take. Never auto-mark a candidate as final merely because its job succeeded.
6. Optionally compare `fast` vs `quality` on a fixed seed while recording preset and settings; seed does NOT imply identical waveform across precision, fast-numerics or LoRA changes.

```bash
YUE2="$HOME/.agents/skills/yue2-studio-core/scripts/yue2.py"
python3 "$YUE2" variations --scene saturn-boss --seed 4200 --count 3 --preset fast
python3 "$YUE2" wait JOB_ID
python3 "$YUE2" download JOB_ID --format flac --out ./outputs/boss-4200.flac
python3 "$YUE2" project-new --name 'Planet Defender OST'
python3 "$YUE2" track-new PROJECT_ID --name 'Saturn Boss'
python3 "$YUE2" track-add TRACK_ID JOB_1 JOB_2 JOB_3
python3 "$YUE2" take-rate JOB_1 --stars 4 --note 'động lực tốt, đoạn kết khó loop'
python3 "$YUE2" track-choose TRACK_ID JOB_1
python3 "$YUE2" album-download PROJECT_ID --format flac --out ./outputs/album.zip
```

**Scorecard (0–5)**: clarity with game SFX; emotional fit; memorable motif; perceived vocal leakage; rhythmic consistency; loop seam after editing. Keep listening notes and do not claim measured BPM or LUFS from prompt text.
