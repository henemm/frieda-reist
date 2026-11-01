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
: "${FR_KN_ADRESSE:=${FR_ADRESSE:+$FR_ADRESSE/$FR_INSTANZ-mcp}}"
: "${FR_PYTHON:=$FR_WURZEL/engine/.venv/bin/python}"
: "${FR_MELDEN:=}"
: "${FR_UMZUG_NACH:=}"
: "${FR_SPERREN:=/tmp}"
case "$FR_MELDEN" in ""|/*) ;; *) FR_MELDEN="$FR_WURZEL/$FR_MELDEN" ;; esac   # relativ zur Wurzel
export FR_INSTANZ FR_TITEL FR_SEITEN FR_ABLAGE FR_DIENST FR_KONNEKTOR FR_KONTEN FR_RM_PORT FR_KN_PORT FR_SB_PORT FR_SCHREIBKOPIE \
  FR_ADRESSE FR_KN_ADRESSE FR_PYTHON FR_MELDEN FR_SPERREN FR_UMZUG_NACH

# Was die Software (engine/) erwartet; ausdrücklich gesetzte Werte gelten weiter
: "${RM_ABLAGE:=$FR_ABLAGE}"
: "${KN_SEITEN:=$FR_SEITEN}"
: "${KN_ZUGAENGE:=$FR_KONNEKTOR/zugaenge.json}"
export RM_ABLAGE KN_SEITEN KN_ZUGAENGE
[ -z "$FR_KN_ADRESSE" ] || { : "${KN_BASIS:=$FR_KN_ADRESSE}"; export KN_BASIS; }

fr_melden() {  # <normal|high> <betreff> <text> [erledigt]: Nachricht an den Betreiber über FR_MELDEN, sonst nichts
  [ -n "$FR_MELDEN" ] || return 0
  "$FR_MELDEN" "$1" "$FR_TITEL: $2" "$3" "${4:-}" > /dev/null 2>&1 || echo "Warning: message not sent."
}
