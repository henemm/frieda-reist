#!/usr/bin/env bash
# Holt die Offline-Grundkarte einer Reise: einen OpenStreetMap-Ausschnitt als PMTiles-Vektorkarte
# (Protomaps-Tagesbuild, Lizenz ODbL, Namensnennung „© OpenStreetMap-Mitwirkende“).
# Der Ausschnitt ist der Rahmen aus reisen/<reise>/plan/karte.yaml, die Datei landet unter
# reisen/<reise>/medien/karte/grundkarte.pmtiles (nicht im Repo, .gitignore). Danach veröffentlichen.
#
# Aufruf:  frieda/werkzeuge/karte-holen.sh <reise>              (Detail bis Zoomstufe 15, Wege und Pfade)
#          MAXZOOM=14 frieda/werkzeuge/karte-holen.sh <reise>   (etwa halb so groß)
#          frieda/werkzeuge/karte-holen.sh <reise> <name>       (regionale Karte der Recherche: Rahmen und Zoom aus
#          grundkarten.<name> der Punkte-Datei in reise.json -> wissen_punkte; Ziel medien/karte/<name>.pmtiles)
# Braucht Internet; das Werkzeug pmtiles kommt einmalig nach engine/.bin/.
set -euo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/../betrieb/gemeinsam.sh"

REISE="${1:?Aufruf: karte-holen.sh <reise> [<regionale Karte>]}"
REGION="${2:-}"
WURZEL="$FR_WURZEL"
PY="$FR_PYTHON"; [ -x "$PY" ] || PY=python3
if [ -n "$REGION" ]; then
  KARTE="$WURZEL/reisen/$REISE/$("$PY" -c 'import json, sys; print(json.load(open(sys.argv[1]))["wissen_punkte"])' "$WURZEL/reisen/$REISE/reise.json")"
  ZIEL="$WURZEL/reisen/$REISE/medien/karte/$REGION.pmtiles"
  MAXZOOM="${MAXZOOM:-$("$PY" -c 'import sys, yaml; print(yaml.safe_load(open(sys.argv[1]))["grundkarten"][sys.argv[2]].get("zoom", 14))' "$KARTE" "$REGION")}"
else
  KARTE="$WURZEL/reisen/$REISE/plan/karte.yaml"
  ZIEL="$WURZEL/reisen/$REISE/medien/karte/grundkarte.pmtiles"
  MAXZOOM="${MAXZOOM:-15}"
fi
PMTILES_VERSION="1.31.2"   # go-pmtiles (BSD-3), github.com/protomaps/go-pmtiles
WERKZEUG="$WURZEL/engine/.bin/pmtiles"

[ -f "$KARTE" ] || { echo "$KARTE fehlt."; exit 1; }

# Ausschnitt: Kartenrahmen plus 15 % Rand je Seite (wie maxBounds in der Vorlage), damit auf breiten
# Bildschirmen (iPad, Desktop) neben dem Rahmen keine leere Fläche bleibt. Reihenfolge west,sued,ost,nord
BBOX="$("$PY" -c 'import sys, yaml; d = yaml.safe_load(open(sys.argv[1])); r = d["grundkarten"][sys.argv[2]]["rahmen"] if sys.argv[2] else d["rahmen"]; dx = (r["ost"] - r["west"]) * 0.15; dy = (r["nord"] - r["sued"]) * 0.15; print(",".join(f"{v:.4f}" for v in (r["west"] - dx, r["sued"] - dy, r["ost"] + dx, r["nord"] + dy)))' "$KARTE" "$REGION")"

# Werkzeug einmalig holen (liegt in engine/.bin, nicht im Repo)
if [ ! -x "$WERKZEUG" ]; then
  case "$(uname -m)" in
    x86_64|amd64) ARCH=x86_64 ;;
    aarch64|arm64) ARCH=arm64 ;;
    *) echo "Unbekannte Prozessorart $(uname -m)."; exit 1 ;;
  esac
  mkdir -p "$(dirname "$WERKZEUG")"
  TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
  URL="https://github.com/protomaps/go-pmtiles/releases/download/v$PMTILES_VERSION/go-pmtiles_${PMTILES_VERSION}_Linux_${ARCH}.tar.gz"
  echo "Hole pmtiles $PMTILES_VERSION ($ARCH) …"
  curl -fsSL "$URL" -o "$TMP/p.tgz" || { echo "Download fehlgeschlagen: $URL (Dateiname auf der Release-Seite prüfen)."; exit 1; }
  tar xzf "$TMP/p.tgz" -C "$TMP" pmtiles
  install -m 755 "$TMP/pmtiles" "$WERKZEUG"
fi

# Neuester Tagesbuild: Protomaps hält die Builds der letzten Woche vor
QUELLE=""
for i in 0 1 2 3 4 5 6 7; do
  TAG="$(date -u -d "-$i day" +%Y%m%d)"
  if curl -fsI "https://build.protomaps.com/$TAG.pmtiles" >/dev/null 2>&1; then QUELLE="https://build.protomaps.com/$TAG.pmtiles"; break; fi
done
[ -n "$QUELLE" ] || { echo "Kein Tagesbuild der letzten 8 Tage gefunden (build.protomaps.com)."; exit 1; }

mkdir -p "$(dirname "$ZIEL")"
echo "Schneide $BBOX bis Zoom $MAXZOOM aus $QUELLE …"
"$WERKZEUG" extract "$QUELLE" "$ZIEL.neu" --bbox="$BBOX" --maxzoom="$MAXZOOM"
"$WERKZEUG" verify "$ZIEL.neu" >/dev/null
mv "$ZIEL.neu" "$ZIEL"
echo "$QUELLE (Stand $TAG), Rahmen $BBOX, Zoom bis $MAXZOOM" > "$ZIEL.quelle.txt"
echo "Fertig: $ZIEL ($(du -h "$ZIEL" | cut -f1)). Jetzt veröffentlichen: frieda/betrieb/deploy.sh $REISE"
