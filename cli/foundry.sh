#!/usr/bin/env bash
# Sync Foundry skills into Claude Code, or zip them for the Claude app.
#   cli/foundry.sh sync [dept]   copy ready skills into ~/.claude/skills/foundry-<dept>-<job>
#   cli/foundry.sh zip  [dept]   write foundry-skills.zip of ready skills for upload
#   cli/foundry.sh status        count stubs and ready skills per department
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cmd="${1:-status}"; dept="${2:-}"
ready() { grep -rl --include=SKILL.md '^status: ready' "$ROOT/departments/${dept}" 2>/dev/null || true; }
case "$cmd" in
  sync)
    for f in $(ready); do
      rel="${f#$ROOT/departments/}"; name="foundry-$(echo "$rel" | cut -d/ -f1)-$(echo "$rel" | cut -d/ -f3)"
      mkdir -p "$HOME/.claude/skills/$name"; cp "$f" "$HOME/.claude/skills/$name/SKILL.md"
    done
    echo "synced $(ready | wc -l) skills into ~/.claude/skills";;
  zip)
    (cd "$ROOT/departments" && ready | sed "s|$ROOT/departments/||" | zip -q "$ROOT/foundry-skills.zip" -@)
    echo "wrote $ROOT/foundry-skills.zip";;
  status)
    for d in "$ROOT"/departments/*/; do
      n=$(basename "$d"); s=$( (grep -rl --include=SKILL.md "^status: stub" "$d" || true) | wc -l); r=$( (grep -rl --include=SKILL.md "^status: ready" "$d" || true) | wc -l)
      printf '%-14s ready %3s  stub %3s\n' "$n" "$r" "$s"
    done;;
  *) echo "usage: foundry.sh sync|zip|status [dept]"; exit 1;;
esac
