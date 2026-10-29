#!/usr/bin/env bash
# Veröffentlicht automatisch, was auf main liegt (docs/betrieb.md, Veröffentlichen): holt origin/main in den
# Veröffentlichungsordner, bringt die Software (Submodul) auf den festgehaltenen Stand und ruft deploy.sh für jede Reise
# auf, sobald main einen neuen Stand hat. Gestartet alle 5 Minuten vom Timer <instanz>-veroeffentlichen.timer und
# gleich nach jedem Schreibvorgang des Schreibwegs (engine/schreiben.py).
# Aufruf von Hand:  frieda/betrieb/veroeffentlichen.sh          (nur wenn main neu ist)
#                   frieda/betrieb/veroeffentlichen.sh --immer  (auch ohne neuen Stand)
# Ist der Veröffentlichungsordner nicht auf main oder nicht sauber, wird nichts angefasst (jemand arbeitet gerade dort).
# Ein fehlgeschlagener Deploy wird beim nächsten Lauf wiederholt, weil nur ein gelungener Lauf den Stand merkt.
# Überwachung: Nach fachlichem Erfolg (nichts Neues oder alles veröffentlicht) wird <FR_DIENST>/veroeffentlichen-erfolg
# berührt; ist FR_HEARTBEAT_VEROEFFENTLICHEN gesetzt (Adresse, in <FR_DIENST>/betrieb.env), wird sie zusätzlich abgerufen.
# Übersprungene Läufe und Fehler tun beides nicht.
# Neue Reisen: Nach dem Veröffentlichen ruft das Skript freischalten.sh für jede Reise auf (legt einer neuen Reise ihren
# geheimen Link an, prüft die Seite, schreibt seiten.json) und stellt bei jedem Lauf ausstehende Links neuer Reisen aus
# der Claude-App zu (zustellen.py). Links stehen nie im Protokoll.
# Die Prüfungen (pytest) laufen einmal je Lauf vor allen Reisen; deploy.sh überspringt sie dann für genau diesen Stand
# (FR_GEPRUEFT). Sonst liefen sie je Reise einmal, und der Lauf stieße bei drei Reisen an die Zeitgrenze der Unit.
# Für Tests überschreibbar: VF_PRUEFEN, VF_STAND, VF_DEPLOY, VF_FREISCHALTEN, VF_AUSSTEHEND, VF_SPERRE, VF_STEMPEL, VF_HEARTBEAT.
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/gemeinsam.sh"

erfolg_melden() {
  mkdir -p "$FR_DIENST"
  touch "${VF_STEMPEL:-$FR_DIENST/veroeffentlichen-erfolg}"
  local hb="${VF_HEARTBEAT:-${FR_HEARTBEAT_VEROEFFENTLICHEN:-}}"
  [ -n "$hb" ] || return 0
  curl -fsS -m 10 --retry 3 -o /dev/null "$hb" || echo "Warnung: Heartbeat nicht erreicht."
}

zustellen() {  # ausstehende Links neuer Reisen (nur wenn welche anstehen)
  [ -s "$ausstehend" ] || return 0
  "$FR_PYTHON" "$FR_BETRIEB/zustellen.py" "$wurzel" "$ausstehend" \
    || echo "Warnung: Links neuer Reisen nicht alle zugestellt, nächster Lauf versucht es wieder."
}

# Alles steckt in main(), damit bash das Skript ganz einliest, bevor git es mit dem Submodul eventuell ersetzt.
main() {
  local stand deploy pruefen immer="" alt neu reise fehler="" freischalten aus
  wurzel="$FR_WURZEL"
  stand="${VF_STAND:-$FR_DIENST/veroeffentlicht}"
  deploy="${VF_DEPLOY:-$FR_BETRIEB/deploy.sh}"
  pruefen="${VF_PRUEFEN:-}"
  freischalten="${VF_FREISCHALTEN:-$FR_BETRIEB/freischalten.sh}"
  ausstehend="${VF_AUSSTEHEND:-$FR_DIENST/neue-reisen-ausstehend.jsonl}"
  [ "${1:-}" = "--immer" ] && immer=1

  exec 9>"${VF_SPERRE:-$FR_SPERREN/$FR_INSTANZ-veroeffentlichen.lock}"
  flock -n 9 || { echo "Läuft schon, übersprungen."; return 0; }

  cd "$wurzel"
  if [ "$(git rev-parse --abbrev-ref HEAD)" != main ]; then
    echo "Veröffentlichungsordner ist nicht auf main ($(git rev-parse --abbrev-ref HEAD)), übersprungen."; return 0
  fi
  if ! git diff --quiet HEAD || [ -n "$(git ls-files --others --exclude-standard)" ]; then
    echo "Ungesicherte Änderungen im Veröffentlichungsordner, übersprungen."; return 0
  fi

  git fetch -q origin main
  neu="$(git rev-parse origin/main)"
  alt="$(cat "$stand" 2>/dev/null || true)"
  if [ -z "$immer" ] && [ "$neu" = "$alt" ]; then zustellen; erfolg_melden; return 0; fi

  git merge -q --ff-only origin/main || { echo "FEHLER: main lässt sich nicht vorspulen (lokale Commits?)."; return 1; }
  # Software (Submodul) auf den Stand bringen, den main festhält
  git submodule update --init --quiet || { echo "FEHLER: Submodul der Software lässt sich nicht holen."; return 1; }
  echo "Veröffentliche $(git log -1 --format='%h %s')"
  # Eigener Ordner für die Testdateien: Mit der Vorgabe (/tmp/pytest-of-<user>) räumt jeder weitere pytest-Lauf auf dem
  # Rechner die Ordner älterer Läufe weg, auch die eines noch laufenden (roter Lauf 29.10.2026 bei gleichzeitigen Tests).
  pruef_tmp="$(mktemp -d)"
  if [ -n "$pruefen" ]; then "$pruefen"; else "$FR_PYTHON" -m pytest engine/tests $( [ -d tests ] && echo tests ) -q --basetemp "$pruef_tmp"; fi \
    || { rm -rf "$pruef_tmp"; echo "FEHLER: Prüfungen rot, nichts veröffentlicht."; return 1; }
  rm -rf "$pruef_tmp"
  FR_GEPRUEFT="$(git rev-parse HEAD)"; export FR_GEPRUEFT
  for reise in reisen/*/reise.json; do
    [ -e "$reise" ] || continue
    reise="$(basename "$(dirname "$reise")")"
    "$deploy" "$reise" || { echo "FEHLER: Deploy von $reise fehlgeschlagen."; fehler=1; }
  done
  [ -n "$fehler" ] && return 1
  # Freischalten: neue Reisen bekommen ihren Link, alle werden geprüft (Ausgabe ohne Links, die sind geheim)
  for reise in reisen/*/reise.json; do
    [ -e "$reise" ] || continue
    reise="$(basename "$(dirname "$reise")")"
    aus="$("$freischalten" "$reise" 2>&1)" || echo "Warnung: $reise nicht freigeschaltet (Grund in der Zeile darunter)."
    printf '%s\n' "$aus" | grep -E '^(FEHLER|Freigeschaltet|Baustein erneuert)' || true
  done
  mkdir -p "$(dirname "$stand")"
  echo "$neu" > "$stand"
  zustellen
  echo "Fertig: $(git log -1 --format='%h') ist online."
  erfolg_melden
}

wurzel=""; ausstehend=""
main "$@"
exit
