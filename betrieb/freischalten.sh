#!/usr/bin/env bash
# Schaltet eine veröffentlichte Reise frei, ohne Handarbeit (docs/neue-reise.md, docs/betrieb.md).
#
#   frieda/betrieb/freischalten.sh <reise>                    geheimer Link zur Seite (falls noch keiner da ist), Prüfung, seiten.json
#   frieda/betrieb/freischalten.sh <reise> --person <schl.>   dazu ein persönlicher Link für die Claude-App (Person aus reise.yaml)
#
# Gibt es noch kein nginx-Baustein <FR_NGINX_SNIPPETS>/<instanz>-<reise>.conf, entsteht er aus vorlagen/nginx-reise.conf
# mit einem neuen Zufalls-Token (root, 640). nginx wird geprüft und neu geladen; schlägt die Prüfung fehl, wird der
# Baustein wieder entfernt. Danach müssen Seite und Rückmeldedienst unter dem Link mit 200 antworten, sonst Abbruch.
# Gibt es den Baustein schon, bleibt der Link, wie er ist (beliebig oft aufrufbar; veroeffentlichen.sh ruft es je Reise auf);
# hat sich nur die Vorlage geändert, wird der Baustein mit demselben Pfad erneuert (nginx geprüft, sonst alter Stand). Der
# Pfad wird aus dem Baustein gelesen und muss nicht mit dem Ordner der Reise beginnen (von Hand angelegte Bausteine).
# Der Link zur Seite kommt nach seiten.json neben den Konnektor-Zugängen (für das Werkzeug meine_reisen).
#
# Voraussetzung (einmalig, einrichten.sh): Im server-Block von FR_ADRESSE steht  include <FR_NGINX_SNIPPETS>/<instanz>-*.conf;
# Ausgabe: „Seite: <url>“ und mit --person „Claude-App: <url>“. Links nie ins Repo, in Issues oder Nachrichten.
# Für Tests überschreibbar: FS_SNIPPETS, FS_BASIS, FS_SUDO, FS_NGINX_TEST, FS_NGINX_LADEN, FS_ABRUF, KN_SEITENLINKS.
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/gemeinsam.sh"

REISE="${1:?Aufruf: freischalten.sh <reise> [--person <schluessel>]}"
PERSON=""
[ "${2:-}" = "--person" ] && PERSON="${3:?--person braucht einen Schlüssel aus reise.yaml}"
WURZEL="$FR_WURZEL"
SNIPPETS="${FS_SNIPPETS:-${FR_NGINX_SNIPPETS:-/etc/nginx/snippets}}"
BASIS="${FS_BASIS:-$FR_ADRESSE}"
SUDO="${FS_SUDO-${FR_SUDO-sudo -n}}"
NGINX_TEST="${FS_NGINX_TEST:-$SUDO nginx -t -q}"
NGINX_LADEN="${FS_NGINX_LADEN:-$SUDO systemctl reload nginx}"
ZUGAENGE="$KN_ZUGAENGE"
SEITENLINKS="${KN_SEITENLINKS:-$(dirname "$ZUGAENGE")/seiten.json}"

abruf() {  # <url> -> HTTP-Code
  if [ -n "${FS_ABRUF:-}" ]; then $FS_ABRUF "$1"; else curl -s -o /dev/null -w '%{http_code}' --max-time 15 "$1"; fi
}

[[ "$REISE" =~ ^[a-z0-9][a-z0-9-]{1,39}$ ]] || { echo "FEHLER: Reise „$REISE“: nur Kleinbuchstaben, Ziffern, Bindestrich."; exit 1; }
[ -f "$WURZEL/reisen/$REISE/reise.yaml" ] || [ -f "$WURZEL/reisen/$REISE/reise.json" ] \
  || { echo "FEHLER: Reise „$REISE“ gibt es nicht."; exit 1; }
[ -n "$BASIS" ] || { echo "FEHLER: FR_ADRESSE ist nicht gesetzt (Einstellungen der Instanz)."; exit 1; }

snippet="$SNIPPETS/$FR_INSTANZ-$REISE.conf"
rendern() {  # <pfad> -> Baustein aus der Vorlage; der Pfad ist das erste Glied des geheimen Links („<reise>-<token>“)
  # Der Pfad wird als Ganzes eingesetzt, nicht aus Reise und Token zusammengesetzt: Ein von Hand angelegter Baustein
  # kann einen anderen Namen als den Ordner der Reise tragen (etwa „japan-…“ für „japan-2027“), und der Link muss bleiben.
  sed -e "s|__REISE__-__TOKEN__|$1|g" -e "s|__TOKEN__|${1##*-}|g" -e "s|__REISE__|$REISE|g" -e "s|__SEITEN__|$FR_SEITEN|g" \
    -e "s|__RM_PORT__|$FR_RM_PORT|g" -e "s|__ZONE__|${FR_INSTANZ//-/_}_api|g" -e "s|__INSTANZ__|$FR_INSTANZ|g" \
    "$FR_BETRIEB/vorlagen/nginx-reise.conf"
}
pfad_aus() {  # <baustein> -> erstes Glied des Pfads aus dem ersten location-Block, leer wenn keiner da ist
  printf '%s\n' "$1" | grep -oP '^location \^~ /\K[^/]+(?=/ \{)' | head -1 || true
}
tmp="$(mktemp)"; trap 'rm -f "$tmp"' EXIT
neu=""
if ! $SUDO test -e "$snippet"; then
  token="$(python3 -c 'import secrets; print(secrets.token_hex(12))')"
  rendern "$REISE-$token" > "$tmp"
  $SUDO install -m 640 "$tmp" "$snippet"
  if ! $NGINX_TEST; then
    $SUDO rm -f "$snippet"
    echo "FEHLER: nginx lehnt die Konfiguration ab; Snippet für $REISE wieder entfernt, nichts geändert."; exit 1
  fi
  $NGINX_LADEN
  neu=1
else
  # Hat sich die Vorlage geändert (z. B. ein neuer location-Block, 29.10.2026 Belege #76), bekommt der Baustein den neuen
  # Stand mit demselben Pfad; der Link bleibt. Lehnt nginx ab, kommt der alte Stand zurück.
  alt="$($SUDO cat "$snippet")"
  pfad="$(pfad_aus "$alt")"
  [ -n "$pfad" ] || { echo "FEHLER: Im Baustein $snippet steht kein Pfad (location ^~ /<reise>-<token>/ fehlt)."; exit 1; }
  rendern "$pfad" > "$tmp"
  if [ "$(cat "$tmp")" != "$alt" ]; then
    sicher="$(mktemp)"; printf '%s\n' "$alt" > "$sicher"
    $SUDO install -m 640 "$tmp" "$snippet"
    if ! $NGINX_TEST; then
      $SUDO install -m 640 "$sicher" "$snippet"; rm -f "$sicher"
      echo "FEHLER: nginx lehnt den erneuerten Baustein für $REISE ab; der alte Stand gilt weiter."; exit 1
    fi
    rm -f "$sicher"
    $NGINX_LADEN
    echo "Baustein erneuert: $REISE"
  fi
fi

pfad="$(pfad_aus "$($SUDO cat "$snippet")")"
[ -n "$pfad" ] || { echo "FEHLER: Im Snippet $snippet steht kein Pfad."; exit 1; }
url="$BASIS/$pfad/"
# Nach dem Neuladen braucht nginx einen Moment, bis die neuen Pfade gelten: Ein neuer Link wird deshalb mehrmals versucht.
versuche=1; [ -n "$neu" ] && versuche="${FS_VERSUCHE:-10}"
for teil in "Seite|" "Rückmeldedienst|api/gesund"; do
  for ((i = 1; ; i++)); do
    code="$(abruf "$url${teil#*|}" || true)"
    { [ "$code" = 200 ] || [ "$i" -ge "$versuche" ]; } && break
    sleep "${FS_WARTEN:-1}"
  done
  [ "$code" = 200 ] || { echo "FEHLER: ${teil%|*} von $REISE antwortet mit ${code:-nichts} statt 200${neu:+ (Link eben angelegt; fehlt das include in nginx?)}."; exit 1; }
done
[ -n "$neu" ] && echo "Freigeschaltet: $REISE"

# Link zur Seite für meine_reisen (Datei nur für den Betreiber lesbar, wie die Zugänge)
python3 - "$SEITENLINKS" "$REISE" "$url" <<'PY'
import json, os, sys
from pathlib import Path
p, reise, url = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
try:
    d = json.loads(p.read_text(encoding="utf-8"))
except (OSError, ValueError):
    d = {}
if d.get(reise) != url:
    d[reise] = url
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    os.chmod(tmp, 0o600)
    tmp.replace(p)
PY
echo "Seite: $url"

if [ -n "$PERSON" ]; then
  [ -n "${KN_BASIS:-}" ] || { echo "FEHLER: FR_KN_ADRESSE ist nicht gesetzt (Einstellungen der Instanz)."; exit 1; }
  link="$(python3 "$WURZEL/engine/konnektor.py" zugang "$REISE" "$PERSON" | grep -oE 'https?://[^ ]+$')"
  [ -n "$link" ] || { echo "FEHLER: Kein Link für die Claude-App ausgestellt."; exit 1; }
  echo "Claude-App: $link"
fi
