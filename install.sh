#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$HOME/.agents/skills"
FORCE=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --project)
      [[ $# -ge 2 ]] || { echo 'Thiếu đường dẫn sau --project' >&2; exit 2; }
      DEST="$2/.agents/skills"; shift 2;;
    --dest)
      [[ $# -ge 2 ]] || { echo 'Thiếu đường dẫn sau --dest' >&2; exit 2; }
      DEST="$2"; shift 2;;
    --force) FORCE=1; shift;;
    -h|--help) echo 'Usage: ./install.sh [--project /path/to/project | --dest /path/to/skills] [--force]'; exit 0;;
    *) echo "Tham số không hỗ trợ: $1" >&2; exit 2;;
  esac
done
mkdir -p "$DEST"
# Preflight before copying: do not leave a half-installed suite from name collisions.
for src in "$ROOT"/skills/yue2-*; do
  name="$(basename "$src")"
  if [[ -e "$DEST/$name" && $FORCE -eq 0 ]]; then
    echo "Đã tồn tại: $DEST/$name. Dùng --force (ghi đè) hoặc cài ở vị trí khác." >&2
    exit 1
  fi
done
for src in "$ROOT"/skills/yue2-*; do
  name="$(basename "$src")"
  if [[ -e "$DEST/$name" ]]; then
    # Explicit --force, preserve old skill as versioned backup.
    backup_root="$(dirname "$DEST")/skills-backups"
    mkdir -p "$backup_root"
    backup="$backup_root/${name}.backup-$(date +%Y%m%d%H%M%S)"
    mv "$DEST/$name" "$backup"
    echo "Backup: $backup"
  fi
  cp -R "$src" "$DEST/$name"
  echo "Installed: $DEST/$name"
done
cat <<EOF

Cài đặt hoàn tất. Pi và Codex tìm thấy ~/.agents/skills hoặc .agents/skills.
Mở phiên agent mới và thử /skill:yue2-game-composer (trên Pi), hoặc yêu cầu dùng skill tương ứng.
Kiểm tra: python3 "$DEST/yue2-studio-core/scripts/yue2.py" doctor
EOF
