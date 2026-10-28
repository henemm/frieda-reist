#!/usr/bin/env bash
# Arbeitet neue Rückmeldungen und Aufträge ein und veröffentlicht danach sofort (docs/betrieb.md, Einarbeiten).
# Gestartet vom Pfad-Wächter <instanz>-einarbeiten.path, sobald eine Eingabe eingeht (<FR_ABLAGE>/.neu), und stündlich
# vom Timer daneben als Sicherheitsnetz. Ohne Neues startet keine KI, ein leerer Lauf kostet also nichts.
#
# Sammelzeit: Nach der letzten neuen Eingabe wartet der Lauf regeln.sammelzeit_minuten der Reise (reise.yaml), höchstens
# FR_MAX_WARTEN_MIN nach der ersten. Ein Lauf zur Zeit (Sperre); was währenddessen eintrifft, bearbeitet derselbe Dienst
# in einem weiteren Durchgang (höchstens FR_DURCHGAENGE).
#
# Ablauf eines Durchgangs:
#  1. Eigene Arbeitskopie <Wurzel>-auto auf einem Branch auto/einarbeiten-…; neue Reisen aus der Claude-App ohne KI anlegen.
#  2. Je Reise mit neuen Einträgen ein eigener KI-Lauf (Claude Code, Auftrag einarbeiten-auftrag.md, dazu die Ergänzung
#     der Instanz <Wurzel>/betrieb/einarbeiten-ergaenzung.md, falls vorhanden). Er darf nur unter reisen/<reise>/ schreiben,
#     andere Reisen und die Ablage nicht lesen, nur Rückmeldeliste und Bauen dieser Reise ausführen und im Web nachschlagen.
#     Was er außerhalb seiner Reise ändert, wird verworfen und gemeldet. Er schreibt Status und Bericht in eine Datei.
#  3. Regeln prüfen, bauen, testen, ein Commit und ein PR für alle Reisen, zusammenführen, sofort veröffentlichen,
#     erst dann die Status setzen. Tests rot oder Regel verletzt: nichts geht online, der Branch bleibt zum Nachsehen.
#  Scheitert der KI-Lauf einer Reise, zählt der Versuch nur für deren Einträge; nach FR_MAX_VERSUCHE wird ein Eintrag
#  aufgegeben (Rückfrage auf der Seite, Meldung). Die anderen Reisen laufen weiter.
#
# Jeder Durchgang mit Neuem schreibt eine Zeile nach <FR_DIENST>/einarbeiten-laeufe.jsonl (Wartezeit, Dauer, Kosten).
# Nach fachlichem Erfolg wird <FR_DIENST>/einarbeiten-erfolg berührt (für die Überwachung). Nachrichten an den Betreiber
# über FR_MELDEN: ein Bericht nach jedem Lauf mit Neuem (erledigt), eine dringende Meldung bei jedem Fehler.
#
# Aufruf von Hand:  frieda/betrieb/einarbeiten.sh      Log: journalctl -u <instanz>-einarbeiten -n 100
# Für Tests überschreibbar: EA_QUELLE, EA_ARBEIT, EA_GESEHEN, EA_VERSUCHE, EA_LAEUFE, EA_STEMPEL, EA_SPERRE,
# EA_AUSSTEHEND, EA_VEROEFFENTLICHEN, EA_ARBEITSKOPIE, VF_STAND.
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/gemeinsam.sh"

PY="$FR_PYTHON"
HILFE="$FR_BETRIEB/einarbeiten_hilfe.py"
hilfe() { "$PY" "$HILFE" "$@"; }
rm_setze() { "$PY" "$quelle/engine/rueckmeldungen.py" setze "$@"; }

erfolg_melden() {
  touch "${EA_STEMPEL:-$FR_DIENST/einarbeiten-erfolg}"
}

# Zustand des laufenden Durchgangs, für Protokoll und Fehlermeldung
lauf_aktiv=""; lauf_start=0; lauf_reisen=""; lauf_anzahl=0; lauf_aelteste=""; lauf_claude=0; lauf_kosten=""; lauf_online=""
protokoll() {  # <ergebnis>
  [ -n "$lauf_aktiv" ] || return 0
  local jetzt wartezeit=""
  jetzt="$(date +%s)"
  [ -z "$lauf_aelteste" ] || wartezeit=$(( jetzt - $(date -d "$lauf_aelteste" +%s) ))
  hilfe protokoll "${EA_LAEUFE:-$FR_DIENST/einarbeiten-laeufe.jsonl}" \
    "ergebnis=$1" "reisen=$lauf_reisen" "anzahl=$lauf_anzahl" "dauer_s=$(( jetzt - lauf_start ))" \
    "claude_s=$lauf_claude" "kosten_usd=$lauf_kosten" "eingabe_bis_ende_s=$wartezeit" "online=${lauf_online:-nein}" \
    || echo "Warnung: Protokoll nicht geschrieben."
  lauf_aktiv=""
}

# Jeder Abbruch (auch durch set -e) meldet sich; gewollte Fehler setzen vorher $grund
grund=""
trap 'rc=$?; [ "$rc" -eq 0 ] || protokoll fehler; [ "$rc" -eq 0 ] || fr_melden high "Einarbeiten fehlgeschlagen" \
  "${grund:-Unerwarteter Fehler.} Was nicht eingearbeitet ist, bleibt offen. Log: journalctl -u $FR_INSTANZ-einarbeiten -n 100"' EXIT

fremd_verwerfen() {  # <reise>: Änderungen des letzten KI-Laufs außerhalb von reisen/<reise>/ verwerfen und ausgeben
  local liste p
  liste="$( { git diff --name-only; git ls-files --others --exclude-standard; } \
    | grep -v -e "^reisen/$1/" -e '^\.einarbeiten/' | sort -u || true)"
  git submodule foreach --quiet 'git reset -q --hard && git clean -qfd' 2>/dev/null || true
  [ -n "$liste" ] || return 0
  while IFS= read -r p; do
    if git ls-files --error-unmatch -- "$p" > /dev/null 2>&1; then git checkout -q -- "$p" 2>/dev/null || true
    else rm -f -- "$p"; fi
  done <<< "$liste"
  printf '%s\n' "$liste"
}

ki_lauf() {  # <reise> <ids…>: ein KI-Lauf für eine Reise -> Rückgabe ≠ 0, wenn er gescheitert ist
  local reise="$1" ids_r ausr auftrag ergaenzung r andere=() kosten rc=0 start
  shift; ids_r="$*"
  ausr="$aus/$reise"; mkdir -p "$ausr"
  auftrag="$(cat "$FR_BETRIEB/einarbeiten-auftrag.md")"
  ergaenzung="$quelle/betrieb/einarbeiten-ergaenzung.md"
  [ -r "$ergaenzung" ] && auftrag="$auftrag"$'\n\n'"Ergänzung dieser Instanz:"$'\n'"$(cat "$ergaenzung")"
  auftrag="${auftrag//__REISE__/$reise}"; auftrag="${auftrag//__IDS__/${ids_r// /, }}"; auftrag="${auftrag//__AUS__/$ausr}"
  # Lesen verboten: andere Reisen (Arbeitskopie und Veröffentlichungsordner) und die Ablage aller Reisen
  for r in "$arbeit"/reisen/*/ "$quelle"/reisen/*/; do
    [ -d "$r" ] && [ "$(basename "$r")" != "$reise" ] && andere+=("Read(/${r%/}/**)")
  done
  andere+=("Read(/$FR_ABLAGE/**)")
  git add -A -- reisen   # Stand vor dem Lauf: was danach im Arbeitsbaum abweicht, hat die KI geändert
  start="$(date +%s)"
  # dontAsk lehnt alles Ungelistete ab, ohne zu fragen; JSON-Ausgabe, damit die Kosten messbar sind
  timeout "${FR_CLAUDE_MIN:-45}m" "${FR_CLAUDE:-claude}" -p "$auftrag" \
    --output-format json --permission-mode dontAsk --no-session-persistence \
    --allowedTools "Edit(/$arbeit/reisen/$reise/**)" "Edit(/$ausr/**)" "WebSearch" "WebFetch" \
      "Bash(python3 engine/rueckmeldungen.py liste $reise)" "Bash(engine/.venv/bin/python engine/bauen.py $reise)" \
    --disallowedTools "${andere[@]}" \
    > "$ausr/claude.log" 2> "$ausr/claude.err" || rc=$?
  lauf_claude=$(( lauf_claude + $(date +%s) - start ))
  kosten="$(hilfe kosten "$ausr/claude.log")" || rc=3
  [ -z "$kosten" ] || lauf_kosten="$(python3 -c 'import sys; print(round(sum(float(x) for x in sys.argv[1:]), 4))' $lauf_kosten $kosten)"
  return "$rc"
}

lauf() {
  local branch reisen="" ids="" roh reise id st kommentar titel url stand merge_sha="" rest aufgegeben text="" geaendert=""
  local ids_neu art x z neue="" reisen_ki="" reisen_ok="" gescheitert="" ids_r fremd regel_rc verstoss
  arbeit="${EA_ARBEIT:-$(dirname "$quelle")/$(basename "$quelle")-auto}"
  gesehen="${EA_GESEHEN:-$FR_DIENST/einarbeiten-gesehen}"
  versuche="${EA_VERSUCHE:-$FR_DIENST/einarbeiten-versuche}"
  stand="${VF_STAND:-$FR_DIENST/veroeffentlicht}"

  roh="$(hilfe neu "$quelle" "$gesehen")"
  if [ -z "$roh" ]; then echo "Nichts Neues."; return 0; fi
  verarbeitet=1

  # Sammelzeit: warten, bis eine Weile nichts mehr eingegangen ist (neue Eingaben verlängern, bis zur Obergrenze)
  while rest="$(hilfe warten "$quelle" "$gesehen")" && [ "$rest" -gt 0 ]; do
    echo "Sammelzeit: noch ${rest} s."
    sleep "$rest"
  done
  roh="$(hilfe neu "$quelle" "$gesehen")"
  [ -n "$roh" ] || { echo "Nichts Neues."; return 0; }
  ids="$(printf '%s\n' "$roh" | awk '$1 != "_neu" {print $1, $2}')"
  ids_neu="$(printf '%s\n' "$roh" | awk '$1 == "_neu" {print $2}')"
  reisen_ki="$(printf '%s\n' "$ids" | awk 'NF {print $1}' | sort -u | tr '\n' ' ')"
  reisen="$reisen_ki"
  echo "Neu: $reisen($(printf '%s\n' "$ids" | grep -c .) Einträge)${ids_neu:+, neue Reisen: $(printf '%s\n' "$ids_neu" | grep -c .)}"

  lauf_aktiv=1; lauf_start="$(date +%s)"; lauf_reisen="${reisen% }${ids_neu:+ _neu}"; lauf_anzahl="$(printf '%s\n' "$ids" $ids_neu | grep -c .)"
  lauf_aelteste="$(printf '%s\n' "$roh" | awk 'NR==1 {print $3}')"; lauf_claude=0; lauf_kosten=""; lauf_online=""

  # Eigene Arbeitskopie, getrennt von der für Sitzungen; Reste eines alten Laufs weg
  branch="auto/einarbeiten-$(date -u +%Y%m%d-%H%M%S)-$RANDOM"
  if [ -d "$arbeit" ]; then
    git -C "$arbeit" reset -q --hard; git -C "$arbeit" clean -qfd
    # Software (Submodul frieda) ändert ein Lauf nie; versehentliche Änderungen verwerfen
    git -C "$arbeit" submodule foreach --quiet 'git reset -q --hard && git clean -qfd' 2>/dev/null || true
  fi
  ARBEITSKOPIE="$arbeit" "${EA_ARBEITSKOPIE:-$FR_BETRIEB/arbeitskopie.sh}" "$branch"
  aus="$arbeit/.einarbeiten"
  rm -rf "$aus"; mkdir -p "$aus"
  cd "$arbeit"

  # Neue Reisen aus der Claude-App: ohne KI anlegen (der Dienst hat alles geprüft); Fehler werden Rückfragen
  if [ -n "$ids_neu" ]; then
    rest="$(hilfe neue_reisen "$quelle" "$arbeit" "$aus/neue_reisen.jsonl" $ids_neu)"   # bricht bei einem Fehler ab (set -e)
    while read -r art x z; do
      case "$art" in
        angelegt) neue="$neue$x "; reisen="$reisen$x "; echo "Neue Reise angelegt: $x ($z)";;
        fehler) echo "Neue Reise nicht angelegt: $x"
          rm_setze _neu "$x" rueckfrage "Nicht angelegt: $z" || true;;
      esac
    done <<< "$rest"
    printf '%s\n' $ids_neu >> "$gesehen"
  fi

  # Je Reise ein KI-Lauf, nur mit den Einträgen und Rechten dieser Reise
  for reise in $reisen_ki; do
    ids_r="$(printf '%s\n' "$ids" | awk -v r="$reise" '$1 == r {print $2}' | tr '\n' ' ')"
    echo "KI-Lauf: $reise (${ids_r% })"
    if ! ki_lauf "$reise" $ids_r; then
      gescheitert="$gescheitert$reise "
      echo "FEHLER: KI-Lauf für $reise abgebrochen."; tail -c 2000 "$aus/$reise/claude.err" "$aus/$reise/claude.log" || true
      git checkout -q -- "reisen/$reise" 2>/dev/null || true; git clean -qfd -- "reisen/$reise"
      fremd_verwerfen "$reise" > /dev/null
      # Scheitert derselbe Eintrag mehrfach, wird er aufgegeben, damit er nicht jede neue Eingabe aufhält
      aufgegeben="$(hilfe versuch "$versuche" "${FR_MAX_VERSUCHE:-3}" $ids_r | tr '\n' ' ')"
      if [ -n "$aufgegeben" ]; then
        printf '%s\n' $aufgegeben >> "$gesehen"
        for id in $aufgegeben; do
          rm_setze "$reise" "$id" rueckfrage "Das konnte nicht automatisch eingearbeitet werden. ${FR_BETREIBER:-Jemand} schaut es sich in der nächsten Sitzung an." || true
        done
        fr_melden high "Einarbeiten aufgegeben" \
          "Die KI ist an ${aufgegeben% } ($reise) mehrfach gescheitert. Die Einträge werden nicht mehr automatisch versucht; bitte in einer Sitzung ansehen."
      fi
      continue
    fi
    fremd="$(fremd_verwerfen "$reise")"
    if [ -n "$fremd" ]; then
      echo "Verworfen (außerhalb von reisen/$reise/): $(printf '%s' "$fremd" | tr '\n' ' ')"
      text="$text- $reise: Änderungen außerhalb der Reise verworfen: $(printf '%s' "$fremd" | tr '\n' ' ')"$'\n'
    fi
    reisen_ok="$reisen_ok$reise "
    # Ab hier gilt der Stand als gesehen: auch wenn die Tests rot sind, nicht neu versuchen
    printf '%s\n' $ids_r >> "$gesehen"
  done
  if [ -n "$reisen_ki" ] && [ -z "$reisen_ok" ] && [ -z "$neue" ]; then
    grund="KI-Lauf abgebrochen (${gescheitert% })."; echo "FEHLER: $grund"; return 1
  fi

  # Regeln, die sonst nur die Anweisung verlangt, maschinell prüfen (Konflikt wird offene Frage, Prüfauftrag ändert
  # keinen Wert). Ein Verstoß wird behandelt wie rote Tests: nichts geht online, der Branch bleibt zum Nachsehen.
  regel_rc=0
  verstoss="$(hilfe regeln "$quelle" "$arbeit" $(for reise in $reisen_ok; do
    printf '%s\n' "$ids" | awk -v r="$reise" '$1 == r {print $1 "/" $2}'; done) 2>&1)" || regel_rc=$?
  if [ "$regel_rc" -ne 0 ]; then
    git add -A reisen && git commit -q -m "WIP: automatisch eingearbeitet, Regelprüfung nicht bestanden" && git push -q -u origin "$branch" || true
    if [ "$regel_rc" -eq 4 ]; then grund="Regel verletzt, Branch $branch zum Nachsehen: $verstoss"
    else grund="Regelprüfung fehlgeschlagen (Code $regel_rc), Branch $branch zum Nachsehen: $(printf '%s' "$verstoss" | tail -c 500)"; fi
    echo "FEHLER: $grund"; return 1
  fi

  bericht_zusammenstellen "$reisen_ok" "$neue"
  if [ -n "$(git status --porcelain -- reisen)" ]; then
    for reise in $reisen_ok $neue; do "$PY" engine/bauen.py "$reise" > /dev/null; done
    if ! "$PY" -m pytest -q engine/tests $( [ -d tests ] && echo tests ) > "$aus/tests.log" 2>&1; then
      git add -A reisen && git commit -q -m "WIP: automatisch eingearbeitet, Tests rot" && git push -q -u origin "$branch" || true
      grund="Tests rot, Branch $branch zum Nachsehen."; echo "FEHLER: $grund"; tail -20 "$aus/tests.log"; return 1
    fi
    titel="$(head -1 "$aus/bericht.md")"
    git add -A reisen
    git commit -q -F - <<TEXT
$titel

$(tail -n +3 "$aus/bericht.md")

Automatisch eingearbeitet (frieda/betrieb/einarbeiten.sh).

Co-Authored-By: Claude <noreply@anthropic.com>
TEXT
    git fetch -q origin && git rebase -q origin/main
    git push -q -u origin "$branch"
    url="$(gh pr create --head "$branch" --title "$titel" \
      --body "$(printf '%s\n\nAutomatisch eingearbeitet (frieda/betrieb/einarbeiten.sh), Tests grün.\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)' "$(cat "$aus/bericht.md")")")"
    gh pr merge "$url" --merge > /dev/null 2>&1 || true
    [ "$(gh pr view "$url" --json state --jq .state)" = MERGED ] || { grund="$url nicht zusammengeführt."; echo "FEHLER: $grund"; return 1; }
    geaendert=1
    merge_sha="$(gh pr view "$url" --json mergeCommit --jq .mergeCommit.oid 2>/dev/null || true)"
    # Fehlt die Angabe, gilt der aktuelle Stand von origin/main (enthält den Merge, falls niemand sonst dazwischen war)
    [ -n "$merge_sha" ] || { git fetch -q origin; merge_sha="$(git rev-parse origin/main)"; }
    git push -q origin --delete "$branch" || true
    echo "Zusammengeführt: $url"
  else
    echo "Keine Dateien geändert."
  fi
  git checkout -q --detach origin/main && git branch -q -D "$branch" || true

  # Sofort veröffentlichen, nicht auf den Timer warten. Hält gerade der Timer die Sperre, meldet das Skript
  # „Läuft schon“ und führt nichts aus; deshalb zählt nur, wenn der veröffentlichte Stand die Änderung enthält.
  if [ -n "$geaendert" ]; then
    # Links neuer Reisen stellt veroeffentlichen.sh zu, sobald ihre Seite online ist
    if [ -s "$aus/neue_reisen.jsonl" ]; then
      cat "$aus/neue_reisen.jsonl" >> "${EA_AUSSTEHEND:-$FR_DIENST/neue-reisen-ausstehend.jsonl}"
      for x in $neue; do
        z="$(python3 -c "import sys,json; print(next(e['aid'] for e in map(json.loads, sys.stdin) if e['ordner'] == sys.argv[1]))" "$x" < "$aus/neue_reisen.jsonl")"
        rm_setze _neu "$z" uebernommen "Angelegt als $x. Die Links stehen in meine_reisen, sobald die Seite online ist." || true
        text="$text- neue Reise $x: angelegt"$'\n'
      done
    fi
    "${EA_VEROEFFENTLICHEN:-$FR_BETRIEB/veroeffentlichen.sh}" || echo "Warnung: Veröffentlichen fehlgeschlagen, der Timer versucht es erneut."
    if git -C "$quelle" merge-base --is-ancestor "$merge_sha" "$(cat "$stand" 2>/dev/null || echo)" 2>/dev/null; then
      lauf_online=ja
    fi
  else
    lauf_online=ja   # nichts geändert: nichts zu veröffentlichen
  fi

  # Status nur für Einträge dieses Laufs und der eigenen Reise, nur gültige Werte (erst jetzt: „aufgenommen“ soll
  # stimmen, wenn man es liest)
  for reise in $reisen_ok; do
    touch "$aus/$reise/status.tsv"
    while IFS=$'\t' read -r x id st kommentar; do
      [ -n "${id:-}" ] || continue
      { [ "$x" = "$reise" ] && printf '%s\n' "$ids" | grep -qxF "$reise $id"; } \
        || { echo "Übersprungen (nicht in diesem Lauf von $reise): $x $id"; continue; }
      case "$st" in uebernommen|verworfen|rueckfrage) ;; *) echo "Übersprungen (Status $st): $id"; continue ;; esac
      rm_setze "$reise" "$id" "$st" "$kommentar"
      text="$text- $reise $id: $st – $kommentar"$'\n'
    done < "$aus/$reise/status.tsv"
  done
  echo "Bericht:"; cat "$aus/bericht.md"
  if [ -n "$gescheitert" ]; then
    protokoll teilweise
  else
    protokoll ok
  fi
  fr_melden normal "$(printf '%s\n' "$ids" | grep -c .) Einträge bearbeitet (${reisen% })" \
    "${text:-Keine Status gesetzt.}"$'\n'"$([ "$lauf_online" = ja ] && echo "Online." || echo "Online in wenigen Minuten.") Rückfragen kommen in der nächsten Sitzung dran." erledigt
  if [ -n "$gescheitert" ]; then
    grund="KI-Lauf abgebrochen (${gescheitert% }); die übrigen Reisen sind eingearbeitet."; echo "FEHLER: $grund"; return 1
  fi
}

bericht_zusammenstellen() {  # <reisen> <neue>: $aus/bericht.md aus den Berichten der Reisen (erste Zeile = Commit-Titel)
  local r teile=() reisen="$1" neue="$2" x
  for r in $reisen; do [ -s "$aus/$r/bericht.md" ] && teile+=("$r"); done
  {
    if [ ${#teile[@]} -eq 1 ]; then
      cat "$aus/${teile[0]}/bericht.md"; echo
    elif [ ${#teile[@]} -eq 0 ] && [ -n "$neue" ]; then
      printf 'Neue Reise angelegt: %s\n\n' "${neue% }"
    else
      printf 'Rückmeldungen eingearbeitet: %s\n\n' "$(echo $reisen $neue | sed 's/ /, /g')"
      for r in "${teile[@]}"; do printf '%s:\n' "$r"; tail -n +3 "$aus/$r/bericht.md"; echo; done
    fi
    for x in $neue; do printf -- '- Neue Reise %s aus der Claude-App angelegt (Status idee).\n' "$x"; done
  } | cat -s > "$aus/bericht.md"
}

main() {
  local durchgang=0
  # Veröffentlichungsordner = Hauptkopie des Repos, auch wenn das Skript aus einer anderen Kopie aufgerufen wird
  quelle="${EA_QUELLE:-$(dirname "$(git -C "$FR_WURZEL" rev-parse --path-format=absolute --git-common-dir)")}"
  exec 9>"${EA_SPERRE:-$FR_SPERREN/$FR_INSTANZ-einarbeiten.lock}"
  flock -n 9 || { echo "Läuft schon, übersprungen."; return 0; }
  touch "${EA_GESEHEN:-$FR_DIENST/einarbeiten-gesehen}"
  # Mehrere Durchgänge: Was während eines Laufs eingeht, löst keinen neuen Start aus (der Dienst läuft ja noch),
  # also schaut der Dienst am Ende selbst noch einmal nach.
  while [ "$durchgang" -lt "${FR_DURCHGAENGE:-3}" ]; do
    durchgang=$((durchgang + 1))
    verarbeitet=0
    lauf
    erfolg_melden
    [ "$verarbeitet" = 1 ] || break
    cd "$quelle"
  done
}

verarbeitet=0; quelle=""; arbeit=""; aus=""; gesehen=""; versuche=""
main "$@"
exit
