#!/usr/bin/env bash
# Veröffentlicht automatisch (docs/betrieb.md, Veröffentlichen). Gestartet alle 5 Minuten vom Timer
# <instanz>-veroeffentlichen.timer und gleich nach jedem Schreibvorgang des Schreibwegs (engine/schreiben.py).
# Aufruf von Hand:  FR_WURZEL=<Bauordner> betrieb/veroeffentlichen.sh          (nur wenn es Neues gibt)
#                   FR_WURZEL=<Bauordner> betrieb/veroeffentlichen.sh --immer  (auch ohne neuen Stand, auch
#                   einen bekannten roten). Ohne FR_WURZEL bricht es ab (#137).
#
# Software direkt (#454, neue Anordnung): Der Bauordner ist der Software-Klon <FR_SEITEN>/_software (FR_WURZEL, das Skript
# läuft aus ihm). Ablauf eines Laufs (main_klon): Speicher-Teil mit der bisherigen Software; git fetch origin main im Klon
# (öffentlich, ohne Anmeldung); ein neuer Commit C wird geprüft, bevor der Klon umschaltet: Nachweis der Pflichtprüfungen
# genau dieses Commits auf GitHub (ohne gh, einmal je Stand), sonst Tests auf dem Server in einem eigenen Arbeitsbaum von C
# (git worktree), der Klon bleibt dabei unberührt. Rot: Rot-Datei am Software-Commit, Alarm wie bisher (einmal je Rot-Phase),
# der Klon bleibt auf dem letzten guten Stand. Grün: Python-Umgebung <FR_DIENST>/python (neu bei geänderter
# engine/requirements.txt), Klon vorspulen (ff-only), ändert sich dabei dieses Skript, Neustart mit exec; dann zieht der
# Speicher-Teil jede Reise auf C nach und deploy.sh bringt die Dienste auf C. Scheitert ein Deploy mit C (Exit 1), fällt der
# Klon auf <FR_DIENST>/software-gut zurück und die Dienste werden mit diesem Stand neu gebaut (Rückfall). Erst nach einem ganz
# grünen Lauf: veroeffentlicht = software-gut = C, Units und nginx abgleichen, Heartbeat. Prüfungen der Instanz aus
# <FR_DIENST>/instanz/tests laufen danach, wenn es sie gibt, und sperren nie (Warnung). Ein Reisen-Repo, gh und Workflows
# gibt es in diesem Weg nicht; ein Anstoß von der Seite (_anstoss.json) ist nur dieser Lauf.
# Umzug (#454, alte Anordnung: Reisen-Repo mit Submodul frieda/): Nach jedem grünen Lauf zieht umzug_454 die Instanz in den
# neuen Zustand um, ohne Handschritt und wiederholbar: Klon anlegen (auf dem Commit des Submoduls), Einstellungen, Meldeweg und
# Prüfungen der Instanz nach <FR_DIENST>/instanz/ kopieren (nie über Neueres), Python-Umgebung bauen und den Klon prüfen,
# zuletzt die Units nur prüfen: Der Lauf stellt sie nie selbst um, das macht der Tech Lead einmalig bei der Auslieferung
# (einrichten.sh --installieren aus dem Klon). Bis dahin eine Warnzeile je Commit und der alte Weg. Zeigen die Units auf den
# Klon, <FR_DIENST>/umzug-454 = fertig und Neustart aus dem Klon; startet ein Lauf schon aus dem Klon, setzt er fertig selbst,
# wenn die Units auf den Klon zeigen (eine frische Instanz ohne Umzug bekommt keinen Zustand).
# Scheitert ein Schritt, bleibt alles beim alten Weg (Warnzeile, kein Alarm), der nächste Lauf versucht es wieder. Der alte
# Bauordner bleibt unangetastet (Rückweg, docs/betrieb.md „Umzug“).
#
# Alte Anordnung (bis zum Umzug, Beschreibung unten): holt origin/main in den Bauordner, bringt die Software (Submodul) auf
# den festgehaltenen Stand und ruft deploy.sh für jede Reise auf, sobald main einen neuen Stand hat.
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
# Alle Reisen im Speicher (#454, Lieferung 1): Im Speicher ist, was im Speicher steht (speicherreisen in gemeinsam.sh). Vor
# dem Speicher-Teil schaltet der Lauf jede übrige Reise aus reisen/ des Bauordners selbst um (reisespeicher.py umschalten:
# Anfangsvorgang aus dem Git-Stand, Vergleich, Stempel „gleich“), nur wenn eine Datenbank des Speichers schon da ist; ist sie
# nicht gleich, bleibt sie in Git, mit einer Warnzeile und ohne Meldung.
# Umschaltung (Stufe 5, #350, docs/betrieb.md „Umschaltung einer Reise“): Eine Reise im Speicher, die in Git
# liegt und noch nie aus dem Speicher veröffentlicht wurde (kein <FR_DIENST>/reise-stand/<reise>.gebaut), baut der
# Speicher-Teil nur mit gültigem Stempel „gleich“ von betrieb/vergleichslauf.sh (reisespeicher.py umschaltung); sonst
# überspringt er sie mit einem Hinweis im Protokoll, der Lauf bleibt grün.
# Ohne GitHub (Stufe 5): Scheitert git fetch bei einer Instanz mit Reisen im Speicher, ist das kein Fehler des Laufs. Die
# Reisen aus dem Speicher sind dann schon veröffentlicht; Software und Git-Reisen warten. Exit 1 nur bei roten Reisen aus
# dem Speicher; Stempel und Heartbeat nur, wenn keine Reise mehr in Git liegt. Merker <FR_DIENST>/software-wartet (seit,
# gemeldet); nach FR_SOFTWARE_WARTET_STUNDEN (Vorgabe 6) genau eine Warnzeile je Störung, keine Nachricht an den Betrieb.
# Gelingt git fetch wieder, wird der Merker gelöscht. Ohne Reisen im Speicher endet ein gescheitertes git fetch wie bisher
# mit Fehler.
# Für Tests überschreibbar: VF_PRUEFEN, VF_STAND, VF_DEPLOY, VF_FREISCHALTEN, VF_AUSSTEHEND, VF_SPERRE, VF_STEMPEL, VF_HEARTBEAT,
# VF_ROT (Rot-Datei), VF_JETZT (Uhr, Sekunden seit 1970), VF_ROTMELDEN (statt engine/waechter.py rot-melden),
# VF_NACHZIEHEN (Befehl statt gh workflow run), VF_LSREMOTE (Befehl statt git ls-remote), VF_CINACHWEIS (Nachweis der
# Pflichtprüfungen: <url> <commit>, gibt „true“ aus), VF_VENV (<ordner> <requirements>: baut die Python-Umgebung),
# VF_UNITS (Abgleich der Units).
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

# Root-Rechte (#465): Der Schreibweg stößt diesen Lauf aus einem Dienst mit NoNewPrivileges an, darin geht kein sudo.
# Freischalten (nginx-Bausteine) und Zustellen neuer Reisen brauchen es; ohne warten sie auf den nächsten Lauf des Timers.
# Geprüft wird erst, wenn es etwas freizuschalten gibt (sudo schreibt jeden Aufruf ins Journal), einmal je Lauf.
root_geht() {
  if [ -z "$root_ok" ]; then
    if ${FR_SUDO-sudo -n} true 2>/dev/null; then root_ok=1; else root_ok=0; fi
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

einstellungen_summe() {  # <datei>: Prüfsumme, leer ohne lesbare Datei wie in fr_einlesen (Erscheinen und Verschwinden
  # zählen als Änderung, #242)
  [ ! -r "$1" ] || sha256sum < "$1" | cut -d' ' -f1
}

iso() { [[ "${1:-}" =~ ^[0-9]+$ ]] && date -u -d "@$1" +%Y-%m-%dT%H:%M:%SZ || true; }

reise_stand_schreiben() {  # <reise> <zustand> [grund]: Zustand des Reise-Stands für api/stand und publish_status
  # (engine/stand.py). nummer wie dort: Commits, die reisen/<reise>/ ändern; im flachen Klon keine. Dauer bei „veroeffentlicht“:
  # Sekunden seit dem Sichern (Zeit des Schreibwegs, sonst des Commits); steht auch im Protokoll (Messung des Zeitziels).
  # Reise aus dem Reisespeicher (#348): nummer ist die Stand-Nummer des materialisierten Inhalts (<ordner>.stand), die Zeit
  # des Sicherns kommt nur vom Schreibweg.
  local r="$1" z="$2" g="${3:-}" n c="" t dauer=null datei gz gn seite
  if ist_speicherreise "$r"; then
    n="$(cat "$FR_DIENST/bau/reisen/$r.stand" 2>/dev/null || true)"
  else
    [ "$(git rev-parse --is-shallow-repository 2>/dev/null)" = false ] || return 0
    n="$(git rev-list --count HEAD -- "reisen/$r" 2>/dev/null)" || return 0
    c="$(git log -1 --format=%ct -- "reisen/$r" 2>/dev/null || true)"
  fi
  [[ "$n" =~ ^[0-9]+$ ]] && [ "$n" -gt 0 ] || return 0
  datei="$FR_DIENST/reise-stand/$r.gesichert.json"
  gn="$(sed -n 's/.*"nummer": *\([0-9]*\).*/\1/p' "$datei" 2>/dev/null || true)"
  gz="$(sed -n 's/.*"zeit": *"\([^"]*\)".*/\1/p' "$datei" 2>/dev/null || true)"
  if [ "$gn" = "$n" ] && [ -n "$gz" ] && gz="$(date -u -d "$gz" +%s 2>/dev/null)"; then c="$gz"; fi
  t="$(jetzt)"
  # Stand, der schon auf der Seite war (<reise>.seite, nach jeder Veröffentlichung): Ein Neubau desselben Stands (--immer,
  # Software-Wechsel, Umschaltung auf den Speicher) hat keine Wartezeit und wird nicht gemessen (#465)
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

haengende_reisen() {  # Reisen, die nach einem abgebrochenen Lauf auf „baut“ stehen geblieben sind (#397). Die Sperre hält dieser
  # Lauf, es baut also keiner mehr: Sie gehören in diesen Lauf, sonst zeigte publish_status „wird gebaut“ bis zum nächsten
  # Software-Wechsel. Nur Git-Reisen, die es gibt (Reisen aus dem Speicher baut der Speicher-Teil).
  local f r
  { grep -l '"zustand": "baut"' "$FR_DIENST"/reise-stand/*.lauf.json 2>/dev/null || true; } | while read -r f; do
    r="$(basename "$f" .lauf.json)"
    if [ -e "reisen/$r/reise.json" ] && ! ist_speicherreise "$r"; then echo "$r"; fi
  done
  return 0
}

reisen_des_laufs() {  # <alt> <neu>: Reisen, die dieser Lauf baut, eine je Zeile. Ohne bekannten alten Stand, mit --immer oder
  # bei einem Software-Wechsel alle; sonst die, deren Ordner sich seit dem zuletzt veröffentlichten Stand geändert hat, und
  # die zuletzt roten (sie bleiben rot gemeldet, bis ihr Bau gelingt). Reisen aus dem Reisespeicher baut der Speicher-Teil;
  # ihre Git-Kopie bleibt bis Stufe 5 liegen und wird nie gebaut (#348).
  local r
  if [ -n "$software" ]; then
    for r in reisen/*/reise.json; do
      [ -e "$r" ] || continue
      r="$(basename "$(dirname "$r")")"
      ist_speicherreise "$r" || ist_vorgemerkt "$r" || echo "$r"
    done
    return 0
  fi
  { git diff --name-only "$1" "$2" -- reisen | cut -d/ -f2
    [ "$rot_art" != reise ] || printf '%s\n' ${rot_reisen//,/ }
    haengende_reisen
  } | sort -u | while read -r r; do
    if [ -n "$r" ] && [ -e "reisen/$r/reise.json" ] && ! ist_speicherreise "$r" && ! ist_vorgemerkt "$r"; then echo "$r"; fi
  done
  return 0
}

software_kennung() {  # [<commit>]: Stand der Software eines Commits im Bauordner: das Submodul frieda/, ohne Submodul (Tests)
  # der Commit selbst. Beschreibt, mit welcher Software eine Reise aus dem Reisespeicher gebaut wurde (#348).
  local c="${1:-HEAD}"
  git rev-parse -q --verify "$c:frieda" 2>/dev/null || git rev-parse -q --verify "$c^{commit}" 2>/dev/null || true
}

rot_vereinigt() {  # <reisen…>: Liste der roten Reisen für die Rot-Datei, Git-Reisen und Reisen aus dem Speicher zusammen
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

ist_vorgemerkt() {  # <reise>: steht sie in der Liste aus vorgemerkte_entfernen?
  [[ " $(echo $vorgemerkt_liste) " == *" $1 "* ]]
}

speicher_reisen_lauf() {  # Speicher-Teil (Stufe 3, #348): Reisen im Speicher (#454: was dort steht) bauen, vor
  # git fetch und ohne Netz (kein git fetch, kein gh, kein ls-remote). Eine Reise ohne Stempel .gebaut, die in Git liegt, wird
  # ohne gültigen Stempel des Vergleichslaufs übersprungen (Stufe 5, #350, reisespeicher.py umschaltung; Hinweis im
  # Protokoll, kein Rot). Gebaut wird eine Reise, wenn ihre Stand-Nummer im
  # Speicher nicht die der Seite ist, mit --immer, ohne Stempel <FR_DIENST>/reise-stand/<reise>.gebaut („<nummer>
  # <software-kennung>“, nur nach gelungenem Deploy) oder nach einem Software-Wechsel; dann stellt neu.py
  # nachziehen-speicher sie vorher um (ein Vorgang, nur bei grünem Probebau). Eine neue Software-Kennung gilt erst, wenn der
  # Git-Teil sie vollständig veröffentlicht hat (Datei veroeffentlicht); bis dahin bleibt jede Reise mit älterem Stempel
  # stehen. Ergebnis: speicher_gut, speicher_rote; Exit 1 bei einer Störung (Speicher nicht lesbar, deploy Exit 1).
  local liste r n pub gn gk modus rc ordner aus kennung geprueft="" vorher log gepr_stand="" aus_pruefung
  liste="$(speicherreisen | while read -r r; do ist_vorgemerkt "$r" || echo "$r"; done | tr '\n' ' ')"
  [ -n "${liste// /}" ] || return 0
  speicher_aktiv=1
  kennung="$(software_kennung HEAD)"
  speicher_kennung="$kennung"
  vorher="$(cat "$stand" 2>/dev/null || true)"
  if [ -n "$vorher" ] && [ -n "$kennung" ] && [ "$(software_kennung "$vorher")" = "$kennung" ]; then
    geprueft=1; gepr_stand="$(git rev-parse HEAD)"   # deploy.sh prüft dann nicht selbst (wie FR_GEPRUEFT im Git-Teil)
  elif [ -n "$software_gepr" ] && [ "$software_gepr" = "$kennung" ]; then
    geprueft=1; gepr_stand="$(git rev-parse HEAD)"   # Software-Klon (#454): dieser Lauf hat den Commit eben geprüft
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
    # Sperre bei der ersten Umschaltung (Stufe 5, #350): ohne Stempel .gebaut entscheidet reisespeicher.py umschaltung
    if [ ! -e "$FR_DIENST/reise-stand/$r.gebaut" ]; then
      rc=0
      aus_pruefung="$("$FR_PYTHON" "$FR_BETRIEB/../engine/reisespeicher.py" umschaltung "$r" 2>&1 < /dev/null)" || rc=$?
      if [ "$rc" = 1 ] && [[ "$aus_pruefung" =~ ^gesperrt\ ([a-z_]+)$ ]]; then
        echo "Note: $r is in git and not cleared for the switch (${BASH_REMATCH[1]}), it stays at its last state."
        continue
      elif [ "$rc" != 0 ]; then
        echo "ERROR: the switch check of $r failed ($(printf '%s\n' "$aus_pruefung" | tail -1)), the next run tries again."
        rm -f "$log"; return 1
      fi
    fi
    gn=""; gk=""
    if [ -r "$FR_DIENST/reise-stand/$r.gebaut" ]; then read -r gn gk < "$FR_DIENST/reise-stand/$r.gebaut" || true; fi
    if [ -n "$gk" ] && [ "$gk" != "$kennung" ]; then
      if [ -z "$geprueft" ]; then
        echo "Note: software ${kennung:0:7} is not published yet (checks of the git part), $r waits at its last good state."
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
  # Freischalten wie bei Git-Reisen (Ausgabe ohne Links), die Wege zum Konnektor einmal danach
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

ci_nachweis() {  # 0, wenn die Pflichtprüfungen der eingebundenen Software-Version auf GitHub grün sind (#403)
  # main der Software ist geschützt: Ein Stand kommt nur dorthin, wenn genau sein Commit tests (leer), tests (instanz) und
  # gitleaks grün hat. Dieser Nachweis ersetzt die zweite Testrunde auf dem Server (10 bis 15 Minuten, in denen alle Reisen
  # warten). Ohne Nachweis (kein Submodul, kein Netz, nicht grün) oder mit FR_CI_NACHWEIS=0 laufen die Tests wie bisher.
  [ "${FR_CI_NACHWEIS:-1}" = 1 ] || return 1
  local url sha repo ok
  url="$(git config --file .gitmodules submodule.frieda.url 2>/dev/null)" || return 1
  sha="$(git rev-parse -q --verify HEAD:frieda 2>/dev/null)" || return 1
  if [ -n "${VF_CINACHWEIS:-}" ]; then ok="$("$VF_CINACHWEIS" "$url" "$sha" 2>/dev/null)" || return 1
  else
    repo="$(printf '%s' "$url" | sed -E 's#^(https://github\.com/|git@github\.com:)##; s#\.git$##')"
    [[ "$repo" =~ ^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$ ]] || return 1
    ok="$(timeout 30 gh api "repos/$repo/commits/$sha/check-runs?per_page=100" --jq '[.check_runs[] | select(.conclusion == "success") | .name] as $g | (["tests (leer)", "tests (instanz)", "gitleaks"] | all(. as $n | $g | index($n) != null))' 2>/dev/null)" || return 1; fi
  [ "$ok" = true ] || return 1
  CI_STAND="${sha:0:7}"
}

pruefen_lauf() {  # <ordner>: pytest über engine/tests oder tests/ des Reisen-Repos; Ausgabe auch nach pruef_log
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

git_reisen_uebrig() {  # Reisen, die noch in Git liegen (reisen/<name>/reise.json im Commit HEAD) und nicht in
  # im Speicher stehen, eine je Zeile (Stufe 5, #350)
  local r
  { git ls-tree --name-only HEAD reisen/ 2>/dev/null || true; } | while IFS= read -r r; do
    r="${r#reisen/}"
    git cat-file -e "HEAD:reisen/$r/reise.json" 2>/dev/null || continue
    ist_speicherreise "$r" || echo "$r"
  done
  return 0
}

software_wartet_merken() {  # git fetch gescheitert (Stufe 5, #350): Merker <FR_DIENST>/software-wartet (seit, gemeldet).
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
  abhaengigkeiten_playwright
}

abhaengigkeiten_playwright() {
  # Playwright: eigene Kopie in <FR_DIENST>/playwright nach engine/tests/playwright/package-lock.json, nie ein
  # Ordner, den andere mitbenutzen. Browser ohne --with-deps (kein sudo); Systembibliotheken richtet einrichten.sh ein.
  # Ohne npm (Instanz ohne Browsertests) bleibt alles, wie es ist. Im Software-Klon (#454) nur vor Tests auf dem Server.
  local summe pw_quelle=engine/tests/playwright pw_ziel="$FR_DIENST/playwright" npm="${VF_NPM:-npm}"
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

git_reisen_umschalten() {  # Lieferung 1 (#454): jede Reise unter reisen/ des Bauordners, die nicht im Speicher steht, auf den
  # Speicher umschalten (engine/reisespeicher.py umschalten). Nur mit vorhandener Datenbank des Speichers (eine Instanz ohne
  # Speicher bleibt beim Git-Weg). „gleich“: ab jetzt Speicherreise. Unterschied oder Fehler: die Reise bleibt in Git, eine
  # Warnzeile mit Grund, keine Meldung (kein Ausfall, #446). Es wird nie gelöscht.
  # Ob es die Datenbank gibt, entscheidet engine/reisespeicher.py (datenbank: Exit 0 ja, 1 nein, 2 nicht lesbar): ein nicht
  # durchsuchbarer Speicher ist ein Fehler des Laufs (Exit 1), nie „keine Datenbank“ (#361, #454 F001).
  local r rc aus geschaltet=""
  fr_speicher_fehlt && return 0
  rc=0; aus="$("$FR_PYTHON" "$FR_BETRIEB/../engine/reisespeicher.py" datenbank 2>&1 < /dev/null)" || rc=$?
  case "$rc" in
    0) ;;
    1) return 0 ;;
    *) echo "ERROR: the trip store cannot be read ($(printf '%s\n' "$aus" | tail -1)), the next run tries again."; return 1 ;;
  esac
  for r in reisen/*/reise.json; do
    [ -e "$r" ] || continue
    r="$(basename "$(dirname "$r")")"
    ist_speicherreise "$r" && continue
    ist_vorgemerkt "$r" && continue
    rc=0; aus="$("$FR_PYTHON" "$FR_BETRIEB/../engine/reisespeicher.py" umschalten "$r" 2>&1 < /dev/null)" || rc=$?
    case "$rc" in
      0) echo "$r switched to the trip store ($(printf '%s\n' "$aus" | tail -1))."; geschaltet=1 ;;
      1) echo "Warning: $r stays in git: it differs from the trip store (betrieb/vergleichslauf.sh $r lists the differences)." ;;
      3) ;;
      *) echo "Warning: $r stays in git: switch to the trip store failed ($(printf '%s\n' "$aus" | tail -1))." ;;
    esac
  done
  [ -z "$geschaltet" ] || speicherreisen_lesen || return 1
}

software_klon() {  # läuft das Skript aus dem Software-Klon, der zugleich der Bauordner ist (neue Anordnung, #454)?
  ! fr_alte_anordnung && [ "$(cd "$FR_BETRIEB/.." && pwd -P)" = "$(cd "$FR_WURZEL" && pwd -P)" ]
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

main_klon() {  # ein Lauf in der neuen Anordnung (#454), Ablauf im Kopf
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
  speicherreisen_lesen || return 1
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
  rc=0; FR_GEPRUEFT="$kopf" "$deploy" --dienste 2>&1 | sed 's/^/  /' || rc=${PIPESTATUS[0]}
  unset FR_BIBLIOTHEKEN_NEU   # Dienste mit FR_PYTHON nur beim ersten Deploy neu starten
  if [ "$rc" != 0 ]; then
    rot_schreiben "$kopf" software "" "deploy of the services failed (exit $rc)"
    rueckfall "deploy of the services with software ${kopf:0:7} failed (exit $rc)"
    alarm_pruefen
    return 1
  fi
  if ! speicher_reisen_lauf; then
    # Speicher kurz nicht lesbar, Umschaltprüfung oder Deploy einer Reise gescheitert: kein Rückfall (die Dienste laufen
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

umzug_kopieren() {  # <quelle> <ziel>: Datei kopieren, wenn das Ziel fehlt oder älter ist; nie über Neueres (#454)
  [ -e "$1" ] || return 0
  if [ ! -e "$2" ] || [ "$1" -nt "$2" ]; then
    mkdir -p "$(dirname "$2")"
    cp -p "$1" "$2.neu" && mv "$2.neu" "$2"
    echo "Move (#454): $(basename "$1") copied to $(dirname "$2")."
  fi
}

umzug_454() {  # Umzug einer Instanz der alten Anordnung in den Software-Klon (#454, docs/betrieb.md „Umzug“); nur nach einem
  # grünen Lauf. Jeder Schritt ist wiederholbar; Units erst, wenn 1 bis 3 grün sind (nur prüfen). Fehler: Warnzeile, kein Alarm.
  # Schritte 1 und 3 (Klon, Python-Umgebung, Prüfung) laufen je Software-Commit einmal: Sind sie für diesen Commit grün,
  # steht er in <FR_DIENST>/umzug-454.geprueft, und die folgenden Läufe gehen gleich zu Schritt 4 (F004). Schritt 2 (Kopieren,
  # nie über Neueres) läuft jedes Mal, er kostet nichts und nimmt eine inzwischen geänderte Einstellung mit.
  local zustand_datei="$FR_DIENST/umzug-454" klon="$FR_SEITEN/_software" url sub aus rc py zustand geprueft_datei units_merker
  local fingerabdruck
  geprueft_datei="$FR_DIENST/umzug-454.geprueft"; units_merker="$FR_DIENST/umzug-454.units"
  zustand="$(cat "$zustand_datei" 2>/dev/null || true)"
  [ "$zustand" != fertig ] && [ "$zustand" != alt ] || return 0   # fertig, oder Rückweg gewählt: kein neuer Umzug
  url="$(git config --file .gitmodules submodule.frieda.url 2>/dev/null)" || return 0
  sub="$(git rev-parse -q --verify HEAD:frieda 2>/dev/null)" || return 0
  py="$FR_DIENST/python/bin/python"
  if [ "$(cat "$geprueft_datei" 2>/dev/null || true)" = "$sub" ] && [ -d "$klon/.git" ] \
     && [ "$(git -C "$klon" rev-parse HEAD 2>/dev/null)" = "$sub" ]; then
    umzug_kopieren_alle
  else
    umzug_vorbereiten || return 0
  fi
  umzug_units
}

umzug_vorbereiten() {  # Schritte 1 bis 3 des Umzugs für den Commit sub (Variablen von umzug_454); Exit 1: nicht grün
  # 1. Software-Klon (öffentlich, ohne Anmeldung, nur main), auf dem Commit, mit dem dieser Lauf grün war
  if [ ! -d "$klon/.git" ]; then
    echo "Move (#454): cloning the software to $klon."
    rm -rf "${klon:?}.neu"
    if ! git clone -q --branch main --single-branch "$url" "$klon.neu" > /dev/null 2>&1 || ! mv "$klon.neu" "$klon"; then
      rm -rf "${klon:?}.neu"
      echo "Warning: move (#454): software clone failed, publishing stays on the old way, the next run tries again."; return 1
    fi
  fi
  git -C "$klon" fetch -q origin main 2>/dev/null || echo "Warning: move (#454): fetch in the software clone failed."
  if [ "$(git -C "$klon" rev-parse HEAD)" != "$sub" ]; then
    if ! git -C "$klon" merge-base --is-ancestor "$sub" origin/main 2>/dev/null; then
      echo "Warning: move (#454): commit ${sub:0:7} of the submodule is not on main of the software, the next run tries again."; return 1
    fi
    git -C "$klon" reset -q --hard "$sub"
  fi
  # 2. Einstellungen, Meldeweg und Prüfungen der Instanz nach <FR_DIENST>/instanz/ (nie über Neueres)
  umzug_kopieren_alle
  # 3. Python-Umgebung unter <FR_DIENST>/python, geprüft mit dem Klon (Nachweis oder Tests im Klon)
  if ! ( cd "$klon" && FR_PYTHON="$py" && python_umgebung "$sub" ); then
    echo "Warning: move (#454): the Python environment $FR_DIENST/python cannot be built; publishing stays on the old way, the next run tries again."
    return 1
  fi
  rc=0; ( cd "$klon" && FR_PYTHON="$py" && software_pruefen "$sub" ) || rc=$?
  if [ "$rc" != 0 ]; then
    echo "Warning: move (#454): checks of the software clone red or not possible; publishing stays on the old way, the next run tries again."
    return 1
  fi
  echo "$sub" > "$geprueft_datei.neu" && mv "$geprueft_datei.neu" "$geprueft_datei"
}

umzug_kopieren_alle() {  # Schritt 2 des Umzugs: Einstellungen, Meldeweg und Prüfungen der Instanz nach <FR_DIENST>/instanz/
  mkdir -p "$FR_DIENST/instanz"
  umzug_kopieren "$wurzel/betrieb/einstellungen.env" "$FR_DIENST/instanz/einstellungen.env"
  umzug_kopieren "$wurzel/betrieb/melden.sh" "$FR_DIENST/instanz/melden.sh"
  if [ -d "$wurzel/tests" ] && [ ! -e "$FR_DIENST/instanz/tests" ]; then
    cp -a "$wurzel/tests" "$FR_DIENST/instanz/tests.neu" && mv "$FR_DIENST/instanz/tests.neu" "$FR_DIENST/instanz/tests"
  fi
}

umzug_units() {  # Schritte 4 und 5 des Umzugs (Variablen von umzug_454)
  # 4. Zuletzt: Units auf den Klon. Der Lauf stellt sie nie selbst um: ExecStart und FR_WURZEL stehen nicht in der
  # Erlaubnisliste des Root-Hilfsprogramms; der Tech Lead stellt sie einmalig bei der Auslieferung um (einrichten.sh
  # --installieren aus dem Klon, docs/betrieb.md „Umzug“). Hier nur prüfen: weichen sie ab, Warnzeile und alter Weg.
  local units="${VF_UNITS:-$FR_BETRIEB/units.py}"
  rc=0; aus="$(FR_WURZEL="$klon" FR_PYTHON="$py" "$units" pruefen 2>&1)" || rc=$?
  if [ "$rc" != 0 ]; then
    # Warnzeile einmal je Commit und Befund (Fingerabdruck der Ausgabe), nicht in jedem Takt (F004)
    fingerabdruck="$sub $rc $(printf '%s\n' "$aus" | sha256sum | cut -c1-16)"
    if [ "$(cat "$units_merker" 2>/dev/null || true)" != "$fingerabdruck" ]; then
      echo "Warning: move (#454): the units cannot be switched to $klon (exit $rc: $(printf '%s\n' "$aus" | tail -1)); publishing stays on the old way, the next run tries again."
      echo "$fingerabdruck" > "$units_merker.neu" && mv "$units_merker.neu" "$units_merker"
    else
      echo "Move (#454): units still differ from the software clone (reported before), publishing stays on the old way."
    fi
    return 0
  fi
  rm -f "$units_merker"
  # 5. fertig; der Rest dieses Laufs kommt aus dem Klon
  echo fertig > "$zustand_datei.neu" && mv "$zustand_datei.neu" "$zustand_datei"
  echo "Move (#454) done: the instance builds from the software clone $klon; the old build folder stays untouched (way back: docs/betrieb.md)."
  umzug_neustart
}

umzug_fertig_im_klon() {  # Schritt 5 des Umzugs für einen Lauf, der schon aus dem Klon startet (Units bei der Auslieferung
  # umgestellt): Zustand selbst auf fertig, falls er es noch nicht ist, aber nur wenn die Units wirklich auf den Klon zeigen
  # (units.py pruefen ohne Abweichung; FR_WURZEL ist hier der Klon). Beim Rückweg (alt) bleibt er. Eine frische Instanz ohne
  # Spur eines Umzugs (umzug-454, .geprueft, .units) bekommt keinen Zustand. Weichen die Units ab: stumm, nichts geschrieben.
  local zustand_datei="$FR_DIENST/umzug-454" zustand
  zustand="$(cat "$zustand_datei" 2>/dev/null || true)"
  [ "$zustand" != fertig ] && [ "$zustand" != alt ] || return 0
  [ -e "$zustand_datei" ] || [ -e "$FR_DIENST/umzug-454.geprueft" ] || [ -e "$FR_DIENST/umzug-454.units" ] || return 0
  "${VF_UNITS:-$FR_BETRIEB/units.py}" pruefen > /dev/null 2>&1 || return 0
  echo fertig > "$zustand_datei.neu" && mv "$zustand_datei.neu" "$zustand_datei"
  rm -f "$FR_DIENST/umzug-454.units"
  echo "Move (#454) done: this run starts from the software clone, the move is marked as done."
}

umzug_neustart() {  # Umzug fertig: den Lauf aus dem Klon fortsetzen (exec, FR_WURZEL = Klon, Python unter FR_DIENST, außer
  # der Aufruf nannte FR_PYTHON selbst)
  local klon="$FR_SEITEN/_software" py=""
  [ -x "$klon/betrieb/veroeffentlichen.sh" ] || return 0
  case "$_aufruf_namen" in *" FR_PYTHON "*) py="$FR_PYTHON" ;; esac
  fr_aufraeumen
  unset _neugestartet
  cd "$klon"
  if [ -n "$py" ]; then FR_WURZEL="$klon" FR_PYTHON="$py" exec "$klon/betrieb/veroeffentlichen.sh"; fi
  FR_WURZEL="$klon" exec "$klon/betrieb/veroeffentlichen.sh"
}

# Alles steckt in main(), damit bash das Skript ganz einliest, bevor git es mit dem Submodul eventuell ersetzt.
main() {
  local deploy alt neu reise freischalten aus rc gut="" rote="" grund laufreisen
  local einstellungen="$fr_einstellungen_datei" einstellungen_vorher
  immer=""; start_ordner="$PWD"
  case "$einstellungen" in /*) ;; *) einstellungen="$PWD/$einstellungen" ;; esac   # wie gemeinsam.sh sie las, vor dem cd
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
  if software_klon; then main_klon "$@"; return; fi
  # Alte Anordnung: Ist der Umzug fertig (#454), läuft der Lauf aus dem Klon (die Units zeigen dann schon dorthin)
  if [ "$(cat "$FR_DIENST/umzug-454" 2>/dev/null || true)" = fertig ] && [ -x "$FR_SEITEN/_software/betrieb/veroeffentlichen.sh" ]; then
    echo "Move (#454) is done, continuing from the software clone."
    umzug_neustart
  fi
  anstoss_weitergeben
  if [ "$(git rev-parse --abbrev-ref HEAD)" != main ]; then
    echo "Build folder is not on main ($(git rev-parse --abbrev-ref HEAD)), skipped."; return 0
  fi
  if ! git diff --quiet HEAD || [ -n "$(git ls-files --others --exclude-standard)" ]; then
    echo "Uncommitted changes in the build folder, skipped."; return 0
  fi

  mkdir -p "$FR_DIENST"   # Zustand des Veröffentlichens (Stand, Rot-Datei, Merker der Warnung, Stempel)
  # Reisen aus dem Reisespeicher zuerst und ohne Netz (#348): Scheitert git fetch (kein GitHub), sind sie schon veröffentlicht.
  # Ohne Reisen im Speicher geschieht hier nichts. Vorher verschwinden die Seiten gelöschter Reisen (#381).
  vorgemerkte_entfernen || return 1
  speicherreisen_lesen || return 1   # im Speicher ist, was im Speicher steht (#454)
  git_reisen_umschalten || return 1  # übrige Git-Reisen auf den Speicher umschalten (#454, Lieferung 1)
  speicher_reisen_lauf || return 1
  ausstehende_neustarts      # vorgemerkt von deploy.sh in einem Lauf ohne Root-Rechte (#494)
  ausstehende_freischalten   # vorgemerkt von einem Lauf ohne Root-Rechte (#465); vor dem Abruf von GitHub, gilt also auch ohne Netz
  einstellungen_vorher="$(einstellungen_summe "$einstellungen")"
  if ! git fetch -q origin main; then
    # Stufe 5 (#350): Ohne GitHub sind die Reisen aus dem Speicher schon veröffentlicht; nur Software und Git-Reisen warten.
    # Ohne Reisen im Speicher ein Fehler wie bisher.
    [ -n "$speicher_aktiv" ] || return 1
    echo "Warning: git fetch failed (no network or GitHub down), software update and trips still in git wait."
    software_wartet_merken
    zustellen
    if [ -n "$speicher_rote" ]; then neu="$(git rev-parse HEAD)"; speicher_rot_melden; return 1; fi
    laufreisen="$(git_reisen_uebrig)"
    if [ -n "$laufreisen" ]; then
      echo "Note: trips still in git ($(echo $laufreisen)) stay at their state; no success stamp without GitHub."
      return 0
    fi
    erfolg_melden
    return 0
  fi
  software_wartet_loeschen
  software_anstossen || true
  neu="$(git rev-parse origin/main)"
  alt="$(cat "$stand" 2>/dev/null || true)"
  if [ -z "$immer" ] && [ "$neu" = "$alt" ] && [ -z "$(haengende_reisen)" ]; then
    zustellen
    if [ -n "$speicher_rote" ]; then speicher_rot_melden; return 1; fi
    rm -f "$rot_datei"; erfolg_melden; umzug_454; return 0
  fi

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
      if [ -n "$speicher_aktiv" ] && [ "$rot_art" = reise ]; then
        # Die Reisen aus dem Speicher wurden eben neu gebaut: ihr Ergebnis gilt statt des gemerkten
        local rot_neu
        rot_neu="$(rot_vereinigt "$(printf '%s\n' ${rot_reisen//,/ } | while read -r r; do ist_speicherreise "$r" || echo "$r"; done)" "$speicher_rote")"
        [ "$rot_neu" = "$rot_reisen" ] || rot_schreiben "$rot_commit" reise "$rot_neu" "$rot_tests"
      fi
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
    if ci_nachweis; then
      echo "Software ${CI_STAND}: required checks green on GitHub (same commit), server tests skipped (#403)."
    elif ! pruefen_lauf engine/tests; then
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
    # Offline-Grundkarte der automatischen Karte (Epic #225, #239): nur wenn sich ihr Rahmen geändert hat; ohne Netz baut die
    # Reise trotzdem (die Karte bleibt schematisch oder beim alten Stand)
    if [ "${FR_GRUNDKARTE_AUTO:-1}" = 1 ] && [ -x "${FR_PYTHON:-}" ]; then
      "$FR_PYTHON" "${VF_GRUNDKARTE:-$FR_BETRIEB/../werkzeuge/grundkarte_auto.py}" "$reise" || echo "Warning: base map of $reise not fetched, built without the new one."
    fi
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
  # shellcheck disable=SC2086
  freischalten_reisen $gut
  [ -z "$gut" ] || wege_pruefen
  if [ -n "$rote" ]; then
    # Teil-Erfolg ist kein fachlicher Erfolg: Stand nicht merken, kein Stempel, kein Heartbeat. Die Rot-Datei nennt die roten
    # Reisen beider Quellen (#348).
    rote="$(rot_vereinigt "$rote" "$speicher_rote")"
    rot_schreiben "$neu" reise "$rote"
    zustellen
    echo "Red: $(git log -1 --format='%h') partly online, not built: $rote."
    alarm_pruefen
    return 1
  fi
  [ -n "$speicher_rote" ] || rm -f "$rot_datei"
  units_abgleichen
  nginx_abgleichen
  mkdir -p "$(dirname "$stand")"
  echo "$neu" > "$stand"
  # Software-Wechsel (#348): Die Reisen aus dem Speicher übernehmen die Software erst jetzt, da sie geprüft und veröffentlicht
  # ist; der Nachlauf startet den Speicher-Teil gleich noch einmal, statt bis zum nächsten Takt zu warten.
  if [ -n "$speicher_aktiv" ] && { [ -n "$speicher_wartet" ] || [ "$(software_kennung HEAD)" != "$speicher_kennung" ]; }; then
    echo "Software changed, trips from the trip store follow in a second run."
    touch "$nochmal"
  fi
  zustellen
  if [ -n "$speicher_rote" ]; then speicher_rot_melden; return 1; fi
  echo "Done: $(git log -1 --format='%h') is online."
  erfolg_melden
  umzug_454
}

speicher_rot_melden() {  # Git-Teil grün, Reisen aus dem Speicher rot: Rot-Datei (art=reise), Alarm nach der Schwelle, kein
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

wurzel=""; ausstehend=""; rot_datei=""; pruefen=""; pruef_tmp=""; pruef_log=""; deploy_log=""; nochmal=""; software=1
root_ok=""; frei_ausstehend=""; neustart_ausstehend=""
speicher_aktiv=""; speicher_kennung=""; speicher_wartet=""; speicher_gut=""; speicher_rote=""; vorgemerkt_liste=""
software_gepr=""; rote_tests_text=""; python_neu=""; stand=""; warnung=""; immer=""; start_ordner="$PWD"
rot_commit=""; rot_art=""; rot_reisen=""; rot_seit=""; rot_gemeldet=""; rot_umgebung=""; rot_geprueft=""; rot_tests=""
trap nachlauf EXIT
main "$@"
exit
