#!/usr/bin/env bash
# Richtet eine Instanz auf dem Server ein (docs/betrieb.md, Neue Instanz).
#
#   frieda/betrieb/einrichten.sh                 prüft Voraussetzungen, erzeugt systemd-Einheiten und nginx-Bausteine aus
#                                                vorlagen/ in einen Ordner und zeigt die Befehle zum Aktivieren
#   frieda/betrieb/einrichten.sh --installieren  dasselbe, dann nach Rückfrage installieren (sudo, ändert /etc)
#
# Werte aus den Einstellungen der Instanz (einstellungen.beispiel); dazu FR_BENUTZER, FR_GRUPPE, FR_HOME (Vorgabe: wer das
# Skript aufruft) und FR_PFAD (PATH der Dienste; git, gh und node müssen darin liegen). Als Dienstbenutzer aufrufen,
# damit die Anmeldung von gh (Credential-Helfer für git push des Schreibwegs) geprüft wird. Ohne --installieren ändert
# das Skript nichts außerhalb des
# Ausgabeordners (EI_ZIEL, Vorgabe /tmp/<instanz>-einrichten).
# Zwei Instanzen auf einem Server: verschiedene FR_INSTANZ, FR_SEITEN und Ports; das Skript bricht ab, wenn eine andere
# installierte Instanz dieselben Ports nutzt.
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/gemeinsam.sh"

INSTALLIEREN=""
[ "${1:-}" = "--installieren" ] && INSTALLIEREN=1
: "${FR_BENUTZER:=$(id -un)}"
: "${FR_GRUPPE:=$(id -gn "$FR_BENUTZER")}"
: "${FR_HOME:=$(getent passwd "$FR_BENUTZER" | cut -d: -f6)}"
: "${FR_PFAD:=$FR_HOME/.local/bin:$FR_HOME/.local/share/fnm/aliases/default/bin:/usr/local/bin:/usr/bin:/bin}"
SYSTEMD="${EI_SYSTEMD:-/etc/systemd/system}"
SNIPPETS="${FR_NGINX_SNIPPETS:-/etc/nginx/snippets}"
ZIEL="${EI_ZIEL:-${TMPDIR:-/tmp}/$FR_INSTANZ-einrichten}"
ZONE="${FR_INSTANZ//-/_}_api"

probleme=0
ok()      { echo "  ok      $*"; }
problem() { echo "  MISSING $*"; probleme=$((probleme + 1)); }
hinweis() { echo "  NOTE    $*"; }

echo "Instance $FR_INSTANZ ($FR_TITEL), trips repo $FR_WURZEL"
echo "Prerequisites:"
[ -f "$FR_WURZEL/engine/bauen.py" ] && ok "software under engine/" || problem "engine/ is missing (submodule frieda and link engine -> frieda/engine, docs/betrieb.md)"
if "$FR_PYTHON" -c 'import yaml, ruamel.yaml' 2> /dev/null; then ok "Python $FR_PYTHON"; else problem "Python with yaml and ruamel.yaml: $FR_PYTHON (python3 -m venv engine/.venv && engine/.venv/bin/pip install -r engine/requirements.txt)"; fi
[ -n "$FR_ADRESSE" ] && ok "address $FR_ADRESSE" || problem "FR_ADRESSE (public address of the pages) in the settings"
git -C "$FR_WURZEL" ls-remote -q origin > /dev/null 2>&1 && ok "git reaches origin" || problem "git -C $FR_WURZEL ls-remote origin does not work without a prompt"
if PATH="$FR_PFAD" command -v gh > /dev/null; then
  # Der Schreibweg pusht nach main mit gh als Credential-Helfer; ohne Anmeldung scheitert jeder Schreibvorgang
  PATH="$FR_PFAD" gh auth status > /dev/null 2>&1 && ok "gh signed in" || problem "gh is not signed in (gh auth login as $FR_BENUTZER)"
else problem "gh not in FR_PFAD"; fi
command -v flock > /dev/null && ok "flock" || problem "flock (util-linux)"
command -v rsync > /dev/null && ok "rsync" || problem "rsync"
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

# Einheiten und Bausteine erzeugen
rm -rf "$ZIEL"; mkdir -p "$ZIEL/systemd" "$ZIEL/nginx"
ersetze() {  # <vorlage> <ziel>
  sed -e "s|__INSTANZ__|$FR_INSTANZ|g" -e "s|__TITEL__|$FR_TITEL|g" -e "s|__WURZEL__|$FR_WURZEL|g" \
      -e "s|__BENUTZER__|$FR_BENUTZER|g" -e "s|__GRUPPE__|$FR_GRUPPE|g" -e "s|__PFAD__|$FR_PFAD|g" \
      -e "s|__SEITEN__|$FR_SEITEN|g" -e "s|__ABLAGE__|$FR_ABLAGE|g" -e "s|__DIENST__|$FR_DIENST|g" \
      -e "s|__KONNEKTOR__|$FR_KONNEKTOR|g" -e "s|__KONTEN__|$FR_KONTEN|g" -e "s|__RM_PORT__|$FR_RM_PORT|g" -e "s|__KN_PORT__|$FR_KN_PORT|g" \
      -e "s|__SB_PORT__|$FR_SB_PORT|g" -e "s|__PYTHON__|$FR_PYTHON|g" \
      -e "s|__KN_ADRESSE__|$FR_KN_ADRESSE|g" -e "s|__ZONE__|$ZONE|g" "$1" > "$2"
}
for v in "$FR_BETRIEB"/vorlagen/*.service "$FR_BETRIEB"/vorlagen/*.timer; do
  ersetze "$v" "$ZIEL/systemd/$FR_INSTANZ-$(basename "$v")"
done
ersetze "$FR_BETRIEB/vorlagen/nginx-konnektor.conf" "$ZIEL/nginx/$FR_INSTANZ-konnektor.conf"
ersetze "$FR_BETRIEB/vorlagen/nginx-zone.conf" "$ZIEL/nginx/$FR_INSTANZ-zone.conf"
if grep -rn "__[A-Z_]*__" "$ZIEL" > /dev/null; then
  problem "placeholder not replaced: $(grep -rho "__[A-Z_]*__" "$ZIEL" | sort -u | tr '\n' ' ')"
fi
echo "Generated in $ZIEL:"; (cd "$ZIEL" && find . -type f | sort | sed 's|^\./|  |')

befehle() {
  cat <<TEXT
sudo install -d -o $FR_BENUTZER -g $FR_GRUPPE -m 755 $FR_SEITEN $FR_DIENST
sudo install -d -o $FR_BENUTZER -g $FR_GRUPPE -m 750 $FR_ABLAGE
sudo install -d -o $FR_BENUTZER -g $FR_GRUPPE -m 700 $FR_KONNEKTOR $FR_KONTEN
sudo install -m 644 $ZIEL/systemd/* $SYSTEMD/
sudo install -m 644 $ZIEL/nginx/$FR_INSTANZ-zone.conf /etc/nginx/conf.d/
sudo install -m 640 $ZIEL/nginx/$FR_INSTANZ-konnektor.conf $SNIPPETS/
sudo systemctl daemon-reload
TEXT
}
echo
echo "Activate (once the server block of $FR_ADRESSE contains  include $SNIPPETS/$FR_INSTANZ-*.conf; ):"
befehle | sed 's/^/  /'
cat <<TEXT
  cd $FR_WURZEL && FR_WURZEL=$FR_WURZEL frieda/betrieb/deploy.sh <first trip>   (installs the code of the services; the check fails before the start)
  sudo systemctl enable --now $FR_INSTANZ-rueckmeldungen $FR_INSTANZ-konnektor $FR_INSTANZ-schreiben
  sudo nginx -t && sudo systemctl reload nginx
  sudo systemctl enable --now $FR_INSTANZ-veroeffentlichen.timer $FR_INSTANZ-waechter.timer
Check:  curl -s 127.0.0.1:$FR_SB_PORT/gesund  answers {"gesund": true};  journalctl -u $FR_INSTANZ-veroeffentlichen -n 20
deploy.sh needs for $FR_BENUTZER: sudo -n systemctl restart $FR_INSTANZ-rueckmeldungen $FR_INSTANZ-konnektor $FR_INSTANZ-schreiben;
freischalten.sh needs: sudo -n nginx -t, systemctl reload nginx, install/test/cat/rm in $SNIPPETS (sudoers, docs/betrieb.md).
TEXT

if [ "$probleme" -gt 0 ]; then echo; echo "$probleme prerequisite(s) missing."; [ -z "$INSTALLIEREN" ] || exit 1; exit 2; fi
[ -n "$INSTALLIEREN" ] || exit 0
echo
read -r -p "Install under /etc now (folders, units, nginx blocks)? Confirm with “yes”: " antwort
[ "$antwort" = yes ] || [ "$antwort" = ja ] || { echo "Nothing installed."; exit 0; }
befehle | while IFS= read -r befehl; do echo "+ $befehl"; bash -c "$befehl"; done
echo "Installed. Continue with deploy.sh, enable and nginx (see above)."
