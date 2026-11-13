#!/usr/bin/env bash
# Schaltet eine veröffentlichte Reise frei, ohne Handarbeit (docs/neue-reise.md, docs/betrieb.md).
#
#   betrieb/freischalten.sh <reise>    geheimer Link zur Seite (falls noch keiner da ist), Prüfung, seiten.json
#   (Links für die Claude-App je Person gibt es nicht mehr, #421: Personen kommen über ihr Konto)
#
# Den nginx-Baustein <FR_NGINX_SNIPPETS>/<instanz>-<reise>.conf legt nur das Hilfsprogramm mit Root-Rechten an
# (FR_NGINX_REISE_HELFER, Vorgabe /usr/local/sbin/<instanz>-nginx-reise-installieren, davor FR_SUDO; #552): Es bekommt den
# Reisenamen auf stdin, legt den Baustein mit einem neuen Zufalls-Token an oder erneuert ihn mit seinem bisherigen Pfad, wenn sich
# die Vorlage geändert hat, prüft nginx (sonst alter Stand) und lädt neu. Seine Ausgabe ist nur der Pfad des Links. Danach müssen
# Seite und Rückmeldedienst unter dem Link mit 200 antworten, sonst Abbruch. Beliebig oft aufrufbar (veroeffentlichen.sh ruft es
# je Reise auf); der Link bleibt, wie er ist, auch bei von Hand angelegten Bausteinen.
# Der Link zur Seite kommt nach seiten.json im Ordner des Konnektors (für das Werkzeug meine_reisen).
#
# Voraussetzung (einmalig, einrichten.sh): Im server-Block von FR_ADRESSE steht  include <FR_NGINX_SNIPPETS>/<instanz>-*.conf;
# Ausgabe: „Seite: <url>“. Links nie ins Repo, in Issues oder Nachrichten.
# Für Tests überschreibbar: FS_BASIS, FS_SUDO, FS_ABRUF, KN_SEITENLINKS.
set -eEuo pipefail
# Jeder Abbruch ohne eigene Meldung bekommt eine ERROR-Zeile mit Zeile und Befehl (unaufgelöst, also ohne Link):
# veroeffentlichen.sh zeigt aus dieser Ausgabe nur ERROR-Zeilen, sonst bliebe „not released“ ohne Grund (#465).
trap 'rc=$?; echo "ERROR: freischalten.sh stopped at line $LINENO (exit $rc): $BASH_COMMAND"' ERR
. "$(dirname "${BASH_SOURCE[0]}")/gemeinsam.sh"

REISE="${1:?usage: freischalten.sh <trip>}"
[ -z "${2:-}" ] || { echo "ERROR: freischalten.sh takes only the trip; links for the Claude app no longer exist (#421)."; exit 1; }
WURZEL="$FR_WURZEL"
BASIS="${FS_BASIS:-$FR_ADRESSE}"
SUDO="${FS_SUDO-${FR_SUDO-sudo -n}}"
HELFER="${FR_NGINX_REISE_HELFER:-/usr/local/sbin/$FR_INSTANZ-nginx-reise-installieren}"
SEITENLINKS="${KN_SEITENLINKS:-$FR_KONNEKTOR/seiten.json}"

abruf() {  # <url> -> HTTP-Code
  if [ -n "${FS_ABRUF:-}" ]; then $FS_ABRUF "$1"; else curl -s -o /dev/null -w '%{http_code}' --max-time 15 "$1"; fi
}

[[ "$REISE" =~ ^[a-z0-9][a-z0-9-]{1,39}$ ]] || { echo "ERROR: trip “$REISE”: lowercase letters, digits and hyphen only."; exit 1; }
# Ordner der Reisen: eine Reise aus dem Reisespeicher liegt materialisiert im Bau-Ordner (Stufe 3, #348), sonst in Git
if [ -n "${FR_REISENORDNER:-}" ]; then REISENORDNER="$FR_REISENORDNER"
elif ist_speicherreise "$REISE"; then REISENORDNER="$FR_DIENST/bau/reisen"
else REISENORDNER="$WURZEL/reisen"; fi
[ -f "$REISENORDNER/$REISE/reise.yaml" ] || [ -f "$REISENORDNER/$REISE/reise.json" ] \
  || { echo "ERROR: trip “$REISE” does not exist."; exit 1; }
[ -n "$BASIS" ] || { echo "ERROR: FR_ADRESSE is not set (settings of the instance)."; exit 1; }
[ -x "$HELFER" ] || { echo "ERROR: helper $HELFER is missing (einrichten.sh --installieren, docs/betrieb.md); nothing changed."; exit 1; }
# Ohne Root-Rechte sofort abbrechen (#465): Aus einem Dienst mit NoNewPrivileges (Schreibweg) scheitert jedes sudo. Geprüft
# wird genau die Regel für das Hilfsprogramm (sudo -l), ohne es aufzurufen.
if [ -n "$SUDO" ] && ! $SUDO -l "$HELFER" > /dev/null 2>&1; then
  echo "ERROR: no root rights here (“$SUDO $HELFER” is not allowed, e.g. NoNewPrivileges in a service); nothing changed."; exit 1
fi

# Baustein über das Hilfsprogramm: Ausgang 0 angelegt oder erneuert und geladen, 2 nichts zu tun, sonst Fehler (nichts
# geladen); auf stdout nur der Pfad, auf stderr der Grund
fehler_datei="$(mktemp)"; trap 'rm -f "$fehler_datei"' EXIT
hrc=0
pfad="$(printf '%s\n' "$REISE" | $SUDO "$HELFER" 2> "$fehler_datei")" || hrc=$?
grund="$(tr '\n' ' ' < "$fehler_datei" | sed 's/ *$//')"
case "$hrc" in
  0|2) ;;
  3) echo "ERROR: the nginx helper rejected $REISE, nothing changed: ${grund:-no reason}"; exit 1 ;;
  4) echo "ERROR: nginx rejects the configuration for $REISE; the old state stays in force, nothing changed: ${grund:-}"; exit 1 ;;
  5) echo "ERROR: block of $REISE installed and tested, but the nginx reload failed: ${grund:-}"; exit 1 ;;
  6) case "$grund" in
       *"rollback failed"*) echo "ERROR: nginx rejects the configuration for $REISE and the rollback failed, not reloaded: $grund" ;;
       *) echo "ERROR: nginx rejects the configuration for $REISE, also with the previous state; the old state stays in force, not reloaded: ${grund:-}" ;;
     esac; exit 1 ;;
  *) echo "ERROR: nginx helper for $REISE ended with exit $hrc, not reloaded: ${grund:-}"; exit 1 ;;
esac
neu=""
if [ "$hrc" = 0 ]; then
  case "$grund" in *"block renewed"*) echo "Block renewed: $REISE" ;; *) neu=1 ;; esac
fi
[[ "$pfad" =~ ^[A-Za-z0-9_-]+$ ]] || { echo "ERROR: no path in the block of $REISE (answer of the helper)."; exit 1; }
url="$BASIS/$pfad/"
# Nach dem Neuladen braucht nginx einen Moment, bis die neuen Pfade gelten: Ein neuer Link wird deshalb mehrmals versucht.
versuche=1; [ -n "$neu" ] && versuche="${FS_VERSUCHE:-10}"
# 429 heißt: Die Anfragebegrenzung von nginx hat gegriffen (je IP, gemeinsam für die API aller Reisen; der Server fragt
# sich hier selbst von außen ab und teilt sich das Kontingent mit seinen übrigen Prüfungen). Das sagt nichts über die
# Reise; warten und erneut fragen, ohne dass es als Versuch zählt (#198). Die Zone lässt alle 2 s einen Abruf nach.
for teil in "page|" "feedback service|api/gesund"; do
  gedrosselt=0
  for ((i = 1; ; i++)); do
    code="$(abruf "$url${teil#*|}" || true)"
    if [ "$code" = 429 ] && [ "$gedrosselt" -lt "${FS_429_VERSUCHE:-6}" ]; then
      gedrosselt=$((gedrosselt + 1)); i=$((i - 1)); sleep "${FS_429_WARTEN:-5}"; continue
    fi
    { [ "$code" = 200 ] || [ "$i" -ge "$versuche" ]; } && break
    sleep "${FS_WARTEN:-1}"
  done
  [ "$code" = 200 ] || { echo "ERROR: ${teil%|*} of $REISE answers with ${code:-nothing} instead of 200${neu:+ (link just created; is the include missing in nginx?)}."; exit 1; }
done
[ -n "$neu" ] && echo "Released: $REISE"

# Link zur Seite für meine_reisen (Datei nur für den Betreiber lesbar)
python3 - "$SEITENLINKS" "$REISE" "$url" <<'PY'
import json, os, sys
from pathlib import Path
p, reise, url = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
try:
    d = json.loads(p.read_text(encoding="utf-8"))
except (OSError, ValueError):
    d = {}
if d.get(reise) != url:
    d[reise] = url
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    os.chmod(tmp, 0o600)
    tmp.replace(p)
PY
echo "Seite: $url"
