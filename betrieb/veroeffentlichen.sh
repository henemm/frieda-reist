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
# Anstoß von der Seite (Organisator:innen, „Veröffentlichen anstoßen“ im Fuß; engine/rueckmeldungen.py api/aktualisieren):
# Liegt <FR_ABLAGE>/_anstoss.json, startet der Lauf den Workflow „Software nachziehen“ des Reisen-Repos (gh workflow run
# FR_NACHZIEHEN_WORKFLOW) und schreibt das Ergebnis nach _anstoss-ergebnis.json; die Seite zeigt es. Der Workflow zieht das
# Submodul nach, und ein späterer Lauf veröffentlicht den neuen Stand wie sonst auch.
# Für Tests überschreibbar: VF_PRUEFEN, VF_STAND, VF_DEPLOY, VF_FREISCHALTEN, VF_AUSSTEHEND, VF_SPERRE, VF_STEMPEL, VF_HEARTBEAT,
# VF_ROT (Rot-Datei), VF_JETZT (Uhr, Sekunden seit 1970), VF_ROTMELDEN (statt engine/waechter.py rot-melden),
# VF_NACHZIEHEN (Befehl statt gh workflow run).
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/gemeinsam.sh"
nur_bauordner

erfolg_melden() {
  mkdir -p "$FR_DIENST"
  touch "${VF_STEMPEL:-$FR_DIENST/veroeffentlichen-erfolg}"
  local hb="${VF_HEARTBEAT:-${FR_HEARTBEAT_VEROEFFENTLICHEN:-}}"
  [ -n "$hb" ] || return 0
  curl -fsS -m 10 --retry 3 -o /dev/null "$hb" || echo "Warning: heartbeat not reached."
}

zustellen() {  # ausstehende Links neuer Reisen (nur wenn welche anstehen)
  [ -s "$ausstehend" ] || return 0
  "$FR_PYTHON" "$FR_BETRIEB/zustellen.py" "$wurzel" "$ausstehend" \
    || echo "Warning: not all links of new trips delivered, the next run tries again."
}

jetzt() { echo "${VF_JETZT:-$(date +%s)}"; }

rot_lesen() {  # Rot-Datei in rot_commit, rot_art, rot_reisen, rot_seit, rot_gemeldet, rot_umgebung, rot_geprueft, rot_tests
  local zeile
  rot_commit=""; rot_art=""; rot_reisen=""; rot_seit=""; rot_gemeldet=""; rot_umgebung=""; rot_geprueft=""; rot_tests=""
  [ -r "$rot_datei" ] || return 0
  while IFS= read -r zeile || [ -n "$zeile" ]; do
    case "$zeile" in
      commit=*) rot_commit="${zeile#*=}" ;;
      art=*) rot_art="${zeile#*=}" ;;
      reisen=*) rot_reisen="${zeile#*=}" ;;
      seit=*) rot_seit="${zeile#*=}" ;;
      gemeldet=*) rot_gemeldet="${zeile#*=}" ;;
      umgebung=*) rot_umgebung="${zeile#*=}" ;;
      geprueft=*) rot_geprueft="${zeile#*=}" ;;
      tests=*) rot_tests="${zeile#*=}" ;;
    esac
  done < "$rot_datei"
}

rot_ablegen() {  # schreibt rot_* in die Rot-Datei (erst daneben, dann umbenennen)
  mkdir -p "$(dirname "$rot_datei")"
  printf 'commit=%s\nart=%s\nreisen=%s\nseit=%s\ngemeldet=%s\numgebung=%s\ngeprueft=%s\ntests=%s\n' \
    "$rot_commit" "$rot_art" "$rot_reisen" "$rot_seit" "$rot_gemeldet" "$rot_umgebung" "$rot_geprueft" "$rot_tests" > "$rot_datei.neu"
  mv "$rot_datei.neu" "$rot_datei"
}

rot_schreiben() {  # <commit> <art> <reisen> [tests]: roter Stand; seit und gemeldet bleiben innerhalb einer Rot-Phase,
  # auch wenn derselbe Commit erneut geprüft wurde. Gemerkt werden dazu Umgebung und Zeit der Prüfung (#203).
  rot_lesen
  if [ -z "$rot_seit" ]; then
    rot_seit="$(date -u -d "@$(jetzt)" +%Y-%m-%dT%H:%M:%SZ)"; rot_gemeldet=0
  fi
  rot_commit="$1"; rot_art="$2"; rot_reisen="$3"; rot_tests="${4:-}"
  rot_umgebung="$(umgebung_stand)"; rot_geprueft="$(jetzt)"
  rot_ablegen
}

umgebung_stand() {  # Fingerabdruck der Prüfumgebung: installierte Bibliotheken, Python, Node, Playwright (#203)
  if [ -n "${VF_UMGEBUNG+x}" ]; then printf '%s' "$VF_UMGEBUNG" | sha256sum | cut -c1-16; return; fi
  # Jeder Teil darf fehlen (kein Python, kein Node, kein Playwright): dann zählt er leer, der Lauf bricht nicht ab
  {
    "$FR_PYTHON" --version 2>/dev/null || true
    "$FR_PYTHON" -m pip freeze --disable-pip-version-check 2>/dev/null || true
    node --version 2>/dev/null || true
    if [ -n "${PLAYWRIGHT_MODUL:-}" ]; then grep -m1 '"version"' "$(dirname "$PLAYWRIGHT_MODUL")/package.json" 2>/dev/null || true; fi
  } | sha256sum | cut -c1-16
}

rot_erneut_pruefen() {  # Bekannter roter Stand: neu prüfen? Ja, wenn sich die Umgebung geändert hat (alle Arten) oder rote
  # Software seit mehr als FR_ROT_NEU_PRUEFEN_MINUTEN (Vorgabe 60) nicht geprüft wurde. Sonst blieb ein Stand rot,
  # obwohl die Ursache in der Umgebung längst behoben war (1./2.11.2026: 7 Stunden). Ausgabe: der Grund.
  local frist="${FR_ROT_NEU_PRUEFEN_MINUTEN:-60}"
  [[ "$frist" =~ ^[0-9]+$ ]] || frist=60
  if [ "$(umgebung_stand)" != "$rot_umgebung" ]; then echo "environment changed"; return 0; fi
  if [ "$rot_art" = software ] && [[ "$rot_geprueft" =~ ^[0-9]+$ ]] && [ $(( $(jetzt) - rot_geprueft )) -gt $(( frist * 60 )) ]; then
    echo "last check more than $frist minutes ago"; return 0
  fi
  return 1
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
  seit_s="$(date -u -d "$rot_seit" +%s 2>/dev/null)" || { echo "Warning: red file with invalid since ($rot_seit)."; return 0; }
  minuten=$(( ($(jetzt) - seit_s) / 60 ))
  [ "$minuten" -ge "$schwelle" ] || return 0
  if [ "$rot_art" = reise ] && [ -n "$rot_reisen" ]; then
    # je Reise und Rot-Phase eine Meldung (schluessel mit seit), darum bei jedem Lauf gefahrlos
    if [ -n "${VF_ROTMELDEN:-}" ]; then
      "$VF_ROTMELDEN" --reisen "$rot_reisen" --seit "$rot_seit" || echo "Warning: message to the organisers not created."
    else
      "$FR_PYTHON" "$wurzel/engine/waechter.py" rot-melden --reisen "$rot_reisen" --seit "$rot_seit" \
        || echo "Warning: message to the organisers not created."
    fi
  fi
  [ "$rot_gemeldet" = 1 ] && return 0
  if alarm_senden "Publishing red for $minuten minutes" \
    "Kind: $rot_art${rot_reisen:+, trips: $rot_reisen}, state ${rot_commit:0:7}, red since $rot_seit (UTC).${rot_tests:+ Red: $rot_tests.} Successful trips are online, red ones stay at their last good state. Log: journalctl -u $FR_INSTANZ-veroeffentlichen -n 100"; then
    rot_gemeldet=1; rot_ablegen
  else
    echo "Warning: alarm to operations not sent, the next run tries again."
  fi
}

pruefen_lauf() {  # <ordner>: pytest über engine/tests oder tests/ des Reisen-Repos; Ausgabe auch nach pruef_log
  local rc=0
  if [ -n "$pruefen" ]; then "$pruefen" "$1" 2>&1 | tee "$pruef_log" || rc=${PIPESTATUS[0]}
  else "$FR_PYTHON" -m pytest "$1" -q --basetemp "$pruef_tmp" 2>&1 | tee "$pruef_log" || rc=${PIPESTATUS[0]}; fi
  return "$rc"
}

rote_tests() {  # die ersten roten Tests aus pruef_log und die erste Fehlerzeile, in einer Zeile für Rot-Datei und Meldung
  local namen erste
  namen="$({ grep -E '^(FAILED|ERROR) ' "$pruef_log" 2>/dev/null || true; } | sed -E 's/^(FAILED|ERROR) //; s/ - .*//' | head -5 | paste -sd, - | sed 's/,/, /g')" || true
  erste="$({ grep -m1 -E '^E +[^ ]' "$pruef_log" 2>/dev/null || true; } | sed -E 's/^E +//' | cut -c1-200)" || true
  printf '%s%s' "$namen" "${erste:+ (first error: $erste)}" | tr -d '\n'
}

anstoss_weitergeben() {  # Anstoß der Seite: Workflow „Software nachziehen“ starten, Ergebnis für die Seite ablegen
  local datei="$FR_ABLAGE/_anstoss.json" ergebnis="$FR_ABLAGE/_anstoss-ergebnis.json" ok=true
  [ -e "$datei" ] || return 0
  if [ -n "${VF_NACHZIEHEN:-}" ]; then "$VF_NACHZIEHEN" > /dev/null 2>&1 || ok=false
  else timeout 60 gh workflow run "$FR_NACHZIEHEN_WORKFLOW" --ref main > /dev/null 2>&1 || ok=false; fi
  if [ "$ok" = true ]; then
    echo "Request from the page: workflow $FR_NACHZIEHEN_WORKFLOW started."
  else
    echo "Warning: request from the page, workflow $FR_NACHZIEHEN_WORKFLOW could not be started (gh signed in, permission actions: write?)."
    fr_melden normal "Publish request failed" "An organiser requested publishing on the page. gh workflow run $FR_NACHZIEHEN_WORKFLOW failed (gh signed in? permission to run workflows?). Log: journalctl -u $FR_INSTANZ-veroeffentlichen -n 50"
  fi
  printf '{"zeit": "%s", "ok": %s}\n' "$(date -u +%Y-%m-%dT%H:%M:%S+00:00)" "$ok" > "$ergebnis.tmp" && mv "$ergebnis.tmp" "$ergebnis"
  rm -f "$datei"
}

abhaengigkeiten() {  # Umgebung der Prüfungen wie in CI (#202): Bibliotheken und Playwright in festen Versionen aus dem Repo.
  # Sonst fehlte nach einem Software-Stand mit neuer Bibliothek nur dem Server etwas, und die Prüfungen blieben rot,
  # bis jemand von Hand installiert (rot 1.11.2026 wegen pyspellchecker). Installiert wird nur, wenn sich eine Liste
  # geändert hat (Prüfsummen in FR_DIENST).
  # Bibliotheken: engine/requirements.txt (Versionen und Hashes, erzeugt aus requirements.in) in FR_PYTHON. Danach
  # starten die Dienste mit FR_PYTHON einmal neu (FR_BIBLIOTHEKEN_NEU an den ersten Deploy des Laufs).
  local liste=engine/requirements.txt merk="$FR_DIENST/requirements.sha256" summe
  if [ -f "$liste" ]; then
    summe="$(sha256sum "$liste" | cut -d' ' -f1)"
    if [ "$summe" != "$(cat "$merk" 2>/dev/null || true)" ]; then
      echo "Installing libraries (engine/requirements.txt changed)."
      if [ -n "${VF_PIP:-}" ]; then "$VF_PIP" -r "$liste"; else "$FR_PYTHON" -m pip install -q --disable-pip-version-check -r "$liste"; fi \
        || return 1
      mkdir -p "$FR_DIENST"
      echo "$summe" > "$merk"
      FR_BIBLIOTHEKEN_NEU=1; export FR_BIBLIOTHEKEN_NEU
    fi
  fi
  # Playwright: eigene Kopie in <FR_DIENST>/playwright nach engine/tests/playwright/package-lock.json, nie ein
  # Ordner, den andere mitbenutzen. Browser ohne --with-deps (kein sudo); Systembibliotheken richtet einrichten.sh ein.
  # Ohne npm (Instanz ohne Browsertests) bleibt alles, wie es ist.
  local pw_quelle=engine/tests/playwright pw_ziel="$FR_DIENST/playwright" npm="${VF_NPM:-npm}"
  [ -f "$pw_quelle/package-lock.json" ] || return 0
  command -v "$npm" > /dev/null 2>&1 || { echo "Note: npm missing, browser tests use what playwright_pfad.py finds."; return 0; }
  summe="$(cat "$pw_quelle/package.json" "$pw_quelle/package-lock.json" | sha256sum | cut -d' ' -f1)"
  if [ "$summe" != "$(cat "$pw_ziel/.stand" 2>/dev/null || true)" ] || [ ! -e "$pw_ziel/node_modules/playwright/index.mjs" ]; then
    echo "Installing Playwright (engine/tests/playwright changed)."
    mkdir -p "$pw_ziel"
    cp "$pw_quelle/package.json" "$pw_quelle/package-lock.json" "$pw_ziel/"
    ( cd "$pw_ziel" && "$npm" ci --silent --no-audit --no-fund && "$npm" exec --no -- playwright install chromium webkit ) || return 1
    echo "$summe" > "$pw_ziel/.stand"
  fi
  PLAYWRIGHT_MODUL="$pw_ziel/node_modules/playwright/index.mjs"; export PLAYWRIGHT_MODUL
}

# Alles steckt in main(), damit bash das Skript ganz einliest, bevor git es mit dem Submodul eventuell ersetzt.
main() {
  local stand deploy immer="" alt neu reise freischalten aus rc gut="" rote="" warnung grund
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
  flock -n 9 || { echo "Already running, skipped."; return 0; }

  cd "$wurzel"
  anstoss_weitergeben
  if [ "$(git rev-parse --abbrev-ref HEAD)" != main ]; then
    echo "Build folder is not on main ($(git rev-parse --abbrev-ref HEAD)), skipped."; return 0
  fi
  if ! git diff --quiet HEAD || [ -n "$(git ls-files --others --exclude-standard)" ]; then
    echo "Uncommitted changes in the build folder, skipped."; return 0
  fi

  mkdir -p "$FR_DIENST"   # Zustand des Veröffentlichens (Stand, Rot-Datei, Merker der Warnung, Stempel)
  git fetch -q origin main
  neu="$(git rev-parse origin/main)"
  alt="$(cat "$stand" 2>/dev/null || true)"
  if [ -z "$immer" ] && [ "$neu" = "$alt" ]; then zustellen; rm -f "$rot_datei"; erfolg_melden; return 0; fi

  git merge -q --ff-only origin/main || { echo "ERROR: main cannot be fast-forwarded (local commits?)."; return 1; }
  # Software (Submodul) auf den Stand bringen, den main festhält
  git submodule update --init --quiet || { echo "ERROR: the software submodule cannot be fetched."; return 1; }

  # Umgebung zuerst (feste Versionen, #202), damit ein bekannter roter Stand sie schon im Fingerabdruck sieht (#203)
  abhaengigkeiten || { echo "ERROR: libraries or Playwright cannot be installed, the next run tries again."; return 1; }
  # Bekannter roter Stand: nicht noch einmal prüfen und bauen (kostet Minuten), kein Stempel, kein Heartbeat; außer die
  # Umgebung hat sich geändert oder rote Software wurde lange nicht geprüft (rot_erneut_pruefen)
  rot_lesen
  if [ -z "$immer" ] && [ -n "$rot_commit" ] && [ "$rot_commit" = "$neu" ]; then
    if grund="$(rot_erneut_pruefen)"; then
      echo "Known red state ${neu:0:7}, checking again ($grund)."
    else
      echo "Known red state ${neu:0:7}, skipped (kind: $rot_art${rot_reisen:+, trips: $rot_reisen}). It is checked again with a new commit, a changed environment, after ${FR_ROT_NEU_PRUEFEN_MINUTEN:-60} minutes (software) or with --immer."
      zustellen
      alarm_pruefen
      return 0
    fi
  fi

  echo "Publishing $(git log -1 --format='%h %s')"
  # Eigener Ordner für die Testdateien: Mit der Vorgabe (/tmp/pytest-of-<user>) räumt jeder weitere pytest-Lauf auf dem
  # Rechner die Ordner älterer Läufe weg, auch die eines noch laufenden (roter Lauf 29.10.2026 bei gleichzeitigen Tests).
  pruef_tmp="$(mktemp -d)"; pruef_log="$pruef_tmp.log"
  if ! pruefen_lauf engine/tests; then
    rm -rf "$pruef_tmp"
    echo "ERROR: checks red (engine/tests, software), nothing published."
    rot_schreiben "$neu" software "" "$(rote_tests)"
    rm -f "$pruef_log"
    alarm_pruefen
    return 1
  fi
  # Tests des Reisen-Repos prüfen Inhalt (Schnappschüsse der Reisen): rot sperrt nie, einmal je Commit eine Nachricht
  if [ -d tests ] && ! pruefen_lauf tests; then
    echo "Warning: tests of the trips repo red (they do not block)."
    if [ "$(cat "$warnung" 2>/dev/null || true)" != "$neu" ]; then
      fr_melden normal "Tests of the trips repo red" "State ${neu:0:7}: the tests in tests/ of the trips repo are red. They do not block publishing (docs/betrieb.md, convention for tests/). Log: journalctl -u $FR_INSTANZ-veroeffentlichen -n 100"
      mkdir -p "$(dirname "$warnung")"
      echo "$neu" > "$warnung"
    fi
  fi
  rm -rf "$pruef_tmp" "$pruef_log"
  FR_GEPRUEFT="$(git rev-parse HEAD)"; export FR_GEPRUEFT
  FR_WEGE_SPAETER=1; export FR_WEGE_SPAETER   # Wege zum Konnektor einmal nach dem Freischalten (wege_pruefen)
  for reise in reisen/*/reise.json; do
    [ -e "$reise" ] || continue
    reise="$(basename "$(dirname "$reise")")"
    rc=0; "$deploy" "$reise" || rc=$?
    unset FR_BIBLIOTHEKEN_NEU   # Dienste mit FR_PYTHON nur beim ersten Deploy neu starten
    case "$rc" in
      0) gut="$gut $reise" ;;
      2) echo "ERROR: build of $reise failed, the trip stays at its last good state."
         rote="${rote:+$rote,}$reise" ;;
      *) echo "ERROR: deploy of $reise failed (exit $rc), the next run tries again."; return 1 ;;
    esac
  done
  # Freischalten nur gelungener Reisen: neue bekommen ihren Link, alle werden geprüft (Ausgabe ohne Links, die sind geheim)
  for reise in $gut; do
    aus="$("$freischalten" "$reise" 2>&1)" || echo "Warning: $reise not released (reason in the line below)."
    printf '%s\n' "$aus" | grep -E '^(ERROR|Released|Block renewed)' || true
  done
  [ -z "$gut" ] || wege_pruefen
  if [ -n "$rote" ]; then
    # Teil-Erfolg ist kein fachlicher Erfolg: Stand nicht merken, kein Stempel, kein Heartbeat
    rot_schreiben "$neu" reise "$rote"
    zustellen
    echo "Red: $(git log -1 --format='%h') partly online, not built: $rote."
    alarm_pruefen
    return 1
  fi
  rm -f "$rot_datei"
  mkdir -p "$(dirname "$stand")"
  echo "$neu" > "$stand"
  zustellen
  echo "Done: $(git log -1 --format='%h') is online."
  erfolg_melden
}

wurzel=""; ausstehend=""; rot_datei=""; pruefen=""; pruef_tmp=""; pruef_log=""
rot_commit=""; rot_art=""; rot_reisen=""; rot_seit=""; rot_gemeldet=""; rot_umgebung=""; rot_geprueft=""; rot_tests=""
main "$@"
exit
