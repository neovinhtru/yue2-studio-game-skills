---
name: yue2-game-arranger
description: Edit YuE2 Studio ABC scores, regenerate arrangements, transcribe permitted audio for covers, or turn a hummed melody into new soundtrack music. Use for changing harmony/melody/tempo/instrumental arrangement while keeping source and revision history.
license: MIT
compatibility: Requires sibling yue2-studio-core skill; cover/hum need optional local transcription models and ffmpeg.
---
# ABC arrangement, cover and humming

Use `../yue2-studio-core/scripts/yue2.py` relative to this SKILL.md.

## Edit a score safely

1. Run `job JOB_ID` to verify the baseline and whether `score` is available (`cot=off` often has no editable ABC).
2. Download `--format abc` and `--format zip` to immutable filenames. Store the exact original and a working copy.
3. Edit **only the working ABC**. Verify headers (`X:`, `T:`, `M:`, `L:`, `Q:`, `K:`), note durations, repeats, rests, parts and bar structure before submission. Avoid losing important voices. For tricky edits, get a musician or render MIDI to check first.
4. `regenerate --parent-id ... --abc-file ...` creates a **new** job; it doesn't mutate the baseline. The same seed cannot guarantee exact audio identity if ABC changed.
5. Listen to resulting FLAC, compare structural markers and timing. Preserve both revisions.

```bash
YUE2="$HOME/.agents/skills/yue2-studio-core/scripts/yue2.py"
python3 "$YUE2" download JOB_ID --format abc --out ./scores/original.abc
cp ./scores/original.abc ./scores/edited.abc
# Edit edited.abc with an editor; do not touch original.abc
python3 "$YUE2" regenerate --parent-id JOB_ID --abc-file ./scores/edited.abc --preset quality
```

## Audio-to-cover

- Only when the user has rights to the source audio and Studio's `status.cover.available=true`.
- File is locally uploaded to Studio (`/api/upload`), not sent to external service by the client.
- For **cover** use `--task melody-full --mode cover`; for **continuation** use `--task melody-full --mode continue`. The engine transcribes with SheetSage2/MERT, which may make note errors.
- It conditions on a transcribed symbolic score; it **does not** clone source vocals or guarantee identical mix/timbre.

```bash
python3 "$YUE2" cover --file ./references/allowed-melody.wav \
  --style 'Instrumental synthesizer-led heroic sci-fi battle score' \
  --task melody-full --mode cover --preset fast
```

## Humming-to-song

Hum only works when `status.hum.available=true`. For normal melody continuation choose `--melody continue`; for a fixed transcription choose `--melody hum_only`. Adapter mode (`--melody ignore --adapter NAME`) requires Studio to report a valid compatible hum adapter. Do not improvise adapter names.

```bash
python3 "$YUE2" hum --file ./references/my-hum.m4a \
  --style 'Instrumental mellow interplanetary exploration theme' \
  --melody continue --preset fast
```
