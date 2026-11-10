#!/usr/bin/env bash
# Baut eine Reise-Seite und legt sie in <FR_SEITEN>/<reise>/ ab (nginx liefert von dort aus), bringt Rückmeldedienst
# und Konnektor auf den Stand der Software und prüft, dass alles antwortet (docs/betrieb.md, Veröffentlichen).
# Aufruf:  FR_WURZEL=<Bauordner> frieda/betrieb/deploy.sh <reise>   (sonst ruft veroeffentlichen.sh es auf)
# Exit:    0 gelungen, 2 Bau dieser Reise gescheitert, 1 alles andere (FR_WURZEL fehlt, Ordner nicht auf main, Reise
#          oder Ordner fehlt, ungesicherte Änderungen, Prüfungen rot, Dienste nicht bereit, Kopieren gescheitert)
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/gemeinsam.sh"
nur_bauordner --main

REISE="${1:?Aufruf: deploy.sh <reise>}"
WURZEL="$FR_WURZEL"
ZIEL="$FR_SEITEN/$REISE"
DIENST="$FR_DIENST"

# Module, die Rückmeldedienst und Konnektor aus <FR_DIENST> laden. Neue Module, die einer davon (auch mittelbar)
# importiert, hier ergänzen; engine/tests/test_betrieb.py prüft das. stand.py lädt reisespeicher.py (Stufe 3, #348): Jede
# Liste mit stand.py trägt es mit; Rückmeldedienst und Konnektor lesen den Speicher nicht selbst.
# Sprachdateien (texte_<kürzel>.py): jede Datei im Ordner engine/ zählt, eine neue Sprache braucht hier keinen Eintrag (docs/sprachen.md)
SPRACHDATEIEN=""
for f in "$WURZEL"/engine/texte_??.py "$WURZEL"/engine/texte_???.py; do [ -e "$f" ] && SPRACHDATEIEN="$SPRACHDATEIEN $(basename "$f")"; done
RM_MODULE="rueckmeldungen.py belege.py reise.py konten.py instanz.py kalender.py stand.py reisespeicher.py stand_git.py texte.py $SPRACHDATEIEN"
KN_MODULE="konnektor.py schnittstelle.py reise.py routen.py packliste.py karte.py konten.py anmeldung.py oauth.py instanz.py belege.py kalender.py push.py stand.py reisespeicher.py texte.py $SPRACHDATEIEN"
# Schreibweg (engine/schreiben.py dienst, ADR-0001 O-3): Für eine Reise aus FR_SPEICHERREISEN (Stufe 2, #347) läuft auch der
# Schreibvorgang (`anwenden`: Werkzeuge, Probebau, Reisespeicher) mit dem Code aus <FR_DIENST>, deshalb steht hier jedes
# Modul, das schreiben.py auch in Funktionen lädt (engine/tests/test_betrieb.py prüft es gegen die Importe), dazu unten
# Vorlage, vendor/ und reisevorlage/. Für Git-Reisen kommt der Code des Schreibvorgangs bis Stufe 5 aus der Arbeitskopie.
SB_MODULE="schreiben.py schreiben_git.py kartendienst.py reisespeicher.py bauen.py routen.py packliste.py gpx.py karte.py neu.py schnittstelle.py konten.py reise.py instanz.py kalender.py stand.py stand_git.py texte.py $SPRACHDATEIEN"
# Push-Dienst (engine/push.py dienst, Issue #21): läuft mit FR_PYTHON (pywebpush), lädt seinen Code aus <FR_DIENST>
PS_MODULE="push.py rueckmeldungen.py belege.py reise.py konten.py instanz.py kalender.py stand.py reisespeicher.py stand_git.py texte.py $SPRACHDATEIEN"

# Quelle der Reise (Stufe 3, #348): Eine Reise aus FR_SPEICHERREISEN baut aus dem Ordner, in den veroeffentlichen.sh sie aus
# dem Reisespeicher materialisiert hat (<FR_DIENST>/bau/reisen/<reise>, außerhalb des Git-Bauordners); jede andere aus Git.
if ist_speicherreise "$REISE"; then
  REISEN="$DIENST/bau/reisen"; GIT_PFADE="engine"; GIT_TEXT="engine/"
else
  REISEN="$WURZEL/reisen"; GIT_PFADE="engine reisen/$REISE"; GIT_TEXT="engine/ or reisen/$REISE"
fi
[ -d "$REISEN/$REISE" ] || { echo "Trip '$REISE' does not exist."; exit 1; }
[ -d "$FR_SEITEN" ] && [ -w "$FR_SEITEN" ] || { echo "$FR_SEITEN is missing or not writable (einrichten.sh, docs/betrieb.md)."; exit 1; }

# Nur gesicherten Stand veröffentlichen: ungesicherte Änderungen an Software oder Reise brechen ab
# shellcheck disable=SC2086
if ! git -C "$WURZEL" diff --quiet HEAD -- $GIT_PFADE || [ -n "$(git -C "$WURZEL" ls-files --others --exclude-standard -- $GIT_PFADE)" ]; then
  echo "ERROR: uncommitted changes in $GIT_TEXT. Commit first, then publish."; exit 1
fi
# Bau: der erste Schritt mit Wirkung. Scheitert er (Baufehler dieser Reise, deterministisch), endet deploy.sh mit 2;
# veroeffentlichen.sh macht dann mit den anderen Reisen weiter, die Seite bleibt auf ihrem letzten guten Stand.
# Warnungen im Plan sperren nie (bauen.py endet dann mit 0).
"$FR_PYTHON" "$WURZEL/engine/bauen.py" --reisen "$REISEN" --ziel "$WURZEL/dist" "$REISE" \
  || { echo "ERROR: build of $REISE failed, the page stays at the last good state."; exit 2; }
# Prüfungen nur der Software (engine/tests); tests/ des Reisen-Repos prüft Inhalt und sperrt nie (docs/betrieb.md).
# veroeffentlichen.sh prüft einmal für alle Reisen und setzt FR_GEPRUEFT auf den geprüften Stand
if [ "${FR_GEPRUEFT:-}" != "$(git -C "$WURZEL" rev-parse HEAD)" ]; then
  pruef_tmp="$(mktemp -d)"   # eigener Ordner für die Testdateien, Grund in veroeffentlichen.sh
  parallel=(); "$FR_PYTHON" -c 'import xdist' 2>/dev/null && parallel=(-n "${FR_PRUEF_PROZESSE:-auto}")   # #395
  "$FR_PYTHON" -m pytest "$WURZEL/engine/tests" -q "${parallel[@]}" --basetemp "$pruef_tmp" || { rm -rf "$pruef_tmp"; exit 1; }
  rm -rf "$pruef_tmp"
fi

# Startprobe (#395, Lehre aus #387): die gebaute Seite im Browser laden; ein Seitenfehler beim Start oder eine leere Seite
# heißt Exit 2, die Seite bleibt auf dem letzten guten Stand. Ohne Playwright nur eine Warnung (HTTP 200 allein hätte #387 nicht gefunden).
PW_MODUL="${PLAYWRIGHT_MODUL:-$WURZEL/engine/tests/playwright/node_modules/playwright/index.mjs}"
if [ -e "$PW_MODUL" ] && command -v node > /dev/null; then
  probe_aus="$(node "$FR_BETRIEB/startprobe.mjs" "$PW_MODUL" "$WURZEL/dist/$REISE" 2>&1)" \
    || { echo "$probe_aus" | head -10; echo "ERROR: start probe of $REISE failed (page error or empty page), the page stays at the last good state."; exit 2; }
else
  echo "Warning: start probe skipped (Playwright or node missing, PLAYWRIGHT_MODUL)."
fi

mkdir -p "$ZIEL"

# Rückmelde-Ablage der Reise (außerhalb Repo und Web-Ordner) und Code der Dienste
mkdir -p "$FR_ABLAGE/$REISE" "$DIENST"
chmod 750 "$FR_ABLAGE" "$FR_ABLAGE/$REISE"
NEU_RM=""; NEU_KN=""; NEU_SB=""; NEU_PS=""
for m in $RM_MODULE; do cmp -s "$WURZEL/engine/$m" "$DIENST/$m" || NEU_RM=1; done
for m in $KN_MODULE; do cmp -s "$WURZEL/engine/$m" "$DIENST/$m" || NEU_KN=1; done
for m in $SB_MODULE; do cmp -s "$WURZEL/engine/$m" "$DIENST/$m" || NEU_SB=1; done
for m in $PS_MODULE; do cmp -s "$WURZEL/engine/$m" "$DIENST/$m" || NEU_PS=1; done
for m in $(printf '%s\n' $RM_MODULE $KN_MODULE $SB_MODULE $PS_MODULE | sort -u); do install -m 644 "$WURZEL/engine/$m" "$DIENST/"; done
# Friedas Symbol (Favicon, App-Symbol) und die Schrift der Anmeldeseiten; der Konnektor liest die Dateien bei jedem
# Abruf, kein Neustart nötig
rsync -a --delete --chmod=D755,F644 --exclude "*.py" "$WURZEL/engine/marke/" "$DIENST/marke/"
# Frieda-App (#21): Manifest, Worker und Skript von Mein Konto; der Konnektor liefert sie aus app/ (ohne Neustart)
rsync -a --delete --chmod=D755,F644 "$WURZEL/engine/app/" "$DIENST/app/"
rsync -a --delete --chmod=D755,F644 --include "*.woff2" --exclude "*" "$WURZEL/engine/vendor/fonts/" "$DIENST/schrift/"
# Bilder der Infoseite (#436): der Konnektor liefert sie aus info/ (ohne Neustart); das Skript zum Erzeugen bleibt im Repo
rsync -a --delete --chmod=D755,F644 --include "*.webp" --exclude "*" "$WURZEL/engine/info/" "$DIENST/info/"
# Was der Probebau und reise_anlegen des Schreibwegs neben den Modulen lesen (Speicherweg, #347; je Vorgang frisch gelesen)
install -m 644 "$WURZEL/engine/vorlage.html" "$WURZEL/engine/sw.vorlage.js" "$DIENST/"
rsync -a --delete --chmod=D755,F644 "$WURZEL/engine/vendor/" "$DIENST/vendor/"
rsync -a --delete --chmod=D755,F644 "$WURZEL/engine/reisevorlage/" "$DIENST/reisevorlage/"
rsync -a --delete --chmod=D755,F644 "$WURZEL/engine/artvorlagen/" "$DIENST/artvorlagen/"   # Vorlagen für Arten (ADR-0011)
mkdir -p "$FR_KONNEKTOR" "$FR_KONTEN" && chmod 700 "$FR_KONNEKTOR" "$FR_KONTEN"
neustart() {
  ${FR_SUDO-sudo -n} systemctl restart "$1" 2>/dev/null && echo "$2 restarted." \
    || echo "$2: code changed, please run: sudo systemctl restart $1"
}
# Neue Bibliotheken in FR_PYTHON (veroeffentlichen.sh, #202): Dienste, die damit laufen, starten neu
[ -n "${FR_BIBLIOTHEKEN_NEU:-}" ] && NEU_SB=1 && NEU_PS=1
# Der Konnektor lädt auch rueckmeldungen.py: ändert sich etwas am Rückmeldedienst, starten beide neu
[ -n "$NEU_RM" ] && neustart "$FR_INSTANZ-rueckmeldungen" "feedback service"
[ -n "$NEU_RM$NEU_KN" ] && neustart "$FR_INSTANZ-konnektor" "Konnektor"
# Der Schreibweg ist nur bei Instanzen aktiv, die ihn eingerichtet haben (einrichten.sh, docs/betrieb.md)
if [ -n "$NEU_SB" ] && systemctl is-enabled --quiet "$FR_INSTANZ-schreiben" 2>/dev/null; then
  neustart "$FR_INSTANZ-schreiben" "Schreibweg"
fi
# Push-Dienst ebenso nur, wenn eingerichtet
if [ -n "$NEU_PS" ] && systemctl is-enabled --quiet "$FR_INSTANZ-push" 2>/dev/null; then
  neustart "$FR_INSTANZ-push" "Push-Dienst"
fi
rsync -a --delete --chmod=D755,F644 "$WURZEL/dist/$REISE/" "$ZIEL/"

# Prüfung: Seite samt PWA-Hülle liegt da, die Dienste antworten (nach einem Neustart kurz warten)
for f in index.html sw.js manifest.json; do
  [ -s "$ZIEL/$f" ] || { echo "ERROR: $ZIEL/$f is missing or empty."; exit 1; }
done
bereit() { for _ in 1 2 3 4 5 6 7 8 9 10; do curl -fsS -o /dev/null "$1" && return 0; sleep 0.5; done; return 1; }
bereit "http://127.0.0.1:$FR_RM_PORT/$REISE/gesund" || { echo "ERROR: feedback service does not respond (systemctl status $FR_INSTANZ-rueckmeldungen)."; exit 1; }
if systemctl is-enabled --quiet "$FR_INSTANZ-konnektor" 2>/dev/null; then
  bereit "http://127.0.0.1:$FR_KN_PORT/gesund" || { echo "ERROR: connector not ready (systemctl status $FR_INSTANZ-konnektor)."; exit 1; }
  # Wege von außen (gemeinsam.sh): beim Veröffentlichen einmal je Lauf nach dem Freischalten statt je Reise
  [ -n "${FR_WEGE_SPAETER:-}" ] || wege_pruefen
fi
echo "Done: $ZIEL ($(du -sh "$ZIEL" | cut -f1))"
