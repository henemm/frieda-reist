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
    (tmp_path / "dienst").mkdir()      # Sperren liegen ohne Einstellung im Dienstordner (#552)
    protokoll = tmp_path / "aufrufe.log"

    def lauf(befehl, regionen="europe/andorra europe/monaco", umgebung=None, **fehler):
        protokoll.write_text("")
        env = {**SAUBER, "PATH": f"{bin_}:/usr/bin:/bin", "TMPDIR": str(tmp_path / "tmp"), "FR_WURZEL": str(tmp_path),
               "FR_INSTANZ": "probe", "FR_TITEL": "Probe", "FR_DIENST": str(tmp_path / "dienst"), "FR_KARTENDIENST_ORDNER": str(ordner),
               "FR_KARTENDIENST_REGIONEN": regionen, "KD_SPEICHER_MIN_MB": "0", "KD_PLATZ_MIN_MB": "0",
               "ATTRAPPE_PROTOKOLL": str(protokoll), **{f"ATTRAPPE_{k.upper()}_FEHLER": v for k, v in fehler.items()},
               **(umgebung or {})}
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


@pytest.mark.parametrize("befehl", ["einspielen", "aktualisieren"])
def test_harter_abbruch_beim_umschalten_wird_zurueckgenommen(kd, befehl):
    """Gegenprüfung F004 (AC-16): Brach ein Lauf hart zwischen den beiden Umbenennungen ab (Datenordner fehlt, der alte Stand
    liegt als .<name>.alt daneben, dazu ein halber Nebenordner), holt der nächste Lauf den alten Stand zurück, bevor er Reste
    aufräumt. einspielen scheitert danach am Download (bisheriger Stand bleibt, Reste weg); aktualisieren findet den
    zurückgeholten Stand aktuell und tut nichts."""
    assert kd["lauf"]("einspielen").returncode == 0
    (kd["ordner"] / "alter-stand.txt").write_text("bisher")
    vorher = {p.name: p.read_bytes() for p in kd["ordner"].iterdir() if p.is_file()}
    kd["ordner"].rename(kd["eltern"] / ".kartendienst.alt")
    (kd["eltern"] / ".kartendienst.neu").mkdir()
    (kd["eltern"] / ".kartendienst.neu" / "halb.txt").write_text("halb")
    r = kd["lauf"](befehl, curl=r"osm\.pbf")
    assert {p.name: p.read_bytes() for p in kd["ordner"].iterdir() if p.is_file()} == vorher, (r.stdout, r.stderr)
    if befehl == "einspielen":
        assert r.returncode != 0, (r.stdout, r.stderr)
        assert [p.name for p in kd["eltern"].iterdir()] == ["kartendienst"]
    else:
        assert r.returncode == 0 and kd["protokoll"].read_text() == "", (r.stdout, r.stderr)
        assert not (kd["eltern"] / ".kartendienst.alt").exists()


def test_aktualisieren_wartet_auf_die_sperre(kd, tmp_path):
    """Gegenprüfung F006: Hält ein anderer Lauf die Sperre (etwa ein Einspielen mitten im Umschalten), verändert aktualisieren
    nichts, auch nicht den alten Stand neben einem fehlenden Datenordner; es scheitert wie bisher an der Sperre."""
    import fcntl
    sperren = tmp_path / "sperren"
    sperren.mkdir()
    umgebung = {"FR_SPERREN": str(sperren), "KD_SPERRE_WARTEN": "1"}
    assert kd["lauf"]("einspielen", umgebung=umgebung).returncode == 0
    kd["ordner"].rename(kd["eltern"] / ".kartendienst.alt")
    vorher = sorted(str(p.relative_to(kd["eltern"])) for p in kd["eltern"].rglob("*"))
    with open(sperren / "probe-kartendienst.lock", "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        r = kd["lauf"]("aktualisieren", umgebung=umgebung)
    assert r.returncode != 0 and "another import is still running" in r.stderr, (r.stdout, r.stderr)
    assert sorted(str(p.relative_to(kd["eltern"])) for p in kd["eltern"].rglob("*")) == vorher
    assert not kd["ordner"].exists() and kd["protokoll"].read_text() == ""
    r = kd["lauf"]("aktualisieren", umgebung=umgebung)     # ohne fremde Sperre: alter Stand zurück, sonst nichts zu tun
    assert r.returncode == 0 and (kd["ordner"] / "abdeckung.json").exists(), (r.stdout, r.stderr)


def test_unlesbare_sperre_des_veroeffentlichens_klare_meldung(kd, tmp_path):
    """Gegenprüfung F013: Ist die Sperre des Veröffentlichens für den Karte-Benutzer nicht lesbar, endet der Lauf mit einer
    klaren Meldung statt einem rohen Fehler der Shell."""
    if os.geteuid() == 0:
        pytest.skip("als root ist jede Datei lesbar")
    sperre = tmp_path / "dienst" / "veroeffentlichen.lock"
    sperre.write_text("")
    sperre.chmod(0o200)
    r = kd["lauf"]("einspielen", umgebung={"FR_SPERREN": str(tmp_path / "tmp"), "KD_SPERRE_WARTEN": "1"})
    assert r.returncode != 0, (r.stdout, r.stderr)
    assert "lock of publishing" in r.stderr and "not readable for the map user" in r.stderr, r.stderr
    assert "Permission denied" not in r.stderr, r.stderr


# ---------- #552, Entscheidung 10: Daten im Zustandsordner des Karte-Benutzers, Umzug ohne Handschritt ----------
UMZUG = WURZEL / "betrieb" / "kartendienst-umzug.sh"


def _umzug(ordner, ziel):
    import getpass
    return subprocess.run(["bash", str(UMZUG), str(ordner), str(ziel), getpass.getuser()], env=SAUBER, capture_output=True,
                          text=True, timeout=60)


def _baum(p):
    return sorted((str(x.relative_to(p)), x.read_text() if x.is_file() else None) for x in p.rglob("*"))


def test_umzug_verschiebt_daten_und_legt_verweis_an(tmp_path):
    """Vorhandene Daten (FR_KARTENDIENST_ORDNER als Ordner) ziehen nach <ziel>/daten um, an ihrer Stelle steht ein Verweis
    dorthin; nichts geht verloren, ein zweiter Lauf ändert nichts."""
    ordner, ziel = tmp_path / "instanz" / "kartendienst", tmp_path / "varlib" / "probe-kartendienst"
    (ordner / "db").mkdir(parents=True)
    (ordner / "abdeckung.json").write_text('{"stand": "x"}')
    (ordner / "db" / "nodes.bin").write_text("daten")
    vorher = _baum(ordner)
    r = _umzug(ordner, ziel)
    assert r.returncode == 0, r.stdout + r.stderr
    assert ordner.is_symlink() and Path(os.readlink(ordner)) == ziel / "daten"
    assert _baum(ziel / "daten") == vorher and _baum(ordner) == vorher       # Leser sehen über den Pfad dasselbe
    assert oct(ziel.stat().st_mode & 0o777) == "0o755"
    r = _umzug(ordner, ziel)
    assert r.returncode == 0 and _baum(ziel / "daten") == vorher and ordner.is_symlink(), r.stdout + r.stderr


def test_umzug_entfernt_setuid_und_setgid(tmp_path):
    """Gegenprüfung F011: Nach dem Umzug gehören die Daten dem Karte-Benutzer (Gruppe docker); keine Datei und kein Ordner
    behält ein setuid- oder setgid-Bit, auch wenn chown es nicht von selbst löscht (Ordner)."""
    ordner, ziel = tmp_path / "instanz" / "kartendienst", tmp_path / "varlib" / "probe-kartendienst"
    (ordner / "sgid").mkdir(parents=True)
    (ordner / "sgid").chmod(0o2755)
    (ordner / "suid.bin").write_text("x")
    (ordner / "suid.bin").chmod(0o4755)
    if not (ordner / "sgid").stat().st_mode & 0o2000 or not (ordner / "suid.bin").stat().st_mode & 0o4000:
        pytest.skip("setuid/setgid lässt sich hier nicht setzen")
    r = _umzug(ordner, ziel)
    assert r.returncode == 0, r.stdout + r.stderr
    for p in [ziel / "daten", *(ziel / "daten").rglob("*")]:
        assert not p.stat().st_mode & 0o6000, (p, oct(p.stat().st_mode))


def test_umzug_ohne_daten_und_nach_abbruch(tmp_path):
    """Ohne vorhandene Daten entsteht nur der Verweis; nach einem Abbruch zwischen Kopie und Löschen (Daten schon am Ziel,
    Rest am alten Ort) räumt ein neuer Lauf den Rest weg, die Daten am Ziel bleiben."""
    ordner, ziel = tmp_path / "instanz" / "kartendienst", tmp_path / "varlib" / "probe-kartendienst"
    ordner.parent.mkdir()
    r = _umzug(ordner, ziel)
    assert r.returncode == 0 and ordner.is_symlink() and Path(os.readlink(ordner)) == ziel / "daten", r.stdout + r.stderr
    ordner.unlink()
    (ordner / "db").mkdir(parents=True)
    (ordner / "db" / "rest.bin").write_text("rest")
    (ziel / "daten" / "db").mkdir(parents=True)
    (ziel / "daten" / "db" / "rest.bin").write_text("rest")
    (ziel / "daten.umzug").mkdir()
    r = _umzug(ordner, ziel)
    assert r.returncode == 0, r.stdout + r.stderr
    assert ordner.is_symlink() and (ziel / "daten" / "db" / "rest.bin").read_text() == "rest"
    assert not (ziel / "daten.umzug").exists()


def test_umzug_fremder_verweis_aendert_nichts(tmp_path):
    ordner, ziel = tmp_path / "instanz" / "kartendienst", tmp_path / "varlib" / "probe-kartendienst"
    ordner.parent.mkdir()
    (tmp_path / "anders").mkdir()
    ordner.symlink_to(tmp_path / "anders")
    r = _umzug(ordner, ziel)
    assert r.returncode != 0 and "ERROR" in r.stdout + r.stderr
    assert Path(os.readlink(ordner)) == tmp_path / "anders" and not (ziel / "daten").exists()


def test_einspielen_schaltet_hinter_dem_verweis_um(kd, tmp_path):
    """Ist FR_KARTENDIENST_ORDNER ein Verweis (Umzug), schaltet das Skript im Zustandsordner um, nicht im Elternordner des
    Verweises; der Verweis bleibt, Leser sehen über ihn den neuen Stand."""
    ziel = tmp_path / "varlib" / "probe-kartendienst"
    ziel.mkdir(parents=True)
    kd["ordner"].symlink_to(ziel / "daten")
    vorher = sorted(p.name for p in kd["eltern"].iterdir())
    r = kd["lauf"]("einspielen")
    assert r.returncode == 0, (r.stdout, r.stderr)
    assert kd["ordner"].is_symlink() and (kd["ordner"] / "abdeckung.json").exists()
    assert (ziel / "daten" / "abdeckung.json").exists()
    assert sorted(p.name for p in kd["eltern"].iterdir()) == vorher       # im Elternordner des Verweises nichts Neues
