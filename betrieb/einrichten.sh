#!/usr/bin/env bash
# Richtet eine Instanz auf dem Server ein (docs/betrieb.md, Neue Instanz).
#
#   frieda/betrieb/einrichten.sh                 prüft Voraussetzungen, erzeugt systemd-Einheiten und nginx-Bausteine aus
#                                                vorlagen/ in einen Ordner und zeigt die Befehle zum Aktivieren
#   frieda/betrieb/einrichten.sh --installieren  dasselbe, dann nach Rückfrage installieren (sudo, ändert /etc)
#
# Werte aus den Einstellungen der Instanz (einstellungen.beispiel); dazu FR_BENUTZER, FR_GRUPPE, FR_HOME (Vorgabe: wer das
# Skript aufruft) und FR_PFAD (PATH der Dienste; claude, gh und node müssen darin liegen). Ohne --installieren ändert das
# Skript nichts außerhalb des Ausgabeordners (EI_ZIEL, Vorgabe /tmp/<instanz>-einrichten).
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
problem() { echo "  FEHLT   $*"; probleme=$((probleme + 1)); }
hinweis() { echo "  HINWEIS $*"; }

echo "Instanz $FR_INSTANZ ($FR_TITEL), Reisen-Repo $FR_WURZEL"
echo "Voraussetzungen:"
[ -f "$FR_WURZEL/engine/bauen.py" ] && ok "Software unter engine/" || problem "engine/ fehlt (Submodul frieda und Verweis engine -> frieda/engine, docs/betrieb.md)"
if "$FR_PYTHON" -c 'import yaml' 2> /dev/null; then ok "Python $FR_PYTHON"; else problem "Python mit yaml: $FR_PYTHON (python3 -m venv engine/.venv && engine/.venv/bin/pip install -r engine/requirements.txt)"; fi
[ -n "$FR_ADRESSE" ] && ok "Adresse $FR_ADRESSE" || problem "FR_ADRESSE (öffentliche Adresse der Seiten) in den Einstellungen"
git -C "$FR_WURZEL" ls-remote -q origin > /dev/null 2>&1 && ok "git erreicht origin" || problem "git -C $FR_WURZEL ls-remote origin geht nicht ohne Rückfrage"
PATH="$FR_PFAD" command -v claude > /dev/null && ok "Claude Code im PATH der Dienste" || problem "claude nicht in FR_PFAD ($FR_PFAD)"
if PATH="$FR_PFAD" command -v gh > /dev/null; then
  PATH="$FR_PFAD" gh auth status > /dev/null 2>&1 && ok "gh angemeldet" || problem "gh ist nicht angemeldet (gh auth login als $FR_BENUTZER)"
else problem "gh nicht in FR_PFAD"; fi
command -v flock > /dev/null && ok "flock" || problem "flock (util-linux)"
command -v rsync > /dev/null && ok "rsync" || problem "rsync"
if [ -d "$FR_SEITEN" ]; then
  [ -w "$FR_SEITEN" ] && ok "$FR_SEITEN beschreibbar" || problem "$FR_SEITEN gehört nicht $FR_BENUTZER"
else hinweis "$FR_SEITEN wird angelegt (sudo install -d -o $FR_BENUTZER -g $FR_GRUPPE $FR_SEITEN)"; fi
[ -n "$FR_MELDEN" ] && { [ -x "$FR_MELDEN" ] && ok "Meldeweg $FR_MELDEN" || problem "FR_MELDEN ist nicht ausführbar: $FR_MELDEN"; } \
  || hinweis "kein Meldeweg (FR_MELDEN): Fehler stehen nur im Journal"
for d in "$SYSTEMD"/*-rueckmeldungen.service "$SYSTEMD"/*-konnektor.service; do
  [ -e "$d" ] || continue
  case "$(basename "$d")" in "$FR_INSTANZ"-*) continue ;; esac
  if grep -qE "^Environment=(RM|KN)_PORT=($FR_RM_PORT|$FR_KN_PORT)$" "$d"; then
    problem "Port $FR_RM_PORT oder $FR_KN_PORT nutzt schon $(basename "$d"); FR_RM_PORT/FR_KN_PORT ändern"
  fi
done

# Einheiten und Bausteine erzeugen
rm -rf "$ZIEL"; mkdir -p "$ZIEL/systemd" "$ZIEL/nginx"
ersetze() {  # <vorlage> <ziel>
  sed -e "s|__INSTANZ__|$FR_INSTANZ|g" -e "s|__TITEL__|$FR_TITEL|g" -e "s|__WURZEL__|$FR_WURZEL|g" \
      -e "s|__BENUTZER__|$FR_BENUTZER|g" -e "s|__GRUPPE__|$FR_GRUPPE|g" -e "s|__PFAD__|$FR_PFAD|g" \
      -e "s|__SEITEN__|$FR_SEITEN|g" -e "s|__ABLAGE__|$FR_ABLAGE|g" -e "s|__DIENST__|$FR_DIENST|g" \
      -e "s|__KONNEKTOR__|$FR_KONNEKTOR|g" -e "s|__RM_PORT__|$FR_RM_PORT|g" -e "s|__KN_PORT__|$FR_KN_PORT|g" \
      -e "s|__KN_ADRESSE__|$FR_KN_ADRESSE|g" -e "s|__ZONE__|$ZONE|g" "$1" > "$2"
}
for v in "$FR_BETRIEB"/vorlagen/*.service "$FR_BETRIEB"/vorlagen/*.timer "$FR_BETRIEB"/vorlagen/*.path; do
  ersetze "$v" "$ZIEL/systemd/$FR_INSTANZ-$(basename "$v")"
done
ersetze "$FR_BETRIEB/vorlagen/nginx-konnektor.conf" "$ZIEL/nginx/$FR_INSTANZ-konnektor.conf"
ersetze "$FR_BETRIEB/vorlagen/nginx-zone.conf" "$ZIEL/nginx/$FR_INSTANZ-zone.conf"
if grep -rn "__[A-Z_]*__" "$ZIEL" > /dev/null; then
  problem "Platzhalter nicht ersetzt: $(grep -rho "__[A-Z_]*__" "$ZIEL" | sort -u | tr '\n' ' ')"
fi
echo "Erzeugt in $ZIEL:"; (cd "$ZIEL" && find . -type f | sort | sed 's|^\./|  |')

befehle() {
  cat <<TEXT
sudo install -d -o $FR_BENUTZER -g $FR_GRUPPE -m 755 $FR_SEITEN $FR_DIENST
sudo install -d -o $FR_BENUTZER -g $FR_GRUPPE -m 750 $FR_ABLAGE
sudo install -d -o $FR_BENUTZER -g $FR_GRUPPE -m 700 $FR_KONNEKTOR
sudo install -m 644 $ZIEL/systemd/* $SYSTEMD/
sudo install -m 644 $ZIEL/nginx/$FR_INSTANZ-zone.conf /etc/nginx/conf.d/
sudo install -m 640 $ZIEL/nginx/$FR_INSTANZ-konnektor.conf $SNIPPETS/
sudo systemctl daemon-reload
TEXT
}
echo
echo "Aktivieren (nachdem im server-Block von $FR_ADRESSE  include $SNIPPETS/$FR_INSTANZ-*.conf;  steht):"
befehle | sed 's/^/  /'
cat <<TEXT
  $FR_WURZEL/frieda/betrieb/deploy.sh <erste reise>     (legt Code der Dienste an, Prüfung schlägt vor dem Start fehl)
  sudo systemctl enable --now $FR_INSTANZ-rueckmeldungen $FR_INSTANZ-konnektor
  sudo nginx -t && sudo systemctl reload nginx
  sudo systemctl enable --now $FR_INSTANZ-veroeffentlichen.timer $FR_INSTANZ-einarbeiten.path $FR_INSTANZ-einarbeiten.timer $FR_INSTANZ-waechter.timer
Prüfen ohne Kosten:  date > $FR_ABLAGE/.neu;  journalctl -u $FR_INSTANZ-einarbeiten -n 20  zeigt „Nichts Neues.“
Für deploy.sh braucht $FR_BENUTZER: sudo -n systemctl restart $FR_INSTANZ-rueckmeldungen $FR_INSTANZ-konnektor;
für freischalten.sh: sudo -n nginx -t, systemctl reload nginx, install/test/cat/rm in $SNIPPETS (sudoers, docs/betrieb.md).
TEXT

if [ "$probleme" -gt 0 ]; then echo; echo "$probleme Voraussetzung(en) fehlen."; [ -z "$INSTALLIEREN" ] || exit 1; exit 2; fi
[ -n "$INSTALLIEREN" ] || exit 0
echo
read -r -p "Jetzt unter /etc installieren (Ordner, Einheiten, nginx-Bausteine)? Mit „ja“ bestätigen: " antwort
[ "$antwort" = ja ] || { echo "Nichts installiert."; exit 0; }
befehle | while IFS= read -r befehl; do echo "+ $befehl"; bash -c "$befehl"; done
echo "Installiert. Weiter mit deploy.sh, enable und nginx (siehe oben)."
