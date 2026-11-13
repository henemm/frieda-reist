#!/usr/bin/env bash
# Eigener Kartendienst der Instanz (Overpass bei Bedarf, #444, docs/betrieb.md „Eigener Kartendienst“): Daten einspielen.
#
#   betrieb/kartendienst.sh einspielen     lädt die Auszüge aus FR_KARTENDIENST_REGIONEN (mit Prüfsumme), spielt sie im
#                                                 Container (Modus init) in einen Nebenordner ein, schreibt abdeckung.json
#                                                 (Rahmen je Region, Prüfsumme der Regionenliste, Zeitpunkt, Stand der Daten),
#                                                 prüft mit einer echten Abfrage und schaltet erst dann auf den neuen Stand um
#   betrieb/kartendienst.sh aktualisieren  dasselbe, aber nur, wenn der Stand älter als ein Monat ist oder sich die
#                                                 Regionenliste geändert hat (täglich vom Timer <instanz>-kartendienst-aktualisieren)
#
# Werte aus den Einstellungen der Instanz: FR_KARTENDIENST_ORDNER (Datenordner, wird als Ganzes umgeschaltet; sein Elternordner
# muss dem Dienstbenutzer gehören), FR_KARTENDIENST_REGIONEN, FR_KARTENDIENST_SPEICHER. Untergrenzen der Prüfung von freiem
# Speicher und Platz in MB: KD_SPEICHER_MIN_MB (1700), KD_PLATZ_MIN_MB (3000); Wartezeit auf die Sperre in
# Sekunden: KD_SPERRE_WARTEN (3600). Arbeitsdateien liegen unter TMPDIR.
# Scheitert ein Schritt, bleibt der bisherige Stand unverändert, der Nebenordner wird gelöscht, Ausgang ungleich 0.
# Läuft nie gleichzeitig mit einem Lauf des Veröffentlichens (dessen Prüfläufe brauchen selbst viel Speicher) und nie doppelt.
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/gemeinsam.sh"

ORDNER="${FR_KARTENDIENST_ORDNER:-}"
ORDNER="${ORDNER%/}"
REGIONEN="${FR_KARTENDIENST_REGIONEN:-}"
SPEICHER="${FR_KARTENDIENST_SPEICHER:-2g}"
SPEICHER_MIN_MB="${KD_SPEICHER_MIN_MB:-1700}"
PLATZ_MIN_MB="${KD_PLATZ_MIN_MB:-3000}"
SPERRE_WARTEN="${KD_SPERRE_WARTEN:-3600}"
ALTER_TAGE=30
PY="$FR_PYTHON"; [ -x "$PY" ] || PY=python3
PROBE="$FR_INSTANZ-kartendienst-probe"
NEBEN="" ALT="" ARBEIT="" UMGESCHALTET=""
DATEIEN=()

fehler() { echo "ERROR: $*" >&2; exit 1; }

eingaben_pruefen() {
  [[ "$ORDNER" =~ ^/[A-Za-z0-9_./-]+$ ]] || fehler "FR_KARTENDIENST_ORDNER (absolute data folder) is missing or invalid."
  [ -n "$REGIONEN" ] || fehler "FR_KARTENDIENST_REGIONEN is empty (e.g. europe/andorra)."
  local r
  set -f
  for r in $REGIONEN; do
    [[ "$r" =~ ^[a-z0-9_-]+(/[a-z0-9_-]+)*$ ]] || fehler "region “$r”: a path of the extracts such as europe/andorra"
  done
  set +f
}

pruefsumme() {  # Prüfsumme der Regionenliste, unabhängig von Reihenfolge und Doppelten
  set -f
  printf '%s\n' $REGIONEN | sort -u | sha256sum | cut -c1-64
  set +f
}

neu_noetig() {  # Ausgang 0: einspielen (keine oder kaputte abdeckung.json, andere Liste, älter als ALTER_TAGE)
  "$PY" -I - "$ORDNER/abdeckung.json" "$(pruefsumme)" "$ALTER_TAGE" <<'PY'
import datetime, json, sys
try:
    with open(sys.argv[1], encoding="utf-8") as f:
        d = json.load(f)
    stand = datetime.datetime.strptime(d["stand"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
    alt = datetime.datetime.now(datetime.timezone.utc) - stand > datetime.timedelta(days=int(sys.argv[3]))
    sys.exit(0 if alt or d.get("regionen_pruefsumme") != sys.argv[2] else 1)
except Exception:
    sys.exit(0)
PY
}

sperren() {  # nie doppelt, nie neben dem Veröffentlichen (Sperre wie veroeffentlichen.sh); beide warten höchstens
  # KD_SPERRE_WARTEN Sekunden (eine Stunde)
  exec 8>"$FR_SPERREN/$FR_INSTANZ-kartendienst.lock"
  flock -w "$SPERRE_WARTEN" 8 || fehler "another import is still running."
  if [ -d "$FR_DIENST" ]; then
    exec 9>"$FR_DIENST/veroeffentlichen.lock"
    flock -w "$SPERRE_WARTEN" 9 || fehler "publishing (with its checks) is still running; try again later."
  fi
}

reserven_pruefen() {  # freier Speicher und Platz neben dem Datenordner und unter TMPDIR
  local frei ort
  frei=$(awk '/^MemAvailable:/ {print int($2 / 1024)}' /proc/meminfo)
  [ "${frei:-0}" -ge "$SPEICHER_MIN_MB" ] || fehler "only ${frei:-0} MB memory available, the import needs $SPEICHER_MIN_MB MB."
  for ort in "$(dirname "$ORDNER")" "${TMPDIR:-/tmp}"; do
    frei=$(df -Pm "$ort" | awk 'NR == 2 {print $4}')
    [ "${frei:-0}" -ge "$PLATZ_MIN_MB" ] || fehler "only ${frei:-0} MB free in $ort, the import needs $PLATZ_MIN_MB MB."
  done
}

weg() {  # <ordner>: löschen; Dateien, die der Container angelegt hat, gehören dessen Benutzer und gehen nur über ihn weg
  [ -n "$1" ] && [ -e "$1" ] || return 0
  rm -rf "$1" 2>/dev/null || docker run --rm --entrypoint rm -v "$(dirname "$1"):/eltern" "$KD_BILD" -rf "/eltern/$(basename "$1")"
  [ ! -e "$1" ]
}

aufraeumen() {  # bei jedem Ende: Probe-Container, Arbeitsdateien, Nebenordner; ein halbes Umschalten zurücknehmen
  local status=$?
  set +e
  [ -z "$ARBEIT" ] || { docker rm -f "$PROBE" > /dev/null 2>&1; rm -rf "$ARBEIT"; }
  if [ -n "$ALT" ] && [ -e "$ALT" ] && [ -z "$UMGESCHALTET" ] && [ ! -e "$ORDNER" ]; then mv "$ALT" "$ORDNER"; fi
  weg "$NEBEN"
  [ -z "$UMGESCHALTET" ] || weg "$ALT"
  exit "$status"
}

herunterladen() {  # Auszüge mit Prüfsumme nach ARBEIT; ihre Dateinamen nach DATEIEN
  local quelle r datei
  quelle="$(cd "$FR_BETRIEB/../engine" && "$PY" -c 'import kartendienst; print(kartendienst.AUSZUEGE)')"
  set -f
  for r in $REGIONEN; do
    datei="${r//\//_}.osm.pbf"
    echo "Downloading $r …"
    curl -fsSL --retry 3 -o "$ARBEIT/$datei" "$quelle/$r-latest.osm.pbf" || fehler "download of $r failed."
    curl -fsSL --retry 3 -o "$ARBEIT/$datei.md5" "$quelle/$r-latest.osm.pbf.md5" || fehler "checksum of $r not available."
    [ "$(md5sum < "$ARBEIT/$datei" | cut -d' ' -f1)" = "$(cut -d' ' -f1 < "$ARBEIT/$datei.md5")" ] || fehler "checksum of $r does not match."
    DATEIEN+=("$datei")
  done
  set +f
}

rahmen_holen() {  # <datei>…: Kopf jeder Datei (osmium fileinfo im Container) nach ARBEIT/<datei>.info.json
  local d
  for d in "$@"; do
    docker run --rm --entrypoint osmium -v "$ARBEIT:/data:ro" "$KD_BILD" fileinfo -j "/data/$d" > "$ARBEIT/$d.info.json" \
      || fehler "osmium fileinfo $d failed."
  done
}

einspielen_im_container() {  # <datei>…: Vorverarbeitung (osmium zu osm.bz2) und Einspielen im Modus init in den Nebenordner
  local vor="osmium cat /data/$1"
  [ "$#" -eq 1 ] || vor="osmium merge$(printf ' /data/%s' "$@")"
  docker rm -f "$FR_INSTANZ-kartendienst-einspielen" > /dev/null 2>&1 || true
  docker run --rm --name "$FR_INSTANZ-kartendienst-einspielen" --memory "$SPEICHER" -e OVERPASS_MODE=init -e OVERPASS_META=no \
    -e OVERPASS_USE_AREAS=false -e OVERPASS_STOP_AFTER_INIT=true -e "OVERPASS_PLANET_URL=file:///data/$1" \
    -e "OVERPASS_PLANET_PREPROCESS=$vor -o /db/planet.osm.bz2 -f osm.bz2 --overwrite" \
    -v "$NEBEN:/db" -v "$ARBEIT:/data:ro" "$KD_BILD" || fehler "import in the container failed."
}

probeabfrage() {  # echte Abfrage gegen den Nebenordner in einem Probe-Container -> ARBEIT/probe.json
  local port
  docker run -d --rm --name "$PROBE" --memory "$SPEICHER" -p 127.0.0.1::80 -e OVERPASS_MODE=init -e OVERPASS_META=no \
    -e OVERPASS_USE_AREAS=false -v "$NEBEN:/db" "$KD_BILD" > /dev/null || fehler "probe container did not start."
  port="$(docker port "$PROBE" 80/tcp | head -n 1 | sed 's/.*://')"
  curl -fsS --retry 30 --retry-delay 1 --retry-all-errors --retry-max-time 90 --max-time 30 -o "$ARBEIT/probe.json" \
    --data-urlencode "data=[out:json];node(1);out ids;" "http://127.0.0.1:$port/api/interpreter" || fehler "probe query failed."
  grep -q '"elements"' "$ARBEIT/probe.json" || fehler "probe query gave no valid answer."
  docker stop -t 20 "$PROBE" > /dev/null 2>&1 || true
}

abdeckung_schreiben() {  # <datei>…: abdeckung.json im Nebenordner
  "$PY" -I - "$NEBEN/abdeckung.json" "$(pruefsumme)" "$ARBEIT/probe.json" "${@/#/$ARBEIT/}" <<'PY'
import datetime, json, sys
ziel, summe, probe, *dateien = sys.argv[1:]
rahmen = []
for d in dateien:
    with open(d + ".info.json", encoding="utf-8") as f:
        w, s, o, n = json.load(f)["header"]["boxes"][0]     # osmium: min_lon, min_lat, max_lon, max_lat
    rahmen.append([float(s), float(w), float(n), float(o)])
with open(probe, encoding="utf-8") as f:
    daten = (json.load(f).get("osm3s") or {}).get("timestamp_osm_base")
jetzt = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
with open(ziel, "w", encoding="utf-8") as f:
    json.dump({"stand": jetzt, "daten": daten, "regionen_pruefsumme": summe, "rahmen": rahmen}, f)
PY
}

wiederherstellen() {  # harter Abbruch zwischen den beiden Umbenennungen: Datenordner fehlt, der alte Stand liegt daneben
  local alt
  alt="$(dirname "$ORDNER")/.$(basename "$ORDNER").alt"
  if [ ! -e "$ORDNER" ] && [ -d "$alt" ]; then
    mv "$alt" "$ORDNER"
    echo "Map service: previous state restored after an interrupted switch."
  fi
}

umschalten() {  # neuen Stand an die Stelle des Datenordners; der alte bleibt bis zum Erfolg daneben
  docker stop "$FR_INSTANZ-kartendienst" > /dev/null 2>&1 || true   # läuft er gerade, startet ihn der nächste Aufruf neu
  if [ -e "$ORDNER" ]; then mv "$ORDNER" "$ALT"; fi
  mv "$NEBEN" "$ORDNER"
  UMGESCHALTET=1
  chmod 755 "$ORDNER"
}

einspielen() {  # nur unter der Sperre aufrufen (Hauptablauf unten)
  local eltern name
  eltern="$(dirname "$ORDNER")"; name="$(basename "$ORDNER")"
  reserven_pruefen
  NEBEN="$eltern/.$name.neu"; ALT="$eltern/.$name.alt"
  weg "$NEBEN"; weg "$ALT"   # Reste eines abgebrochenen Laufs
  ARBEIT="$(mktemp -d "${TMPDIR:-/tmp}/kartendienst-XXXXXX")"
  trap aufraeumen EXIT
  mkdir "$NEBEN"; chmod 755 "$NEBEN"   # 755, sonst kann der Container die Datenbank nicht öffnen
  herunterladen
  [ "${#DATEIEN[@]}" -gt 0 ] || fehler "nothing downloaded."
  rahmen_holen "${DATEIEN[@]}"
  einspielen_im_container "${DATEIEN[@]}"
  probeabfrage
  abdeckung_schreiben "${DATEIEN[@]}"
  umschalten
  echo "Map service: regions $REGIONEN imported into $ORDNER."
}

case "${1:-}" in
  einspielen|aktualisieren) ;;
  *) echo "Usage: kartendienst.sh einspielen|aktualisieren" >&2; exit 2 ;;
esac
eingaben_pruefen
[ -d "$(dirname "$ORDNER")" ] && [ -w "$(dirname "$ORDNER")" ] || fehler "$(dirname "$ORDNER") does not exist or is not writable."
# Die Sperre gilt für den ganzen Lauf, auch für Wiederherstellen und Prüfen: Sonst holte ein Timer-Lauf den alten Stand
# zurück, während ein anderer Lauf gerade umschaltet
sperren
wiederherstellen   # vor dem Aufräumen der Reste, sonst ginge der alte Stand verloren
if [ "$1" = einspielen ] || neu_noetig; then
  einspielen
else
  echo "Map service is up to date (same regions, younger than $ALTER_TAGE days)."
fi
