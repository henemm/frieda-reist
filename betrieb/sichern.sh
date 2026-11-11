#!/usr/bin/env bash
# Frische Schnappschüsse der Konten-Datenbank und des Reisespeichers (#506), für das Server-Backup der Instanz: Es ruft
# dieses Skript unmittelbar vor dem Archivieren auf, damit <FR_KONTEN>/sicherung/konten.db und
# <Speicher>/sicherung/reisen.db den Stand von jetzt haben und nicht den des letzten Wächter-Laufs (bis zu einem Tag
# älter). Schreibt wie der Wächter-Lauf über die Backup-API von SQLite (engine/konten.py sichern,
# engine/reisespeicher.py sichern); scheitert ein Schnappschuss, bleibt der vorige stehen.
# Versucht immer beide. Exit 0: beide geschrieben; Exit 1: mindestens einer gescheitert. Keine Nachricht über den
# Meldeweg: Den Fehler meldet das aufrufende Backup (kein Heartbeat).
# Aufruf (als Betriebsbenutzer der Instanz):  FR_WURZEL=<Bauordner> <Bauordner>/frieda/betrieb/sichern.sh
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/gemeinsam.sh"

fehler=0
for modul in konten reisespeicher; do
  if ! "$FR_PYTHON" "$FR_WURZEL/engine/$modul.py" sichern; then
    echo "ERROR: snapshot of $modul failed, the previous snapshot stays." >&2
    fehler=1
  fi
done
exit "$fehler"
