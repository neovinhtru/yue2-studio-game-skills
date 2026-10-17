---
name: yue2-game-composer
description: Compose original background music for Godot/Unity sci-fi, casual, arcade, top-down and twin-stick shooter games using YuE2 Studio. Use for planet themes, menus, exploration, combat, boss encounters, victory, horror ambiences and instrumental soundtrack prompt engineering.
license: MIT
compatibility: Requires sibling yue2-studio-core skill and running local ianiv/YuE2 Studio.
---
# Composer: game-aware instrumental prompts

Use the script `../yue2-studio-core/scripts/yue2.py` relative to this skill directory. Never invent an output filename or generation result before `job.status=done` and file download.

## Workflow

1. Ask/derive scene, intended emotional curve, duration target, intended musical role (full track vs looping ambience), BPM target, density, dominant instruments, acceptable vocals, game engine and audio mix context. If unspecified, pick a suitable scene from `assets/scenes.json`.
2. Treat the prewritten scenes as **starting points**; adjust the `style` for action pacing and the gameplay SFX frequency range. Output concise English music descriptors, but explain to user in Vietnamese.
3. Run `doctor`; use `scenes` to inspect presets. Start with `fast` for prototypes.
4. Submit a scene or user-authored style. Prefer `cot=full` when ABC editing may follow; `melody` for a guided lead line; `off` if speed matters more than symbolic editability.
5. Instrumental generation: `lyrics` contains only section labels and `[Instrumental]` placeholders. These may be imperfect; check the audio. Optionally specify a known valid adapter using `--lora NAME`; `--auto-instrumental-lora` selects only when discovery is unambiguous.
6. Wait (don't confuse queued with done), download FLAC and ABC if available, capture seed/job metadata. The actual track length is model-determined, not guaranteed by an English duration request.

## Scene usage

```bash
YUE2="$HOME/.agents/skills/yue2-studio-core/scripts/yue2.py"
python3 "$YUE2" scenes
python3 "$YUE2" create --scene earth-combat --preset fast --seed 1501
# Or with instrumental LoRA detected in local Studio (if unambiguous):
python3 "$YUE2" create --scene mars-battle --preset quality --auto-instrumental-lora
# Fully customized:
python3 "$YUE2" create --title 'Alien Ambush' \
  --style 'Instrumental intense sci-fi horror combat, 145 BPM, distorted bass, metallic percussion, no lyrics' \
  --lyrics '[Intro]\n[Instrumental]\n[Verse]\n[Instrumental]\n[Outro]' \
  --cot full --preset fast
```

**Shell note:** For newlines in literal `--lyrics`, use `$'[Intro]\n...'` on bash/zsh or a UTF-8 `--lyrics-file`. Basic single quotes do not expand `\n`.

## Cue design for game loops

- Limit overly dramatic full-song climaxes in exploration loops; ask for repeating motifs and steady harmonic beds.
- Leave spectral room for shooting impacts, dialogue and HUD alerts. Game mixer may need sidechain/ducking.
- Generate separate menu, exploration, fight, boss and victory cues rather than expecting a single audio file to expose editable stems.
- Design dynamic transitions with game middleware/engine. YuE2 Studio does not return a guaranteed synchronized multistem arrangement.

## Available original prompt scenes

`menu`, `earth-combat`, `moon-exploration`, `mars-battle`, `saturn-boss`, `alien-horror`, `victory`, `game-over`. See `assets/scenes.json`.
