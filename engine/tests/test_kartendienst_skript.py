"""Tests für betrieb/kartendienst.sh (Einspielen und Aktualisieren des eigenen Kartendienstes, #444, AC-16 und AC-17).

Ohne Docker und ohne Netz: Attrappen für docker, curl und osmium liegen vorn im Suchpfad. Jede Attrappe schreibt ihren Aufruf
in ein Protokoll und scheitert, wenn ihr Aufruf auf das Muster in ATTRAPPE_<NAME>_FEHLER passt (grep -E).

Schnittstelle (Entscheidung in der RED-Phase):
  betrieb/kartendienst.sh einspielen | aktualisieren   Werte aus den Einstellungen der Instanz (gemeinsam.sh): FR_WURZEL,
      FR_INSTANZ, FR_KARTENDIENST_ORDNER (Datenordner, wird als Ganzes umgeschaltet), FR_KARTENDIENST_REGIONEN
  KD_SPEICHER_MIN_MB, KD_PLATZ_MIN_MB      Untergrenzen der Prüfung von Speicher und Platz (interne Namen, ohne FR_; Tests: 0)
  Arbeitsdateien (Downloads, osm.bz2) unter TMPDIR oder im Nebenordner; neben dem Datenordner bleibt danach nichts liegen.
  Die Rahmen je Region kommen aus `osmium fileinfo` (lokal oder im Container); die Attrappen antworten auf -j/--json mit
  header.boxes und auf -g mit einem Rahmen (min_lon,min_lat,max_lon,max_lat).
  abdeckung.json: {"stand": "<Zeitpunkt>", "regionen_pruefsumme": "<Summe>", "rahmen": [[süd, west, nord, ost], ...]}
"""
import datetime
import json
import os
import subprocess
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parents[2]
SKRIPT = WURZEL / "betrieb" / "kartendienst.sh"
SAUBER = {k: v for k, v in os.environ.items() if not k.startswith(("FR_", "RM_", "KN_", "EA_", "VF_", "FS_", "WA_", "EI_", "KD_"))}

ATTRAPPE = r'''#!/usr/bin/env bash
# Attrappe __NAME__: protokolliert, scheitert auf Muster, antwortet auf die nötigen Fragen
echo "__NAME__ $*" >> "$ATTRAPPE_PROTOKOLL"
muster="${ATTRAPPE___GROSS___FEHLER:-}"
if [ -n "$muster" ] && printf '%s\n' "$*" | grep -Eq -- "$muster"; then echo "__NAME__: Fehler (Attrappe)" >&2; exit 1; fi
alle="$*"
# Ziel einer Ausgabedatei (-o DATEI, --output DATEI, -O) beschreiben
ziel=""; vorher=""
for a in "$@"; do
  case "$vorher" in -o|--output|--output-document) ziel="$a" ;; esac
  case "$a" in --output=*) ziel="${a#--output=}" ;; esac
  vorher="$a"
done
case "$alle" in
  *fileinfo*)
    case "$alle" in
      *-j*|*--json*) echo '{"header": {"boxes": [[1.40, 42.40, 1.80, 42.70]]}, "data": {"bbox": [1.40, 42.40, 1.80, 42.70]}}' ;;
      *) echo "(1.40,42.40,1.80,42.70)" ;;
    esac
    exit 0 ;;
  *.md5*)
    summe="$(printf 'pbf-daten' | md5sum | cut -d' ' -f1)"
    if [ -n "$ziel" ]; then echo "$summe  region-latest.osm.pbf" > "$ziel"; else echo "$summe  region-latest.osm.pbf"; fi
    exit 0 ;;
  *interpreter*|*api/*)
    antwort='{"osm3s": {"timestamp_osm_base": "2026-10-01T00:00:00Z"}, "elements": []}'
    if [ -n "$ziel" ]; then echo "$antwort" > "$ziel"; else echo "$antwort"; fi
    exit 0 ;;
esac
if [ -n "$ziel" ]; then mkdir -p "$(dirname "$ziel")"; printf 'pbf-daten' > "$ziel"; fi
exit 0
'''


@pytest.fixture
def kd(tmp_path):
    """-> lauf(befehl, regionen, **fehler) -> CompletedProcess; dazu Datenordner und Protokoll."""
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    for name in ("docker", "curl", "osmium"):
        p = bin_ / name
        p.write_text(ATTRAPPE.replace("__NAME__", name).replace("__GROSS__", name.upper()), encoding="utf-8")
        p.chmod(0o755)
    eltern = tmp_path / "daten"
    eltern.mkdir()
    ordner = eltern / "kartendienst"
    (tmp_path / "tmp").mkdir()
    protokoll = tmp_path / "aufrufe.log"

    def lauf(befehl, regionen="europe/andorra europe/monaco", **fehler):
        protokoll.write_text("")
        env = {**SAUBER, "PATH": f"{bin_}:/usr/bin:/bin", "TMPDIR": str(tmp_path / "tmp"), "FR_WURZEL": str(tmp_path),
               "FR_INSTANZ": "probe", "FR_TITEL": "Probe", "FR_KARTENDIENST_ORDNER": str(ordner),
               "FR_KARTENDIENST_REGIONEN": regionen, "KD_SPEICHER_MIN_MB": "0", "KD_PLATZ_MIN_MB": "0",
               "ATTRAPPE_PROTOKOLL": str(protokoll), **{f"ATTRAPPE_{k.upper()}_FEHLER": v for k, v in fehler.items()}}
        return subprocess.run(["bash", str(SKRIPT), befehl], env=env, capture_output=True, text=True, timeout=120)
    return {"lauf": lauf, "ordner": ordner, "eltern": eltern, "protokoll": protokoll}


def abdeckung(ordner):
    return json.loads((ordner / "abdeckung.json").read_text(encoding="utf-8"))


def alter_stand(ordner, tage):
    d = abdeckung(ordner)
    alt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=tage)
    d["stand"] = alt.strftime("%Y-%m-%dT%H:%M:%SZ")
    (ordner / "abdeckung.json").write_text(json.dumps(d), encoding="utf-8")
    os.utime(ordner / "abdeckung.json", (alt.timestamp(), alt.timestamp()))


def test_einspielen_erfolg_schaltet_um(kd):
    """AC-16 (Erfolg): abdeckung.json mit Rahmen je Region, Prüfsumme der Regionenliste und Stand; neben dem Datenordner
    bleibt nichts liegen."""
    r = kd["lauf"]("einspielen")
    assert r.returncode == 0, (r.stdout, r.stderr)
    d = abdeckung(kd["ordner"])
    assert d["stand"] and d["regionen_pruefsumme"]
    assert len(d["rahmen"]) == 2
    for s, w, n, o in d["rahmen"]:
        assert (s, w, n, o) == pytest.approx((42.40, 1.40, 42.70, 1.80))
    assert [p.name for p in kd["eltern"].iterdir()] == ["kartendienst"]
    assert oct(kd["ordner"].stat().st_mode & 0o777) == oct(0o755)
    log = kd["protokoll"].read_text()
    assert "europe/andorra" in log and "europe/monaco" in log and "docker" in log


@pytest.mark.parametrize("schritt, fehler", [
    ("download", {"curl": r"osm\.pbf"}),
    ("vorverarbeitung", {"osmium": r"merge|cat", "docker": r"osmium (merge|cat)"}),
    ("einspielen", {"docker": r"init"}),
    ("probeabfrage", {"curl": r"interpreter|api/", "docker": r"interpreter|api/"}),
])
def test_einspielen_mit_rueckweg(kd, schritt, fehler):
    """AC-16: Scheitert ein Schritt, bleibt der bisherige Stand samt abdeckung.json unverändert, der Nebenordner ist weg, und der
    Ausgang ist ungleich 0."""
    assert kd["lauf"]("einspielen").returncode == 0
    (kd["ordner"] / "alter-stand.txt").write_text("bisher")
    vorher = {p.name: p.read_bytes() for p in kd["ordner"].iterdir() if p.is_file()}
    r = kd["lauf"]("einspielen", "europe/andorra", **fehler)
    assert r.returncode != 0, (schritt, r.stdout, r.stderr)
    assert {p.name: p.read_bytes() for p in kd["ordner"].iterdir() if p.is_file()} == vorher, schritt
    assert [p.name for p in kd["eltern"].iterdir()] == ["kartendienst"], schritt


def test_neu_einspielen_bei_geaenderter_liste(kd):
    """AC-17: Gleiche Liste und jünger als ein Monat: der tägliche Lauf tut nichts. Geänderte Liste oder älter als ein Monat:
    er spielt neu ein."""
    assert kd["lauf"]("einspielen").returncode == 0
    summe = abdeckung(kd["ordner"])["regionen_pruefsumme"]
    r = kd["lauf"]("aktualisieren")
    assert r.returncode == 0, (r.stdout, r.stderr)
    assert kd["protokoll"].read_text() == "", "gleiche Liste, junger Stand: kein Abruf, kein Container"
    r = kd["lauf"]("aktualisieren", "europe/andorra")
    assert r.returncode == 0, (r.stdout, r.stderr)
    neu = abdeckung(kd["ordner"])
    assert neu["regionen_pruefsumme"] != summe and len(neu["rahmen"]) == 1
    assert "europe/andorra" in kd["protokoll"].read_text()
    alter_stand(kd["ordner"], 40)
    r = kd["lauf"]("aktualisieren", "europe/andorra")
    assert r.returncode == 0 and "europe/andorra" in kd["protokoll"].read_text(), (r.stdout, r.stderr)
    assert abdeckung(kd["ordner"])["stand"] > (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
