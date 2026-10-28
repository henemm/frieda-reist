#!/usr/bin/env bash
# Baut eine Reise-Seite und legt sie in <FR_SEITEN>/<reise>/ ab (nginx liefert von dort aus), bringt Rückmeldedienst
# und Konnektor auf den Stand der Software und prüft, dass alles antwortet (docs/betrieb.md, Veröffentlichen).
# Aufruf:  frieda/betrieb/deploy.sh <reise>
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/gemeinsam.sh"

REISE="${1:?Aufruf: deploy.sh <reise>}"
WURZEL="$FR_WURZEL"
ZIEL="$FR_SEITEN/$REISE"
DIENST="$FR_DIENST"

# Module, die Rückmeldedienst und Konnektor aus <FR_DIENST> laden. Neue Module, die einer davon (auch mittelbar)
# importiert, hier ergänzen; engine/tests/test_betrieb.py prüft das.
RM_MODULE="rueckmeldungen.py reise.py konten.py"
KN_MODULE="konnektor.py reise.py konten.py anmeldung.py oauth.py"

[ -d "$WURZEL/reisen/$REISE" ] || { echo "Reise '$REISE' gibt es nicht."; exit 1; }
[ -d "$FR_SEITEN" ] && [ -w "$FR_SEITEN" ] || { echo "$FR_SEITEN fehlt oder ist nicht beschreibbar (einrichten.sh, docs/betrieb.md)."; exit 1; }

# Nur gesicherten Stand veröffentlichen: ungesicherte Änderungen an Software oder Reise brechen ab
if ! git -C "$WURZEL" diff --quiet HEAD -- engine "reisen/$REISE" || [ -n "$(git -C "$WURZEL" ls-files --others --exclude-standard -- engine "reisen/$REISE")" ]; then
  echo "FEHLER: ungesicherte Änderungen in engine/ oder reisen/$REISE. Erst committen, dann veröffentlichen."; exit 1
fi
"$FR_PYTHON" "$WURZEL/engine/bauen.py" --reisen "$WURZEL/reisen" --ziel "$WURZEL/dist" "$REISE"
"$FR_PYTHON" -m pytest "$WURZEL/engine/tests" $( [ -d "$WURZEL/tests" ] && echo "$WURZEL/tests" ) -q

mkdir -p "$ZIEL"

# Rückmelde-Ablage der Reise (außerhalb Repo und Web-Ordner) und Code der Dienste
mkdir -p "$FR_ABLAGE/$REISE" "$DIENST"
chmod 750 "$FR_ABLAGE" "$FR_ABLAGE/$REISE"
NEU_RM=""; NEU_KN=""
for m in $RM_MODULE; do cmp -s "$WURZEL/engine/$m" "$DIENST/$m" || NEU_RM=1; done
for m in $KN_MODULE; do cmp -s "$WURZEL/engine/$m" "$DIENST/$m" || NEU_KN=1; done
for m in $(printf '%s\n' $RM_MODULE $KN_MODULE | sort -u); do install -m 644 "$WURZEL/engine/$m" "$DIENST/"; done
# Friedas Symbol (Favicon, App-Symbol); der Konnektor liest die Dateien bei jedem Abruf, kein Neustart nötig
rsync -a --delete --chmod=D755,F644 --exclude "*.py" "$WURZEL/engine/marke/" "$DIENST/marke/"
mkdir -p "$FR_KONNEKTOR" && chmod 700 "$FR_KONNEKTOR"
neustart() {
  ${FR_SUDO-sudo -n} systemctl restart "$1" 2>/dev/null && echo "$2 neu gestartet." \
    || echo "$2: Code geändert, bitte: sudo systemctl restart $1"
}
# Der Konnektor lädt auch rueckmeldungen.py: ändert sich etwas am Rückmeldedienst, starten beide neu
[ -n "$NEU_RM" ] && neustart "$FR_INSTANZ-rueckmeldungen" "Rückmeldedienst"
[ -n "$NEU_RM$NEU_KN" ] && neustart "$FR_INSTANZ-konnektor" "Konnektor"
rsync -a --delete --chmod=D755,F644 "$WURZEL/dist/$REISE/" "$ZIEL/"

# Prüfung: Seite samt PWA-Hülle liegt da, die Dienste antworten (nach einem Neustart kurz warten)
for f in index.html sw.js manifest.json; do
  [ -s "$ZIEL/$f" ] || { echo "FEHLER: $ZIEL/$f fehlt oder ist leer."; exit 1; }
done
bereit() { for _ in 1 2 3 4 5 6 7 8 9 10; do curl -fsS -o /dev/null "$1" && return 0; sleep 0.5; done; return 1; }
bereit "http://127.0.0.1:$FR_RM_PORT/$REISE/gesund" || { echo "FEHLER: Rückmeldedienst antwortet nicht (systemctl status $FR_INSTANZ-rueckmeldungen)."; exit 1; }
if systemctl is-enabled --quiet "$FR_INSTANZ-konnektor" 2>/dev/null; then
  bereit "http://127.0.0.1:$FR_KN_PORT/gesund" || { echo "FEHLER: Konnektor nicht bereit (systemctl status $FR_INSTANZ-konnektor)."; exit 1; }
fi
echo "Fertig: $ZIEL ($(du -sh "$ZIEL" | cut -f1))"
