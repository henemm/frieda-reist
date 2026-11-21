#!/usr/bin/env bash
# Veröffentlicht automatisch (docs/betrieb.md, Veröffentlichen). Gestartet alle 5 Minuten vom Timer
# <instanz>-veroeffentlichen.timer und gleich nach jedem Schreibvorgang des Schreibwegs (engine/schreiben.py).
# Aufruf von Hand:  FR_WURZEL=<Bauordner> <Bauordner>/betrieb/veroeffentlichen.sh          (nur wenn es Neues gibt)
#                   FR_WURZEL=<Bauordner> <Bauordner>/betrieb/veroeffentlichen.sh --immer  (auch ohne neuen Stand, auch
#                   einen bekannten roten). Ohne FR_WURZEL bricht es ab (#137).
#
# Software direkt (#454): Der Bauordner ist der Software-Klon <FR_SEITEN>/_software (FR_WURZEL, das Skript läuft aus ihm);
# einen anderen Weg gibt es seit #557 nicht mehr (kein Reisen-Repo, keine eingebundene Software, kein Workflow, kein gh). Ablauf eines
# Laufs (main_klon): Speicher-Teil mit der bisherigen Software; git fetch origin main im Klon (öffentlich, ohne Anmeldung);
# ein neuer Commit C wird geprüft, bevor der Klon umschaltet: Nachweis der Pflichtprüfungen genau dieses Commits auf GitHub
# (ohne gh, einmal je Stand), sonst Tests auf dem Server in einem eigenen Arbeitsbaum von C (git worktree), der Klon bleibt
# dabei unberührt. Rot: Rot-Datei am Software-Commit, Alarm wie bisher (einmal je Rot-Phase), der Klon bleibt auf dem letzten
# guten Stand. Grün: Python-Umgebung <FR_DIENST>/python (neu bei geänderter engine/requirements.txt), Klon vorspulen
# (ff-only), ändert sich dabei dieses Skript, Neustart mit exec; dann zieht der Speicher-Teil jede Reise auf C nach und
# deploy.sh bringt die Dienste auf C. Scheitert ein Deploy mit C (Exit 1), fällt der Klon auf <FR_DIENST>/software-gut zurück
# und die Dienste werden mit diesem Stand neu gebaut (Rückfall). Erst nach einem ganz grünen Lauf: veroeffentlicht =
# software-gut = C, Units und nginx abgleichen, Heartbeat. Prüfungen der Instanz aus <FR_DIENST>/instanz/tests laufen danach,
# wenn es sie gibt, und sperren nie (Warnung). Ein Anstoß von der Seite (_anstoss.json) ist nur dieser Lauf.
# Umzug (#454): Ein Lauf aus dem Klon setzt <FR_DIENST>/umzug-454 auf fertig, wenn es Spuren des Umzugs gibt und die Units auf
# den Klon zeigen (umzug_fertig_im_klon); eine frische Instanz ohne Umzug bekommt keinen Zustand.
# Aufräumen (#557, altbau_entfernen, docs/betrieb.md „Aufräumen nach dem Umzug“): Liegt noch der alte Bauordner
# <FR_SEITEN>/_bau (das frühere Reisen-Repo) oder eine alte Arbeitskopie <FR_SEITEN>/_bau-schreiben-*, archiviert der Lauf
# _bau nach <FR_DIENST>/archiv/ und entfernt beides, aber nur wenn umzug-454 = fertig ist, keine Unit mehr auf _bau zeigt und
# jede Reise aus _bau/reisen im Reisespeicher steht (oder gelöscht ist). Vorher: Platzprüfung, Archiv gelesen und geprüft,
# jeder Pfad aufgelöst innerhalb von FR_SEITEN und kein Link. Danach der Merker <FR_DIENST>/altbau-557; mit ihm tut der
# Schritt nichts mehr. Fehler sind eine Warnzeile, einmal je Störung, kein Alarm, kein Abbruch; der nächste Lauf versucht es
# erneut. Einen Rückweg auf den alten Weg gibt es nicht (Entscheidung des Product Owners, 20.11.2026).
#
# Tor (#142): Sperren können nur die Tests der Software (engine/tests) und ein gescheiterter Bau einer Reise (deploy.sh
# Exit 2). Eine rote Reise hält die anderen nicht auf; sie bleibt auf ihrem letzten guten Stand.
# Rot-Datei <FR_DIENST>/veroeffentlichen-rot: merkt einen roten Stand (commit, art, reisen, seit, gemeldet). Derselbe
# Commit wird ohne --immer nicht noch einmal geprüft („Bekannter roter Stand“). Ab FR_ROT_MELDEN_NACH_MINUTEN Minuten
# Rot geht genau einmal je Rot-Phase ein Alarm an den Betrieb, bei roten Reisen dazu eine Meldung an deren
# Organisator:innen (engine/waechter.py rot-melden). Infrastrukturfehler (deploy.sh Exit 1, Vorspulen) werden nicht
# gemerkt; der nächste Lauf wiederholt sie, weil nur ein ganz gelungener Lauf den Stand merkt.
# Überwachung: Nach fachlichem Erfolg (nichts Neues oder alles veröffentlicht) wird <FR_DIENST>/veroeffentlichen-erfolg
# berührt; ist FR_HEARTBEAT_VEROEFFENTLICHEN gesetzt (Adresse, in <FR_DIENST>/betrieb.env), wird sie zusätzlich abgerufen.
# Übersprungene Läufe, rote Stände (auch teilweise rot) und Fehler tun beides nicht.
# Neue Reisen: Nach dem Veröffentlichen ruft das Skript freischalten.sh für jede gelungene Reise auf (legt einer neuen Reise
# ihren geheimen Link an, prüft die Seite, schreibt seiten.json) und stellt ausstehende Links neuer Reisen aus der
# Claude-App zu (zustellen.py). Links stehen nie im Protokoll.
# Reise-Stand (Epic #223, engine/stand.py): Je Reise schreibt der Lauf ihren Zustand nach <FR_DIENST>/reise-stand/<reise>.lauf.json
# (baut, veroeffentlicht mit Dauer seit dem Sichern, fehlgeschlagen mit Grund); api/stand und publish_status lesen ihn.
# Anstoß aus dem Schreibweg (#624): Der Schreibweg legt nur den Merker <FR_DIENST>/veroeffentlichen-anstoss; die Path-Einheit
# <instanz>-veroeffentlichen.path startet daraufhin den Dienst, und dieser Lauf entfernt den Merker vor der Sperre.
# Startet ein Lauf, während ein anderer die Sperre hält (Anstoß während eines Timer-Laufs), merkt er das in
# <FR_DIENST>/veroeffentlichen-nochmal; der laufende startet danach gleich noch einmal, statt bis zum Timer zu warten.
# Alle Reisen im Speicher (#454, #557): Gebaut werden nur Reisen aus dem Reisespeicher (speicherreisen in gemeinsam.sh).
# Ohne GitHub: Scheitert git fetch, ist das kein Fehler des Laufs. Die Reisen aus dem Speicher sind dann schon
# veröffentlicht; nur die Software wartet. Merker <FR_DIENST>/software-wartet (seit, gemeldet); nach
# FR_SOFTWARE_WARTET_STUNDEN (Vorgabe 6) genau eine Warnzeile je Störung, keine Nachricht an den Betrieb. Gelingt git fetch
# wieder, wird der Merker gelöscht.
# Für Tests überschreibbar: VF_PRUEFEN, VF_STAND, VF_DEPLOY, VF_FREISCHALTEN, VF_AUSSTEHEND, VF_SPERRE, VF_STEMPEL, VF_HEARTBEAT,
# VF_ROT (Rot-Datei), VF_JETZT (Uhr, Sekunden seit 1970), VF_ROTMELDEN (statt engine/waechter.py rot-melden), VF_CINACHWEIS
# (Nachweis der Pflichtprüfungen: <url> <commit>, gibt „true“ aus), VF_VENV (<ordner> <requirements>: baut die
# Python-Umgebung), VF_GLIBC (erkannte Glibc-Version, #582), VF_UNITS (Abgleich der Units), VF_PLATZ (<ordner>: freier Platz in Bytes) und VF_ARCHIV (<archivdatei>
# <ordner>: baut das Archiv des alten Bauordners) für das Aufräumen.
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/gemeinsam.sh"

erfolg_melden() {
  mkdir -p "$FR_DIENST"
  touch "${VF_STEMPEL:-$FR_DIENST/veroeffentlichen-erfolg}"
  local hb="${VF_HEARTBEAT:-${FR_HEARTBEAT_VEROEFFENTLICHEN:-}}"
  [ -n "$hb" ] || return 0
  curl -fsS -m 10 --retry 3 -o /dev/null "$hb" || echo "Warning: heartbeat not reached."
}

# Root-Rechte (#465): Der Schreibweg stößt diesen Lauf aus einem Dienst mit NoNewPrivileges an, darin geht kein sudo.
# Freischalten (nginx-Bausteine) und Zustellen neuer Reisen brauchen es; ohne warten sie auf den nächsten Lauf des Timers.
# Geprüft wird erst, wenn es etwas freizuschalten gibt (sudo schreibt jeden Aufruf ins Journal), einmal je Lauf.
root_geht() {
  if [ -z "$root_ok" ]; then
    # sudo -l statt „sudo true“: Die sudoers-Datei der Instanz erlaubt nur die Hilfsprogramme und Neustarts (#552); in einem
    # Dienst mit NoNewPrivileges scheitert auch sudo -l
    local s="${FR_SUDO-sudo -n}"
    if [ -z "$s" ] || $s -l > /dev/null 2>&1; then root_ok=1; else root_ok=0; fi
  fi
  [ "$root_ok" = 1 ]
}

freischalten_reisen() {  # <reisen…>: freischalten (Ausgabe ohne Links, die sind geheim); ohne Root-Rechte vormerken
  local r aus
  for r in "$@"; do
    if ! root_geht; then
      grep -qxF "$r" "$frei_ausstehend" 2>/dev/null || echo "$r" >> "$frei_ausstehend"
      echo "Note: $r not released in this run (no root rights, e.g. started by the write path); the next timer run does it."
      continue
    fi
    aus="$("$freischalten" "$r" 2>&1)" || echo "Warning: $r not released (reason in the line below)."
    printf '%s\n' "$aus" | grep -E '^(ERROR|Released|Block renewed)' || true
  done
}

ausstehende_freischalten() {  # vorgemerkte Reisen eines Laufs ohne Root-Rechte, im nächsten Lauf mit Root-Rechten (#465)
  local liste
  [ -s "$frei_ausstehend" ] && root_geht || return 0
  liste="$(sort -u "$frei_ausstehend")"; rm -f "$frei_ausstehend"
  # shellcheck disable=SC2086  # eine Reise je Zeile, Namen ohne Leerzeichen (freischalten.sh prüft sie)
  freischalten_reisen $liste
}

ausstehende_neustarts() {  # von deploy.sh vorgemerkte Neustarts eines Laufs ohne Root-Rechte (#494)
  local u rest=""
  [ -s "$neustart_ausstehend" ] && root_geht || return 0
  while IFS= read -r u; do   # eine Einheit je Zeile; eine Zeile, die kein Einheitenname ist, fällt weg
    [[ "$u" =~ ^[A-Za-z0-9@._-]+$ ]] || continue
    if ${FR_SUDO-sudo -n} systemctl restart "$u" 2>/dev/null; then
      echo "$u restarted (pending from a run without root rights)."
    else
      rest="$rest$u"$'\n'
      echo "Warning: restart of $u failed; the next run tries again."
    fi
  done < <(awk '!gesehen[$0]++' "$neustart_ausstehend")
  if [ -n "$rest" ]; then printf '%s' "$rest" > "$neustart_ausstehend"; else rm -f "$neustart_ausstehend"; fi
}

zustellen() {  # ausstehende Links neuer Reisen (nur wenn welche anstehen)
  [ -s "$ausstehend" ] || return 0
  # zustellen.py schaltet die neue Reise frei; ohne Root-Rechte bleibt sie für den nächsten Lauf stehen (#465)
  root_geht || { echo "Note: new trips are delivered by the next timer run (no root rights in this run)."; return 0; }
  "$FR_PYTHON" "$FR_BETRIEB/zustellen.py" "$wurzel" "$ausstehend" \
    || echo "Warning: not all links of new trips delivered, the next run tries again."
}

jetzt() { echo "${VF_JETZT:-$(date +%s)}"; }

iso() { [[ "${1:-}" =~ ^[0-9]+$ ]] && date -u -d "@$1" +%Y-%m-%dT%H:%M:%SZ || true; }

reise_stand_schreiben() {  # <reise> <zustand> [grund]: Zustand des Reise-Stands für api/stand und publish_status
  # (engine/stand.py). nummer ist die Stand-Nummer des materialisierten Inhalts (<ordner>.stand, #348). Dauer bei
  # „veroeffentlicht“: Sekunden seit dem Sichern (Zeit des Schreibwegs); steht auch im Protokoll (Messung des Zeitziels).
  local r="$1" z="$2" g="${3:-}" n c="" t dauer=null datei gz gn seite
  n="$(cat "$FR_DIENST/bau/reisen/$r.stand" 2>/dev/null || true)"
  [[ "$n" =~ ^[0-9]+$ ]] && [ "$n" -gt 0 ] || return 0
  datei="$FR_DIENST/reise-stand/$r.gesichert.json"
  gn="$(sed -n 's/.*"nummer": *\([0-9]*\).*/\1/p' "$datei" 2>/dev/null || true)"
  gz="$(sed -n 's/.*"zeit": *"\([^"]*\)".*/\1/p' "$datei" 2>/dev/null || true)"
  if [ "$gn" = "$n" ] && [ -n "$gz" ] && gz="$(date -u -d "$gz" +%s 2>/dev/null)"; then c="$gz"; fi
  t="$(jetzt)"
  # Stand, der schon auf der Seite war (<reise>.seite, nach jeder Veröffentlichung): Ein Neubau desselben Stands (--immer,
  # Software-Wechsel) hat keine Wartezeit und wird nicht gemessen (#465)
  seite="$FR_DIENST/reise-stand/$r.seite"
  if [ "$z" = veroeffentlicht ] && [ "$(cat "$seite" 2>/dev/null || true)" = "$n" ]; then
    echo "Published $r state $n again (already on the page)."
  elif [ "$z" = veroeffentlicht ] && [[ "$c" =~ ^[0-9]+$ ]]; then
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
  [ "$z" != veroeffentlicht ] || { printf '%s\n' "$n" > "$seite.neu" && mv "$seite.neu" "$seite"; }
}

baugrund() {  # Grund eines gescheiterten Baus aus der Ausgabe von deploy.sh: die Meldungen von bauen.py („ - …“), sonst die
  # letzte Zeile mit ERROR, sonst die letzte Zeile überhaupt
  local g
  g="$({ grep -E '^ +- ' "$deploy_log" 2>/dev/null || true; } | sed -E 's/^ +- //' | head -3 | paste -sd '|' - | sed 's/|/; /g')" || true
  [ -n "$g" ] || g="$({ grep -E 'ERROR' "$deploy_log" 2>/dev/null || true; } | tail -1)" || true
  [ -n "$g" ] || g="$({ grep -v '^[[:space:]]*$' "$deploy_log" 2>/dev/null || true; } | tail -1)" || true
  printf '%s' "$g"
}

software_kennung() {  # [<commit>]: Stand der Software eines Commits im Software-Klon: der Commit selbst. Beschreibt, mit
  # welcher Software eine Reise aus dem Reisespeicher gebaut wurde (#348).
  local c="${1:-HEAD}"
  git rev-parse -q --verify "$c^{commit}" 2>/dev/null || true
}

rot_vereinigt() {  # <reisen…>: Liste der roten Reisen für die Rot-Datei, ohne Doppelte, durch Komma getrennt
  printf '%s\n' "$@" | tr ', ' '\n\n' | sed '/^$/d' | sort -u | paste -sd, -
}

vorgemerkte_entfernen() {  # #381: Reisen, die zur Löschung vorgemerkt oder schon entfernt sind (engine/konten.py vorgemerkt),
  # werden nicht gebaut, ihr Webordner <FR_SEITEN>/<reise> verschwindet sofort (die Seite liefert 404). Holt eine
  # Organisator:in die Reise zurück, fehlt sie in der Liste und wird wieder gebaut (die Seite hat keinen Stand mehr).
  # Ist die Liste nicht lesbar: Exit 1, nichts wird gebaut (fail closed).
  local r
  # ohne Kontendatenbank (auch nicht am alten Ort, instanz.konten) ist keine Reise vorgemerkt
  [ -e "$FR_KONTEN/konten.db" ] || [ -e "$FR_ABLAGE/_konten/konten.db" ] || return 0
  vorgemerkt_liste="$("$FR_PYTHON" "$FR_BETRIEB/../engine/konten.py" vorgemerkt)" \
    || { echo "ERROR: the list of deleted trips cannot be read, the next run tries again."; return 1; }
  for r in $vorgemerkt_liste; do
    [[ "$r" =~ ^[a-z0-9][a-z0-9-]{0,40}$ ]] || continue
    if [ -e "$FR_SEITEN/$r" ]; then
      rm -rf "${FR_SEITEN:?}/$r"
      echo "$r is marked for deletion: page removed."
    fi
  done
  return 0
}

entfernte_bausteine() {  # #527: nginx-Baustein <FR_NGINX_SNIPPETS>/<instanz>-<reise>.conf jeder endgültig entfernten Reise
  # (Löschprotokoll, engine/konten.py entfernt; nicht die Schonfrist, dort kann die Reise mit ihrem Link zurückkommen) über das
  # Hilfsprogramm mit --entfernen löschen (Sicherung, nginx -t, Rückweg, Reload; #552). Der Wächter hat keine Root-Rechte.
  # Die noch liegende Datei ist die Vormerkung: geprüft ohne Root, sudo nur bei echter Arbeit. Ohne Root-Rechte oder bei
  # einem Fehler des Hilfsprogramms holt es der nächste Lauf nach. Kein Ausfall (die Seite liefert ohnehin 404): nur
  # Warnzeilen, immer Rückgabe 0.
  local r liste datei helfer fehler_datei hrc grund
  [ -e "$FR_KONTEN/konten.db" ] || [ -e "$FR_ABLAGE/_konten/konten.db" ] || return 0
  liste="$("$FR_PYTHON" "$FR_BETRIEB/../engine/konten.py" entfernt)" \
    || { echo "Warning: the list of removed trips cannot be read, nginx blocks stay until the next run."; return 0; }
  helfer="${FR_NGINX_REISE_HELFER:-/usr/local/sbin/$FR_INSTANZ-nginx-reise-installieren}"
  for r in $liste; do
    [[ "$r" =~ ^[a-z0-9][a-z0-9-]{1,39}$ ]] || continue   # Muster des Hilfsprogramms und von freischalten.sh
    datei="${FR_NGINX_SNIPPETS:-/etc/nginx/snippets}/$FR_INSTANZ-$r.conf"
    [ -e "$datei" ] || continue
    if ! root_geht; then
      echo "Note: nginx block of $r not removed in this run (no root rights); the next timer run does it."
      continue
    fi
    if [ ! -x "$helfer" ]; then
      echo "Warning: nginx block of $r not removed, helper $helfer is missing (einrichten.sh --installieren)."
      continue
    fi
    fehler_datei="$(mktemp)"
    hrc=0
    printf '%s\n' "$r" | ${FR_SUDO-sudo -n} "$helfer" --entfernen > /dev/null 2> "$fehler_datei" || hrc=$?
    grund="$(tr '\n' ' ' < "$fehler_datei" | sed 's/ *$//')"
    rm -f "$fehler_datei"
    case "$hrc" in
      0) echo "Block removed: $r" ;;
      2) ;;   # nichts mehr da (Wettlauf)
      *) echo "Warning: nginx block of $r not removed (exit $hrc), the next run tries again: ${grund:-no reason}" ;;
    esac
  done
  return 0
}

ist_vorgemerkt() {  # <reise>: steht sie in der Liste aus vorgemerkte_entfernen?
  [[ " $(echo $vorgemerkt_liste) " == *" $1 "* ]]
}

speicher_reisen_lauf() {  # Speicher-Teil (Stufe 3, #348): Reisen im Speicher (#454: was dort steht) bauen, vor
  # git fetch und ohne Netz. Gebaut wird eine Reise, wenn ihre Stand-Nummer im
  # Speicher nicht die der Seite ist, mit --immer, ohne Stempel <FR_DIENST>/reise-stand/<reise>.gebaut („<nummer>
  # <software-kennung>“, nur nach gelungenem Deploy) oder nach einem Software-Wechsel; dann stellt neu.py
  # nachziehen-speicher sie vorher um (ein Vorgang, nur bei grünem Probebau). Eine neue Software-Kennung gilt erst, wenn der
  # Lauf sie geprüft oder vollständig veröffentlicht hat (Datei veroeffentlicht); bis dahin bleibt jede Reise mit älterem Stempel
  # stehen. Ergebnis: speicher_gut, speicher_rote; Exit 1 bei einer Störung (Speicher nicht lesbar, deploy Exit 1).
  local liste r n pub gn gk modus rc ordner aus kennung geprueft="" vorher log gepr_stand=""
  liste="$(speicherreisen | while read -r r; do ist_vorgemerkt "$r" || echo "$r"; done | tr '\n' ' ')"
  [ -n "${liste// /}" ] || return 0
  speicher_aktiv=1
  kennung="$(software_kennung HEAD)"
  speicher_kennung="$kennung"
  vorher="$(cat "$stand" 2>/dev/null || true)"
  if [ -n "$vorher" ] && [ -n "$kennung" ] && [ "$(software_kennung "$vorher")" = "$kennung" ]; then
    geprueft=1; gepr_stand="$(git rev-parse HEAD)"   # deploy.sh prüft dann nicht selbst (FR_GEPRUEFT)
  elif [ -n "$software_gepr" ] && [ "$software_gepr" = "$kennung" ]; then
    geprueft=1; gepr_stand="$(git rev-parse HEAD)"   # Software-Klon (#454): dieser Lauf hat den Commit eben geprüft
  fi
  # Die Prüfung der Software gilt dem Commit, nicht dem Veröffentlichen (#599): Ist der Commit im Klon schon geprüft
  # (Nachweis oder Tests vor dem Vorspulen), führt deploy.sh die Tests nicht vor jeder Reise erneut aus, auch wenn eine
  # rote Reise das Veröffentlichen des Stands noch aufhält. Nachziehen auf die neue Kennung wartet trotzdem (geprueft).
  if [ -z "$gepr_stand" ] && [ "$(cat "$FR_DIENST/software-geprueft" 2>/dev/null || true)" = "$(git rev-parse HEAD)" ]; then
    gepr_stand="$(git rev-parse HEAD)"
  fi
  # shellcheck disable=SC2086
  aus="$("$FR_PYTHON" "$FR_BETRIEB/../engine/reisespeicher.py" staende $liste)" \
    || { echo "ERROR: the trip store cannot be read ($aus), the next run tries again."; return 1; }
  log="$(mktemp)"
  while read -r -u 3 r n pub; do   # eigener Kanal: deploy.sh und Python lesen sonst die Liste mit
    [ -n "$r" ] || continue
    if [ "$n" = - ]; then
      echo "Note: $r has no entry in the trip store, skipped."; continue
    fi
    gn=""; gk=""
    if [ -r "$FR_DIENST/reise-stand/$r.gebaut" ]; then read -r gn gk < "$FR_DIENST/reise-stand/$r.gebaut" || true; fi
    if [ -n "$gk" ] && [ "$gk" != "$kennung" ]; then
      if [ -z "$geprueft" ]; then
        echo "Note: software ${kennung:0:7} is not checked yet, $r waits at its last good state."
        speicher_wartet=1; continue
      fi
      modus=nachziehen
    elif [ -n "$immer" ] || [ -z "$gk" ] || [ "$n" != "$pub" ]; then
      modus=bauen
    else
      continue
    fi
    ordner="$FR_DIENST/bau/reisen/$r"
    mkdir -p "$FR_DIENST/bau/reisen"
    rc=0
    if [ "$modus" = nachziehen ]; then
      echo "Software changed (${gk:0:7} -> ${kennung:0:7}): converting $r from the trip store."
      "$FR_PYTHON" "$FR_BETRIEB/../engine/neu.py" nachziehen-speicher "$r" "$ordner" > "$log" 2>&1 || rc=$?
      sed 's/^/  /' "$log"
    else
      "$FR_PYTHON" "$FR_BETRIEB/../engine/reisespeicher.py" materialisieren "$r" "$ordner" > "$log" 2>&1 || rc=$?
    fi
    case "$rc" in
      0) ;;
      2) if [ "$modus" = nachziehen ]; then
           echo "ERROR: $r cannot be converted to the new software, the trip stays at its last good state."
           deploy_log="$log"; reise_stand_schreiben "$r" fehlgeschlagen "$(baugrund)"
           speicher_rote="${speicher_rote:+$speicher_rote,}$r"; continue
         fi
         if grep -q '^ - ' "$log"; then   # Datei der Ablage fehlt oder ist beschädigt (#349): roter Bau, keine Störung
           sed 's/^/  /' "$log"
           echo "ERROR: build of $r failed, the trip stays at its last good state."
           deploy_log="$log"; reise_stand_schreiben "$r" fehlgeschlagen "$(baugrund)"
           speicher_rote="${speicher_rote:+$speicher_rote,}$r"; continue
         fi
         echo "ERROR: $r cannot be read from the trip store ($(tail -1 "$log")), the next run tries again."; rm -f "$log"; return 1 ;;
      *) echo "ERROR: $r cannot be read from the trip store ($(tail -1 "$log")), the next run tries again."; rm -f "$log"; return 1 ;;
    esac
    reise_stand_schreiben "$r" baut
    echo "Publishing $r from the trip store, state $(cat "$ordner.stand" 2>/dev/null)."
    rc=0; FR_GEPRUEFT="$gepr_stand" FR_WEGE_SPAETER=1 "$deploy" "$r" 2>&1 | tee "$log" || rc=${PIPESTATUS[0]}
    case "$rc" in
      0) mkdir -p "$FR_DIENST/reise-stand"
         echo "$(cat "$ordner.stand") $kennung" > "$FR_DIENST/reise-stand/$r.gebaut.neu"
         mv "$FR_DIENST/reise-stand/$r.gebaut.neu" "$FR_DIENST/reise-stand/$r.gebaut"
         reise_stand_schreiben "$r" veroeffentlicht
         speicher_gut="$speicher_gut $r" ;;
      2) echo "ERROR: build of $r failed, the trip stays at its last good state."
         deploy_log="$log"; reise_stand_schreiben "$r" fehlgeschlagen "$(baugrund)"
         speicher_rote="${speicher_rote:+$speicher_rote,}$r" ;;
      *) echo "ERROR: deploy of $r failed (exit $rc), the next run tries again."; rm -f "$log"; return 1 ;;
    esac
  done 3<<< "$aus"
  rm -f "$log"; deploy_log=""
  # Freischalten (Ausgabe ohne Links), die Wege zum Konnektor einmal danach
  # shellcheck disable=SC2086
  freischalten_reisen $speicher_gut
  [ -z "$speicher_gut" ] || wege_pruefen
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

pruefen_lauf() {  # <ordner>: pytest über engine/tests oder die Prüfungen der Instanz; Ausgabe auch nach pruef_log
  local rc=0
  if [ -n "$pruefen" ]; then "$pruefen" "$1" 2>&1 | tee "$pruef_log" || rc=${PIPESTATUS[0]}
  else
    # Software-Tests parallel (pytest-xdist, #395): seriell mit Nice=10 rund 30 Minuten, die CI braucht parallel 7. Ohne xdist
    # in FR_PYTHON seriell wie bisher; FR_PRUEF_PROZESSE (Vorgabe auto) begrenzt die Zahl der Prozesse.
    local parallel=()
    if [ "$1" = engine/tests ] && "$FR_PYTHON" -c 'import xdist' 2>/dev/null; then parallel=(-n "${FR_PRUEF_PROZESSE:-auto}"); fi
    "$FR_PYTHON" -m pytest "$1" -q "${parallel[@]}" --basetemp "$pruef_tmp" 2>&1 | tee "$pruef_log" || rc=${PIPESTATUS[0]}
  fi
  return "$rc"
}

rote_tests() {  # die ersten roten Tests aus pruef_log und die erste Fehlerzeile, in einer Zeile für Rot-Datei und Meldung
  local namen erste
  namen="$({ grep -E '^(FAILED|ERROR) ' "$pruef_log" 2>/dev/null || true; } | sed -E 's/^(FAILED|ERROR) //; s/ - .*//' | head -5 | paste -sd, - | sed 's/,/, /g')" || true
  erste="$({ grep -m1 -E '^E +[^ ]' "$pruef_log" 2>/dev/null || true; } | sed -E 's/^E +//' | cut -c1-200)" || true
  printf '%s%s' "$namen" "${erste:+ (first error: $erste)}" | tr -d '\n'
}

software_wartet_merken() {  # git fetch gescheitert (#350): Merker <FR_DIENST>/software-wartet (seit, gemeldet).
  # Erst nach FR_SOFTWARE_WARTET_STUNDEN (Vorgabe 6) genau eine Warnzeile je Störung, keine Nachricht über fr_melden: Ein
  # GitHub-Ausfall ist kein Ausfall der Reisen; den Zustand zeigt der Monitor der Instanz aus dem Merker.
  local datei="$FR_DIENST/software-wartet" seit="" gemeldet="" zeile t stunden="${FR_SOFTWARE_WARTET_STUNDEN:-6}"
  [[ "$stunden" =~ ^[0-9]+$ ]] || stunden=6
  t="$(jetzt)"
  if [ -r "$datei" ]; then
    while IFS= read -r zeile || [ -n "$zeile" ]; do
      case "$zeile" in
        seit=*) seit="${zeile#*=}" ;;
        gemeldet=*) gemeldet="${zeile#*=}" ;;
      esac
    done < "$datei"
  fi
  if ! [[ "$seit" =~ ^[0-9]+$ ]]; then
    seit="$t"; gemeldet=0
  elif [ "$gemeldet" != 1 ] && [ $(( 10#$t - 10#$seit )) -ge $(( 10#$stunden * 3600 )) ]; then
    echo "Warning: Software update waiting since $(( (10#$t - 10#$seit) / 3600 )) h ($(iso "$seit")); trips from the trip store are published."
    gemeldet=1
  else
    return 0
  fi
  mkdir -p "$FR_DIENST"
  printf 'seit=%s\ngemeldet=%s\n' "$seit" "$gemeldet" > "$datei.neu" && mv "$datei.neu" "$datei"
}

software_wartet_loeschen() {  # git fetch gelungen: die Störung ist vorbei, die nächste warnt wieder einmal
  rm -f "$FR_DIENST/software-wartet"
}

abhaengigkeiten_playwright() {
  # Playwright: eigene Kopie in <FR_DIENST>/playwright nach engine/tests/playwright/package-lock.json, nie ein
  # Ordner, den andere mitbenutzen. Browser ohne --with-deps (kein sudo); Systembibliotheken richtet einrichten.sh ein.
  # Ohne npm (Instanz ohne Browsertests) bleibt alles, wie es ist. Im Software-Klon (#454) nur vor Tests auf dem Server.
  # Die Browser liegen daneben in <FR_DIENST>/playwright/browser (PLAYWRIGHT_BROWSERS_PATH), nicht im Heimatverzeichnis: Der
  # Konnektor macht damit Bilder der Seite (page_view, #618) und sieht als Dienst mit ProtectHome kein Heimatverzeichnis.
  local summe pw_quelle=engine/tests/playwright pw_ziel="$FR_DIENST/playwright" npm="${VF_NPM:-npm}"
  [ -f "$pw_quelle/package-lock.json" ] || return 0
  command -v "$npm" > /dev/null 2>&1 || { echo "Note: npm missing, browser tests use what playwright_pfad.py finds."; return 0; }
  summe="$(cat "$pw_quelle/package.json" "$pw_quelle/package-lock.json" | sha256sum | cut -d' ' -f1)"
  if [ "$summe" != "$(cat "$pw_ziel/.stand" 2>/dev/null || true)" ] || [ ! -e "$pw_ziel/node_modules/playwright/index.mjs" ] \
     || [ ! -d "$pw_ziel/browser" ]; then
    echo "Installing Playwright (engine/tests/playwright changed or its browsers missing)."
    mkdir -p "$pw_ziel"
    cp "$pw_quelle/package.json" "$pw_quelle/package-lock.json" "$pw_ziel/"
    ( cd "$pw_ziel" && "$npm" ci --silent --no-audit --no-fund \
      && PLAYWRIGHT_BROWSERS_PATH="$pw_ziel/browser" "$npm" exec --no -- playwright install chromium webkit ) || return 1
    mkdir -p "$pw_ziel/browser"
    echo "$summe" > "$pw_ziel/.stand"
  fi
  PLAYWRIGHT_MODUL="$pw_ziel/node_modules/playwright/index.mjs"; export PLAYWRIGHT_MODUL
  PLAYWRIGHT_BROWSERS_PATH="$pw_ziel/browser"; export PLAYWRIGHT_BROWSERS_PATH
}

software_klon() {  # läuft das Skript aus dem Software-Klon, der zugleich der Bauordner ist (#454)?
  [ "$(cd "$FR_BETRIEB/.." && pwd -P)" = "$(cd "$FR_WURZEL" && pwd -P)" ]
}

anstoss_lauf() {  # Anstoß der Seite im Software-Klon (#454): dieser Lauf ist der angestoßene; kein Workflow, kein gh
  local datei="$FR_ABLAGE/_anstoss.json" ergebnis="$FR_ABLAGE/_anstoss-ergebnis.json"
  [ -e "$datei" ] || return 0
  echo "Request from the page: this run publishes the newest state of the software."
  printf '{"zeit": "%s", "ok": true}\n' "$(date -u +%Y-%m-%dT%H:%M:%S+00:00)" > "$ergebnis.tmp" && mv "$ergebnis.tmp" "$ergebnis"
  rm -f "$datei"
}

ci_nachweis_commit() {  # <commit>: 0, wenn die Pflichtprüfungen genau dieses Software-Commits auf GitHub grün sind (#403, #454)
  # Abfrage ohne Anmeldung (öffentliches Repo, curl auf die API, kein gh); ein Fehler heißt „kein Nachweis“, dann prüft der
  # Server selbst. Mit FR_CI_NACHWEIS=0 immer ohne Nachweis.
  [ "${FR_CI_NACHWEIS:-1}" = 1 ] || return 1
  local url repo ok sha="$1"
  url="$(git config --get remote.origin.url 2>/dev/null)" || return 1
  if [ -n "${VF_CINACHWEIS:-}" ]; then ok="$("$VF_CINACHWEIS" "$url" "$sha" 2>/dev/null)" || ok=""
  else
    ok=""
    repo="$(printf '%s' "$url" | sed -E 's#^(https://github\.com/|git@github\.com:)##; s#\.git$##')"
    if [[ "$repo" =~ ^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$ ]]; then
      ok="$(curl -fsS -m 30 -H 'Accept: application/vnd.github+json' \
              "https://api.github.com/repos/$repo/commits/$sha/check-runs?per_page=100" 2>/dev/null \
            | "$FR_PYTHON" -c 'import json, sys
g = {r.get("name") for r in json.load(sys.stdin).get("check_runs", []) if r.get("conclusion") == "success"}
print("true" if {"tests (leer)", "tests (instanz)", "gitleaks"} <= g else "false")' 2>/dev/null)" || ok=""
    fi
  fi
  if [ -z "$ok" ]; then echo "Note: required checks of ${sha:0:7} not retrievable, the server checks itself."; return 1; fi
  [ "$ok" = true ] || return 1
  CI_STAND="${sha:0:7}"
}

python_verwaltet() {  # wird die Python-Umgebung unter <FR_DIENST>/python von hier gepflegt? Ja, wenn FR_PYTHON sie nennt
  # (Vorgabe der neuen Anordnung) oder VF_VENV sie für Tests baut; ein ausdrücklich anderes FR_PYTHON bleibt unberührt
  [ -n "${VF_VENV:-}" ] || [ "$FR_PYTHON" = "$FR_DIENST/python/bin/python" ]
}

python_umgebung() {  # <commit>: die Live-Umgebung <FR_DIENST>/python auf die Abhängigkeiten eines schon angenommenen
  # Commits bringen (python_kandidat, bei Bedarf gleich übernehmen). Für einen neuen, noch ungeprüften Commit nur
  # python_kandidat: übernommen wird erst nach grüner Prüfung (#454, F003).
  python_kandidat "$1" || return 1
  [ -z "$python_neu" ] || python_uebernehmen
}

python_kandidat() {  # <commit>: Python-Umgebung für die Abhängigkeiten dieses Commits (#454), außerhalb des Klons, damit
  # Umschalten und Rückfall sie nicht berühren. Passt die Live-Umgebung <FR_DIENST>/python (Prüfsumme von
  # engine/requirements.txt im Commit gleich der in python/.requirements.sha256, bin/python da), geschieht nichts
  # (python_neu leer). Sonst entsteht eine neue Umgebung daneben (<FR_DIENST>/python.neu, python_neu); die laufende bleibt
  # unverändert, bis python_uebernehmen sie atomar tauscht (F003). Nur der allererste Bau (weder Merker noch bin/python)
  # entsteht an Ort und Stelle, dann läuft noch nichts mit ihr.
  python_neu=""
  python_verwaltet || return 0
  local ziel="$FR_DIENST/python" kand="$FR_DIENST/python.neu" merk summe liste
  merk="$ziel/.requirements.sha256"
  liste="$(mktemp)"
  git show "$1:engine/requirements.txt" > "$liste" 2>/dev/null || : > "$liste"
  summe="$(sha256sum < "$liste" | cut -d' ' -f1)"
  if [ "$summe" = "$(cat "$merk" 2>/dev/null || true)" ] && { [ -n "${VF_VENV:-}" ] || [ -x "$ziel/bin/python" ]; }; then
    rm -f "$liste"; return 0
  fi
  glibc_pruefen || { rm -f "$liste"; return 1; }
  if [ ! -e "$merk" ] && [ ! -x "$ziel/bin/python" ]; then
    echo "Building the Python environment $ziel (engine/requirements.txt of ${1:0:7})."
    mkdir -p "$ziel"
    python_bauen "$ziel" "$liste" || { rm -f "$liste"; return 1; }
    rm -f "$liste"
    echo "$summe" > "$merk"
    FR_BIBLIOTHEKEN_NEU=1; export FR_BIBLIOTHEKEN_NEU
    return 0
  fi
  echo "Building a new Python environment for ${1:0:7} next to the running one (engine/requirements.txt changed); it replaces $ziel only after green checks."
  rm -rf "${kand:?}"   # Rest eines abgebrochenen Laufs: nur der eigene Bauordner, nie die laufende Umgebung
  mkdir -p "$kand"
  if ! python_bauen "$kand" "$liste"; then rm -f "$liste"; rm -rf "${kand:?}"; return 1; fi
  rm -f "$liste"
  echo "$summe" > "$kand/.requirements.sha256"
  python_neu="$kand"
}

GLIBC_MINDESTENS="2.28"   # Räder wie pillow-heif (#582, manylinux_2_28) brauchen sie
glibc_pruefen() {  # vor dem Bau einer neuen Python-Umgebung: Glibc des Servers mindestens GLIBC_MINDESTENS (VF_GLIBC in Tests);
  # sonst Abbruch mit klarer Meldung, bevor etwas gebaut oder getauscht wird; die laufende Umgebung bleibt
  local v
  v="${VF_GLIBC:-$(python3 -c 'import platform; print(platform.libc_ver()[1])' 2>/dev/null || true)}"
  if [ -z "$v" ] || [ "$(printf '%s\n%s\n' "$GLIBC_MINDESTENS" "$v" | sort -V | head -1)" != "$GLIBC_MINDESTENS" ]; then
    echo "ERROR: glibc ${v:-unknown} is older than $GLIBC_MINDESTENS (needed by engine/requirements.txt, e.g. pillow-heif); the Python environment is not rebuilt, the running one stays."
    return 1
  fi
}

python_bauen() {  # <ziel> <liste>: venv anlegen und die Bibliotheken der Liste installieren (VF_VENV in Tests)
  if [ -n "${VF_VENV:-}" ]; then "$VF_VENV" "$1" "$2"; return; fi
  python3 -m venv "$1" && "$1/bin/python" -m pip install -q --disable-pip-version-check -r "$2"
}

verzeichnisse_tauschen() {  # <a> <b>: beide Ordner in einem Schritt tauschen (renameat2 RENAME_EXCHANGE); Exit 1, wenn das
  # Dateisystem es nicht kann
  python3 -c 'import ctypes, os, sys
libc = ctypes.CDLL(None, use_errno=True)
f = getattr(libc, "renameat2", None)
sys.exit(1 if f is None or f(-100, os.fsencode(sys.argv[1]), -100, os.fsencode(sys.argv[2]), 2) != 0 else 0)' "$1" "$2" 2>/dev/null
}

python_uebernehmen() {  # die geprüfte neue Umgebung (python_neu) atomar an die Stelle von <FR_DIENST>/python setzen; die
  # bisherige bleibt als <FR_DIENST>/python.alt (für den Rückfall dieses Laufs), die davor wird verworfen
  local ziel="$FR_DIENST/python" alt="$FR_DIENST/python.alt"
  [ -n "$python_neu" ] || return 0
  rm -rf "${alt:?}"
  if verzeichnisse_tauschen "$python_neu" "$ziel"; then
    mv "$python_neu" "$alt"
  else
    mv "$ziel" "$alt" && mv "$python_neu" "$ziel" || return 1
  fi
  echo "Python environment $ziel replaced (engine/requirements.txt changed); the previous one stays as $alt."
  python_neu=""
  python_getauscht=1; export python_getauscht   # überlebt den Neustart des Skripts (exec) für den Rückfall
  FR_BIBLIOTHEKEN_NEU=1; export FR_BIBLIOTHEKEN_NEU
}

python_verwerfen() {  # rote oder abgebrochene Prüfung: die neue Umgebung verwerfen, die laufende bleibt, wie sie war
  [ -z "$python_neu" ] || rm -rf "${python_neu:?}"
  python_neu=""
}

python_zurueck() {  # Rückfall: hat dieser Lauf die Umgebung getauscht, die vorige (python.alt) wieder einsetzen
  local ziel="$FR_DIENST/python" alt="$FR_DIENST/python.alt"
  [ -n "${python_getauscht:-}" ] && [ -d "$alt" ] || return 0
  if ! verzeichnisse_tauschen "$alt" "$ziel"; then
    rm -rf "${ziel:?}.verworfen"
    mv "$ziel" "$ziel.verworfen" && mv "$alt" "$ziel" || { echo "ERROR: the previous Python environment could not be restored."; return 1; }
  fi
  echo "Python environment $ziel back to the previous one."
  unset python_getauscht
  FR_BIBLIOTHEKEN_NEU=1; export FR_BIBLIOTHEKEN_NEU
}

software_pruefen() {  # <commit>: Prüfung vor dem Umschalten (#454): Nachweis auf GitHub, sonst Tests auf dem Server in einem
  # eigenen Arbeitsbaum dieses Commits (git worktree); der Klon bleibt dabei, wie er ist. Exit 0 grün, 1 rot (Namen der
  # roten Tests in rote_tests_text), 2 Störung (Arbeitsbaum nicht anlegbar).
  local c="$1" baum rc=0
  rote_tests_text=""
  if ci_nachweis_commit "$c"; then
    echo "Software ${CI_STAND}: required checks green on GitHub (same commit), server tests skipped (#403)."
    return 0
  fi
  baum="$(mktemp -d)"
  pruef_tmp="$(mktemp -d)"; pruef_log="$pruef_tmp.log"
  if ! git worktree add -q --detach "$baum/software" "$c" > /dev/null 2>&1; then
    echo "ERROR: working tree of ${c:0:7} cannot be created, the next run tries again."
    rm -rf "$baum" "$pruef_tmp"; return 2
  fi
  echo "Checking software ${c:0:7} on the server (engine/tests in its own working tree)."
  ( cd "$baum/software" && { [ -n "$pruefen" ] || abhaengigkeiten_playwright; } && pruefen_lauf engine/tests ) || rc=$?
  [ "$rc" = 0 ] || rote_tests_text="$(rote_tests)"
  git worktree remove --force "$baum/software" > /dev/null 2>&1 || true
  git worktree prune > /dev/null 2>&1 || true
  rm -rf "$baum" "$pruef_tmp" "$pruef_log"
  [ "$rc" = 0 ] || return 1
}

instanz_pruefen() {  # <commit>: Prüfungen der Instanz <FR_DIENST>/instanz/tests (#454): wenn vorhanden, nach dem Wechsel; rot
  # ist eine Warnung (einmal je Commit eine normale Nachricht), sie sperren nie
  local ordner="$FR_DIENST/instanz/tests" c="$1"
  [ -d "$ordner" ] || return 0
  pruef_tmp="$(mktemp -d)"; pruef_log="$pruef_tmp.log"
  if ! pruefen_lauf "$ordner"; then
    echo "Warning: checks of the instance red ($ordner; they do not block)."
    if [ "$(cat "$warnung" 2>/dev/null || true)" != "$c" ]; then
      fr_melden normal "Checks of the instance red" "Software ${c:0:7}: the checks in $ordner are red. They do not block publishing (docs/betrieb.md). Log: journalctl -u $FR_INSTANZ-veroeffentlichen -n 100"
      mkdir -p "$(dirname "$warnung")"
      echo "$c" > "$warnung"
    fi
  fi
  rm -rf "$pruef_tmp" "$pruef_log"
}

rueckfall() {  # <grund>: Klon zurück auf <FR_DIENST>/software-gut, Dienste mit diesem Stand neu bauen (#454)
  local gut
  gut="$(cat "$FR_DIENST/software-gut" 2>/dev/null || true)"
  if [ -z "$gut" ] || ! git cat-file -e "$gut^{commit}" 2>/dev/null; then
    echo "ERROR: $1; no last good software state known, the next run tries again."; return 0
  fi
  if [ "$gut" = "$(git rev-parse HEAD)" ]; then echo "ERROR: $1, the next run tries again."; python_zurueck; return 0; fi
  echo "ERROR: $1; back to the last good software state ${gut:0:7}, the pages stay at their last good state."
  git reset -q --hard "$gut"
  python_zurueck
  # Code der Dienste zurück auf den guten Stand (deploy.sh --dienste baut keine Reise)
  FR_GEPRUEFT="$gut" "$deploy" --dienste 2>&1 | sed 's/^/  /' \
    || echo "ERROR: the services could not be restored to ${gut:0:7}, the next run tries again."
}

main_klon() {  # ein Lauf im Software-Klon (#454), Ablauf im Kopf
  local neu kopf grund rc
  anstoss_lauf
  if [ "$(git rev-parse --abbrev-ref HEAD)" != main ]; then
    echo "Software clone is not on main ($(git rev-parse --abbrev-ref HEAD)), skipped."; return 0
  fi
  if ! git diff --quiet HEAD || [ -n "$(git ls-files --others --exclude-standard)" ]; then
    echo "Uncommitted changes in the software clone, skipped."; return 0
  fi
  mkdir -p "$FR_DIENST"
  umzug_fertig_im_klon
  vorgemerkte_entfernen || return 1
  entfernte_bausteine
  speicherreisen_lesen || return 1
  altbau_entfernen                   # #557: alter Bauordner nach Archiv weg; Fehler nur als Warnzeile
  speicher_reisen_lauf || return 1   # mit der Software, die jetzt da ist
  ausstehende_neustarts
  ausstehende_freischalten
  kopf="$(git rev-parse HEAD)"
  if git fetch -q origin main; then
    software_wartet_loeschen
    neu="$(git rev-parse origin/main)"
  else
    echo "Warning: git fetch of the software failed (no network or GitHub down), the software update waits."
    software_wartet_merken
    neu="$kopf"
  fi
  if [ "$neu" != "$kopf" ]; then
    if ! git merge-base --is-ancestor "$kopf" "$neu" 2>/dev/null; then
      echo "ERROR: main of the software cannot be fast-forwarded (local commits?)."; return 1
    fi
    rot_lesen
    if [ -z "$immer" ] && [ -n "$rot_commit" ] && [ "$rot_commit" = "$neu" ]; then
      if grund="$(rot_erneut_pruefen)"; then
        echo "Known red state ${neu:0:7}, checking again ($grund)."
      else
        echo "Known red state ${neu:0:7}, skipped (kind: $rot_art). It is checked again with a new commit, a changed environment, after ${FR_ROT_NEU_PRUEFEN_MINUTEN:-60} minutes or with --immer. The services keep running with ${kopf:0:7}."
        zustellen
        alarm_pruefen
        return 0
      fi
    fi
    # Neue Abhängigkeiten: eigene Umgebung neben der laufenden, geprüft wird mit ihr; die laufende bleibt bis zum Grün (F003)
    python_kandidat "$neu" || { echo "ERROR: Python environment for ${neu:0:7} cannot be built, the next run tries again."; return 1; }
    rc=0
    if [ -n "$python_neu" ] && [ -x "$python_neu/bin/python" ]; then
      FR_PYTHON="$python_neu/bin/python" software_pruefen "$neu" || rc=$?
    else
      software_pruefen "$neu" || rc=$?
    fi
    if [ "$rc" = 2 ]; then python_verwerfen; return 1; fi
    if [ "$rc" != 0 ]; then
      python_verwerfen
      echo "ERROR: checks red (engine/tests, software ${neu:0:7}), the software stays at ${kopf:0:7}."
      rot_schreiben "$neu" software "" "$rote_tests_text"
      alarm_pruefen
      return 1
    fi
    echo "$neu" > "$FR_DIENST/software-geprueft.neu" && mv "$FR_DIENST/software-geprueft.neu" "$FR_DIENST/software-geprueft"   # #599
    git merge -q --ff-only "$neu" || { python_verwerfen; echo "ERROR: the software clone cannot be fast-forwarded."; return 1; }
    python_uebernehmen || { echo "ERROR: the new Python environment cannot be put in place, the next run tries again."; return 1; }
    echo "Software ${kopf:0:7} -> ${neu:0:7}."
    # Ändert das Vorspulen dieses Skript oder seine Grundlage, läuft der Rest mit dem neuen Code (exec, höchstens einmal)
    if [ "${_neugestartet:-}" != "$$" ] && ! git diff --quiet "$kopf" "$neu" -- betrieb/veroeffentlichen.sh betrieb/gemeinsam.sh; then
      echo "The publishing script changed with the update, restarting."
      fr_aufraeumen
      _neugestartet="$$"; export _neugestartet
      cd "$start_ordner"
      exec "$0" "$@"
    fi
    kopf="$neu"
  fi
  if [ -z "$immer" ] && [ "$(cat "$stand" 2>/dev/null || true)" = "$kopf" ]; then
    zustellen
    if [ -n "$speicher_rote" ]; then neu="$kopf"; speicher_rot_melden; return 1; fi
    rm -f "$rot_datei"; erfolg_melden; return 0
  fi
  # Software kopf veröffentlichen: Reisen auf diesen Stand nachziehen, Dienste mit ihm (deploy.sh)
  echo "Publishing software $(git log -1 --format='%h %s')"
  python_umgebung "$kopf" || { echo "ERROR: Python environment for ${kopf:0:7} cannot be built, the next run tries again."; return 1; }
  software_gepr="$kopf"; speicher_gut=""; speicher_rote=""
  # Erst der Code der Dienste mit kopf (deploy.sh --dienste). Nur scheitert dieser Deploy, fällt die Software auf
  # software-gut zurück, mit Rot-Datei am Commit (er wird nicht im nächsten Takt erneut ausgerollt; ein Alarm je Rot-Phase,
  # F002). Erst danach zieht der Speicher-Teil die Reisen auf die Kennung von kopf nach: Nach einem Rückfall läuft so nie
  # alter Code auf schon umgestellten Reisedaten.
  # Browser für das Bild der Seite (page_view, #618) und die Startprobe: nur bei geänderter Sperrdatei oder fehlenden Browsern
  # wird installiert; scheitert es, bleibt es eine Warnung (das Bild sagt dann selbst, dass es nicht geht), der Lauf geht weiter
  abhaengigkeiten_playwright || echo "Warning: Playwright cannot be installed (page picture and start probe use what is there), the next run tries again."
  rc=0; FR_GEPRUEFT="$kopf" "$deploy" --dienste 2>&1 | sed 's/^/  /' || rc=${PIPESTATUS[0]}
  unset FR_BIBLIOTHEKEN_NEU   # Dienste mit FR_PYTHON nur beim ersten Deploy neu starten
  if [ "$rc" != 0 ]; then
    rot_schreiben "$kopf" software "" "deploy of the services failed (exit $rc)"
    rueckfall "deploy of the services with software ${kopf:0:7} failed (exit $rc)"
    alarm_pruefen
    return 1
  fi
  if ! speicher_reisen_lauf; then
    # Speicher kurz nicht lesbar oder Deploy einer Reise gescheitert: kein Rückfall (die Dienste laufen
    # mit kopf, Reisen sind womöglich schon umgestellt), der Lauf ist rot und der nächste versucht es wieder
    echo "ERROR: publishing the trips with software ${kopf:0:7} failed, the next run tries again."
    return 1
  fi
  neu="$kopf"
  if [ -n "$speicher_rote" ]; then zustellen; speicher_rot_melden; return 1; fi
  rm -f "$rot_datei"
  units_abgleichen
  nginx_abgleichen
  mkdir -p "$(dirname "$stand")"
  echo "$kopf" > "$stand"
  echo "$kopf" > "$FR_DIENST/software-gut.neu" && mv "$FR_DIENST/software-gut.neu" "$FR_DIENST/software-gut"
  instanz_pruefen "$kopf"
  zustellen
  echo "Done: software $(git log -1 --format='%h') is online."
  erfolg_melden
}

umzug_fertig_im_klon() {  # Schritt 5 des Umzugs (#454) für einen Lauf aus dem Klon (Units bei der Auslieferung umgestellt):
  # Zustand selbst auf fertig, falls er es noch nicht ist, aber nur wenn die Units wirklich auf den Klon zeigen (units.py
  # pruefen ohne Abweichung; FR_WURZEL ist hier der Klon). Ein anderer gesetzter Zustand (alt, aus der Zeit vor #557) bleibt,
  # wie er ist; dann räumt altbau_entfernen auch nichts auf. Eine frische Instanz ohne Spur eines Umzugs (umzug-454,
  # .geprueft, .units) bekommt keinen Zustand. Weichen die Units ab: stumm, nichts geschrieben.
  local zustand_datei="$FR_DIENST/umzug-454" zustand
  zustand="$(cat "$zustand_datei" 2>/dev/null || true)"
  [ "$zustand" != fertig ] && [ "$zustand" != alt ] || return 0
  [ -e "$zustand_datei" ] || [ -e "$FR_DIENST/umzug-454.geprueft" ] || [ -e "$FR_DIENST/umzug-454.units" ] || return 0
  "${VF_UNITS:-$FR_BETRIEB/units.py}" pruefen > /dev/null 2>&1 || return 0
  echo fertig > "$zustand_datei.neu" && mv "$zustand_datei.neu" "$zustand_datei"
  rm -f "$FR_DIENST/umzug-454.units"
  echo "Move (#454) done: this run starts from the software clone, the move is marked as done."
}

altbau_warnen() {  # <schlüssel> <text>: Warnzeile des Aufräumens, einmal je Störung (Merker <FR_DIENST>/altbau-557.warnung)
  local merker="$FR_DIENST/altbau-557.warnung"
  [ "$(cat "$merker" 2>/dev/null || true)" != "$1" ] || return 0
  echo "Warning: old build folder not removed: $2; the next run tries again."
  { mkdir -p "$FR_DIENST" && printf '%s\n' "$1" > "$merker"; } || true
}

altbau_entfernen() {  # #557: alten Bauordner <FR_SEITEN>/_bau und <FR_SEITEN>/_bau-schreiben-* nach einem Archiv entfernen
  # (Ablauf und Bedingungen im Kopf). Rückgabe immer 0: Fehler sind eine Warnzeile (altbau_warnen), nie ein Alarm.
  local merker="$FR_DIENST/altbau-557" bau="$FR_SEITEN/_bau" ziele=() p real seiten_real fremd r frei bedarf
  local units aus rc archiv_ordner archiv tmp liste
  [ ! -e "$merker" ] || return 0
  [ -n "$FR_SEITEN" ] && [ -d "$FR_SEITEN" ] || return 0
  for p in "$bau" "$FR_SEITEN"/_bau-schreiben-*; do
    if [ -e "$p" ] || [ -L "$p" ]; then ziele+=("$p"); fi
  done
  [ "${#ziele[@]}" -gt 0 ] || return 0
  [ "$(cat "$FR_DIENST/umzug-454" 2>/dev/null || true)" = fertig ] || return 0
  # Pfadprüfung vor allem anderen: kein Link, aufgelöst innerhalb von FR_SEITEN, nie FR_SEITEN selbst, der Klon oder der
  # Dienstordner, und nichts davon liegt darin
  seiten_real="$(cd "$FR_SEITEN" && pwd -P)"
  for p in "${ziele[@]}"; do
    real="$(realpath -e "$p" 2>/dev/null || true)"
    if [ -L "$p" ] || [ ! -d "$p" ] || [ -z "$real" ] || [ "$real" != "$seiten_real/$(basename "$p")" ]; then
      altbau_warnen "pfad $p" "$p is a link or not a folder inside $FR_SEITEN"; return 0
    fi
    for fremd in "$FR_WURZEL" "$FR_DIENST" "$FR_SPEICHER" "$FR_SEITEN/_software" "$FR_SEITEN/_dienst"; do
      fremd="$(realpath -m "$fremd" 2>/dev/null || echo "$fremd")"
      case "$fremd/" in "$real"/*)
        altbau_warnen "pfad $p" "$p contains $fremd"; return 0 ;;
      esac
    done
  done
  # Jede Reise aus _bau/reisen steht im Reisespeicher (oder ist gelöscht, vorgemerkte_entfernen)
  fremd=""
  for p in "$bau"/reisen/*/; do
    [ -f "$p/reise.yaml" ] || [ -f "$p/reise.json" ] || continue
    r="$(basename "$p")"
    ist_speicherreise "$r" || ist_vorgemerkt "$r" || fremd="${fremd:+$fremd, }$r"
  done
  if [ -n "$fremd" ]; then
    altbau_warnen "reisen $fremd" "trips not in the trip store: $fremd"; return 0
  fi
  # Keine Unit zeigt mehr auf den alten Bauordner (units.py pruefen: keine Abweichung, die ihn nennt)
  units="${VF_UNITS:-$FR_BETRIEB/units.py}"
  rc=0; aus="$("$units" pruefen 2>&1)" || rc=$?
  if { [ "$rc" != 0 ] && [ "$rc" != 3 ] && [ "$rc" != 4 ]; } || [[ "$aus" == *"$bau"* ]]; then
    altbau_warnen "units $rc" "units still point to $bau or cannot be compared (exit $rc)"; return 0
  fi
  # Archiv von _bau (ohne _bau-schreiben-*) nach <FR_DIENST>/archiv/: erst Platz, dann bauen, lesen und prüfen
  archiv_ordner="$FR_DIENST/archiv"
  if [ -d "$bau" ]; then
    bedarf=$(( $(du -sb "$bau" 2>/dev/null | cut -f1 || echo 0) + 536870912 ))   # unverdichtete Größe plus 512 MiB Reserve
    if [ -n "${VF_PLATZ:-}" ]; then frei="$("$VF_PLATZ" "$FR_DIENST" 2>/dev/null || true)"
    else frei="$(df -PB1 "$FR_DIENST" 2>/dev/null | awk 'NR == 2 {print $4}' || true)"; fi
    if ! [[ "$frei" =~ ^[0-9]+$ ]] || [ "$frei" -lt "$bedarf" ]; then
      altbau_warnen "platz" "not enough free space for the archive (free ${frei:-unknown} bytes, needed $bedarf)"; return 0
    fi
    mkdir -p "$archiv_ordner" 2>/dev/null || { altbau_warnen "archiv" "the archive folder $archiv_ordner cannot be created"; return 0; }
    archiv="$archiv_ordner/bau-$(date -u +%Y%m%dT%H%M%SZ).tar.gz"
    tmp="$archiv.neu"
    rc=0
    if [ -n "${VF_ARCHIV:-}" ]; then "$VF_ARCHIV" "$tmp" "$bau" > /dev/null 2>&1 || rc=$?
    else tar -czf "$tmp" -C "$FR_SEITEN" _bau > /dev/null 2>&1 || rc=$?; fi
    liste="$(tar -tzf "$tmp" 2>/dev/null)" || rc=2
    if [ "$rc" = 0 ]; then
      for p in "$bau"/reisen/*/; do
        [ -f "$p/reise.yaml" ] || [ -f "$p/reise.json" ] || continue
        r="$(basename "$p")"
        grep -qE "(^|/)reisen/$r/reise\.(yaml|json)$" <<< "$liste" || { rc=3; break; }
      done
    fi
    if [ "$rc" != 0 ]; then
      rm -f "$tmp"
      altbau_warnen "archiv" "the archive of $bau could not be built or read (exit $rc)"; return 0
    fi
    mv "$tmp" "$archiv" || { rm -f "$tmp"; altbau_warnen "archiv" "the archive $archiv could not be stored"; return 0; }
    echo "Old build folder archived: $archiv."
  fi
  # Löschen, erst danach der Merker (ein abgebrochenes Löschen versucht der nächste Lauf erneut)
  for p in "${ziele[@]}"; do
    [ ! -L "$p" ] || { altbau_warnen "pfad $p" "$p became a link"; return 0; }
    rm -rf -- "${p:?}" || { altbau_warnen "loeschen" "$p could not be removed completely"; return 0; }
  done
  printf 'entfernt=%s\narchiv=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${archiv:-}" > "$merker.neu" && mv "$merker.neu" "$merker" \
    || { rm -f "$merker.neu"; altbau_warnen "merker" "removed, but the marker $merker could not be written"; return 0; }
  rm -f "$FR_DIENST/altbau-557.warnung"
  echo "Old build folder removed (${#ziele[@]} folders), the archive stays in $archiv_ordner."
  return 0
}

# Alles steckt in main(), damit bash das Skript ganz einliest, bevor das Vorspulen des Klons es eventuell ersetzt.
main() {
  immer=""; start_ordner="$PWD"
  wurzel="$FR_WURZEL"
  stand="${VF_STAND:-$FR_DIENST/veroeffentlicht}"
  deploy="${VF_DEPLOY:-$FR_BETRIEB/deploy.sh}"
  pruefen="${VF_PRUEFEN:-}"
  freischalten="${VF_FREISCHALTEN:-$FR_BETRIEB/freischalten.sh}"
  ausstehend="${VF_AUSSTEHEND:-$FR_KONNEKTOR/neue-reisen-ausstehend.jsonl}"
  rot_datei="${VF_ROT:-$FR_DIENST/veroeffentlichen-rot}"
  warnung="$FR_DIENST/veroeffentlichen-warnung"
  frei_ausstehend="${VF_FREI_AUSSTEHEND:-$FR_DIENST/freischalten-ausstehend}"   # Reisen eines Laufs ohne Root-Rechte (#465)
  neustart_ausstehend="$FR_DIENST/neustart-ausstehend"   # Neustarts eines Laufs ohne Root-Rechte, deploy.sh merkt sie vor (#494)
  [ "${1:-}" = "--immer" ] && immer=1

  # Sperre in FR_DIENST, nicht in FR_SPERREN (bis #552 mit der Vorgabe /tmp): Der Schreibweg startet diesen Lauf aus einem Dienst mit
  # PrivateTmp, sein /tmp ist nicht das des Timers, und die Sperre griff nicht (zwei Läufe gleichzeitig, #211)
  mkdir -p "$FR_DIENST"
  # Anstoß-Merker des Schreibwegs (#624) vor der Sperre entfernen: Die Path-Einheit (PathExists) startet diesen Dienst, solange
  # er liegt; bliebe er liegen, liefe der Dienst ohne Ende. Ein Anstoß nach diesem Punkt legt ihn neu, systemd prüft nach dem
  # Ende des Laufs erneut und startet noch einmal; bei belegter Sperre greift zusätzlich veroeffentlichen-nochmal.
  rm -f "$FR_DIENST/veroeffentlichen-anstoss"
  exec 9>"${VF_SPERRE:-$FR_DIENST/veroeffentlichen.lock}"
  chmod 644 "${VF_SPERRE:-$FR_DIENST/veroeffentlichen.lock}" 2>/dev/null || true   # der Kartendienst liest sie als anderer Benutzer
  if ! flock -n 9; then
    # Der laufende Lauf startet danach noch einmal (nachlauf), damit ein neuer Stand nicht bis zum Timer wartet (#230)
    touch "$FR_DIENST/veroeffentlichen-nochmal"
    echo "Already running, skipped; the running one publishes again afterwards."
    return 0
  fi
  nochmal="$FR_DIENST/veroeffentlichen-nochmal"
  rm -f "$nochmal"

  cd "$wurzel"
  if ! software_klon; then
    echo "ERROR: $FR_WURZEL is not the software clone this script runs from ($FR_BETRIEB); publishing runs only from <FR_SEITEN>/_software (#454, #557)." >&2
    return 1
  fi
  main_klon "$@"
}

speicher_rot_melden() {  # Software grün, Reisen aus dem Speicher rot: Rot-Datei (art=reise), Alarm nach der Schwelle, kein
  # Stempel, kein Heartbeat (#348). Der Server legt kein Issue an (A-2).
  rot_schreiben "$neu" reise "$(rot_vereinigt "$speicher_rote")"
  echo "Red: trips from the trip store not built: $speicher_rote."
  alarm_pruefen
}

# Einheiten abgleichen (#260): Weichen die installierten systemd-Einheiten von den Vorlagen ab, genau eine normale Meldung je
# Abweichung (Fingerabdruck der Ausgabe in <FR_DIENST>/units-gemeldet). Nur melden: kein Alarm, kein Abbruch, ein Fehler hier
# (Ausgang 1) stoppt nichts. Ausgang 0 = alles gleich: der Merker wird gelöscht, eine spätere Abweichung meldet wieder.
units_abgleichen() {
  local aus rc=0 merker="$FR_DIENST/units-gemeldet" fp
  local units="${VF_UNITS:-$FR_BETRIEB/units.py}"
  aus="$("$units" pruefen 2>&1)" || rc=$?
  if [ "$rc" = 3 ]; then
    # Nur erlaubte Abweichungen: über das Hilfsprogramm mit Root-Rechten installieren (ohne es bleibt es bei der Meldung). Was
    # danach noch abweicht, steht in der neuen Prüfung; ein Fehler beim Installieren stoppt nichts.
    local inst
    inst="$("$units" installieren 2>&1)" || true
    rc=0; aus="$("$units" pruefen 2>&1)" || rc=$?
    [ "$rc" = 0 ] || aus="$aus"$'\n'"Install attempt: ${inst:-no output}"
  fi
  case "$rc" in
    0) rm -f "$merker"; return 0 ;;
    3|4) ;;
    *) echo "Warning: unit comparison failed (exit $rc), skipped."; return 0 ;;
  esac
  fp="$(printf '%s' "$aus" | sha256sum | cut -d' ' -f1)"
  echo "Warning: installed units differ from the templates (exit $rc)."
  if [ "$(cat "$merker" 2>/dev/null || true)" != "$fp" ]; then
    if fr_melden normal "Units differ from the templates" "$aus"; then
      { mkdir -p "$(dirname "$merker")" && echo "$fp" > "$merker"; } || true
    fi
  fi
  return 0
}

# nginx-Bausteine abgleichen (#206, #445): Weicht nur die Orte-Datei des Konnektors ab, installiert sie das Hilfsprogramm mit
# Root-Rechten (nginx.py installieren, Grammatik, nginx -t mit Rückweg; ohne Hilfsprogramm bleibt es bei der Meldung). Was danach
# noch abweicht (Konnektor-Baustein, Zonendatei: bewusster Schritt mit nginx.py anwenden, docs/betrieb.md), meldet genau eine
# normale Meldung je Abweichung mit dem Ergebnis des Versuchs (letzte Zeile der Ausgabe von installieren). Der Fingerabdruck
# (<FR_DIENST>/nginx-gemeldet) kommt aus der zweiten Prüfung, nicht aus dem Text des Versuchs. Ist danach alles gleich, aber der
# Versuch endete nicht mit 0 oder 2 (etwa 5: installiert, Neuladen gescheitert), wird das ebenso einmal gemeldet (Fingerabdruck aus
# dem Ausgang). Kein Alarm; ein Fehler hier stoppt nichts.
nginx_abgleichen() {
  local aus rc=0 merker="$FR_DIENST/nginx-gemeldet" fp inst="" irc="" kurz
  local abgleich="${VF_NGINX:-$FR_BETRIEB/nginx.py}"
  aus="$("$abgleich" pruefen 2>&1)" || rc=$?
  if [ "$rc" = 3 ]; then
    irc=0; inst="$("$abgleich" installieren 2>&1)" || irc=$?
    rc=0; aus="$("$abgleich" pruefen 2>&1)" || rc=$?
    if [ "$rc" = 0 ]; then
      case "$irc" in
        0|2) echo "nginx locations of the connector installed from the template." ;;
        *) rc=3; aus="nginx blocks equal the templates, but the install attempt ended with exit $irc (not reloaded or not secured)." ;;
      esac
    fi
  fi
  case "$rc" in
    0) rm -f "$merker"; return 0 ;;
    3) ;;
    *) echo "Warning: nginx comparison failed (exit $rc), skipped."; return 0 ;;
  esac
  fp="$(printf '%s' "$aus" | sha256sum | cut -d' ' -f1)"
  echo "Warning: installed nginx blocks differ from the templates."
  if [ "$(cat "$merker" 2>/dev/null || true)" != "$fp" ]; then
    kurz="$(printf '%s\n' "$inst" | sed '/^[[:space:]]*$/d' | tail -n 1)"
    if fr_melden normal "nginx blocks differ from the templates" "$aus"$'\n'"Install attempt: ${kurz:-no output}"; then
      { mkdir -p "$(dirname "$merker")" && echo "$fp" > "$merker"; } || true
    fi
  fi
  return 0
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

wurzel=""; ausstehend=""; rot_datei=""; pruefen=""; pruef_tmp=""; pruef_log=""; deploy_log=""; nochmal=""
root_ok=""; frei_ausstehend=""; neustart_ausstehend=""; deploy=""; freischalten=""; neu=""
speicher_aktiv=""; speicher_kennung=""; speicher_wartet=""; speicher_gut=""; speicher_rote=""; vorgemerkt_liste=""
software_gepr=""; rote_tests_text=""; python_neu=""; stand=""; warnung=""; immer=""; start_ordner="$PWD"
rot_commit=""; rot_art=""; rot_reisen=""; rot_seit=""; rot_gemeldet=""; rot_umgebung=""; rot_geprueft=""; rot_tests=""
trap nachlauf EXIT
main "$@"
exit
