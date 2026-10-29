#!/usr/bin/env bash
# Arbeitskopie für Änderungen auf dem Server (docs/betrieb.md, Arbeitskopien).
#
# Der Veröffentlichungsordner (Hauptkopie des Reisen-Repos) steht immer auf main, der Timer (veroeffentlichen.sh) baut
# von dort. Dort wird nicht gearbeitet, sonst setzt der Timer aus. Gearbeitet wird in einem Git-Worktree daneben, je
# Änderung auf einem eigenen Branch; der Schreibweg nutzt eine eigene (<Wurzel>-schreiben, engine/schreiben.py).
#
# Aufruf:  frieda/betrieb/arbeitskopie.sh <branch>   legt <Wurzel>-arbeit an (oder ARBEITSKOPIE) bzw. wechselt dort auf <branch>
#
# Was nicht im Repo liegt (Python-Umgebung, Werkzeuge, Grundkarten, Projekt-Einstellungen), wird aus dem
# Veröffentlichungsordner verlinkt statt kopiert. Die Grundkarten sind damit geteilt.
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/gemeinsam.sh"

BRANCH="${1:?Aufruf: arbeitskopie.sh <branch>}"
# Veröffentlichungsordner = Hauptkopie des Repos, egal aus welcher Kopie das Skript aufgerufen wird
QUELLE="$(dirname "$(git -C "$FR_WURZEL" rev-parse --path-format=absolute --git-common-dir)")"
ZIEL="${ARBEITSKOPIE:-$(dirname "$QUELLE")/$(basename "$QUELLE")-arbeit}"

cd "$QUELLE"
git fetch -q origin
if [ ! -d "$ZIEL" ]; then
  if git show-ref -q --verify "refs/heads/$BRANCH"; then git worktree add -q "$ZIEL" "$BRANCH"
  else git worktree add -q -b "$BRANCH" "$ZIEL" origin/main; fi
else
  cd "$ZIEL"
  if [ -n "$(git status --porcelain --untracked-files=no --ignore-submodules=all)" ]; then echo "$ZIEL hat ungesicherte Änderungen, erst committen."; exit 1; fi
  if git show-ref -q --verify "refs/heads/$BRANCH"; then git checkout -q "$BRANCH"
  else git checkout -q -b "$BRANCH" origin/main; fi
fi

# Software als Submodul (frieda); Änderungen daran entstehen im Repo der Software
git -C "$ZIEL" submodule update --init --quiet

verlinke() {  # verlinke <pfad relativ zum Repo>
  local q="$QUELLE/$1" z="$ZIEL/$1"
  [ -e "$q" ] || return 0
  [ -L "$z" ] && return 0
  [ -e "$z" ] && { [ "$(cd "$q" 2>/dev/null && pwd -P)" = "$(cd "$z" 2>/dev/null && pwd -P)" ] || echo "Übersprungen, existiert schon: $z"; return 0; }
  mkdir -p "$(dirname "$z")"
  ln -s "$q" "$z"
}
verlinke engine/.venv
verlinke engine/.bin
verlinke .claude/settings.json
for d in "$QUELLE"/reisen/*/medien/karte; do [ -e "$d" ] && verlinke "${d#"$QUELLE"/}"; done

echo "Arbeitskopie: $ZIEL auf Branch $(git -C "$ZIEL" branch --show-current)"
