---
name: yue2-game-export
description: Convert generated YuE2 Studio soundtrack FLAC files to game-ready OGG Vorbis, WAV and FLAC, prepare approximate seamless looping audio via crossfade, verify audio metadata, produce checksums/manifests, and plan Godot/Unity music delivery.
license: MIT
compatibility: Requires sibling yue2-studio-core skill, local ffmpeg and ffprobe for export.
---
# Export music assets for games

Use `../yue2-studio-core/scripts/yue2.py` relative to this SKILL.md.

## Workflow

1. `download JOB_ID --format flac --out original.flac` after `job.status=done`. FLAC is the untouched master; never overwrite.
2. Use `analyze --input original.flac` to inspect real codec/sample rate/duration. Studio normally renders 48 kHz stereo, but **measure the file**.
3. For Godot game music, prefer streaming OGG Vorbis for long BGM; WAV for short uncompressed assets or edits; Unity may use OGG or native engine import compression. Avoid MP3 for loop assets due to encoder padding/gapless complexities.
4. If a loop is requested, use `export --loop --crossfade 1.5` to overlap **end onto beginning**, discarding one crossfade window in total. This smooths the waveform but does **not guarantee harmonically seamless looping**. Audition by repeating the result; if chord progression or beat alignment is off, edit at bar boundaries in a DAW.
5. Keep `--manifest` JSON with hash, actual duration and provenance; match the game's audio mixer gain/ducking rather than irreversible auto-loudness assumptions.

```bash
YUE2="$HOME/.agents/skills/yue2-studio-core/scripts/yue2.py"
python3 "$YUE2" download JOB_ID --format flac --out ./audio/master-combat.flac
python3 "$YUE2" analyze --input ./audio/master-combat.flac
python3 "$YUE2" export --input ./audio/master-combat.flac \
  --out ./godot/audio/combat-loop.ogg --loop --crossfade 1.5 --manifest
python3 "$YUE2" export --input ./audio/master-combat.flac \
  --out ./godot/audio/combat.wav --manifest
```

## Validation checklist

- Confirm exported audio exists and hashes are recorded.
- Run an audible test of two consecutive loops; inspect clicks at wrap-around. Mechanical crossfade alone cannot guarantee meter/phrase coherence.
- Check peak/headroom when multiple audio assets are mixed; refrain from claiming exact LUFS unless measured with a suitable meter.
- For Godot, import `.ogg` and enable looping in the relevant resource/player settings; test actual engine behavior. For Unity, configure looping on the `AudioSource`/clip accordingly.
- Preserve model and source-audio license evidence; do not treat generation as automatic commercial clearance.
