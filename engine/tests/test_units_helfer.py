"""Tests für das Hilfsprogramm mit Root-Rechten, das ungefährliche Änderungen der systemd-Einheiten installiert (#260, PR 2;
betrieb/vorlagen/units-installieren.py). Die Funktionen laufen direkt mit Parametern in einem Testordner, ohne root; erfundene
Instanz „probe“ und Benutzer „hans“."""
import importlib.util
import os
import re
import subprocess
from pathlib import Path

import pytest

BETRIEB = Path(__file__).resolve().parents[2] / "betrieb"
VORLAGE = BETRIEB / "vorlagen" / "units-installieren.py"
SAUBER = {k: v for k, v in os.environ.items() if not k.startswith(("FR_", "RM_", "KN_", "EA_", "VF_", "FS_", "WA_", "EI_"))}
EINHEIT = ("[Unit]\nDescription=probe\n\n[Service]\nUser=hans\nExecStart=/usr/bin/probe\nEnvironment=PATH=/usr/bin\n"
           "Environment=FR_ZEITZONE=UTC\nTimeoutStartSec=10min\n")
NAME = "probe-konnektor.service"


@pytest.fixture
def h(tmp_path):
    """Hilfsprogramm aus der Vorlage, Platzhalter ersetzt; Testordner als systemd-Ordner mit installierter Einheit."""
    text = VORLAGE.read_text(encoding="utf-8").replace("__INSTANZ__", "probe").replace("__BENUTZER__", "hans")
    datei = tmp_path / "helfer.py"
    datei.write_text(text, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("helfer", datei)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    systemd = tmp_path / "systemd"
    systemd.mkdir()
    (systemd / NAME).write_text(EINHEIT, encoding="utf-8")
    geladen = []

    def lauf(neu, einheit=NAME, **kw):
        if isinstance(neu, str):
            neu = neu.encode("utf-8")
        return modul.installieren(einheit, neu, systemd=str(systemd), neu_laden=lambda: geladen.append(1), **kw)

    return {"m": modul, "lauf": lauf, "systemd": systemd, "geladen": geladen, "tmp": tmp_path, "text": text}


def abgelehnt(h, neu, einheit=NAME):
    vorher = (h["systemd"] / einheit).read_bytes() if (h["systemd"] / einheit).exists() else None
    with pytest.raises(h["m"].Abgelehnt):
        h["lauf"](neu, einheit)
    assert not h["geladen"]
    nachher = (h["systemd"] / einheit).read_bytes() if (h["systemd"] / einheit).exists() else None
    assert nachher == vorher


# ---------- AC-1: feste Menge von Einheiten ----------

@pytest.mark.parametrize("einheit", [
    "probe-andere.service", "fremd-konnektor.service", "probe-konnektor.timer", "probe-veroeffentlichen.timer", "../probe-konnektor.service",
    "probe-konnektor.service/", "/etc/systemd/system/probe-konnektor.service", "probe-konnektor.service\n", "", "probe-konnektor",
])
def test_ac1_nur_die_feste_menge_der_einheiten(h, einheit):
    (h["systemd"] / "probe-andere.service").write_text(EINHEIT)
    (h["systemd"] / "fremd-konnektor.service").write_text(EINHEIT)
    with pytest.raises(h["m"].Abgelehnt):
        h["lauf"](EINHEIT.replace("UTC", "Europe/Berlin"), einheit)
    assert not h["geladen"]


@pytest.mark.parametrize("art", ["konnektor", "push", "rueckmeldungen", "schreiben", "veroeffentlichen", "waechter"])
def test_ac1_alle_sechs_einheiten_sind_erlaubt(h, art):
    name = f"probe-{art}.service"
    (h["systemd"] / name).write_text(EINHEIT)
    assert h["lauf"](EINHEIT.replace("UTC", "Europe/Berlin"), name) == 0


# ---------- AC-2: nur erlaubte Zeilen dürfen sich unterscheiden ----------

def test_ac2_erlaubte_aenderung_wird_installiert(h):
    neu = EINHEIT.replace("FR_ZEITZONE=UTC", "FR_ZEITZONE=Europe/Berlin").replace("10min", "45min") + "Environment=FR_DIENST=/srv/probe/_dienst\n"
    assert h["lauf"](neu) == 0
    datei = h["systemd"] / NAME
    assert datei.read_text(encoding="utf-8") == neu
    assert oct(datei.stat().st_mode & 0o777) == "0o644"
    assert h["geladen"] == [1]


def test_ac2_gleiche_datei_ist_nichts_zu_tun(h):
    assert h["lauf"](EINHEIT) == 2
    assert not h["geladen"]


@pytest.mark.parametrize("aenderung", [
    lambda t: t.replace("ExecStart=/usr/bin/probe", "ExecStart=/bin/sh"),
    lambda t: t.replace("Environment=PATH=/usr/bin", "Environment=PATH=/tmp"),
    lambda t: t + "ExecStartPre=/bin/true\n",
    lambda t: t.replace("Description=probe\n", "Description=probe\nAfter=x\n"),
    lambda t: t.replace("ExecStart=/usr/bin/probe\nEnvironment=PATH=/usr/bin\n", "Environment=PATH=/usr/bin\nExecStart=/usr/bin/probe\n"),   # Reihenfolge
    lambda t: t.replace("[Service]\n", "[Service]\nExecStart=/usr/bin/probe\n"),                                                              # doppelte Zeile
    lambda t: t + "\n[Install]\nWantedBy=multi-user.target\n",
])
def test_ac2_andere_zeilen_lehnen_ab(h, aenderung):
    abgelehnt(h, aenderung(EINHEIT))


def test_ac2_erlaubte_zeile_darf_wegfallen(h):
    assert h["lauf"](EINHEIT.replace("Environment=FR_ZEITZONE=UTC\n", "")) == 0


def test_ac2_ein_name_hoechstens_einmal_und_nur_aus_der_liste(h):
    abgelehnt(h, EINHEIT + "Environment=FR_ZEITZONE=Europe/Berlin\n")
    for zeile in ("Environment=FR_WURZEL=/tmp/x", "Environment=RM_ABLAGE=/tmp/x", "Environment=KN_PORT=1", "Environment=FR_DIENST2=/x"):
        abgelehnt(h, EINHEIT + zeile + "\n")


@pytest.mark.parametrize("zeile", [
    "Environment=FR_DIENST=relativ/pfad", "Environment=FR_DIENST=/a b", "Environment=FR_DIENST=/a/../b", "Environment=FR_DIENST=$X",
    'Environment=FR_DIENST="/a"', "Environment=FR_DIENST=/a;b", "Environment=FR_DIENST=", "Environment=FR_ZEITZONE=a b", "Environment=FR_ZEITZONE=%H",
    "Environment=FR_ZEITZONE=$(id)", "TimeoutStartSec=$X", "TimeoutStartSec=10 min", "TimeoutStartSec=999999999", "TimeoutStartSec=0", "TimeoutStartSec=infinity",
])
def test_ac2_werte_muessen_dem_muster_entsprechen(h, zeile):
    basis = EINHEIT.replace("Environment=FR_ZEITZONE=UTC\n", "").replace("TimeoutStartSec=10min\n", "")
    abgelehnt(h, basis + zeile + "\n")


# ---------- AC-3: strenges Einlesen ----------

@pytest.mark.parametrize("neu", [
    EINHEIT + "Environment=FR_DIENST=/a\\\n",                   # Fortsetzungszeile
    EINHEIT + "# Kommentar\\\nExecStart=/bin/sh\n",             # Fortsetzung auch im Kommentar
    EINHEIT.replace("\n", "\r\n"),                              # CR
    EINHEIT + "\x00",                                           # NUL
    EINHEIT + "\x07\n",                                         # Steuerzeichen
    EINHEIT + ".include /tmp/x\n",                              # Zeile ohne „=“
    EINHEIT + "irgendwas\n",
    EINHEIT + "#" * 70000,                                      # zu groß
    b"\xff\xfe[Service]\n",                                     # kein UTF-8
])
def test_ac3_strenges_einlesen(h, neu):
    abgelehnt(h, neu)


UNICODE_LEERRAUM = [" ", " ", "\u0085", " ", "　", "​", "﻿"]


@pytest.mark.parametrize("zeichen", UNICODE_LEERRAUM)
def test_ac3_unicode_leerraum_verschiebt_nichts(h, zeichen):
    """systemd kennt nur Leerzeichen und Tab als Leerraum. Python-strip() kannte mehr: Aus „<NBSP>User=hans“ wurde für uns
    User=hans, für systemd ein ignorierter Schlüssel, der Dienst liefe ohne User= als root (Gegenprüfung 3.11.2026, F001)."""
    neu = EINHEIT.replace("UTC", "Europe/Berlin")
    for ersatz in (zeichen + "User=hans", "User" + zeichen + "=hans", "User=" + zeichen + "hans", "User=hans" + zeichen):
        abgelehnt(h, neu.replace("User=hans", ersatz))
    abgelehnt(h, neu.replace("[Service]", zeichen + "[Service]"))
    abgelehnt(h, neu.replace("ExecStart=/usr/bin/probe", zeichen + "ExecStart=/usr/bin/probe"))
    abgelehnt(h, neu.replace("Environment=FR_ZEITZONE", zeichen + "Environment=FR_ZEITZONE"))


def test_ac3_nicht_ascii_in_kommentaren_und_werten_anderer_zeilen_ist_harmlos(h):
    neu = "# Zeitgrenze für Tests\n" + EINHEIT.replace("Description=probe", "Description=veröffentlichen").replace("UTC", "Europe/Berlin")
    (h["systemd"] / NAME).write_text(EINHEIT.replace("Description=probe", "Description=veröffentlichen"), encoding="utf-8")
    assert h["lauf"](neu) == 0


def test_ac3_leeres_environment_setzt_die_liste_zurueck_und_wird_abgelehnt(h):
    abgelehnt(h, EINHEIT.replace("Environment=PATH=/usr/bin\n", "Environment=PATH=/usr/bin\nEnvironment=\n") + "Environment=FR_DIENST=/srv/x\n")
    (h["systemd"] / NAME).write_text(EINHEIT + "Environment=\n")
    abgelehnt(h, EINHEIT + "Environment=\nEnvironment=FR_DIENST=/srv/x\n")


def test_ac3_kommentare_und_leerzeilen_sind_harmlos(h):
    assert h["lauf"]("# Vorlage\n" + EINHEIT.replace("UTC", "Europe/Berlin") + "\n") == 0


# ---------- AC-4: Benutzer, Zustand der installierten Datei, Drop-ins ----------

@pytest.mark.parametrize("ersatz", ["User=root", "User=hans2", "User=", "User=hans extra"])
def test_ac4_user_muss_der_eingetragene_benutzer_sein(h, ersatz):
    abgelehnt(h, EINHEIT.replace("User=hans", ersatz).replace("UTC", "Europe/Berlin"))


def test_ac4_user_fehlt_in_der_neuen_datei(h):
    abgelehnt(h, EINHEIT.replace("User=hans\n", "").replace("UTC", "Europe/Berlin"))


def test_ac4_installierte_datei_mit_fremdem_user(h):
    (h["systemd"] / NAME).write_text(EINHEIT.replace("User=hans", "User=root"))
    abgelehnt(h, EINHEIT.replace("User=hans", "User=root").replace("UTC", "Europe/Berlin"))


def test_ac4_installierte_datei_fehlt(h):
    (h["systemd"] / NAME).unlink()
    abgelehnt(h, EINHEIT)


def test_ac4_symlink_wird_nicht_gefolgt(h):
    ziel = h["tmp"] / "anderswo.service"
    ziel.write_text(EINHEIT)
    (h["systemd"] / NAME).unlink()
    (h["systemd"] / NAME).symlink_to(ziel)
    abgelehnt(h, EINHEIT.replace("UTC", "Europe/Berlin"))
    assert ziel.read_text() == EINHEIT


def test_ac4_dropin_ordner_lehnt_ab(h):
    (h["systemd"] / f"{NAME}.d").mkdir()
    abgelehnt(h, EINHEIT.replace("UTC", "Europe/Berlin"))


# ---------- AC-5: gleiche Liste wie units.py, keine Umlenkung ----------

def test_ac5_erlaubnisliste_ist_in_helfer_und_units_py_gleich(h):
    import importlib.util as u
    spec = u.spec_from_file_location("units", BETRIEB / "units.py")
    units = u.module_from_spec(spec)
    spec.loader.exec_module(units)
    assert {k: v.pattern for k, v in h["m"].ERLAUBT.items()} == {k: v.pattern for k, v in units.ERLAUBT.items()}


def test_ac5_keine_umlenkung_ueber_umgebung_oder_argumente(h):
    quelltext = h["text"]
    assert "os.environ" not in quelltext and "getenv" not in quelltext
    assert not re.search(r"\bsys\.argv\[[^1]", quelltext)       # nur das Argument 1 (Einheit)
    assert h["m"].SYSTEMD == "/etc/systemd/system" and h["m"].SYSTEMCTL == "/usr/bin/systemctl"
    assert quelltext.startswith("#!/usr/bin/python3 -I")


# ---------- AC-6: atomar, daemon-reload, nur der Name ----------

def test_ac6_atomar_ohne_reste_und_nur_der_name_auf_stdout(h, capsys):
    neu = EINHEIT.replace("UTC", "Europe/Berlin")
    rc = h["m"].main(["helfer", NAME], neu.encode(), systemd=str(h["systemd"]), neu_laden=lambda: h["geladen"].append(1))
    assert rc == 0 and capsys.readouterr().out == NAME + "\n"
    assert sorted(p.name for p in h["systemd"].iterdir()) == [NAME]      # keine temporäre Datei bleibt
    assert h["geladen"] == [1]


def test_ac6_fehler_beim_schreiben_laesst_die_alte_datei(h, monkeypatch):
    alt = (h["systemd"] / NAME).read_bytes()
    monkeypatch.setattr(os, "replace", lambda *a, **k: (_ for _ in ()).throw(OSError("voll")))
    with pytest.raises(OSError):
        h["lauf"](EINHEIT.replace("UTC", "Europe/Berlin"))
    assert (h["systemd"] / NAME).read_bytes() == alt
    assert sorted(p.name for p in h["systemd"].iterdir()) == [NAME]


def test_ac6_ablehnung_gibt_ausgang_3_und_nichts_auf_stdout(h, capsys):
    rc = h["m"].main(["helfer", NAME], EINHEIT.replace("User=hans", "User=root").encode(), systemd=str(h["systemd"]), neu_laden=lambda: None)
    assert rc == 3 and capsys.readouterr().out == ""


def test_ac6_falsche_argumentzahl(h):
    assert h["m"].main(["helfer"], b"", systemd=str(h["systemd"]), neu_laden=lambda: None) == 3
    assert h["m"].main(["helfer", NAME, "extra"], b"", systemd=str(h["systemd"]), neu_laden=lambda: None) == 3


# ---------- Erzeugung durch einrichten.sh ----------

def test_einrichten_erzeugt_das_hilfsprogramm_mit_eingesetzten_werten(tmp_path):
    ziel = tmp_path / "soll"
    env = {**SAUBER, "FR_WURZEL": str(tmp_path), "FR_INSTANZ": "probe", "FR_TITEL": "Probe", "FR_BENUTZER": "hans", "EI_ZIEL": str(ziel)}
    r = subprocess.run(["bash", str(BETRIEB / "einrichten.sh"), "--erzeugen"], env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    datei = ziel / "sbin" / "probe-units-installieren"
    text = datei.read_text(encoding="utf-8")
    assert 'INSTANZ = "probe"' in text and 'BENUTZER = "hans"' in text and "__" not in text.replace("__name__", "").replace("__main__", "")
