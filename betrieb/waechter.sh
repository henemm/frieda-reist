#!/usr/bin/env bash
# Täglicher Lauf des Wächters und Erinnerers (docs/waechter.md): legt Meldungen an Personen an (Fristen, ab-Termine,
# Statuswechsel) und, wenn veränderliche Angaben zu lange nicht geprüft wurden, einen Prüfauftrag für das Einarbeiten
# (der Pfad-Wächter <instanz>-einarbeiten.path startet es). Gestartet vom Timer <instanz>-waechter.timer. Reisen ohne
# Baustein waechter und mit Status vor „fest“ werden übersprungen. Ohne Neues kostet der Lauf nichts.
# Nachricht an den Betreiber über FR_MELDEN: eine Sammelnachricht, wenn es etwas zu melden gibt (erledigt), und bei einem
# Fehler eine dringende Meldung. Nach Erfolg wird <FR_DIENST>/waechter-erfolg berührt (für die Überwachung).
# Aufruf von Hand:  frieda/betrieb/waechter.sh      Log: journalctl -u <instanz>-waechter -n 100
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/gemeinsam.sh"

STEMPEL="${WA_STEMPEL:-$FR_DIENST/waechter-erfolg}"

bericht="$(mktemp)"
trap 'rm -f "$bericht"' EXIT

if ! "$FR_PYTHON" "$FR_WURZEL/engine/waechter.py" lauf --bericht "$bericht"; then
  fr_melden high "Wächter fehlgeschlagen" "Der tägliche Lauf des Wächters ist abgebrochen, es kommen keine neuen Meldungen. Log: journalctl -u $FR_INSTANZ-waechter -n 100"
  exit 1
fi

mkdir -p "$(dirname "$STEMPEL")" && touch "$STEMPEL"
if [ -s "$bericht" ]; then
  fr_melden normal "Wächter und Erinnerer" "$(cat "$bericht")" erledigt
fi
