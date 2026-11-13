# Gemeinsame Grundlage der Betriebsskripte (wird mit „. gemeinsam.sh“ eingelesen, nicht aufgerufen).
#
# Eine Instanz baut aus dem Software-Klon <FR_SEITEN>/_software (#454, docs/betrieb.md „Bauordner“), früher aus einem
# Reisen-Repo mit dieser Software als Submodul frieda/ (alte Anordnung, bis zum Umzug). Die Skripte hier kennen keine
# Instanz: Pfade, Adressen, Namen, Meldeweg und Überwachung kommen aus den Einstellungen.
#
#   FR_WURZEL         Bauordner: der Software-Klon (neu) oder das Reisen-Repo (alt). Ohne Angabe das Repo, das diese Software
#                     als Submodul einbindet. deploy.sh und veroeffentlichen.sh verlangen die Angabe (nur_bauordner, unten).
#   FR_EINSTELLUNGEN  Einstellungsdatei der Instanz, Vorgabe <FR_DIENST>/instanz/einstellungen.env (#454); fehlt sie dort, gilt
#                     (Übergang) der alte Ort <FR_WURZEL>/betrieb/einstellungen.env (Vorlage: betrieb/einstellungen.beispiel).
#                     Darin nur Zeilen NAME=wert mit Namen FR_…, ohne Shell-Auswertung. Was schon in der Umgebung steht
#                     (systemd, Aufruf von Hand, Tests), gilt vor der Datei. FR_DIENST für diese Suche kommt aus der Umgebung
#                     (sonst <FR_SEITEN>/_dienst bzw. /srv/<FR_INSTANZ>/_dienst), nie aus der Datei selbst.
#   <FR_DIENST>/instanz/  Ort der Instanz (#454): einstellungen.env, melden.sh (Meldeweg), optional tests/; vom Backup erfasst.
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

fr_alte_anordnung() {  # Bauordner in der alten Anordnung (#454): Reisen-Repo mit der Software als Submodul frieda/
  [ -e "$FR_WURZEL/.gitmodules" ] || [ -d "$FR_WURZEL/frieda/betrieb" ]
}

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
  if [ ! -e "$1" ] && [ ! -L "$1" ]; then return 0; fi    # fehlende Datei ist normal (Beispielreisen, Instanzen ohne Einstellungen)
  if [ ! -f "$1" ] || [ ! -r "$1" ]; then   # vorhanden, aber nicht lesbar: nicht still überspringen (#361)
    echo "ERROR: $1 exists but cannot be read." >&2; exit 1
  fi
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

# Ort der Einstellungen (#454): <FR_DIENST>/instanz/einstellungen.env, sonst (Übergang) der alte Ort im Reisen-Repo. Der
# Dienstordner kommt hier nur aus der Umgebung; die Datei kann ihn nicht selbst nennen.
fr_dienst_vorab="${FR_DIENST:-${FR_SEITEN:-/srv/${FR_INSTANZ:-frieda}}/_dienst}"
if [ -n "${FR_EINSTELLUNGEN:-}" ]; then
  fr_einstellungen_datei="$FR_EINSTELLUNGEN"
elif [ -e "$fr_dienst_vorab/instanz/einstellungen.env" ] || [ -L "$fr_dienst_vorab/instanz/einstellungen.env" ]; then
  fr_einstellungen_datei="$fr_dienst_vorab/instanz/einstellungen.env"
else
  fr_einstellungen_datei="$FR_WURZEL/betrieb/einstellungen.env"
fi
fr_einlesen "$fr_einstellungen_datei"

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
# Python der Dienste (#454): fest unter <FR_DIENST>/python, außerhalb des Software-Klons; in der alten Anordnung (Submodul
# frieda/ im Reisen-Repo) bis zum Umzug weiter <FR_WURZEL>/engine/.venv, außer die neue Umgebung steht schon
if fr_alte_anordnung && [ ! -x "$FR_DIENST/python/bin/python" ]; then
  : "${FR_PYTHON:=$FR_WURZEL/engine/.venv/bin/python}"
else
  : "${FR_PYTHON:=$FR_DIENST/python/bin/python}"
fi
: "${FR_MELDEN:=}"
: "${FR_UMZUG_NACH:=}"
: "${FR_SPERREN:=$FR_DIENST}"   # Sperren im Dienstordner, nicht im gemeinsamen Ordner für Temporäres (#552)
: "${FR_EIGENE_ADRESSEN:=}"   # Adressen, die nicht ins Anfragekontingent zählen: die des Servers selbst, getrennt durch Leerzeichen (nginx-zone.conf, #206)
: "${FR_ZEITZONE:=UTC}"   # Zeitzone der Zeiten in Konnektor und Diensten, wenn die der Person unbekannt ist (#227)
: "${FR_SPEICHER:=$FR_SEITEN/_speicher}"   # Reisespeicher (engine/reisespeicher.py, ADR-0009), wie instanz.speicher()
: "${FR_SPEICHERREISEN:=}"   # nur noch Übergang (#454): gelesen, wirkungslos; im Speicher ist, was im Speicher steht
# Meldeweg (#454): <FR_DIENST>/instanz/melden.sh, auch wenn die umgezogene Einstellung noch den alten relativen Pfad nennt;
# sonst relativ zur Wurzel wie bisher. Ohne Meldeweg wird nichts gesendet.
case "$FR_MELDEN" in
  /*) ;;
  "") [ ! -x "$FR_DIENST/instanz/melden.sh" ] || FR_MELDEN="$FR_DIENST/instanz/melden.sh" ;;
  *) if [ -x "$FR_DIENST/instanz/$(basename "$FR_MELDEN")" ]; then FR_MELDEN="$FR_DIENST/instanz/$(basename "$FR_MELDEN")"
     else FR_MELDEN="$FR_WURZEL/$FR_MELDEN"; fi ;;
esac
export FR_INSTANZ FR_TITEL FR_SEITEN FR_ABLAGE FR_DIENST FR_KONNEKTOR FR_KONTEN FR_RM_PORT FR_KN_PORT FR_SB_PORT FR_SCHREIBKOPIE \
  FR_ADRESSE FR_KN_ADRESSE FR_PYTHON FR_MELDEN FR_SPERREN FR_UMZUG_NACH FR_NACHZIEHEN_WORKFLOW FR_ZEITZONE FR_EIGENE_ADRESSEN \
  FR_SPEICHER FR_SPEICHERREISEN

# Eigener Kartendienst (#444, docs/betrieb.md): Overpass-Image per Digest gepinnt, damit ein Update des Images nichts ungeprüft
# ändert (nicht mitgeliefert; Overpass AGPL, Daten ODbL). Ein neuer Digest ist eine bewusste Änderung mit Abnahme.
KD_BILD="wiktorn/overpass-api@sha256:9bb5f4a9b54cd225bf828c04c67e7f4010650ff4d70b72157a9473a9ba02d93c"

# Reisen im Speicher (#454): Im Speicher ist, was im Speicher steht (engine/reisespeicher.py speicherreisen, wie
# instanz.speicherreisen()); FR_SPEICHERREISEN zählt nicht mehr. Ohne Datenbank keine (kein Python-Aufruf). Ist der Speicher
# nicht lesbar: Fehlermeldung und Abbruch des Skripts (fail closed, #361), nie „keine Reisen“. Ein Lauf kann die Liste mit
# speicherreisen_lesen einmal holen (Merker fr_speicherreisen_liste); sonst fragt jeder Aufruf den Speicher.
fr_speicher_fehlt() {  # Exit 0 nur, wenn die Datenbank des Speichers sicher fehlt: keine reisen.db, und der nächste vorhandene
  # Ordner auf dem Weg dorthin ist durchsuchbar. Ein `[ -e reisen.db ]` allein sähe in einem nicht durchsuchbaren Ordner
  # „keine Datenbank“ (fail open, #454 F001); dann entscheidet engine/reisespeicher.py, und das ist ein Fehler (#361).
  local d="$FR_SPEICHER"
  if [ -e "$d/reisen.db" ] || [ -L "$d/reisen.db" ]; then return 1; fi
  while [ ! -e "$d" ] && [ "$d" != / ]; do d="$(dirname "$d")"; done
  [ -d "$d" ] && [ -x "$d" ]
}

speicherreisen_lesen() {  # Liste aus dem Speicher holen und merken; Exit 1, wenn er nicht lesbar ist
  # Fail closed wie instanz.speicherreisen (#361): leer nur, wenn die Datenbank sicher fehlt (fr_speicher_fehlt, ohne
  # Python); sonst engine/reisespeicher.py speicherreisen, und jeder Fehler dort bricht ab
  local aus
  fr_speicherreisen_gelesen=""
  if fr_speicher_fehlt; then fr_speicherreisen_liste=""; fr_speicherreisen_gelesen=1; return 0; fi
  aus="$("$FR_PYTHON" "$FR_BETRIEB/../engine/reisespeicher.py" speicherreisen 2>&1)" \
    || { echo "ERROR: the trip store cannot be read ($(printf '%s\n' "$aus" | tail -1))." >&2; return 1; }
  fr_speicherreisen_liste="$aus"; fr_speicherreisen_gelesen=1
}

speicherreisen() {  # Reisen im Speicher, eine je Zeile
  if [ -z "${fr_speicherreisen_gelesen:-}" ]; then speicherreisen_lesen || exit 1; fi
  [ -z "$fr_speicherreisen_liste" ] || printf '%s\n' "$fr_speicherreisen_liste"
}

ist_speicherreise() {  # <reise>: kommt sie aus dem Reisespeicher? Sonst aus Git (bis zum Umzug, #454).
  # Ohne Pipe: grep -q endete beim ersten Treffer, der Schreiber stürbe an SIGPIPE, und unter pipefail wäre die Antwort
  # zufällig „nein“
  local r
  [ -n "${1:-}" ] || return 1
  if [ -z "${fr_speicherreisen_gelesen:-}" ]; then speicherreisen_lesen || exit 1; fi
  while IFS= read -r r; do [ "$r" != "$1" ] || return 0; done <<< "$fr_speicherreisen_liste"
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

# Alarm der Stufe high nur bei einem Ausfall, bei dem jemand jetzt handeln muss und kann (#446, CLAUDE.md, docs/betrieb.md
# „Meldeweg“); jede Stelle steht begründet in ALARMSTELLEN in engine/tests/test_betrieb.py. Einmal je Störung: Der Merker
# <FR_DIENST>/alarm-<schluessel> entsteht nur, wenn der Meldeweg Erfolg meldet (sonst versucht es der nächste Lauf wieder), und
# fällt mit fr_alarm_ende, sobald der Teil wieder gelingt. Wie lange eine Störung anhält, zeigt die Überwachung, nicht der Alarm.
fr_alarm() {  # <schluessel> <betreff> <text>
  local merker="$FR_DIENST/alarm-$1"
  [ -n "$FR_MELDEN" ] || return 0
  if [ -e "$merker" ]; then echo "Alarm \"$2\" already sent for this disruption (since $(cat "$merker" 2>/dev/null))."; return 0; fi
  if "$FR_MELDEN" high "$FR_TITEL: $2" "$3" > /dev/null 2>&1; then
    { mkdir -p "$FR_DIENST" && date -u +%Y-%m-%dT%H:%M:%SZ > "$merker"; } || echo "Warning: alarm marker not written."
  else
    echo "Warning: alarm not sent, the next run tries again."
  fi
}

fr_alarm_ende() {  # <schluessel>: Störung vorbei, eine spätere meldet wieder
  rm -f "$FR_DIENST/alarm-$1"
}

wege_pruefen() {  # Wege von außen: Jede Art Pfad des Konnektors muss über die öffentliche Adresse bei ihm ankommen
  # (Kopf X-Frieda), nicht bei nginx. Fehlt ein Ort im server-Block, geht die Seite, aber etwa das Kalender-Abo nicht
  # (1.11.2026). Nur Warnung im Protokoll, keine Meldung
  # (#445: kein Ausfall; die Abweichung meldet nginx_abgleichen einmal als Issue, der Monitor der Instanz prüft sie als
  # Warnung). Die Reiseseite selbst ist davon nicht betroffen. Die Abrufe kommen vom Server
  # selbst und zählen in nginx in dieselbe Begrenzung wie die Prüfung von freischalten.sh; veroeffentlichen.sh ruft sie
  # deshalb einmal je Lauf nach dem Freischalten auf (FR_WEGE_SPAETER), nicht je Reise (frieda-reist#163).
  # 429 heißt: Die Anfragebegrenzung von nginx (5/min auf /anmelden) hat gegriffen, der Ort ist da. Dann wartet die Prüfung
  # und fragt erneut, statt „fehlt“ zu melden (#279: 48 Fehlalarme an einem Tag).
  local weg fehlen="" kopf versuch
  [ -n "${FR_KN_ADRESSE:-}" ] || return 0
  systemctl is-enabled --quiet "$FR_INSTANZ-konnektor" 2>/dev/null || return 0
  # /manifest.webmanifest, /sw.js, /konto.js: Frieda-App und Schalter für Benachrichtigungen auf Mein Konto (#21); /info/: Bilder und Infoseite (#436, #440)
  for weg in /gesund /anmelden /kalender/0000000000000000000000000000000000000000.ics /schrift/pruefung.woff2 /favicon.svg \
             /manifest.webmanifest /sw.js /konto.js /info/pruefung.webp; do
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
}
