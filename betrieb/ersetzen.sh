#!/bin/bash
# Dateien in einen Ordner bringen, ohne dass ein gleichzeitiger Leser sie fehlend oder halb geschrieben findet (#489).
#
#   ersetzen.sh <zielordner> <datei>...
#
# Unveränderte Dateien bleiben unberührt (gleicher Inode). Eine geänderte oder neue Datei wird erst als Temp-Datei im
# Zielordner geschrieben und dann umbenannt (rename ist atomar im selben Dateisystem); Rechte 644. deploy.sh ersetzt so
# die Module in <FR_DIENST>, während der Schreibweg daraus lädt. Exit ungleich 0, wenn eine Datei nicht ersetzt werden
# konnte; Reste werden aufgeräumt.
set -euo pipefail

[ "$#" -ge 2 ] || { echo "usage: ersetzen.sh <target dir> <file>..." >&2; exit 64; }
ziel="$1"
shift
mkdir -p "$ziel"

tmp=""
trap '[ -n "$tmp" ] && rm -f "$tmp"' EXIT
for quelle in "$@"; do
  name="$(basename "$quelle")"
  cmp -s "$quelle" "$ziel/$name" && continue
  [ -f "$quelle" ] || { echo "ERROR: $quelle missing." >&2; exit 1; }
  tmp="$(mktemp "$ziel/.$name.XXXXXX")"
  cp "$quelle" "$tmp"
  chmod 644 "$tmp"
  mv -f "$tmp" "$ziel/$name"
  tmp=""
done
