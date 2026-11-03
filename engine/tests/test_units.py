"""Tests für den Abgleich der systemd-Einheiten mit den Vorlagen (#260, betrieb/units.py, einrichten.sh --erzeugen).
Alles mit erfundenen Einheiten und einer erfundenen Instanz „probe“; es wird nichts unter /etc gelesen oder geschrieben."""
import importlib.util
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

BETRIEB = Path(__file__).resolve().parents[2] / "betrieb"
SAUBER = {k: v for k, v in os.environ.items() if not k.startswith(("FR_", "RM_", "KN_", "EA_", "VF_", "FS_", "WA_", "EI_"))}
EINHEIT = "[Unit]\nDescription=probe\n\n[Service]\nUser=hem\nExecStart=/usr/bin/probe\nEnvironment=FR_DIENST=/srv/x\nTimeoutStartSec=10min\n"


def units():
    spec = importlib.util.spec_from_file_location("units", BETRIEB / "units.py")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def instanz_env(tmp_path, **extra):
    return {**SAUBER, "FR_WURZEL": str(tmp_path), "FR_INSTANZ": "probe", "FR_TITEL": "Probe", **extra}


def test_einrichten_erzeugen_schreibt_die_einheiten_ohne_ausgabe(tmp_path):
    ziel = tmp_path / "soll"
    r = subprocess.run(["bash", str(BETRIEB / "einrichten.sh"), "--erzeugen"], env=instanz_env(tmp_path, EI_ZIEL=str(ziel)),
                       capture_output=True, text=True)
    assert r.returncode == 0 and r.stdout == "", (r.stdout, r.stderr)
    assert (ziel / "systemd" / "probe-konnektor.service").exists()
    assert (ziel / "systemd" / "probe-veroeffentlichen.timer").exists()
    assert not re.search(r"__[A-Z_]+__", (ziel / "systemd" / "probe-konnektor.service").read_text())


def test_einrichten_erzeugen_schreibt_nur_nach_ei_ziel(tmp_path):
    systemd = tmp_path / "systemd"
    systemd.mkdir()
    ziel = tmp_path / "soll"
    env = instanz_env(tmp_path, EI_ZIEL=str(ziel), EI_SYSTEMD=str(systemd))
    assert subprocess.run(["bash", str(BETRIEB / "einrichten.sh"), "--erzeugen"], env=env).returncode == 0
    assert list(systemd.iterdir()) == []


def test_gleiche_einheit_ist_kein_unterschied():
    assert units().abgleich(EINHEIT, EINHEIT, "probe-x.service") == ([], [], [])


def test_erlaubt_sind_nur_umgebungswerte_und_zeitgrenze():
    soll = EINHEIT.replace("10min", "45min") + "Environment=FR_ZEITZONE=Europe/Berlin\n"
    setzen, entfernen, gesperrt = units().abgleich(soll, EINHEIT, "probe-x.service")
    assert gesperrt == []
    assert ("Service", "Environment", "FR_ZEITZONE=Europe/Berlin") in setzen
    assert ("Service", "TimeoutStartSec", "45min") in setzen and ("Service", "TimeoutStartSec", "10min") in entfernen


@pytest.mark.parametrize("zeile", [
    "User=root", "ExecStart=/bin/sh -c evil", "Environment=PATH=/tmp", "Environment=FR_X=$(id)", "Environment=FR_X=a b",
    'Environment=FR_X="a"', "Environment=FR_X=a;b", "TimeoutStartSec=$X", "ExecStartPre=/bin/true", "ReadWritePaths=/",
])
def test_alles_andere_ist_gesperrt(zeile):
    setzen, entfernen, gesperrt = units().abgleich(EINHEIT + zeile + "\n", EINHEIT, "probe-x.service")
    assert setzen == [] and entfernen == [] and len(gesperrt) == 1, (setzen, gesperrt)


def test_timer_und_fehlende_einheit_sind_gesperrt():
    u = units()
    assert u.abgleich("[Timer]\nOnCalendar=daily\n", "[Timer]\nOnCalendar=hourly\n", "probe-x.timer")[2]
    assert u.abgleich(EINHEIT, None, "probe-x.service")[2]


def test_pruefen_ausgang_0_3_4(tmp_path):
    systemd = tmp_path / "systemd"
    systemd.mkdir()
    env = instanz_env(tmp_path, EI_SYSTEMD=str(systemd))
    ziel = tmp_path / "soll"
    subprocess.run(["bash", str(BETRIEB / "einrichten.sh"), "--erzeugen"], env={**env, "EI_ZIEL": str(ziel)}, check=True)

    def lauf():
        return subprocess.run([sys.executable, str(BETRIEB / "units.py"), "pruefen"], env=env, capture_output=True, text=True)

    for datei in (ziel / "systemd").iterdir():
        shutil.copy(datei, systemd / datei.name)
    r = lauf()
    assert r.returncode == 0 and r.stdout == "", (r.stdout, r.stderr)
    konnektor = systemd / "probe-konnektor.service"
    konnektor.write_text(re.sub(r"(?m)^Environment=FR_ZEITZONE=.*\n", "", konnektor.read_text()))
    r = lauf()
    assert r.returncode == 3 and "probe-konnektor.service" in r.stdout and "FR_ZEITZONE" in r.stdout, (r.stdout, r.stderr)
    konnektor.write_text(konnektor.read_text().replace("User=", "User=x"))
    r = lauf()
    assert r.returncode == 4 and "BLOCKED" in r.stdout
    (systemd / "probe-waechter.service").unlink()
    assert "probe-waechter.service" in lauf().stdout
