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
# Anstoß vom Server (#250): Hat main der Software (git ls-remote, URL aus .gitmodules) einen anderen Stand als das
# eingebundene Submodul, startet der Lauf denselben Workflow, einmal je Stand; Stand und Zeit stehen danach in
# <FR_DIENST>/nachziehen-angestossen („SHA Epoche“, nur nach Erfolg von gh). Für denselben Stand startet er erst nach
# FR_NACHZIEHEN_WIEDERHOLEN_STUNDEN wieder. Fehler dabei sind Warnungen, das Veröffentlichen läuft weiter.
# Reise-Stand (Epic #223, engine/stand.py): Je Reise schreibt der Lauf ihren Zustand nach <FR_DIENST>/reise-stand/<reise>.lauf.json
# (baut, veroeffentlicht mit Dauer seit dem Sichern, fehlgeschlagen mit Grund); api/stand und publish_status lesen ihn.
# Zeitziel 2 Minuten vom Sichern bis zur Veröffentlichung (#230): Ein reiner Inhaltsstand (seit dem zuletzt veröffentlichten
# Stand nur Änderungen unter reisen/) baut nur die geänderten Reisen und überspringt die Prüfungen der Software, die für
# genau diese Software schon grün waren. Ein Software-Wechsel (alles außerhalb von reisen/, auch das Submodul) prüft weiter
# vollständig und baut alle Reisen; nur dann laufen auch die Tests des Reisen-Repos (nach dem Bauen, sie sperren nie).
# Startet ein Lauf, während ein anderer die Sperre hält (Schreibweg während eines Timer-Laufs), merkt er das in
# <FR_DIENST>/veroeffentlichen-nochmal; der laufende startet danach gleich noch einmal, statt bis zum Timer zu warten.
# Für Tests überschreibbar: VF_PRUEFEN, VF_STAND, VF_DEPLOY, VF_FREISCHALTEN, VF_AUSSTEHEND, VF_SPERRE, VF_STEMPEL, VF_HEARTBEAT,
# VF_ROT (Rot-Datei), VF_JETZT (Uhr, Sekunden seit 1970), VF_ROTMELDEN (statt engine/waechter.py rot-melden),
# VF_NACHZIEHEN (Befehl statt gh workflow run), VF_LSREMOTE (Befehl statt git ls-remote).
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

einstellungen_summe() {  # <datei>: Prüfsumme, leer ohne lesbare Datei wie in fr_einlesen (Erscheinen und Verschwinden
  # zählen als Änderung, #242)
  [ ! -r "$1" ] || sha256sum < "$1" | cut -d' ' -f1
}

iso() { [[ "${1:-}" =~ ^[0-9]+$ ]] && date -u -d "@$1" +%Y-%m-%dT%H:%M:%SZ || true; }

reise_stand_schreiben() {  # <reise> <zustand> [grund]: Zustand des Reise-Stands für api/stand und publish_status
  # (engine/stand.py). nummer wie dort: Commits, die reisen/<reise>/ ändern; im flachen Klon keine. Dauer bei „veroeffentlicht“:
  # Sekunden seit dem Sichern (Zeit des Schreibwegs, sonst des Commits); steht auch im Protokoll (Messung des Zeitziels).
  local r="$1" z="$2" g="${3:-}" n c t dauer=null datei gz gn
  [ "$(git rev-parse --is-shallow-repository 2>/dev/null)" = false ] || return 0
  n="$(git rev-list --count HEAD -- "reisen/$r" 2>/dev/null)" || return 0
  [[ "$n" =~ ^[0-9]+$ ]] && [ "$n" -gt 0 ] || return 0
  c="$(git log -1 --format=%ct -- "reisen/$r" 2>/dev/null || true)"
  datei="$FR_DIENST/reise-stand/$r.gesichert.json"
  gn="$(sed -n 's/.*"nummer": *\([0-9]*\).*/\1/p' "$datei" 2>/dev/null || true)"
  gz="$(sed -n 's/.*"zeit": *"\([^"]*\)".*/\1/p' "$datei" 2>/dev/null || true)"
  if [ "$gn" = "$n" ] && [ -n "$gz" ] && gz="$(date -u -d "$gz" +%s 2>/dev/null)"; then c="$gz"; fi
  t="$(jetzt)"
  if [ "$z" = veroeffentlicht ] && [[ "$c" =~ ^[0-9]+$ ]]; then
    dauer=$(( t - c )); [ "$dauer" -ge 0 ] || dauer=0
    if [ "$dauer" -gt 120 ]; then   # Zeitziel 2 Minuten (Product Owner, E3, 2.11.2026; engine/stand.py ZIEL_SEKUNDEN)
      echo "Warning: $r state $n published $dauer s after saving, longer than the target of 120 s."
    else
      echo "Published $r state $n, $dauer s after saving."
    fi
  fi
  g="$(printf '%s' "$g" | tr '\000-\037' ' ' | sed "s/[\\\\\"]/'/g" | cut -c1-300)"
  datei="$FR_DIENST/reise-stand/$r.lauf.json"
  mkdir -p "$FR_DIENST/reise-stand"
  printf '{"zustand": "%s", "nummer": %s, "gesichert": "%s", "seit": "%s", "dauer": %s, "grund": "%s"}\n' \
    "$z" "$n" "$(iso "$c")" "$(iso "$t")" "$dauer" "$g" > "$datei.neu" && mv "$datei.neu" "$datei"
}

baugrund() {  # Grund eines gescheiterten Baus aus der Ausgabe von deploy.sh: die Meldungen von bauen.py („ - …“), sonst die
  # letzte Zeile mit ERROR
  local g
  g="$({ grep -E '^ +- ' "$deploy_log" 2>/dev/null || true; } | sed -E 's/^ +- //' | head -3 | paste -sd '|' - | sed 's/|/; /g')" || true
  [ -n "$g" ] || g="$({ grep -E 'ERROR' "$deploy_log" 2>/dev/null || true; } | tail -1)" || true
  printf '%s' "$g"
}

reisen_des_laufs() {  # <alt> <neu>: Reisen, die dieser Lauf baut, eine je Zeile. Ohne bekannten alten Stand, mit --immer oder
  # bei einem Software-Wechsel alle; sonst die, deren Ordner sich seit dem zuletzt veröffentlichten Stand geändert hat, und
  # die zuletzt roten (sie bleiben rot gemeldet, bis ihr Bau gelingt).
  local r
  if [ -n "$software" ]; then
    for r in reisen/*/reise.json; do [ -e "$r" ] && basename "$(dirname "$r")"; done
    return 0
  fi
  { git diff --name-only "$1" "$2" -- reisen | cut -d/ -f2
    [ "$rot_art" != reise ] || printf '%s\n' ${rot_reisen//,/ }
  } | sort -u | while read -r r; do
    if [ -n "$r" ] && [ -e "reisen/$r/reise.json" ]; then echo "$r"; fi
  done
  return 0
}

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

software_anstossen() {  # neuer Stand auf main der Software: Workflow „Software nachziehen“ starten, einmal je Stand (#250)
  # Gelesen wird der Stand von origin/main (gerade geholt), nicht HEAD: So zählt auch ein Submodul, das erst mit diesem
  # Lauf in den Bauordner kommt. Ohne Submodul frieda/ geschieht nichts.
  local url eingebunden fern merk="$FR_DIENST/nachziehen-angestossen" m_stand="" m_zeit="" t
  url="$(git config --blob origin/main:.gitmodules submodule.frieda.url 2>/dev/null)" || return 0
  eingebunden="$(git rev-parse -q --verify origin/main:frieda 2>/dev/null)" || return 0
  [ -n "$url" ] && [ -n "$eingebunden" ] || return 0
  if [ -n "${VF_LSREMOTE:-}" ]; then fern="$("$VF_LSREMOTE" "$url" refs/heads/main 2>/dev/null)" || fern=""
  else fern="$(timeout 30 git ls-remote "$url" refs/heads/main 2>/dev/null)" || fern=""; fi
  fern="$(printf '%s\n' "$fern" | awk '$2 == "refs/heads/main" {print $1; exit}')"
  if [ -z "$fern" ]; then
    echo "Warning: state of main of the software unknown (git ls-remote failed), no request to update the software."
    return 0
  fi
  [ "$fern" != "$eingebunden" ] || return 0
  [ -f "$merk" ] && { read -r m_stand m_zeit < "$merk" || true; }
  t="$(jetzt)"
  local stunden="$FR_NACHZIEHEN_WIEDERHOLEN_STUNDEN"
  [[ "$stunden" =~ ^[0-9]+$ ]] || stunden=6
  if [ "$m_stand" = "$fern" ] && [[ "$m_zeit" =~ ^[0-9]+$ ]] && [ $(( 10#$t - 10#$m_zeit )) -lt $(( 10#$stunden * 3600 )) ]; then
    return 0
  fi
  local ok=true
  if [ -n "${VF_NACHZIEHEN:-}" ]; then "$VF_NACHZIEHEN" > /dev/null 2>&1 || ok=false
  else timeout 60 gh workflow run "$FR_NACHZIEHEN_WORKFLOW" --ref main > /dev/null 2>&1 || ok=false; fi
  if [ "$ok" != true ]; then
    echo "Warning: new software state on main, workflow $FR_NACHZIEHEN_WORKFLOW could not be started (gh signed in, permission actions: write?). The next run tries again."
    return 0
  fi
  echo "New software state on main (${fern:0:7}, included ${eingebunden:0:7}): workflow $FR_NACHZIEHEN_WORKFLOW started."
  mkdir -p "$FR_DIENST"
  echo "$fern $t" > "$merk.tmp" && mv "$merk.tmp" "$merk"
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
  local stand deploy immer="" alt neu reise freischalten aus rc gut="" rote="" warnung grund laufreisen
  local einstellungen="${FR_EINSTELLUNGEN:-$FR_WURZEL/betrieb/einstellungen.env}" einstellungen_vorher start_ordner="$PWD"
  case "$einstellungen" in /*) ;; *) einstellungen="$PWD/$einstellungen" ;; esac   # wie gemeinsam.sh sie las, vor dem cd
  wurzel="$FR_WURZEL"
  stand="${VF_STAND:-$FR_DIENST/veroeffentlicht}"
  deploy="${VF_DEPLOY:-$FR_BETRIEB/deploy.sh}"
  pruefen="${VF_PRUEFEN:-}"
  freischalten="${VF_FREISCHALTEN:-$FR_BETRIEB/freischalten.sh}"
  ausstehend="${VF_AUSSTEHEND:-$FR_KONNEKTOR/neue-reisen-ausstehend.jsonl}"
  rot_datei="${VF_ROT:-$FR_DIENST/veroeffentlichen-rot}"
  warnung="$FR_DIENST/veroeffentlichen-warnung"
  [ "${1:-}" = "--immer" ] && immer=1

  # Sperre in FR_DIENST, nicht in FR_SPERREN (Vorgabe /tmp): Der Schreibweg startet diesen Lauf aus einem Dienst mit
  # PrivateTmp, sein /tmp ist nicht das des Timers, und die Sperre griff nicht (zwei Läufe gleichzeitig, #211)
  mkdir -p "$FR_DIENST"
  exec 9>"${VF_SPERRE:-$FR_DIENST/veroeffentlichen.lock}"
  if ! flock -n 9; then
    # Der laufende Lauf startet danach noch einmal (nachlauf), damit ein neuer Stand nicht bis zum Timer wartet (#230)
    touch "$FR_DIENST/veroeffentlichen-nochmal"
    echo "Already running, skipped; the running one publishes again afterwards."
    return 0
  fi
  nochmal="$FR_DIENST/veroeffentlichen-nochmal"
  rm -f "$nochmal"

  cd "$wurzel"
  anstoss_weitergeben
  if [ "$(git rev-parse --abbrev-ref HEAD)" != main ]; then
    echo "Build folder is not on main ($(git rev-parse --abbrev-ref HEAD)), skipped."; return 0
  fi
  if ! git diff --quiet HEAD || [ -n "$(git ls-files --others --exclude-standard)" ]; then
    echo "Uncommitted changes in the build folder, skipped."; return 0
  fi

  mkdir -p "$FR_DIENST"   # Zustand des Veröffentlichens (Stand, Rot-Datei, Merker der Warnung, Stempel)
  einstellungen_vorher="$(einstellungen_summe "$einstellungen")"
  git fetch -q origin main
  software_anstossen || true
  neu="$(git rev-parse origin/main)"
  alt="$(cat "$stand" 2>/dev/null || true)"
  if [ -z "$immer" ] && [ "$neu" = "$alt" ]; then zustellen; rm -f "$rot_datei"; erfolg_melden; return 0; fi

  git merge -q --ff-only origin/main || { echo "ERROR: main cannot be fast-forwarded (local commits?)."; return 1; }
  # Software (Submodul) auf den Stand bringen, den main festhält
  git submodule update --init --quiet || { echo "ERROR: the software submodule cannot be fetched."; return 1; }
  # Geänderte Einstellungen wirken im selben Lauf (#242): gemeinsam.sh hat die Datei schon vor dem Vorspulen gelesen.
  # Neustart mit denselben Argumenten und ohne die alten Werte (nur die vom Aufruf bleiben), höchstens einmal je Lauf.
  if [ "${_neugestartet:-}" != "$$" ] && [ "$(einstellungen_summe "$einstellungen")" != "$einstellungen_vorher" ]; then
    echo "Settings changed by the update, restarting."
    fr_aufraeumen
    _neugestartet="$$"; export _neugestartet   # gilt nur für diesen Prozess (exec behält die PID)
    cd "$start_ordner"   # $0 und eine relative FR_EINSTELLUNGEN gelten vom Ordner des Aufrufs aus
    exec "$0" "$@"
  fi

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

  # Software-Wechsel oder reiner Inhaltsstand (#230): Software ist alles außerhalb von reisen/ (Submodul, Werkzeuge, Tests)
  software=1
  if [ -z "$immer" ] && [ -n "$alt" ] && git merge-base --is-ancestor "$alt" "$neu" 2>/dev/null \
     && git diff --quiet "$alt" "$neu" -- . ':(exclude)reisen'; then
    software=""
  fi
  laufreisen="$(reisen_des_laufs "$alt" "$neu")"
  for reise in $laufreisen; do reise_stand_schreiben "$reise" baut; done

  echo "Publishing $(git log -1 --format='%h %s')${software:- (content only: $(echo $laufreisen))}"
  pruef_tmp="$(mktemp -d)"; pruef_log="$pruef_tmp.log"
  if [ -n "$software" ]; then
    # Eigener Ordner für die Testdateien: Mit der Vorgabe (/tmp/pytest-of-<user>) räumt jeder weitere pytest-Lauf auf dem
    # Rechner die Ordner älterer Läufe weg, auch die eines noch laufenden (roter Lauf 29.10.2026 bei gleichzeitigen Tests).
    if ! pruefen_lauf engine/tests; then
      rm -rf "$pruef_tmp"
      echo "ERROR: checks red (engine/tests, software), nothing published."
      rot_schreiben "$neu" software "" "$(rote_tests)"
      rm -f "$pruef_log"
      alarm_pruefen
      return 1
    fi
  else
    echo "Software unchanged since ${alt:0:7} (checked then), checks skipped."
  fi
  FR_GEPRUEFT="$(git rev-parse HEAD)"; export FR_GEPRUEFT
  FR_WEGE_SPAETER=1; export FR_WEGE_SPAETER   # Wege zum Konnektor einmal nach dem Freischalten (wege_pruefen)
  deploy_log="$pruef_tmp.deploy"
  for reise in $laufreisen; do
    rc=0; "$deploy" "$reise" 2>&1 | tee "$deploy_log" || rc=${PIPESTATUS[0]}
    unset FR_BIBLIOTHEKEN_NEU   # Dienste mit FR_PYTHON nur beim ersten Deploy neu starten
    case "$rc" in
      0) gut="$gut $reise"; reise_stand_schreiben "$reise" veroeffentlicht ;;
      2) echo "ERROR: build of $reise failed, the trip stays at its last good state."
         reise_stand_schreiben "$reise" fehlgeschlagen "$(baugrund)"
         rote="${rote:+$rote,}$reise" ;;
      *) echo "ERROR: deploy of $reise failed (exit $rc), the next run tries again."; rm -rf "$pruef_tmp" "$deploy_log"; return 1 ;;
    esac
  done
  rm -f "$deploy_log"
  # Tests des Reisen-Repos prüfen Inhalt (Schnappschüsse der Reisen): rot sperrt nie, einmal je Commit eine Nachricht. Sie
  # laufen nach dem Bauen und nur bei einem Software-Wechsel, damit sie keinen neuen Stand aufhalten (#230).
  if [ -n "$software" ] && [ -d tests ] && ! pruefen_lauf tests; then
    echo "Warning: tests of the trips repo red (they do not block)."
    if [ "$(cat "$warnung" 2>/dev/null || true)" != "$neu" ]; then
      fr_melden normal "Tests of the trips repo red" "State ${neu:0:7}: the tests in tests/ of the trips repo are red. They do not block publishing (docs/betrieb.md, convention for tests/). Log: journalctl -u $FR_INSTANZ-veroeffentlichen -n 100"
      mkdir -p "$(dirname "$warnung")"
      echo "$neu" > "$warnung"
    fi
  fi
  rm -rf "$pruef_tmp" "$pruef_log"
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

# Nachlauf (#230): Kam während dieses Laufs ein neuer Stand (ein zweiter Lauf fand die Sperre belegt), gleich noch einmal
# laufen. exec ersetzt den Prozess: Die Sperre (fd 9) wird beim erneuten Öffnen frei und neu genommen.
nachlauf() {
  local rc=$?
  if [ -n "$nochmal" ] && [ -e "$nochmal" ]; then
    rm -f "$nochmal"
    echo "A new state arrived during the run, publishing again."
    unset _neugestartet   # der neue Lauf darf wieder einmal neu starten (#242)
    exec "$0"
  fi
  exit "$rc"
}

wurzel=""; ausstehend=""; rot_datei=""; pruefen=""; pruef_tmp=""; pruef_log=""; deploy_log=""; nochmal=""; software=1
rot_commit=""; rot_art=""; rot_reisen=""; rot_seit=""; rot_gemeldet=""; rot_umgebung=""; rot_geprueft=""; rot_tests=""
trap nachlauf EXIT
main "$@"
exit
