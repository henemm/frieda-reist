#!/usr/bin/env bash
# Einmaliger Umzug der Daten des eigenen Kartendienstes in den Zustandsordner des Karte-Benutzers (#552, Entscheidung 10).
#
#   kartendienst-umzug.sh <FR_KARTENDIENST_ORDNER> /var/lib/<instanz>-kartendienst <instanz>-karte
#
# Ruft einrichten.sh --installieren mit Root-Rechten auf. Danach liegen die Daten in <ziel>/daten (der Ordner gehört dem
# Karte-Benutzer, 755, lesbar für Konnektor und Container), und an der Stelle von FR_KARTENDIENST_ORDNER steht ein Verweis dorthin (root-eigen, wenn
# als root aufgerufen). Leser (Konnektor, Docker-Bind-Mount der Einheit) nutzen den Pfad unverändert; das Umschalten beim
# Einspielen geschieht im Zustandsordner, nicht im Elternordner von FR_KARTENDIENST_ORDNER (der gehört der Instanz).
#
# Wiederholbar, verliert nichts: Erst eine vollständige Kopie unter <ziel>/daten.umzug, dann umbenennen (gleicher Ordner), erst
# dann der alte Ordner weg. Bricht ein Lauf ab, bleibt entweder der alte Ordner ganz stehen (Kopie unfertig, wird beim nächsten
# Lauf neu gemacht) oder die Daten liegen schon vollständig am Ziel (der Rest am alten Ort wird beim nächsten Lauf entfernt).
# Ein Verweis, der woandershin zeigt, oder etwas anderes als ein Ordner an der Stelle: Fehler, nichts geändert.
set -euo pipefail

ordner="${1:-}"; ziel="${2:-}"; benutzer="${3:-}"
ordner="${ordner%/}"; ziel="${ziel%/}"
muster='^/[A-Za-z0-9_./-]+$'
if ! [[ "$ordner" =~ $muster && "$ziel" =~ $muster && "$benutzer" =~ ^[a-z_][a-z0-9_-]*$ ]]; then
  echo "usage: kartendienst-umzug.sh <data folder> <state folder> <user>" >&2; exit 2
fi
daten="$ziel/daten"

if [ -L "$ordner" ]; then
  if [ "$(readlink "$ordner")" = "$daten" ]; then echo "Map service data already in $daten."; exit 0; fi
  echo "ERROR: $ordner points to $(readlink "$ordner"), not to $daten; nothing changed." >&2; exit 1
fi
if [ -e "$ordner" ] && [ ! -d "$ordner" ]; then
  echo "ERROR: $ordner is neither a folder nor a link; nothing changed." >&2; exit 1
fi

install -d -m 755 "$ziel"
chown "$benutzer:" "$ziel" 2>/dev/null || chown "$benutzer" "$ziel"
if [ -d "$ordner" ]; then
  if [ ! -e "$daten" ]; then
    rm -rf "$daten.umzug"                     # Rest eines abgebrochenen Laufs (der alte Ordner ist noch ganz da)
    cp -a "$ordner" "$daten.umzug"
    # Nur der Ordner selbst wechselt den Eigentümer, der Inhalt nie: Die Datenbank gehört dem Benutzer im Container (overpass,
    # Kennung 1000 im Abbild; dessen Start setzt das selbst), sonst scheitert der Abfragedienst beim Start an seinen
    # eigenen Dateien (Umstellung 14.11.2026)
    chown "$benutzer:" "$daten.umzug" 2>/dev/null || chown "$benutzer" "$daten.umzug"
    # keine setuid/setgid-Bits für den Karte-Benutzer (Gruppe docker); chown löscht sie bei Ordnern nicht
    find "$daten.umzug" -perm /6000 ! -type l -exec chmod ug-s {} +
    # abdeckung.json liest der Konnektor (Dienstbenutzer, nicht in der Gruppe des Karte-Benutzers); alte Dateien tragen
    # oft 0660 aus der Umask des Dienstbenutzers
    [ ! -f "$daten.umzug/abdeckung.json" ] || chmod 644 "$daten.umzug/abdeckung.json"
    mv "$daten.umzug" "$daten"
  fi
  rm -rf "$ordner"                            # die Daten liegen vollständig am Ziel
fi
rm -rf "$daten.umzug"
ln -s "$daten" "$ordner"
echo "Map service data in $daten; $ordner points there."
