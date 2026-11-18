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
    assert set(erlaubt) == {("Service", "Environment:FR_DIENST"), ("Service", "Environment:FR_ZEITZONE"), ("Service", "TimeoutStartSec"),
                            ("Service", "MemoryHigh"), ("Service", "MemoryMax"), ("Service", "MemorySwapMax")}   # #538
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
    r = _installieren(env)
    assert r.returncode == 5
    # nur die Meldung, nicht noch einmal die Liste der Abweichungen: veroeffentlichen.sh hängt diese Ausgabe an die Prüfung an,
    # die dieselbe Liste enthält (#306)
    assert "is not installed" in r.stdout and "FR_ZEITZONE" not in r.stdout, r.stdout


def test_installieren_hilfsprogramm_ausgang_5_endet_mit_5(tmp_path):
    """#445, AC-21: Scheitert daemon-reload im Hilfsprogramm (Ausgang 5, Datei schon ersetzt), meldet units.py das als Fehler."""
    systemd, env = _installierte_einheiten(tmp_path)
    protokoll = _attrappen(tmp_path, env, systemd)
    helfer = tmp_path / "helfer.sh"
    helfer.write_text(f'#!/bin/sh\necho "helfer $1" >> {protokoll}\ncat > {systemd}/$1\n'
                      'echo "systemctl daemon-reload failed" >&2\nexit 5\n')
    konnektor = systemd / "probe-konnektor.service"
    konnektor.write_text(re.sub(r"(?m)^Environment=FR_ZEITZONE=.*\n", "", konnektor.read_text()))
    r = _installieren(env)
    assert r.returncode == 5, (r.stdout, r.stderr)
    assert "exit 5" in r.stdout and "daemon-reload failed" in r.stdout, r.stdout


def test_installieren_ohne_abweichung_tut_nichts(tmp_path):
    systemd, env = _installierte_einheiten(tmp_path)
    protokoll = _attrappen(tmp_path, env, systemd)
    assert _installieren(env).returncode == 0
    assert not protokoll.exists()


# ---------- #552, AC-13: Sandbox-Zeilen gehen nie automatisch ----------

def test_sandbox_nicht_in_erlaubnisliste(tmp_path):
    """Sandbox- und Benutzerzeilen stehen in keiner Erlaubnisliste; fehlen sie in einer installierten Unit, ist das eine
    gesperrte Abweichung (Einmalschritt einrichten.sh --installieren), die units.py pruefen meldet."""
    helfer = (BETRIEB / "vorlagen" / "units-installieren.py").read_text(encoding="utf-8")
    # nur die Erlaubnisliste des Hilfsprogramms: Seine Prüfung „User= ist der Dienstbenutzer“ nennt "User" zu Recht
    helfer = helfer[helfer.index("ERLAUBT = {"):]
    helfer = helfer[:helfer.index("\n}\n")]
    for schluessel in ("ReadWritePaths", "ProtectSystem", "ProtectHome", "InaccessiblePaths", "User", "NoNewPrivileges"):
        assert not [k for k in units().ERLAUBT if schluessel in k[1]], schluessel
        assert f'"{schluessel}"' not in helfer, schluessel
    systemd, env = _installierte_einheiten(tmp_path)
    for name in ("probe-konnektor.service", "probe-schreiben.service"):
        datei = systemd / name
        datei.write_text("".join(z for z in datei.read_text().splitlines(keepends=True)
                                 if not z.startswith(("InaccessiblePaths=", "ReadWritePaths=", "ProtectHome=read-only"))))
    r = subprocess.run([sys.executable, str(BETRIEB / "units.py"), "pruefen"], env=env, capture_output=True, text=True)
    assert r.returncode == 4, r.stdout + r.stderr
    assert "probe-konnektor.service" in r.stdout and "probe-schreiben.service" in r.stdout, r.stdout


# ---------- #538: Speichergrenzen der Dauerdienste in der Erlaubnisliste ----------

SPEICHER = ("MemoryHigh", "MemoryMax", "MemorySwapMax")
GUELTIG = ("256M", "1G", "4G", "99999M")
UNGUELTIG = ("infinity", "0", "0M", "50%", "512K", "1T", "0256M", "100000M", "256m", "256", "256M\n", "", " 256M", "256 M")


@pytest.mark.parametrize("schluessel", SPEICHER)
@pytest.mark.parametrize("wert", GUELTIG)
def test_speicherwert_gueltig(schluessel, wert):
    """AC-6: gültige Werte werden angenommen."""
    assert units().erlaubt(("Service", schluessel, wert)), (schluessel, wert)


@pytest.mark.parametrize("schluessel", SPEICHER)
@pytest.mark.parametrize("wert", UNGUELTIG)
def test_speicherwert_ungueltig(schluessel, wert):
    """AC-7: Der Schlüssel steht in der Liste, aber das Muster lehnt den Wert ab (vollständiger Treffer, auch kein
    Zeilenumbruch am Ende)."""
    u = units()
    assert ("Service", schluessel) in u.ERLAUBT
    assert not u.erlaubt(("Service", schluessel, wert)), (schluessel, wert)


def test_ungueltige_grenze_ist_gesperrt():
    """AC-9: Eine Grenzzeile mit gültigem Wert ist eine erlaubte Abweichung, mit ungültigem Wert eine gesperrte."""
    u = units()
    ist = EINHEIT + "MemoryMax=256M\n"
    setzen, entfernen, gesperrt = u.abgleich(EINHEIT + "MemoryMax=512M\n", ist, "probe-x.service")
    assert gesperrt == [] and ("Service", "MemoryMax", "512M") in setzen and ("Service", "MemoryMax", "256M") in entfernen
    for wert in ("infinity", "0", "50%"):
        setzen, _, gesperrt = u.abgleich(EINHEIT + f"MemoryMax={wert}\n", ist, "probe-x.service")
        assert setzen == [] and len(gesperrt) == 1, (wert, gesperrt)


def _helfer_programm(tmp_path, systemd, alt):
    """Echtes Hilfsprogramm aus der Vorlage als ausführbares Programm, das in den Testordner installiert (kein daemon-reload).
    alt=True: Stand vor #538, die drei Speicher-Schlüssel fehlen in seiner Erlaubnisliste."""
    benutzer = re.search(r"(?m)^User=(.*)$", (systemd / "probe-konnektor.service").read_text()).group(1)
    text = (BETRIEB / "vorlagen" / "units-installieren.py").read_text(encoding="utf-8")
    text = text.replace("__INSTANZ__", "probe").replace("__BENUTZER__", benutzer)
    if alt:
        text = "".join(z for z in text.splitlines(keepends=True) if not re.match(r'\s*\("Service", "Memory', z))
    modul = tmp_path / ("helfer-alt.py" if alt else "helfer-neu.py")
    modul.write_text(text, encoding="utf-8")
    programm = tmp_path / ("helfer-alt" if alt else "helfer-neu")
    programm.write_text(f"#!{sys.executable}\nimport importlib.util, sys\n"
                        f"spec = importlib.util.spec_from_file_location('h', {str(modul)!r})\n"
                        "m = importlib.util.module_from_spec(spec)\nspec.loader.exec_module(m)\n"
                        f"sys.exit(m.main(sys.argv, systemd={str(systemd)!r}, neu_laden=lambda: None))\n")
    programm.chmod(0o755)
    return programm


def _ohne_speichergrenzen(systemd, name):
    """Installierte Einheit wie vor #538: die drei Speicherzeilen fehlen."""
    datei = systemd / name
    text = datei.read_text()
    assert all(f"\n{k}=" in text for k in SPEICHER), f"{name}: Vorlage ohne Speichergrenzen"
    datei.write_text(re.sub(r"(?m)^Memory(?:High|Max|SwapMax)=.*\n", "", text))


def test_neue_grenzen_installiert_der_abgleich_ohne_handarbeit(tmp_path):
    """AC-8 (Ende zu Ende): Eine installierte Unit ohne Speicherzeilen ist eine erlaubte Abweichung; das echte Hilfsprogramm
    installiert sie, danach endet pruefen mit 0."""
    systemd, env = _installierte_einheiten(tmp_path)
    protokoll = _attrappen(tmp_path, env, systemd)
    env["FR_UNITS_HELFER"] = str(_helfer_programm(tmp_path, systemd, alt=False))
    _ohne_speichergrenzen(systemd, "probe-konnektor.service")
    r = subprocess.run([sys.executable, str(BETRIEB / "units.py"), "pruefen"], env=env, capture_output=True, text=True)
    assert r.returncode == 3 and "MemoryMax" in r.stdout and "BLOCKED" not in r.stdout, r.stdout
    r = _installieren(env)
    assert r.returncode == 0, (r.stdout, r.stderr)
    assert "MemoryMax=" in (systemd / "probe-konnektor.service").read_text()
    assert "systemctl restart probe-konnektor" in protokoll.read_text()


def test_alter_helfer_nur_normale_meldung(tmp_path):
    """AC-10: Kennt das installierte Hilfsprogramm die Speicher-Schlüssel noch nicht, lehnt es ab und ändert nichts;
    units.py meldet den Fehlschlag (Ausgang 5), die erneute Prüfung bleibt bei Ausgang 3. veroeffentlichen.sh macht daraus genau
    eine normale Meldung (test_betrieb.py::test_alter_helfer_meldet_einmal_normal)."""
    systemd, env = _installierte_einheiten(tmp_path)
    _attrappen(tmp_path, env, systemd)
    env["FR_UNITS_HELFER"] = str(_helfer_programm(tmp_path, systemd, alt=True))
    _ohne_speichergrenzen(systemd, "probe-push.service")
    vorher = (systemd / "probe-push.service").read_text()
    r = _installieren(env)
    assert r.returncode == 5 and "probe-push.service: install failed (exit 3)" in r.stdout and "outside the allowed list" in r.stdout, r.stdout
    assert (systemd / "probe-push.service").read_text() == vorher
    r = subprocess.run([sys.executable, str(BETRIEB / "units.py"), "pruefen"], env=env, capture_output=True, text=True)
    assert r.returncode == 3, r.stdout


# ---------- Path-Einheit des Veröffentlichens (#624) ----------

def test_path_einheit_in_einheiten():
    """#624 AC-9: Der Abgleich kennt .path-Einheiten (neben .service und .timer)."""
    u = units()
    assert u.EINHEITEN.match("probe-veroeffentlichen.path")
    assert u.EINHEITEN.match("probe-konnektor.service") and u.EINHEITEN.match("probe-veroeffentlichen.timer")


def test_fehlende_path_einheit_ist_gesperrt(tmp_path):
    """#624 AC-9: Fehlt die installierte Path-Einheit, ist das eine gesperrte Abweichung (Ausgang 4), mit ihrem Namen."""
    systemd, env = _installierte_einheiten(tmp_path)
    assert (systemd / "probe-veroeffentlichen.path").exists(), "einrichten.sh --erzeugen schreibt keine .path-Einheit"
    r = subprocess.run([sys.executable, str(BETRIEB / "units.py"), "pruefen"], env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    (systemd / "probe-veroeffentlichen.path").unlink()
    r = subprocess.run([sys.executable, str(BETRIEB / "units.py"), "pruefen"], env=env, capture_output=True, text=True)
    assert r.returncode == 4 and "probe-veroeffentlichen.path" in r.stdout and "BLOCKED" in r.stdout, r.stdout + r.stderr
