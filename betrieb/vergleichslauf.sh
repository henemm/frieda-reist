#!/usr/bin/env bash
# Vergleichslauf (Stufe 3, #348, ADR-0009): hält je Reise den Dateistand aus Git gegen den Export aus dem Reisespeicher
# (engine/reisespeicher.py vergleichen, nur Prüfsummen). Läuft von Hand, kein Timer; Voraussetzung zum Umschalten einer Reise
# auf den Speicher (erzwungen erst mit Stufe 5, #350).
# Aufruf:  FR_WURZEL=<Bauordner> frieda/betrieb/vergleichslauf.sh [--bis N] [<reise>…]
#          Ohne Reise: jede Reise, die in Git (reisen/<reise>) liegt und einen Eintrag im Speicher hat; eine Reise nur in Git
#          oder nur im Speicher hat nichts zu vergleichen und wird mit einem Hinweis übersprungen.
#          --bis N vergleicht mit Stand N des Speichers (etwa dem, den der Anfangsvorgang übernommen hat), sonst dem neuesten.
# Der Dateistand aus Git kommt aus dem Commit HEAD (git archive in einen Wegwerf-Ordner): Der Bauordner bleibt unberührt,
# ungesicherte Änderungen zählen nicht.
# Stempel je Reise: <FR_DIENST>/vergleich/<reise>.json {zeit (UTC), ergebnis: gleich | unterschied | fehler, stand, git
# (Commit), unterschiede (Anzahl)}. Eine Auskunft, keine Sperre.
# Exit: 0 alles gleich, 1 mindestens ein Unterschied, 2 mindestens ein Fehler (das schlimmste Ergebnis zählt; ein Fehler bei
# einer Reise bricht die übrigen nicht ab).
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/gemeinsam.sh"
nur_bauordner

RS="$FR_BETRIEB/../engine/reisespeicher.py"
bis=""
reisen=()
while [ $# -gt 0 ]; do
  case "$1" in
    --bis) bis="${2:?--bis needs a state number}"; shift 2 ;;
    *) reisen+=("$1"); shift ;;
  esac
done
[ -z "$bis" ] || [[ "$bis" =~ ^[0-9]+$ ]] || { echo "ERROR: --bis needs a state number."; exit 2; }

alle=""
if [ ${#reisen[@]} -eq 0 ]; then
  for r in "$FR_WURZEL"/reisen/*/; do [ -d "$r" ] && reisen+=("$(basename "$r")"); done
  alle=1
fi
[ ${#reisen[@]} -gt 0 ] || { echo "No trips to compare."; exit 0; }

gesamt=0
# Speicher nicht lesbar: ein Fehler, nie ein stilles Überspringen. Ohne Reiseliste ist dann nichts zu vergleichen (Exit 2);
# mit Liste meldet vergleichen den Fehler je Reise.
if ! staende="$("$FR_PYTHON" "$RS" staende "${reisen[@]}" 2>&1)"; then
  echo "ERROR: the trip store cannot be read: $(printf '%s\n' "$staende" | tail -1)"
  [ -z "$alle" ] || exit 2
  staende=""; gesamt=2
fi
git_stand="$(git -C "$FR_WURZEL" rev-parse HEAD)"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT

stempel() {  # <reise> <ergebnis> <stand> <unterschiede>
  local datei="$FR_DIENST/vergleich/$1.json"
  mkdir -p "$FR_DIENST/vergleich"
  printf '{"zeit": "%s", "ergebnis": "%s", "stand": %s, "git": "%s", "unterschiede": %s}\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$2" "${3:-null}" "$git_stand" "$4" > "$datei.neu"
  mv "$datei.neu" "$datei"
}

for r in "${reisen[@]}"; do
  n="$(printf '%s\n' "$staende" | awk -v r="$r" '$1 == r {print $2; exit}')"
  [ "$n" != - ] || n=""
  if [ -n "$alle" ] && [ -z "$n" ]; then echo "Note: $r has no entry in the trip store, nothing to compare."; continue; fi
  if [ -z "$(git -C "$FR_WURZEL" ls-tree -d HEAD "reisen/$r")" ]; then
    echo "Note: $r is not in git (reisen/$r), nothing to compare."; continue
  fi
  ordner="$tmp/$r"
  mkdir -p "$ordner"
  git -C "$FR_WURZEL" archive HEAD "reisen/$r" | tar -x -C "$ordner"
  rc=0
  aus="$("$FR_PYTHON" "$RS" vergleichen "$r" "$ordner/reisen/$r" ${bis:+--bis "$bis"} 2>&1)" || rc=$?
  printf '%s\n' "$aus" | sed "s/^/$r: /"
  stand="${bis:-$n}"
  case "$rc" in
    0) stempel "$r" gleich "$stand" 0 ;;
    1) stempel "$r" unterschied "$stand" "$(printf '%s\n' "$aus" | grep -cE '^(nur im Speicher|nur im Ordner|verschieden): ')" ;;
    *) stempel "$r" fehler "$stand" 0; rc=2 ;;
  esac
  [ "$rc" -le "$gesamt" ] || gesamt="$rc"
  rm -rf "$ordner"
done
exit "$gesamt"
