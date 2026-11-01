#!/usr/bin/env bash
# Veröffentlicht automatisch, was auf main liegt (docs/betrieb.md, Veröffentlichen): holt origin/main in den
# Bauordner, bringt die Software (Submodul) auf den festgehaltenen Stand und ruft deploy.sh für jede Reise
# auf, sobald main einen neuen Stand hat. Gestartet alle 5 Minuten vom Timer <instanz>-veroeffentlichen.timer und
# gleich nach jedem Schreibvorgang des Schreibwegs (engine/schreiben.py).
# Aufruf von Hand:  FR_WURZEL=<Bauordner> frieda/betrieb/veroeffentlichen.sh          (nur wenn main neu ist)
#                   FR_WURZEL=<Bauordner> frieda/betrieb/veroeffentlichen.sh --immer  (auch ohne neuen Stand, auch
#                   einen bekannten roten). Ohne FR_WURZEL bricht es ab (#137).
# Ist der Bauordner nicht auf main oder nicht sauber, wird nichts angefasst und nichts gemerkt.
# Tor (#142): Sperren können nur die Tests der Software (engine/tests) und ein gescheiterter Bau einer Reise (deploy.sh
# Exit 2). Die Tests des Reisen-Repos (tests/) prüfen Inhalt: rot dort ist nur eine Warnung (einmal je Commit eine
# Nachricht an den Betrieb). Eine rote Reise hält die anderen nicht auf; sie bleibt auf ihrem letzten guten Stand.
# Rot-Datei <FR_DIENST>/veroeffentlichen-rot: merkt einen roten Stand (commit, art, reisen, seit, gemeldet). Derselbe
# Commit wird ohne --immer nicht noch einmal geprüft („Bekannter roter Stand“). Ab FR_ROT_MELDEN_NACH_MINUTEN Minuten
# Rot geht genau einmal je Rot-Phase ein Alarm an den Betrieb, bei roten Reisen dazu eine Meldung an deren
# Organisator:innen (engine/waechter.py rot-melden). Infrastrukturfehler (deploy.sh Exit 1, Vorspulen, Submodul) werden
# nicht gemerkt; der nächste Lauf wiederholt sie, weil nur ein ganz gelungener Lauf den Stand merkt.
# Überwachung: Nach fachlichem Erfolg (nichts Neues oder alles veröffentlicht) wird <FR_DIENST>/veroeffentlichen-erfolg
# berührt; ist FR_HEARTBEAT_VEROEFFENTLICHEN gesetzt (Adresse, in <FR_DIENST>/betrieb.env), wird sie zusätzlich abgerufen.
# Übersprungene Läufe, rote Stände (auch teilweise rot) und Fehler tun beides nicht.
# Neue Reisen: Nach dem Veröffentlichen ruft das Skript freischalten.sh für jede gelungene Reise auf (legt einer neuen Reise
# ihren geheimen Link an, prüft die Seite, schreibt seiten.json) und stellt ausstehende Links neuer Reisen aus der
# Claude-App zu (zustellen.py). Links stehen nie im Protokoll.
# Die Prüfungen (pytest) laufen einmal je Lauf vor allen Reisen; deploy.sh überspringt sie dann für genau diesen Stand
# (FR_GEPRUEFT). Sonst liefen sie je Reise einmal, und der Lauf stieße bei drei Reisen an die Zeitgrenze der Unit.
# Für Tests überschreibbar: VF_PRUEFEN, VF_STAND, VF_DEPLOY, VF_FREISCHALTEN, VF_AUSSTEHEND, VF_SPERRE, VF_STEMPEL, VF_HEARTBEAT,
# VF_ROT (Rot-Datei), VF_JETZT (Uhr, Sekunden seit 1970), VF_ROTMELDEN (statt engine/waechter.py rot-melden).
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/gemeinsam.sh"
nur_bauordner

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

jetzt() { echo "${VF_JETZT:-$(date +%s)}"; }

rot_lesen() {  # Rot-Datei in rot_commit, rot_art, rot_reisen, rot_seit, rot_gemeldet (leer, wenn es keine gibt)
  local zeile
  rot_commit=""; rot_art=""; rot_reisen=""; rot_seit=""; rot_gemeldet=""
  [ -r "$rot_datei" ] || return 0
  while IFS= read -r zeile || [ -n "$zeile" ]; do
    case "$zeile" in
      commit=*) rot_commit="${zeile#*=}" ;;
      art=*) rot_art="${zeile#*=}" ;;
      reisen=*) rot_reisen="${zeile#*=}" ;;
      seit=*) rot_seit="${zeile#*=}" ;;
      gemeldet=*) rot_gemeldet="${zeile#*=}" ;;
    esac
  done < "$rot_datei"
}

rot_ablegen() {  # schreibt rot_* in die Rot-Datei (erst daneben, dann umbenennen)
  mkdir -p "$(dirname "$rot_datei")"
  printf 'commit=%s\nart=%s\nreisen=%s\nseit=%s\ngemeldet=%s\n' \
    "$rot_commit" "$rot_art" "$rot_reisen" "$rot_seit" "$rot_gemeldet" > "$rot_datei.neu"
  mv "$rot_datei.neu" "$rot_datei"
}

rot_schreiben() {  # <commit> <art> <reisen>: neuer roter Stand; seit und gemeldet bleiben innerhalb einer Rot-Phase
  rot_lesen
  if [ -z "$rot_seit" ]; then
    rot_seit="$(date -u -d "@$(jetzt)" +%Y-%m-%dT%H:%M:%SZ)"; rot_gemeldet=0
  fi
  rot_commit="$1"; rot_art="$2"; rot_reisen="$3"
  rot_ablegen
}

alarm_senden() {  # <betreff> <text>: wie fr_melden high, aber mit Rückgabewert (Erfolg des Meldewegs)
  [ -n "$FR_MELDEN" ] || return 0
  "$FR_MELDEN" high "$FR_TITEL: $1" "$2" > /dev/null 2>&1
}

alarm_pruefen() {  # Alarm ab der Schwelle: Meldung an die Organisator:innen roter Reisen, einmal je Rot-Phase an den Betrieb
  local schwelle="${FR_ROT_MELDEN_NACH_MINUTEN:-30}" seit_s minuten
  rot_lesen
  [ -n "$rot_seit" ] || return 0
  [[ "$schwelle" =~ ^[0-9]+$ ]] || schwelle=30
  seit_s="$(date -u -d "$rot_seit" +%s 2>/dev/null)" || { echo "Warnung: Rot-Datei mit ungültigem seit ($rot_seit)."; return 0; }
  minuten=$(( ($(jetzt) - seit_s) / 60 ))
  [ "$minuten" -ge "$schwelle" ] || return 0
  if [ "$rot_art" = reise ] && [ -n "$rot_reisen" ]; then
    # je Reise und Rot-Phase eine Meldung (schluessel mit seit), darum bei jedem Lauf gefahrlos
    if [ -n "${VF_ROTMELDEN:-}" ]; then
      "$VF_ROTMELDEN" --reisen "$rot_reisen" --seit "$rot_seit" || echo "Warnung: Meldung an die Organisator:innen nicht angelegt."
    else
      "$FR_PYTHON" "$wurzel/engine/waechter.py" rot-melden --reisen "$rot_reisen" --seit "$rot_seit" \
        || echo "Warnung: Meldung an die Organisator:innen nicht angelegt."
    fi
  fi
  [ "$rot_gemeldet" = 1 ] && return 0
  if alarm_senden "Veröffentlichen seit $minuten Minuten rot" \
    "Art: $rot_art${rot_reisen:+, Reisen: $rot_reisen}, Stand ${rot_commit:0:7}, rot seit $rot_seit (UTC). Gelungene Reisen sind online, rote bleiben auf ihrem letzten guten Stand. Log: journalctl -u $FR_INSTANZ-veroeffentlichen -n 100"; then
    rot_gemeldet=1; rot_ablegen
  else
    echo "Warnung: Alarm an den Betrieb nicht gesendet, nächster Lauf versucht es wieder."
  fi
}

pruefen_lauf() {  # <ordner>: pytest über engine/tests oder tests/ des Reisen-Repos
  if [ -n "$pruefen" ]; then "$pruefen" "$1"; return; fi
  "$FR_PYTHON" -m pytest "$1" -q --basetemp "$pruef_tmp"
}

# Alles steckt in main(), damit bash das Skript ganz einliest, bevor git es mit dem Submodul eventuell ersetzt.
main() {
  local stand deploy immer="" alt neu reise freischalten aus rc gut="" rote="" warnung
  wurzel="$FR_WURZEL"
  stand="${VF_STAND:-$FR_DIENST/veroeffentlicht}"
  deploy="${VF_DEPLOY:-$FR_BETRIEB/deploy.sh}"
  pruefen="${VF_PRUEFEN:-}"
  freischalten="${VF_FREISCHALTEN:-$FR_BETRIEB/freischalten.sh}"
  ausstehend="${VF_AUSSTEHEND:-$FR_KONNEKTOR/neue-reisen-ausstehend.jsonl}"
  rot_datei="${VF_ROT:-$FR_DIENST/veroeffentlichen-rot}"
  warnung="$FR_DIENST/veroeffentlichen-warnung"
  [ "${1:-}" = "--immer" ] && immer=1

  exec 9>"${VF_SPERRE:-$FR_SPERREN/$FR_INSTANZ-veroeffentlichen.lock}"
  flock -n 9 || { echo "Läuft schon, übersprungen."; return 0; }

  cd "$wurzel"
  if [ "$(git rev-parse --abbrev-ref HEAD)" != main ]; then
    echo "Bauordner ist nicht auf main ($(git rev-parse --abbrev-ref HEAD)), übersprungen."; return 0
  fi
  if ! git diff --quiet HEAD || [ -n "$(git ls-files --others --exclude-standard)" ]; then
    echo "Ungesicherte Änderungen im Bauordner, übersprungen."; return 0
  fi

  mkdir -p "$FR_DIENST"   # Zustand des Veröffentlichens (Stand, Rot-Datei, Merker der Warnung, Stempel)
  git fetch -q origin main
  neu="$(git rev-parse origin/main)"
  alt="$(cat "$stand" 2>/dev/null || true)"
  if [ -z "$immer" ] && [ "$neu" = "$alt" ]; then zustellen; rm -f "$rot_datei"; erfolg_melden; return 0; fi

  git merge -q --ff-only origin/main || { echo "FEHLER: main lässt sich nicht vorspulen (lokale Commits?)."; return 1; }
  # Software (Submodul) auf den Stand bringen, den main festhält
  git submodule update --init --quiet || { echo "FEHLER: Submodul der Software lässt sich nicht holen."; return 1; }

  # Bekannter roter Stand: nicht noch einmal prüfen und bauen (kostet Minuten), kein Stempel, kein Heartbeat
  rot_lesen
  if [ -z "$immer" ] && [ -n "$rot_commit" ] && [ "$rot_commit" = "$neu" ]; then
    echo "Bekannter roter Stand ${neu:0:7}, übersprungen (Art: $rot_art${rot_reisen:+, Reisen: $rot_reisen}). Neu geprüft wird mit einem neuen Commit oder --immer."
    zustellen
    alarm_pruefen
    return 0
  fi

  echo "Veröffentliche $(git log -1 --format='%h %s')"
  # Eigener Ordner für die Testdateien: Mit der Vorgabe (/tmp/pytest-of-<user>) räumt jeder weitere pytest-Lauf auf dem
  # Rechner die Ordner älterer Läufe weg, auch die eines noch laufenden (roter Lauf 29.10.2026 bei gleichzeitigen Tests).
  pruef_tmp="$(mktemp -d)"
  if ! pruefen_lauf engine/tests; then
    rm -rf "$pruef_tmp"
    echo "FEHLER: Prüfungen rot (engine/tests, Software), nichts veröffentlicht."
    rot_schreiben "$neu" software ""
    alarm_pruefen
    return 1
  fi
  # Tests des Reisen-Repos prüfen Inhalt (Schnappschüsse der Reisen): rot sperrt nie, einmal je Commit eine Nachricht
  if [ -d tests ] && ! pruefen_lauf tests; then
    echo "Warnung: Tests des Reisen-Repos rot (sperren nicht)."
    if [ "$(cat "$warnung" 2>/dev/null || true)" != "$neu" ]; then
      fr_melden normal "Tests des Reisen-Repos rot" "Stand ${neu:0:7}: Die Tests in tests/ des Reisen-Repos sind rot. Sie sperren das Veröffentlichen nicht (docs/betrieb.md, Konvention für tests/). Log: journalctl -u $FR_INSTANZ-veroeffentlichen -n 100"
      mkdir -p "$(dirname "$warnung")"
      echo "$neu" > "$warnung"
    fi
  fi
  rm -rf "$pruef_tmp"
  FR_GEPRUEFT="$(git rev-parse HEAD)"; export FR_GEPRUEFT
  for reise in reisen/*/reise.json; do
    [ -e "$reise" ] || continue
    reise="$(basename "$(dirname "$reise")")"
    rc=0; "$deploy" "$reise" || rc=$?
    case "$rc" in
      0) gut="$gut $reise" ;;
      2) echo "FEHLER: Bau von $reise gescheitert, die Reise bleibt auf ihrem letzten guten Stand."
         rote="${rote:+$rote,}$reise" ;;
      *) echo "FEHLER: Deploy von $reise fehlgeschlagen (Exit $rc), nächster Lauf versucht es wieder."; return 1 ;;
    esac
  done
  # Freischalten nur gelungener Reisen: neue bekommen ihren Link, alle werden geprüft (Ausgabe ohne Links, die sind geheim)
  for reise in $gut; do
    aus="$("$freischalten" "$reise" 2>&1)" || echo "Warnung: $reise nicht freigeschaltet (Grund in der Zeile darunter)."
    printf '%s\n' "$aus" | grep -E '^(FEHLER|Freigeschaltet|Baustein erneuert)' || true
  done
  if [ -n "$rote" ]; then
    # Teil-Erfolg ist kein fachlicher Erfolg: Stand nicht merken, kein Stempel, kein Heartbeat
    rot_schreiben "$neu" reise "$rote"
    zustellen
    echo "Rot: $(git log -1 --format='%h') teilweise online, nicht gebaut: $rote."
    alarm_pruefen
    return 1
  fi
  rm -f "$rot_datei"
  mkdir -p "$(dirname "$stand")"
  echo "$neu" > "$stand"
  zustellen
  echo "Fertig: $(git log -1 --format='%h') ist online."
  erfolg_melden
}

wurzel=""; ausstehend=""; rot_datei=""; pruefen=""; pruef_tmp=""
rot_commit=""; rot_art=""; rot_reisen=""; rot_seit=""; rot_gemeldet=""
main "$@"
exit
