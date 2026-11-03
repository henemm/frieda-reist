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


def test_dropin_ordner_ist_eine_gesperrte_abweichung(tmp_path):
    systemd, env = _installierte_einheiten(tmp_path)
    (systemd / "probe-konnektor.service.d").mkdir()
    r = subprocess.run([sys.executable, str(BETRIEB / "units.py"), "pruefen"], env=env, capture_output=True, text=True)
    assert r.returncode == 4 and "probe-konnektor.service" in r.stdout and "drop-in" in r.stdout.lower(), r.stdout


def test_unicode_leerraum_und_leeres_environment_sind_gesperrt():
    u = units()
    neu = EINHEIT.replace("User=hem", " User=hem")
    assert u.abgleich(neu, EINHEIT, "probe-x.service")[2]
    setzen, entfernen, gesperrt = u.abgleich(EINHEIT + "Environment=\n", EINHEIT, "probe-x.service")
    assert gesperrt and setzen == []


def test_erlaubnisliste_ist_eine_feste_namensliste():
    erlaubt = units().ERLAUBT
    assert set(erlaubt) == {("Service", "Environment:FR_DIENST"), ("Service", "Environment:FR_ZEITZONE"), ("Service", "TimeoutStartSec")}
    for zeile in ("Environment=FR_WURZEL=/tmp/x", "Environment=RM_ABLAGE=/tmp/x", "Environment=KN_PORT=1"):
        setzen, _, gesperrt = units().abgleich(EINHEIT + zeile + "\n", EINHEIT, "probe-x.service")
        assert setzen == [] and len(gesperrt) == 1


# ---------- Installieren (AC-7) ----------

def _installierte_einheiten(tmp_path):
    systemd = tmp_path / "systemd"
    systemd.mkdir()
    env = instanz_env(tmp_path, EI_SYSTEMD=str(systemd))
    ziel = tmp_path / "soll"
    subprocess.run(["bash", str(BETRIEB / "einrichten.sh"), "--erzeugen"], env={**env, "EI_ZIEL": str(ziel)}, check=True)
    for datei in (ziel / "systemd").iterdir():
        shutil.copy(datei, systemd / datei.name)
    return systemd, env


def _attrappen(tmp_path, env, systemd):
    """Hilfsprogramm-Attrappe (schreibt stdin in die Einheit und protokolliert) und systemctl-Attrappe (protokolliert)."""
    protokoll = tmp_path / "protokoll.log"
    helfer = tmp_path / "helfer.sh"
    helfer.write_text(f'#!/bin/sh\necho "helfer $1" >> {protokoll}\ncat > {systemd}/$1\n')
    helfer.chmod(0o755)
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    (bin_ / "systemctl").write_text(f'#!/bin/sh\necho "systemctl $*" >> {protokoll}\n')
    (bin_ / "systemctl").chmod(0o755)
    env.update({"FR_SUDO": "", "FR_UNITS_HELFER": str(helfer), "PATH": f"{bin_}:{os.environ['PATH']}"})
    return protokoll


def _installieren(env):
    return subprocess.run([sys.executable, str(BETRIEB / "units.py"), "installieren"], env=env, capture_output=True, text=True)


def test_installieren_nur_erlaubte_abweichungen_dann_ausgang_0(tmp_path):
    systemd, env = _installierte_einheiten(tmp_path)
    protokoll = _attrappen(tmp_path, env, systemd)
    for art in ("konnektor", "push", "veroeffentlichen"):
        datei = systemd / f"probe-{art}.service"
        datei.write_text(re.sub(r"(?m)^(Environment=FR_ZEITZONE=.*|TimeoutStartSec=.*)\n", "", datei.read_text()))
    r = _installieren(env)
    assert r.returncode == 0, (r.stdout, r.stderr)
    zeilen = protokoll.read_text().splitlines()
    assert sorted(z for z in zeilen if z.startswith("helfer")) == ["helfer probe-konnektor.service", "helfer probe-push.service",
                                                                  "helfer probe-veroeffentlichen.service"]
    # Neustart nur der Dauerdienste: veroeffentlichen und waechter nie
    neustarts = [z for z in zeilen if z.startswith("systemctl restart")]
    assert sorted(neustarts) == ["systemctl restart probe-konnektor", "systemctl restart probe-push"]


def test_installieren_gesperrtes_wird_nicht_uebergeben_und_bleibt_ausgang_4(tmp_path):
    systemd, env = _installierte_einheiten(tmp_path)
    protokoll = _attrappen(tmp_path, env, systemd)
    konnektor = systemd / "probe-konnektor.service"
    konnektor.write_text(re.sub(r"(?m)^Environment=FR_ZEITZONE=.*\n", "", konnektor.read_text()))
    waechter = systemd / "probe-waechter.service"
    waechter.write_text(waechter.read_text().replace("User=", "User=x"))
    r = _installieren(env)
    assert r.returncode == 4 and "probe-waechter.service" in r.stdout
    zeilen = protokoll.read_text().splitlines()
    assert [z for z in zeilen if z.startswith("helfer")] == ["helfer probe-konnektor.service"]
    assert not any("waechter" in z for z in zeilen)


def test_installieren_ohne_hilfsprogramm_meldet_ausgang_5(tmp_path):
    systemd, env = _installierte_einheiten(tmp_path)
    _attrappen(tmp_path, env, systemd)
    env["FR_UNITS_HELFER"] = str(tmp_path / "gibt-es-nicht")
    konnektor = systemd / "probe-konnektor.service"
    konnektor.write_text(re.sub(r"(?m)^Environment=FR_ZEITZONE=.*\n", "", konnektor.read_text()))
    assert _installieren(env).returncode == 5


def test_installieren_ohne_abweichung_tut_nichts(tmp_path):
    systemd, env = _installierte_einheiten(tmp_path)
    protokoll = _attrappen(tmp_path, env, systemd)
    assert _installieren(env).returncode == 0
    assert not protokoll.exists()
