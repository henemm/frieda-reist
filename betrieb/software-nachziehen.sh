#!/usr/bin/env bash
# Software nachziehen (#161, #168, #250): läuft im Workflow „Software nachziehen“ des Reisen-Repos (Vorlage
# betrieb/software-nachziehen.yml), im Klon des Reisen-Repos auf dem Runner, aus dem neuen Stand der Software. Der Workflow
# hat das Submodul frieda/ schon gesetzt, wenn ein neuer Stand da ist, und übergibt ALT, NEU und NEU_DA (ja|nein).
#
# Ablauf (docs/betrieb.md, „Software nachziehen“):
# 1. Umstellen: neu.py nachziehen für jede Reise mit reise.json, in jedem Lauf, auch ohne neuen Stand (idempotent).
#    Reisen aus dem Reisespeicher (FR_SPEICHERREISEN in betrieb/einstellungen.env, #348) überspringen Umstellen und Tor:
#    Sie stellt der Server beim Veröffentlichen selbst um, ihre Git-Kopie ist veraltet.
#    Ein offener Punkt (OPEN/OFFEN) sperrt nicht, er erscheint als Warnung; sperren kann nur der Bau.
# 2. Nichts geändert (weder Submodul noch Reisen): Ende, grün, kein Commit.
# 3. Tor wie beim Veröffentlichen (#142, #168): engine/tests nur bei neuem Stand, der Bau jeder Reise in jedem Lauf mit
#    Änderung; die Tests des Reisen-Repos (tests/) sind nur eine Warnung.
# 4. Übernehmen: ein Commit des Bots mit Submodul und umgestellten Reisen, darunter die Liste der Commits und die
#    Meldungen der Umstellung je Reise.
# 5. Scheitert der Push (Wettlauf mit dem Schreibweg), wird auf origin/main zurückgesetzt, das Submodul erneut gesetzt,
#    neu umgestellt, neu geprüft und neu committet. Höchstens drei Versuche, nie erzwungen; scheitern alle, endet der Lauf
#    rot ohne Issue (der nächste Lauf versucht es wieder).
# 6. Tor rot: ohne offenes Issue (Label software-nachziehen) entsteht eins, und der Lauf endet rot (GitHub mailt). Mit
#    offenem Issue: Warnung, Exit 0, kein Commit; nennt das Issue den aktuellen Stand noch nicht, bekommt es einen
#    Kommentar mit Stand und Lauf.
# Texte für den Betreiber (Commit, Issue, Protokoll) stehen wie in allen Skripten in betrieb/ hier; die Meldungen der
# Umstellung kommen aus neu.py in der Sprache der Reise.
# Für Tests: SN_PAUSE (Sekunden zwischen zwei Push-Versuchen, Vorgabe 10).
set -euo pipefail

# Alles steckt in main(), damit bash das Skript ganz einliest, bevor git das Submodul (und damit dieses Skript) ändert.
main() {
  : "${ALT:?ALT fehlt}" "${NEU:?NEU fehlt}" "${NEU_DA:?NEU_DA fehlt}"
  local pause="${SN_PAUSE:-10}" tmp stand versuch
  tmp="${RUNNER_TEMP:-$(mktemp -d)}"
  lauf_url="${GITHUB_SERVER_URL:-}/${GITHUB_REPOSITORY:-}/actions/runs/${GITHUB_RUN_ID:-}"
  if [ "$NEU_DA" = ja ]; then stand="$NEU"; else stand="$ALT"; fi
  kurz="${stand:0:7}"
  meldungen="$tmp/umstellung"

  git config user.name "github-actions[bot]"
  git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

  for versuch in 1 2 3; do
    if [ "$versuch" -gt 1 ]; then
      echo "Push gescheitert (main hat sich bewegt), Versuch $versuch: zurück auf origin/main, neu umstellen und prüfen."
      sleep "$pause"
      git fetch -q origin main
      git reset -q --hard origin/main
      if [ "$NEU_DA" = ja ]; then
        git -C frieda checkout -q "$NEU"
      else
        git submodule update -q frieda
      fi
    fi

    umstellen
    git add -A -- reisen
    git add frieda
    if git diff --cached --quiet; then
      echo "Nichts zu übernehmen: Software und Reisen sind auf dem Stand."
      return 0
    fi

    if ! tor; then
      git reset -q
      issue_regel
      return $?
    fi

    nachricht > "$tmp/nachricht"
    git commit -q -F "$tmp/nachricht"
    if git push -q origin HEAD:main; then
      echo "Übernommen: $(head -n 1 "$tmp/nachricht")"
      return 0
    fi
  done
  echo "::error::Übernahme nach main dreimal gescheitert, der nächste Lauf versucht es wieder."
  return 1
}

speicherreisen_der_instanz() {  # FR_SPEICHERREISEN, eine Reise je Zeile, gelesen wie fr_einlesen (betrieb/gemeinsam.sh):
  # ein Wert aus der Umgebung gilt vor betrieb/einstellungen.env des Reisen-Repos, dort die erste Zeile; ohne
  # Shell-Auswertung, Leerzeichen und leere Teile fallen weg. Fehlt beides: keine.
  local zeile wert r
  if [ -n "${FR_SPEICHERREISEN+x}" ]; then
    wert="$FR_SPEICHERREISEN"
  else
    [ -r betrieb/einstellungen.env ] || return 0
    zeile=""
    while IFS= read -r r || [ -n "$r" ]; do
      case "$r" in FR_SPEICHERREISEN=*) zeile="$r"; break ;; esac
    done < betrieb/einstellungen.env
    [ -n "$zeile" ] || return 0
    wert="${zeile#*=}"; wert="${wert%$'\r'}"
    case "$wert" in \"*\") wert="${wert:1:${#wert}-2}" ;; \'*\') wert="${wert:1:${#wert}-2}" ;; esac
  fi
  local IFS=,
  for r in $wert; do
    r="${r#"${r%%[![:space:]]*}"}"; r="${r%"${r##*[![:space:]]}"}"
    [ -z "$r" ] || printf '%s\n' "$r"
  done
}

aus_dem_speicher() {  # <reise>: Reise aus dem Reisespeicher (Stufe 3, #348)? Die stellt der Server selbst um
  # (neu.py nachziehen-speicher); ihre Git-Kopie bleibt bis Stufe 5 unberührt liegen und wird hier weder umgestellt noch gebaut.
  # ohne Pipe zu grep -q (SIGPIPE unter pipefail, wie ist_speicherreise in gemeinsam.sh)
  local r
  while IFS= read -r r; do [ "$r" != "$1" ] || return 0; done <<< "$(speicherreisen_der_instanz)"
  return 1
}

umstellen() {  # neu.py nachziehen je Reise; Meldungen geänderter Reisen nach $meldungen, offene Punkte als Warnung
  local r reise ausgabe zeile
  : > "$meldungen"
  for r in reisen/*/reise.json; do
    [ -e "$r" ] || continue
    reise="$(basename "$(dirname "$r")")"
    if aus_dem_speicher "$reise"; then
      echo "Übersprungen: $reise (Reisespeicher, der Server stellt sie um)"; continue
    fi
    # Exit 1 bei offenen Punkten: sperrt nicht (das kann nur der Bau)
    ausgabe="$(python frieda/engine/neu.py nachziehen "reisen/$reise" 2>&1)" || true
    while IFS= read -r zeile; do
      case "$zeile" in OPEN*|OFFEN*|Traceback*|*Error*) echo "::warning::$reise: $zeile" ;; esac
    done <<< "$ausgabe"
    if [ -n "$(git status --porcelain -- "reisen/$reise")" ]; then
      echo "Umgestellt: $reise"
      echo "$ausgabe" | sed 's/^/  /'
      { echo "reisen/$reise:"; echo "$ausgabe" | sed 's/^/- /'; } >> "$meldungen"
    fi
  done
}

tor() {  # 0 grün, 1 rot; rot_text nennt, was sperrt
  local r reise rote=""
  rot_text=""
  if [ "$NEU_DA" = ja ]; then
    # Wie bisher über den Link engine -> frieda/engine des Reisen-Repos; ohne Link im Ordner der Software
    if [ -d engine/tests ]; then
      python -m pytest -q -rs -n auto engine/tests || rot_text="die Tests der Software (engine/tests)"
    else
      (cd frieda && python -m pytest -q -rs -n auto engine/tests) || rot_text="die Tests der Software (engine/tests)"
    fi
  fi
  # Jede Reise wie beim Veröffentlichen; Warnungen im Plan sperren nie (bauen.py endet dann mit 0)
  for r in reisen/*/reise.json; do
    [ -e "$r" ] || continue
    reise="$(basename "$(dirname "$r")")"
    aus_dem_speicher "$reise" && continue
    if ! python frieda/engine/bauen.py --reisen reisen --ziel "${RUNNER_TEMP:-$tmp}/dist" "$reise"; then
      echo "::error::Bau von $reise gescheitert"
      rote="$rote $reise"
    fi
  done
  [ -z "$rote" ] || rot_text="${rot_text:+$rot_text und }der Bau von${rote}"
  if [ -d tests ] && ! python -m pytest -q -rs tests; then
    echo "::warning::Tests des Reisen-Repos (tests/) rot. Sie sperren das Nachziehen nicht (docs/betrieb.md, Konvention für tests/)."
  fi
  [ -z "$rot_text" ]
}

nachricht() {  # Commit-Nachricht: erste Zeile, Liste der Commits der Software, Meldungen der Umstellung je Reise
  if [ "$NEU_DA" = ja ]; then
    echo "Software auf Stand $kurz (automatisch)"
    echo
    echo "$(git -C frieda rev-list --count "$ALT..$NEU") Commit(s) seit ${ALT:0:7}:"
    git -C frieda log --reverse --format='- %h %s' "$ALT..$NEU"
  else
    echo "Reisen auf den Stand der Software umgestellt (automatisch)"
  fi
  if [ -s "$meldungen" ]; then
    echo
    echo "Umstellung der Reisen (neu.py nachziehen):"
    cat "$meldungen"
  fi
}

issue_regel() {  # Tor rot: Issue anlegen und rot enden, oder offenes Issue (einmal je Stand) kommentieren und grün enden
  local liste nummer text
  # Scheitert die Abfrage, ist unbekannt, ob schon ein Issue offen ist: kein weiteres anlegen, rot enden (GitHub mailt)
  if ! liste="$(gh issue list --label software-nachziehen --state open --json number,title,comments)" \
     || ! nummer="$(printf '%s' "$liste" | jq -r '.[0].number // empty')"; then
    echo "::error::Tor rot: $rot_text. Nichts übernommen; offene Issues (Label software-nachziehen) nicht abfragbar, kein Issue angelegt."
    return 1
  fi
  if [ -z "$nummer" ]; then
    gh label create software-nachziehen --color B60205 \
      --description "Automatisches Nachziehen der Software ist an Tests gescheitert" > /dev/null 2>&1 || true
    gh issue create --label software-nachziehen \
      --title "Software-Stand $kurz lässt sich nicht automatisch übernehmen" \
      --body "Mit dem Stand $kurz der Software scheitert $rot_text. Die Software (oder die betroffene Reise) anpassen, dann übernimmt der nächste Lauf den Stand selbst. Solange dieses Issue offen ist, meldet sich ein rotes Tor nur mit einer Warnung im Lauf und einem Kommentar je neuem Stand. Lauf: $lauf_url" \
      || echo "::error::Issue konnte nicht angelegt werden."
    echo "::error::Tor rot: $rot_text. Nichts übernommen."
    return 1
  fi
  echo "::warning::Tor rot: $rot_text. Nichts übernommen; offenes Issue #$nummer."
  text="$(printf '%s' "$liste" | jq -r '.[0] | ([.title] + [(.comments // [])[] | .body]) | join("\n")' 2>/dev/null)" || text=""
  if ! printf '%s' "$text" | grep -qF "$kurz"; then
    gh issue comment "$nummer" --body "Auch mit dem Stand $kurz der Software scheitert $rot_text. Lauf: $lauf_url" > /dev/null \
      || echo "::warning::Kommentar an Issue #$nummer gescheitert."
  fi
  return 0
}

main "$@"
exit $?
