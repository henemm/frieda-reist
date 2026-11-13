#!/usr/bin/env bash
# Richtet eine Instanz auf dem Server ein (docs/betrieb.md, Neue Instanz).
#
#   betrieb/einrichten.sh                 prüft Voraussetzungen, erzeugt systemd-Einheiten und nginx-Bausteine aus
#                                         vorlagen/ in einen Ordner und zeigt die Befehle zum Aktivieren
#   betrieb/einrichten.sh --installieren  dasselbe, dann nach Rückfrage installieren (sudo, ändert /etc)
#
# Aufruf im Software-Klon (#454): FR_WURZEL=<FR_SEITEN>/_software, ein Klon dieses öffentlichen Repos auf main (ohne
# Anmeldung, ohne Reisen-Repo, ohne gh). Einstellungen der Instanz liegen in <FR_DIENST>/instanz/einstellungen.env
# (Vorlage einstellungen.beispiel), dazu optional <FR_DIENST>/instanz/melden.sh (Meldeweg) und tests/. Dazu FR_BENUTZER,
# FR_GRUPPE, FR_HOME (Vorgabe: wer das Skript aufruft) und FR_PFAD (PATH der Dienste; git und node müssen darin liegen).
# Ohne --installieren ändert das Skript nichts außerhalb des Ausgabeordners (EI_ZIEL, Vorgabe /tmp/<instanz>-einrichten).
# Zwei Instanzen auf einem Server: verschiedene FR_INSTANZ, FR_SEITEN und Ports; das Skript bricht ab, wenn eine andere
# installierte Instanz dieselben Ports nutzt.
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/gemeinsam.sh"

INSTALLIEREN=""
[ "${1:-}" = "--installieren" ] && INSTALLIEREN=1
# --erzeugen: nur die Einheiten und Bausteine nach EI_ZIEL schreiben (ohne Prüfungen, ohne Ausgabe, ohne Änderung an /etc);
# der Abgleich der Einheiten (units.py, #260) nutzt dieselbe Ersetzung wie die Einrichtung
NUR_ERZEUGEN=""
[ "${1:-}" = "--erzeugen" ] && NUR_ERZEUGEN=1
: "${FR_BENUTZER:=$(id -un)}"
: "${FR_GRUPPE:=$(id -gn "$FR_BENUTZER")}"
: "${FR_HOME:=$(getent passwd "$FR_BENUTZER" | cut -d: -f6)}"
: "${FR_PFAD:=$FR_HOME/.local/bin:$FR_HOME/.local/share/fnm/aliases/default/bin:/usr/local/bin:/usr/bin:/bin}"
SYSTEMD="${EI_SYSTEMD:-/etc/systemd/system}"
SNIPPETS="${FR_NGINX_SNIPPETS:-/etc/nginx/snippets}"
ZIEL="${EI_ZIEL:-${TMPDIR:-/tmp}/$FR_INSTANZ-einrichten}"
ZB="${FR_INSTANZ//-/_}"
ZONE="${ZB}_api"   # Zone der Reise-Bausteine (freischalten.sh), definiert in nginx-zone.conf (#316)
# Eigener Kartendienst (#444): nur mit FR_KARTENDIENST_REGIONEN; der Container lauscht eine Portnummer über dem Socket
KD_REGIONEN="${FR_KARTENDIENST_REGIONEN:-}"
KD_ORDNER="${FR_KARTENDIENST_ORDNER:-}"
KD_PORT="${FR_KARTENDIENST_PORT:-12345}"
KD_SPEICHER="${FR_KARTENDIENST_SPEICHER:-2g}"
KD_RUHE="${FR_KARTENDIENST_RUHE:-15min}"
# Ordner der Software, aus dem die Units die Skripte starten (#454): in der alten Anordnung das Submodul <FR_WURZEL>/frieda,
# im Software-Klon der Bauordner selbst. FR_DIENST als Umgebungswert der Unit nur im Klon (dort liegen die Einstellungen
# unter <FR_DIENST>/instanz/); in der alten Anordnung ein Kommentar, damit die Soll-Units den installierten gleichen
if fr_alte_anordnung; then
  SOFTWARE="$FR_WURZEL/frieda"; UMGEBUNG_DIENST="# FR_DIENST aus den Einstellungen (alte Anordnung, #454)"
else
  SOFTWARE="$FR_WURZEL"; UMGEBUNG_DIENST="Environment=FR_DIENST=$FR_DIENST"
fi

probleme=0
ok()      { echo "  ok      $*"; }
problem() { echo "  MISSING $*"; probleme=$((probleme + 1)); }
hinweis() { echo "  NOTE    $*"; }

# Eigene Drosselzonen der Instanz (nginx-zone.conf) und Adressen, die nicht zählen: Schleife immer, dazu FR_EIGENE_ADRESSEN
EIGENE_ADRESSEN=""; GESEHEN=" "
set -f   # keine Dateinamen-Erweiterung der Eingabe
shopt -s globasciiranges   # [0-9] meint nur ASCII-Ziffern
export LC_COLLATE=C
for a in 127.0.0.1 ::1 ${FR_EIGENE_ADRESSEN:-}; do
  # IPv4 oder IPv6 mit Größe des Netzes; kein „/0“ (das nähme jeden aus)
  if ! [[ "$a" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}(/([1-9]|[12][0-9]|3[0-2]))?$ || "$a" =~ ^[0-9A-Fa-f:]*:[0-9A-Fa-f:]*(/([1-9][0-9]?|1[01][0-9]|12[0-8]))?$ ]]; then
    problem "FR_EIGENE_ADRESSEN: not an address: $a"; continue
  fi
  case "$GESEHEN" in *" $a "*) continue ;; esac
  GESEHEN="$GESEHEN$a "
  EIGENE_ADRESSEN="${EIGENE_ADRESSEN:+$EIGENE_ADRESSEN\\n    }$a 1;"
done
set +f

if [ -n "$KD_REGIONEN" ]; then
  [[ "$KD_PORT" =~ ^[1-9][0-9]{1,4}$ ]] && [ "$KD_PORT" -lt 65535 ] || problem "FR_KARTENDIENST_PORT “$KD_PORT”: a port number below 65535"
  [[ "$KD_ORDNER" =~ ^/[A-Za-z0-9_./-]+$ ]] || problem "FR_KARTENDIENST_ORDNER (absolute data folder of the map service) in the settings"
  [[ "$KD_SPEICHER" =~ ^[1-9][0-9]*[kmg]$ ]] || problem "FR_KARTENDIENST_SPEICHER “$KD_SPEICHER”: e.g. 2g"
  [[ "$KD_RUHE" =~ ^[1-9][0-9]*(s|min|h)$ ]] || problem "FR_KARTENDIENST_RUHE “$KD_RUHE”: e.g. 15min"
fi
KD_PORT_INNEN=$((${KD_PORT//[!0-9]/0} + 1))

if [ -z "$NUR_ERZEUGEN" ]; then
echo "Instance $FR_INSTANZ ($FR_TITEL), software clone $FR_WURZEL"
echo "Prerequisites:"
[ -f "$FR_WURZEL/engine/bauen.py" ] && ok "software under engine/" \
  || problem "engine/ is missing: FR_WURZEL is the software clone (git clone --branch main <software repo> $FR_SEITEN/_software, docs/betrieb.md)"
if "$FR_PYTHON" -c 'import yaml, ruamel.yaml' 2> /dev/null; then ok "Python $FR_PYTHON"; else problem "Python with yaml and ruamel.yaml: $FR_PYTHON (python3 -m venv $FR_DIENST/python && $FR_DIENST/python/bin/pip install -r $FR_WURZEL/engine/requirements.txt)"; fi
[ -n "$FR_ADRESSE" ] && ok "address $FR_ADRESSE" || problem "FR_ADRESSE (public address of the pages) in the settings"
# Die Software kommt öffentlich und ohne Anmeldung (#454): ein Probeabruf von main ohne Rückfrage
GIT_TERMINAL_PROMPT=0 git -C "$FR_WURZEL" fetch -q --dry-run origin main > /dev/null 2>&1 && ok "software clone fetches main without sign-in" \
  || problem "git -C $FR_WURZEL fetch origin main does not work without a prompt (clone of the public software repo?)"
[ -f "$FR_DIENST/instanz/einstellungen.env" ] && ok "settings of the instance $FR_DIENST/instanz/einstellungen.env" \
  || hinweis "settings of the instance: copy betrieb/einstellungen.beispiel to $FR_DIENST/instanz/einstellungen.env"
# The connector stands at the root of its address: pages link to /anmelden, OAuth expects /.well-known/ (#163)
if [ -z "$FR_KN_ADRESSE" ] || [[ "$FR_KN_ADRESSE" =~ ^https://[^/]+$ ]]; then [ -z "$FR_KN_ADRESSE" ] || ok "connector at $FR_KN_ADRESSE/mcp"
else problem "FR_KN_ADRESSE “$FR_KN_ADRESSE”: only https://<host>, without path and without trailing / (the connector stands at the root)"; fi
command -v flock > /dev/null && ok "flock" || problem "flock (util-linux)"
command -v rsync > /dev/null && ok "rsync" || problem "rsync"
if [ -n "$KD_REGIONEN" ]; then   # eigener Kartendienst (#444)
  command -v docker > /dev/null && ok "docker (own map service)" || problem "docker (own map service, FR_KARTENDIENST_REGIONEN)"
  [ -x /usr/lib/systemd/systemd-socket-proxyd ] && ok "systemd-socket-proxyd" || problem "/usr/lib/systemd/systemd-socket-proxyd (own map service)"
fi
if [ -d "$FR_SEITEN" ]; then
  [ -w "$FR_SEITEN" ] && ok "$FR_SEITEN writable" || problem "$FR_SEITEN does not belong to $FR_BENUTZER"
else hinweis "$FR_SEITEN will be created (sudo install -d -o $FR_BENUTZER -g $FR_GRUPPE $FR_SEITEN)"; fi
[ -n "$FR_MELDEN" ] && { [ -x "$FR_MELDEN" ] && ok "reporting channel $FR_MELDEN" || problem "FR_MELDEN is not executable: $FR_MELDEN"; } \
  || hinweis "no reporting channel (FR_MELDEN): errors appear only in the journal"
for d in "$SYSTEMD"/*-rueckmeldungen.service "$SYSTEMD"/*-konnektor.service "$SYSTEMD"/*-schreiben.service; do
  [ -e "$d" ] || continue
  case "$(basename "$d")" in "$FR_INSTANZ"-*) continue ;; esac
  if grep -qE "^Environment=(RM_PORT|KN_PORT|FR_SB_PORT)=($FR_RM_PORT|$FR_KN_PORT|$FR_SB_PORT)$" "$d"; then
    problem "Port $FR_RM_PORT, $FR_KN_PORT or $FR_SB_PORT is already used by $(basename "$d"); change FR_RM_PORT/FR_KN_PORT/FR_SB_PORT"
  fi
done
fi   # NUR_ERZEUGEN

# Einheiten und Bausteine erzeugen
rm -rf "$ZIEL"; mkdir -p "$ZIEL/systemd" "$ZIEL/nginx"
ersetze() {  # <vorlage> <ziel>
  sed -e "s|__INSTANZ__|$FR_INSTANZ|g" -e "s|__TITEL__|$FR_TITEL|g" -e "s|__SOFTWARE__|$SOFTWARE|g" -e "s|__UMGEBUNG_DIENST__|$UMGEBUNG_DIENST|g" -e "s|__WURZEL__|$FR_WURZEL|g" \
      -e "s|__BENUTZER__|$FR_BENUTZER|g" -e "s|__GRUPPE__|$FR_GRUPPE|g" -e "s|__PFAD__|$FR_PFAD|g" \
      -e "s|__SEITEN__|$FR_SEITEN|g" -e "s|__ABLAGE__|$FR_ABLAGE|g" -e "s|__DIENST__|$FR_DIENST|g" \
      -e "s|__KONNEKTOR__|$FR_KONNEKTOR|g" -e "s|__KONTEN__|$FR_KONTEN|g" -e "s|__RM_PORT__|$FR_RM_PORT|g" -e "s|__KN_PORT__|$FR_KN_PORT|g" \
      -e "s|__SB_PORT__|$FR_SB_PORT|g" -e "s|__PYTHON__|$FR_PYTHON|g" -e "s|__ZEITZONE__|$FR_ZEITZONE|g" \
      -e "s|__KN_ADRESSE__|$FR_KN_ADRESSE|g" -e "s|__ZONE__|$ZONE|g" -e "s|__SNIPPETS__|$SNIPPETS|g" \
      -e "s|__ZONE_API__|$ZONE|g" -e "s|__ZONE_MCP__|${ZB}_mcp|g" -e "s|__ZONE_ANMELDEN__|${ZB}_anmelden|g" -e "s|__ZONE_KONTO__|${ZB}_konto|g" \
      -e "s|__EIGENE_ADRESSEN__|$EIGENE_ADRESSEN|g" -e "s|__EIGEN__|${ZB}_eigen|g" -e "s|__SCHLUESSEL__|${ZB}_schluessel|g" \
      -e "s|__KD_PORT__|$KD_PORT|g" -e "s|__KD_PORT_INNEN__|$KD_PORT_INNEN|g" -e "s|__KD_ORDNER__|$KD_ORDNER|g" \
      -e "s|__KD_SPEICHER__|$KD_SPEICHER|g" -e "s|__KD_RUHE__|$KD_RUHE|g" -e "s|__KD_BILD__|$KD_BILD|g" "$1" > "$2"
}
for v in "$FR_BETRIEB"/vorlagen/*.service "$FR_BETRIEB"/vorlagen/*.timer; do
  ersetze "$v" "$ZIEL/systemd/$FR_INSTANZ-$(basename "$v")"
done
ersetze "$FR_BETRIEB/vorlagen/nginx-konnektor-orte.inc" "$ZIEL/nginx/$FR_INSTANZ-konnektor-orte.inc"
ersetze "$FR_BETRIEB/vorlagen/nginx-konnektor.inc" "$ZIEL/nginx/$FR_INSTANZ-konnektor.inc"
ersetze "$FR_BETRIEB/vorlagen/nginx-zone.conf" "$ZIEL/nginx/$FR_INSTANZ-zone.conf"
# Eigener Kartendienst (#444): eigener Unterordner, damit der Abgleich der Einheiten (#260) ihn nicht sieht
if [ -n "$KD_REGIONEN" ]; then
  mkdir -p "$ZIEL/kartendienst"
  for v in "$FR_BETRIEB"/vorlagen/kartendienst/*; do
    ersetze "$v" "$ZIEL/kartendienst/$FR_INSTANZ-$(basename "$v")"
  done
fi
# Hilfsprogramm mit Root-Rechten für den Abgleich der Einheiten (#260): wird bewusst einmal installiert (docs/betrieb.md)
mkdir -p "$ZIEL/sbin"
ersetze "$FR_BETRIEB/vorlagen/units-installieren.py" "$ZIEL/sbin/$FR_INSTANZ-units-installieren"
# Hilfsprogramm mit Root-Rechten für die Orte-Datei des Konnektors (#445): ebenso einmal bewusst installiert
ersetze "$FR_BETRIEB/vorlagen/nginx-orte-installieren.py" "$ZIEL/sbin/$FR_INSTANZ-nginx-orte-installieren"
if grep -rn "__[A-Z_]*__" "$ZIEL" > /dev/null; then
  problem "placeholder not replaced: $(grep -rho "__[A-Z_]*__" "$ZIEL" | sort -u | tr '\n' ' ')"
fi
if [ -n "$NUR_ERZEUGEN" ]; then [ "$probleme" -eq 0 ] || exit 1; exit 0; fi
echo "Generated in $ZIEL:"; (cd "$ZIEL" && find . -type f | sort | sed 's|^\./|  |')

befehle() {
  cat <<TEXT
sudo install -d -o $FR_BENUTZER -g $FR_GRUPPE -m 755 $FR_SEITEN $FR_DIENST
sudo install -d -o $FR_BENUTZER -g $FR_GRUPPE -m 700 $FR_DIENST/instanz
TEXT
  # Software-Klon (#454): der Bauordner, öffentlich und ohne Anmeldung, nur main
  [ -d "$FR_SEITEN/_software/.git" ] || echo "git clone -q --branch main --single-branch $(git -C "$FR_BETRIEB/.." config --get remote.origin.url 2>/dev/null || echo '<software repo>') $FR_SEITEN/_software"
  cat <<TEXT
sudo install -d -o $FR_BENUTZER -g $FR_GRUPPE -m 750 $FR_ABLAGE
sudo install -d -o $FR_BENUTZER -g $FR_GRUPPE -m 700 $FR_KONNEKTOR $FR_KONTEN
sudo install -m 644 $ZIEL/systemd/* $SYSTEMD/
sudo install -m 644 $ZIEL/nginx/$FR_INSTANZ-zone.conf /etc/nginx/conf.d/
sudo install -m 640 $ZIEL/nginx/$FR_INSTANZ-konnektor-orte.inc $ZIEL/nginx/$FR_INSTANZ-konnektor.inc $SNIPPETS/
TEXT
  [ -z "$KD_REGIONEN" ] || cat <<TEXT
sudo install -d -o $FR_BENUTZER -g $FR_GRUPPE -m 755 $KD_ORDNER
sudo usermod -aG docker $FR_BENUTZER
sudo install -m 644 $ZIEL/kartendienst/* $SYSTEMD/
TEXT
  echo "sudo systemctl daemon-reload"
}
echo
echo "Activate (once the server block of $FR_ADRESSE contains  include $SNIPPETS/$FR_INSTANZ-*.conf;"
echo "the connector stands at the root of $FR_KN_ADRESSE, whose server block includes $FR_INSTANZ-konnektor-orte.inc):"
befehle | sed 's/^/  /'
cat <<TEXT
  cd $FR_WURZEL && FR_WURZEL=$FR_WURZEL betrieb/deploy.sh --dienste   (installs the code of the services; the check fails before the start)
  sudo systemctl enable --now $FR_INSTANZ-rueckmeldungen $FR_INSTANZ-konnektor $FR_INSTANZ-schreiben $FR_INSTANZ-push
  sudo nginx -t && sudo systemctl reload nginx
  sudo systemctl enable --now $FR_INSTANZ-veroeffentlichen.timer $FR_INSTANZ-waechter.timer
Check:  curl -s 127.0.0.1:$FR_SB_PORT/gesund  answers {"gesund": true};  journalctl -u $FR_INSTANZ-veroeffentlichen -n 20
deploy.sh needs for $FR_BENUTZER: sudo -n systemctl restart $FR_INSTANZ-rueckmeldungen $FR_INSTANZ-konnektor $FR_INSTANZ-schreiben $FR_INSTANZ-push;
freischalten.sh needs: sudo -n nginx -t, systemctl reload nginx, install/test/cat/rm in $SNIPPETS (sudoers, docs/betrieb.md).
Units helper (#260, once, deliberately; without it only differences are reported, nothing is installed):
  sudo install -m 755 -o root -g root $ZIEL/sbin/$FR_INSTANZ-units-installieren /usr/local/sbin/
  sudoers for $FR_BENUTZER: NOPASSWD: /usr/local/sbin/$FR_INSTANZ-units-installieren
TEXT
[ -z "$KD_REGIONEN" ] || cat <<TEXT
Own map service (#444; regions: $KD_REGIONEN): first import as $FR_BENUTZER, then enable socket and timer:
  cd $FR_WURZEL && FR_WURZEL=$FR_WURZEL betrieb/kartendienst.sh einspielen
  sudo systemctl enable --now $FR_INSTANZ-kartendienst.socket
  sudo systemctl enable --now $FR_INSTANZ-kartendienst-aktualisieren.timer
  Settings: FR_KARTENDIENST=http://127.0.0.1:$KD_PORT/api/interpreter  (map_points_fetch asks it first inside its coverage, FR_KARTENDIENST_ORDNER tells it which)
TEXT
cat <<TEXT
nginx locations helper (#445, once, deliberately; installs only $FR_INSTANZ-konnektor-orte.inc, without it only differences are reported):
  sudo install -m 755 -o root -g root $ZIEL/sbin/$FR_INSTANZ-nginx-orte-installieren /usr/local/sbin/
  sudoers for $FR_BENUTZER: NOPASSWD: /usr/local/sbin/$FR_INSTANZ-nginx-orte-installieren
TEXT

if [ "$probleme" -gt 0 ]; then echo; echo "$probleme prerequisite(s) missing."; [ -z "$INSTALLIEREN" ] || exit 1; exit 2; fi
[ -n "$INSTALLIEREN" ] || exit 0
echo
read -r -p "Install under /etc now (folders, units, nginx blocks)? Confirm with “yes”: " antwort
[ "$antwort" = yes ] || [ "$antwort" = ja ] || { echo "Nothing installed."; exit 0; }
befehle | while IFS= read -r befehl; do echo "+ $befehl"; bash -c "$befehl"; done
echo "Installed. Continue with deploy.sh, enable and nginx (see above)."
