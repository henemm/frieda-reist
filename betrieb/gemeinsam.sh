# Gemeinsame Grundlage der Betriebsskripte (wird mit „. gemeinsam.sh“ eingelesen, nicht aufgerufen).
#
# Eine Instanz ist ein Reisen-Repo mit dieser Software als Submodul frieda/ (docs/betrieb.md). Die Skripte hier kennen
# keine Instanz: Pfade, Adressen, Namen, Meldeweg und Überwachung kommen aus den Einstellungen.
#
#   FR_WURZEL         Wurzel des Reisen-Repos. Ohne Angabe das Repo, das diese Software als Submodul einbindet.
#                     deploy.sh und veroeffentlichen.sh verlangen die Angabe (nur_bauordner, unten).
#   FR_EINSTELLUNGEN  Einstellungsdatei der Instanz, Vorgabe <FR_WURZEL>/betrieb/einstellungen.env (Vorlage:
#                     betrieb/einstellungen.beispiel). Darin nur Zeilen NAME=wert mit Namen FR_…, ohne Shell-Auswertung.
#                     Was schon in der Umgebung steht (systemd, Aufruf von Hand, Tests), gilt vor der Datei.
#   <FR_DIENST>/betrieb.env  Geheime Werte (Überwachungsadressen, Meldeweg), nur für den Betriebsbenutzer lesbar,
#                     nie im Repo; gleiche Form, wird nach den Einstellungen gelesen.

# Namen der Werte, die schon beim Aufruf (systemd, Hand, Tests) in der Umgebung stehen; nur beim ersten Einlesen gebildet,
# damit sie einen Neustart mit exec überstehen (veroeffentlichen.sh, #242). Kein FR_-Präfix: fr_aufraeumen und die
# Einstellungsvorlage erfassen den Merker nicht. Der Merker gilt nur für den Prozess, der ihn gesetzt hat (exec behält die
# PID): Ein innerer Lauf, etwa die Tests unter einem echten Lauf, erbt ihn sonst und räumt beim Neustart seine eigenen
# Werte weg.
if [ "${_aufruf_pid:-}" != "$$" ]; then
  _aufruf_namen=" $(compgen -e | grep -E '^(FR_|RM_ABLAGE$|KN_SEITEN$|KN_BASIS$)' | tr '\n' ' ' || true)"
  _aufruf_pid="$$"
  export _aufruf_namen _aufruf_pid
fi

fr_aufraeumen() {  # Werte entfernen, die nicht vom Aufruf stammen (Datei, betrieb.env, Vorgaben, abgeleitete), vor exec
  local name
  for name in $(compgen -v FR_ || true) RM_ABLAGE KN_SEITEN KN_BASIS; do
    case "$_aufruf_namen" in *" $name "*) ;; *) unset "$name" ;; esac
  done
}

FR_BETRIEB="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fr_wurzel_angegeben="${FR_WURZEL:-}"

if [ -z "${FR_WURZEL:-}" ]; then
  FR_WURZEL="$(git -C "$FR_BETRIEB" rev-parse --show-superproject-working-tree 2>/dev/null || true)"
  [ -n "$FR_WURZEL" ] || { echo "ERROR: root of the instance unknown (set FR_WURZEL or include the software as a submodule)." >&2; exit 1; }
fi
FR_WURZEL="$(cd "$FR_WURZEL" && pwd)"
export FR_WURZEL

# Gebaut und veröffentlicht wird nur im Bauordner der Instanz (docs/betrieb.md, Ordner; #137). Die Units und der
# Schreibweg nennen ihn mit FR_WURZEL. Ohne diese Angabe nähme ein Aufruf von Hand den Ordner, in dem das Skript
# zufällig liegt, etwa einen Arbeitsordner auf einem Branch.
nur_bauordner() {  # [--main]: ohne FR_WURZEL abbrechen; mit --main auch, wenn HEAD nicht der Branch main ist
  local skript zweig
  skript="$(basename "$0")"
  if [ -z "$fr_wurzel_angegeben" ]; then
    echo "ERROR: FR_WURZEL is missing. $skript runs only in the build folder: FR_WURZEL=<Bauordner> frieda/betrieb/$skript …" >&2
    exit 1
  fi
  if [ "${1:-}" = --main ]; then
    zweig="$(git -C "$FR_WURZEL" symbolic-ref -q --short HEAD 2>/dev/null || echo "detached HEAD")"
    if [ "$zweig" != main ]; then
      echo "ERROR: $FR_WURZEL is not on main ($zweig). Only what is on main gets built." >&2
      exit 1
    fi
  fi
}

fr_einlesen() {  # <datei>: NAME=wert-Zeilen übernehmen, Vorhandenes bleibt; nur Namen FR_…
  local zeile name wert
  [ -r "$1" ] || return 0
  while IFS= read -r zeile || [ -n "$zeile" ]; do
    zeile="${zeile%$'\r'}"
    case "$zeile" in ''|'#'*) continue ;; esac
    name="${zeile%%=*}"; wert="${zeile#*=}"
    if [[ ! "$name" =~ ^FR_[A-Z0-9_]+$ ]] || [ "$name" = "$zeile" ]; then
      echo "Warning: $1: line ignored (expected FR_NAME=value): $name" >&2; continue
    fi
    case "$wert" in \"*\") wert="${wert:1:${#wert}-2}" ;; \'*\') wert="${wert:1:${#wert}-2}" ;; esac
    [ -n "${!name+x}" ] || export "$name=$wert"
  done < "$1"
}

fr_einlesen "${FR_EINSTELLUNGEN:-$FR_WURZEL/betrieb/einstellungen.env}"

# Vorgaben (Erklärung in einstellungen.beispiel)
: "${FR_INSTANZ:=frieda}"
[[ "$FR_INSTANZ" =~ ^[a-z][a-z0-9-]{0,30}$ ]] || { echo "ERROR: FR_INSTANZ “$FR_INSTANZ”: lowercase letters, digits and hyphen only." >&2; exit 1; }
: "${FR_TITEL:=Frieda}"
: "${FR_SEITEN:=/srv/$FR_INSTANZ}"
: "${FR_DIENST:=$FR_SEITEN/_dienst}"
fr_einlesen "$FR_DIENST/betrieb.env"
: "${FR_ABLAGE:=$FR_SEITEN/_rueckmeldungen}"
: "${FR_KONNEKTOR:=$FR_SEITEN/_konnektor}"
: "${FR_KONTEN:=$FR_SEITEN/_konten}"
: "${FR_RM_PORT:=8771}"
: "${FR_KN_PORT:=8772}"
: "${FR_SB_PORT:=8773}"
: "${FR_SCHREIBKOPIE:=$FR_WURZEL-schreiben}"
: "${FR_ADRESSE:=}"
: "${FR_KN_ADRESSE:=$FR_ADRESSE}"   # Konnektor an der Wurzel der Adresse (/mcp, Anmeldung, OAuth; #163)
: "${FR_PYTHON:=$FR_WURZEL/engine/.venv/bin/python}"
: "${FR_MELDEN:=}"
: "${FR_UMZUG_NACH:=}"
: "${FR_SPERREN:=/tmp}"
: "${FR_EIGENE_ADRESSEN:=}"   # Adressen, die nicht ins Anfragekontingent zählen: die des Servers selbst, getrennt durch Leerzeichen (nginx-zone.conf, #206)
: "${FR_ZEITZONE:=UTC}"   # Zeitzone der Zeiten in Konnektor und Diensten, wenn die der Person unbekannt ist (#227)
: "${FR_SPEICHER:=$FR_SEITEN/_speicher}"   # Reisespeicher (engine/reisespeicher.py, ADR-0009), wie instanz.speicher()
: "${FR_SPEICHERREISEN:=}"   # Reisen aus dem Reisespeicher, kommagetrennt (Vorgabe: keine, alles über Git)
case "$FR_MELDEN" in ""|/*) ;; *) FR_MELDEN="$FR_WURZEL/$FR_MELDEN" ;; esac   # relativ zur Wurzel
export FR_INSTANZ FR_TITEL FR_SEITEN FR_ABLAGE FR_DIENST FR_KONNEKTOR FR_KONTEN FR_RM_PORT FR_KN_PORT FR_SB_PORT FR_SCHREIBKOPIE \
  FR_ADRESSE FR_KN_ADRESSE FR_PYTHON FR_MELDEN FR_SPERREN FR_UMZUG_NACH FR_NACHZIEHEN_WORKFLOW FR_ZEITZONE FR_EIGENE_ADRESSEN \
  FR_SPEICHER FR_SPEICHERREISEN

speicherreisen() {  # Reisen aus FR_SPEICHERREISEN, eine je Zeile; Leerzeichen und leere Teile fallen weg wie in
  # instanz.speicherreisen()
  local r
  local IFS=,
  for r in $FR_SPEICHERREISEN; do
    r="${r#"${r%%[![:space:]]*}"}"; r="${r%"${r##*[![:space:]]}"}"   # wie strip(): nur am Rand
    [ -z "$r" ] || printf '%s\n' "$r"
  done
}

ist_speicherreise() {  # <reise>: kommt sie aus dem Reisespeicher (Stufe 3, #348)? Sonst aus Git.
  # Ohne Pipe: grep -q endete beim ersten Treffer, der Schreiber stürbe an SIGPIPE, und unter pipefail wäre die Antwort
  # zufällig „nein“
  local r
  [ -n "${1:-}" ] || return 1
  while IFS= read -r r; do [ "$r" != "$1" ] || return 0; done <<< "$(speicherreisen)"
  return 1
}

# Workflow des Reisen-Repos, den ein Anstoß von der Seite startet (veroeffentlichen.sh, docs/betrieb.md „Anstoß“)
: "${FR_NACHZIEHEN_WORKFLOW:=software-nachziehen.yml}"
# Anstoß vom Server (veroeffentlichen.sh, #250): denselben neuen Software-Stand frühestens nach so vielen Stunden erneut
: "${FR_NACHZIEHEN_WIEDERHOLEN_STUNDEN:=6}"
# Was die Software (engine/) erwartet; ausdrücklich gesetzte Werte gelten weiter
: "${RM_ABLAGE:=$FR_ABLAGE}"
: "${KN_SEITEN:=$FR_SEITEN}"
export RM_ABLAGE KN_SEITEN
[ -z "$FR_KN_ADRESSE" ] || { : "${KN_BASIS:=$FR_KN_ADRESSE}"; export KN_BASIS; }

fr_melden() {  # <normal|high> <betreff> <text> [erledigt]: Nachricht an den Betreiber über FR_MELDEN, sonst nichts
  [ -n "$FR_MELDEN" ] || return 0
  "$FR_MELDEN" "$1" "$FR_TITEL: $2" "$3" "${4:-}" > /dev/null 2>&1 || echo "Warning: message not sent."
}

wege_pruefen() {  # Wege von außen: Jede Art Pfad des Konnektors muss über die öffentliche Adresse bei ihm ankommen
  # (Kopf X-Frieda), nicht bei nginx. Fehlt ein Ort im server-Block, geht die Seite, aber etwa das Kalender-Abo nicht
  # (1.11.2026). Nur Warnung und Meldung: Die Reiseseite selbst ist davon nicht betroffen. Die Abrufe kommen vom Server
  # selbst und zählen in nginx in dieselbe Begrenzung wie die Prüfung von freischalten.sh; veroeffentlichen.sh ruft sie
  # deshalb einmal je Lauf nach dem Freischalten auf (FR_WEGE_SPAETER), nicht je Reise (frieda-reist#163).
  # 429 heißt: Die Anfragebegrenzung von nginx (5/min auf /anmelden) hat gegriffen, der Ort ist da. Dann wartet die Prüfung
  # und fragt erneut, statt „fehlt“ zu melden (#279: 48 Fehlalarme an einem Tag).
  local weg fehlen="" kopf versuch
  [ -n "${FR_KN_ADRESSE:-}" ] || return 0
  systemctl is-enabled --quiet "$FR_INSTANZ-konnektor" 2>/dev/null || return 0
  # /manifest.webmanifest, /sw.js, /konto.js: Frieda-App und Schalter für Benachrichtigungen auf Mein Konto (#21)
  for weg in /gesund /anmelden /kalender/0000000000000000000000000000000000000000.ics /schrift/pruefung.woff2 /favicon.svg \
             /manifest.webmanifest /sw.js /konto.js; do
    for versuch in 1 2 3 4; do
      kopf=$(curl -sS -I --max-time 10 "$FR_KN_ADRESSE$weg" 2>/dev/null)
      case "$kopf" in HTTP/*" 429"*) [ "$versuch" -lt 4 ] && { sleep "${FR_WEGE_429_WARTEN:-13}"; continue; } ;; esac
      break
    done
    printf '%s\n' "$kopf" | grep -qi '^x-frieda:' || fehlen="$fehlen $weg"
  done
  [ -n "$fehlen" ] || return 0
  echo "Warning: these paths do not reach the connector via $FR_KN_ADRESSE:$fehlen"
  echo "         nginx: include the block $FR_INSTANZ-konnektor-orte.inc from betrieb/vorlagen/ (einrichten.sh, docs/betrieb.md)."
  fr_melden high "nginx: paths to the connector missing" "These paths do not reach the connector via $FR_KN_ADRESSE:$fehlen. Include the block $FR_INSTANZ-konnektor-orte.inc from betrieb/vorlagen/ (einrichten.sh)."
}
