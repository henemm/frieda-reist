"""Tests für engine/konten.py (Paket J1, Issue #45): Szenarien aus #43, soweit sie ohne Web und Konnektor gehen.
Alle Beispiele sind erfunden."""
import json
import re
import sqlite3
import stat
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import konten  # noqa: E402

IDA, KARL, MO = "ida@beispiel.invalid", "karl@beispiel.invalid", "mo@beispiel.invalid"


@pytest.fixture(autouse=True)
def umgebung(tmp_path, monkeypatch):
    monkeypatch.setenv("RM_ABLAGE", str(tmp_path / "ablage"))
    monkeypatch.setenv("FR_MAIL_DATEI", str(tmp_path / "mails.jsonl"))
    monkeypatch.setenv("FR_BASIS", "https://frieda.beispiel.invalid")
    uhr = {"t": 1_800_000_000.0}
    monkeypatch.setattr(konten, "_jetzt", lambda: uhr["t"])
    return {"tmp": tmp_path, "uhr": uhr}


def mails(umgebung, an=None):
    p = umgebung["tmp"] / "mails.jsonl"
    alle = [json.loads(z) for z in p.read_text().splitlines()] if p.exists() else []
    return [m for m in alle if an is None or m["an"] == an]


def letzter_code(umgebung, an):
    an = an.strip().lower()
    return re.search(r"Dein Code für Frieda: (\d{3}) (\d{3})", mails(umgebung, an)[-1]["text"]).expand(r"\1\2")


def einloggen(umgebung, an, name=None, **kw):
    konten.code_anfordern(an)
    return konten.anmelden(an, letzter_code(umgebung, an), name=name, **kw)


def test_szenario1_neu_ohne_einladung(umgebung):
    konten.code_anfordern("  Ida@Beispiel.INVALID ")
    m = mails(umgebung, IDA)[0]
    assert "Dein Code für Frieda" in m["text"] and "https://frieda.beispiel.invalid/anmelden?schritt=code&email=" in m["text"]
    code = letzter_code(umgebung, IDA)
    with pytest.raises(konten.NameNoetig):
        konten.anmelden(IDA, code)                      # neues Konto braucht einen Namen …
    token, k = konten.anmelden(IDA, code, name="Ida")   # … derselbe Code gilt danach noch
    assert k["id"].startswith("K-") and k["email"] == IDA and k["name"] == "Ida" and k["rechte"] == []
    assert konten.sitzung(token)["id"] == k["id"]
    assert konten.mitgliedschaften(k["id"]) == []
    with pytest.raises(konten.KontoFehler):            # Code ist verbraucht
        konten.anmelden(IDA, code)
    # Reisen anlegen: erst bitten, dann entscheidet der Betreiber
    assert konten.reisen_anlegen_anfragen(k["id"]) == "offen"
    assert [a["email"] for a in konten.anfragen()] == [IDA]
    konten.freischalten(k["id"])
    assert konten.recht(konten.konto(k["id"]), "reise_anlegen") and konten.anfragen() == []
    assert konten.reisen_anlegen_anfragen(k["id"]) == "schon_erlaubt"


def test_abgelehnte_bitte_bleibt_abgelehnt(umgebung):
    _, k = einloggen(umgebung, IDA, "Ida")
    konten.reisen_anlegen_anfragen(k["id"])
    konten.freischalten(k["id"], ja=False)
    assert konten.reisen_anlegen_anfragen(k["id"]) == "abgelehnt" and not konten.recht(konten.konto(k["id"]),
                                                                                         "reise_anlegen")


def test_szenario2_eingeladen_gilt_beim_ersten_anmelden(umgebung):
    r = konten.einladen("winterwoche", "karl", KARL, "einbringer", "Karl", "Ida", titel="Winterwoche im Allgäu",
                        seite="https://frieda.beispiel.invalid/winterwoche-x/")
    assert r == {"sofort": False}
    m = mails(umgebung, KARL)[0]
    assert "Ida hat dich zur Reise „Winterwoche im Allgäu“ eingeladen (du bringst ein)." in m["text"]
    assert "https://frieda.beispiel.invalid/einladung/" in m["text"] and "Lesen geht ohne Anmeldung" in m["text"]
    _, k = einloggen(umgebung, KARL)                    # Name kommt aus der Einladung
    assert k["name"] == "Karl"
    assert [(x["reise"], x["schluessel"]) for x in konten.mitgliedschaften(k["id"])] == [("winterwoche", "karl")]
    assert konten.mitglied(k["id"], "winterwoche") == "karl" and konten.konto_von_person("winterwoche",
                                                                                          "karl") == k["id"]


def test_einladungslink_mit_anderer_adresse(umgebung):
    konten.einladen("winterwoche", "karl", "karl.arbeit@beispiel.invalid", "einbringer", "Karl", "Ida")
    link = re.search(r"/einladung/(\S+)", mails(umgebung)[-1]["text"]).group(1)
    e = konten.einladung(link)
    assert e["reise"] == "winterwoche" and e["name"] == "Karl" and not e["eingeloest"]
    # Karl meldet sich über den Link mit seiner privaten Adresse an
    _, k = einloggen(umgebung, KARL, einladung=link)
    assert k["name"] == "Karl" and konten.mitglied(k["id"], "winterwoche") == "karl"
    assert konten.einladung(link)["eingeloest"]
    # wer sich später mit der Arbeitsadresse anmeldet, bekommt die Person nicht noch einmal
    _, k2 = einloggen(umgebung, "karl.arbeit@beispiel.invalid", "Karl A.")
    assert konten.mitgliedschaften(k2["id"]) == []


def test_einladung_einloesen_angemeldet(umgebung):
    _, k = einloggen(umgebung, KARL, "Karl")
    konten.einladen("winterwoche", "karl", "karl.arbeit@beispiel.invalid", "einbringer", "Karl", "Ida")
    link = re.search(r"/einladung/(\S+)", mails(umgebung)[-1]["text"]).group(1)
    assert konten.einladung_einloesen(link, k["id"]) == "winterwoche"
    with pytest.raises(konten.KontoFehler):
        konten.einladung_einloesen(link, k["id"])
    umgebung["uhr"]["t"] += 31 * 86400
    konten.einladen("sommer", "karl", "karl.arbeit@beispiel.invalid", "einbringer", "Karl", "Ida")
    alt = re.search(r"/einladung/(\S+)", mails(umgebung)[-1]["text"]).group(1)
    umgebung["uhr"]["t"] += 31 * 86400
    assert konten.einladung(alt) is None                # abgelaufen


def test_szenario4_konto_und_zweite_reise_sofort(umgebung):
    _, k = einloggen(umgebung, KARL, "Karl")
    r = konten.einladen("sommer", "karl", "KARL@beispiel.invalid", "reisend", "Karl", "Ida", titel="Sommer am See")
    assert r == {"sofort": True} and konten.mitglied(k["id"], "sommer") == "karl"
    m = mails(umgebung, KARL)[-1]
    assert "steht ab jetzt bei deinen Reisen" in m["text"] and "/einladung/" not in m["text"]


def test_szenario5_neues_geraet_gleiches_konto(umgebung):
    t1, k1 = einloggen(umgebung, IDA, "Ida", geraet="Handy")
    t2, k2 = einloggen(umgebung, IDA, geraet="Rechner")
    assert k1["id"] == k2["id"] and t1 != t2
    assert {g["geraet"] for g in konten.geraete(k1["id"])} == {"Handy", "Rechner"}
    konten.abmelden(t1)
    assert konten.sitzung(t1) is None and konten.sitzung(t2)["id"] == k1["id"]
    konten.alle_abmelden(k1["id"])
    assert konten.sitzung(t2) is None


def test_szenario6_adresse_aendern(umgebung):
    _, ida = einloggen(umgebung, IDA, "Ida")
    _, karl = einloggen(umgebung, KARL, "Karl")
    with pytest.raises(konten.KontoFehler, match="gehört schon zu einem Konto"):
        konten.code_anfordern(KARL, zweck="adresse", konto=ida["id"])
    neu = "ida.neu@beispiel.invalid"
    konten.code_anfordern(neu, zweck="adresse", konto=ida["id"])
    m = mails(umgebung, neu)[-1]
    assert "neue Adresse bestätigen" in m["betreff"] and "/anmelden?" not in m["text"]
    code = re.search(r"(\d{3}) (\d{3})", m["text"]).expand(r"\1\2")
    with pytest.raises(konten.KontoFehler):            # Code gehört zu Idas Konto, nicht zu Karls
        konten.adresse_aendern(karl["id"], neu, code)
    konten.code_anfordern(neu, zweck="adresse", konto=ida["id"])
    code = re.search(r"(\d{3}) (\d{3})", mails(umgebung, neu)[-1]["text"]).expand(r"\1\2")
    assert konten.adresse_aendern(ida["id"], " Ida.Neu@beispiel.invalid", code) == neu
    assert konten.konto(ida["id"])["email"] == neu and konten.konto_per_email(IDA) is None
    _, wieder = einloggen(umgebung, neu)
    assert wieder["id"] == ida["id"]                    # feste Kennung bleibt


def test_hoechstens_ein_konto_je_adresse(umgebung):
    _, a = einloggen(umgebung, IDA, "Ida")
    _, b = einloggen(umgebung, "IDA@beispiel.invalid", "Ida zwei")
    assert a["id"] == b["id"] and b["name"] == "Ida"
    with sqlite3.connect(konten.pfad()) as v:
        assert v.execute("SELECT COUNT(*) FROM konten").fetchone()[0] == 1
        with pytest.raises(sqlite3.IntegrityError):
            v.execute("INSERT INTO konten (id, email, angelegt) VALUES ('K-x', ?, 'heute')", (IDA,))


def test_szenario10_entfernen_und_sperren(umgebung):
    konten.einladen("winterwoche", "karl", KARL, "einbringer", "Karl", "Ida")
    t, k = einloggen(umgebung, KARL)
    assert konten.entfernen("winterwoche", "karl") and konten.mitglied(k["id"], "winterwoche") is None
    assert konten.sitzung(t)                             # aus der Reise genommen, Konto bleibt
    konten.sperren(k["id"])
    assert konten.sitzung(t) is None
    konten.code_anfordern(KARL)
    with pytest.raises(konten.KontoFehler, match="gesperrt"):
        konten.anmelden(KARL, letzter_code(umgebung, KARL))
    konten.sperren(k["id"], False)
    assert einloggen(umgebung, KARL)[1]["id"] == k["id"]


def test_szenario11_konto_selbst_loeschen(umgebung):
    konten.einladen("winterwoche", "karl", KARL, "einbringer", "Karl", "Ida")
    t, k = einloggen(umgebung, KARL)
    konten.loeschen(k["id"])
    assert konten.konto(k["id"]) is None and konten.sitzung(t) is None
    assert konten.konto_von_person("winterwoche", "karl") is None
    _, neu = einloggen(umgebung, KARL, "Karl")           # Adresse ist wieder frei, neues Konto
    assert neu["id"] != k["id"]


def test_zusammenfuehren(umgebung):
    konten.einladen("winterwoche", "karl", KARL, "einbringer", "Karl", "Ida")
    _, alt = einloggen(umgebung, KARL)
    konten.recht_setzen(alt["id"], "reise_anlegen")
    _, neu = einloggen(umgebung, "karl2@beispiel.invalid", "Karl")
    konten.zusammenfuehren(alt["id"], neu["id"])
    assert konten.konto(alt["id"]) is None and konten.mitglied(neu["id"], "winterwoche") == "karl"
    assert konten.recht(konten.konto(neu["id"]), "reise_anlegen")


def test_code_falsch_abgelaufen_zu_oft(umgebung):
    konten.code_anfordern(IDA)
    code = letzter_code(umgebung, IDA)
    for _ in range(konten.CODE_VERSUCHE):
        with pytest.raises(konten.KontoFehler, match="stimmt nicht"):
            konten.anmelden(IDA, "000000" if code != "000000" else "111111", name="Ida")
    with pytest.raises(konten.KontoFehler, match="stimmt nicht"):
        konten.anmelden(IDA, code, name="Ida")          # nach 5 Fehlversuchen ist auch der richtige verbraucht
    umgebung["uhr"]["t"] += 3600
    konten.code_anfordern(IDA)
    code = letzter_code(umgebung, IDA)
    umgebung["uhr"]["t"] += konten.CODE_MINUTEN * 60 + 1
    with pytest.raises(konten.KontoFehler, match="stimmt nicht"):
        konten.anmelden(IDA, code, name="Ida")
    with pytest.raises(konten.KontoFehler, match="stimmt nicht"):
        konten.anmelden(MO, "123456", name="Mo")        # nie angefordert: derselbe Satz


def test_code_mit_leerzeichen(umgebung):
    konten.code_anfordern(IDA)
    c = letzter_code(umgebung, IDA)
    assert konten.anmelden(IDA, f" {c[:3]} {c[3:]} ", name="Ida")[1]["email"] == IDA


def test_begrenzung_je_adresse_und_ip(umgebung):
    for _ in range(3):
        konten.code_anfordern(IDA, ip="192.0.2.1")
    with pytest.raises(konten.KontoFehler, match="Zu viele"):
        konten.code_anfordern(IDA, ip="192.0.2.1")
    umgebung["uhr"]["t"] += 15 * 60 + 1
    konten.code_anfordern(IDA, ip="192.0.2.1")
    for i in range(6):
        konten.code_anfordern(f"p{i}@beispiel.invalid", ip="192.0.2.1")
    with pytest.raises(konten.KontoFehler, match="Zu viele"):
        konten.code_anfordern("q@beispiel.invalid", ip="192.0.2.1")
    konten.code_anfordern("q@beispiel.invalid", ip="192.0.2.2")


def test_keine_auskunft_ueber_adressen(umgebung):
    einloggen(umgebung, IDA, "Ida")
    assert konten.code_anfordern(IDA) is None and konten.code_anfordern(MO) is None
    a, b = mails(umgebung, IDA)[-1], mails(umgebung, MO)[-1]
    gleich = lambda m, e: re.sub(r"\d", "0", m["text"].replace(e, "X").replace(e.replace("@", "%40"), "X"))
    assert gleich(a, IDA) == gleich(b, MO)


def test_geheimnisse_nur_als_hash(umgebung):
    konten.einladen("winterwoche", "karl", KARL, "einbringer", "Karl", "Ida")
    link = re.search(r"/einladung/(\S+)", mails(umgebung)[-1]["text"]).group(1)
    konten.code_anfordern(IDA)
    code = letzter_code(umgebung, IDA)
    token, _ = konten.anmelden(IDA, code, name="Ida")
    konten.code_anfordern(IDA)
    offen = letzter_code(umgebung, IDA)
    roh = b"".join(p.read_bytes() for p in konten.pfad().parent.iterdir())
    for geheim in (link, token, offen):
        assert geheim.encode() not in roh
    assert stat.S_IMODE(konten.pfad().stat().st_mode) == 0o600
    assert stat.S_IMODE(konten.pfad().parent.stat().st_mode) == 0o700


def test_sitzung_rollierend_und_abgelaufen(umgebung):
    t, _ = einloggen(umgebung, IDA, "Ida")
    for _ in range(3):
        umgebung["uhr"]["t"] += 300 * 86400              # genutzt alle 300 Tage: bleibt gültig
        assert konten.sitzung(t)
    umgebung["uhr"]["t"] += 366 * 86400
    assert konten.sitzung(t) is None
    assert konten.sitzung("zu-kurz") is None and konten.sitzung(None) is None


def test_eingaben_pruefen(umgebung):
    for falsch in ("", "ida", "ida@", "a b@c.de", None, 5, "x" * 250 + "@c.de"):
        with pytest.raises(konten.KontoFehler):
            konten.code_anfordern(falsch)
    with pytest.raises(konten.KontoFehler):
        konten.einladen("Böse Reise", "karl", KARL, "einbringer", "Karl", "Ida")
    with pytest.raises(konten.KontoFehler):
        konten.einladen("winterwoche", "karl", KARL, "chef", "Karl", "Ida")
    _, k = einloggen(umgebung, IDA, "Ida")
    with pytest.raises(konten.KontoFehler):
        konten.name_setzen(k["id"], "x" * 81)
    assert konten.name_setzen(k["id"], "  Ida   Muster ") == "Ida Muster"


def test_person_schon_mit_anderem_konto(umgebung):
    konten.einladen("winterwoche", "karl", KARL, "einbringer", "Karl", "Ida")
    einloggen(umgebung, KARL)
    with pytest.raises(konten.KontoFehler, match="anderen Konto"):
        konten.einladen("winterwoche", "karl", MO, "einbringer", "Karl", "Ida")


def test_mail_ohne_einrichtung(umgebung, monkeypatch):
    monkeypatch.delenv("FR_MAIL_DATEI")
    monkeypatch.delenv("FR_SMTP_HOST", raising=False)
    with pytest.raises(konten.KontoFehler, match="nicht eingerichtet"):
        konten.code_anfordern(IDA)


def test_mail_per_smtp(umgebung, monkeypatch):
    gesendet = []

    class SMTP:
        def __init__(self, host, port, timeout):
            gesendet.append(("verbinde", host, port))

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def starttls(self):
            gesendet.append("starttls")

        def login(self, u, p):
            gesendet.append(("login", u))

        def send_message(self, m):
            gesendet.append((m["To"], m["From"], m["Subject"]))

    monkeypatch.delenv("FR_MAIL_DATEI")
    monkeypatch.setattr(konten.smtplib, "SMTP", SMTP)
    for k, w in {"FR_SMTP_HOST": "smtp.beispiel.invalid", "FR_SMTP_USER": "u", "FR_SMTP_PASS": "p",
                 "FR_ABSENDER": "Frieda <frieda@beispiel.invalid>"}.items():
        monkeypatch.setenv(k, w)
    konten.code_anfordern(IDA)
    assert gesendet[:3] == [("verbinde", "smtp.beispiel.invalid", 587), "starttls", ("login", "u")]
    assert gesendet[3][0] == IDA and gesendet[3][2].startswith("Frieda: dein Code")


def test_befehle(umgebung, capsys):
    _, k = einloggen(umgebung, IDA, "Ida")
    konten.reisen_anlegen_anfragen(k["id"])
    assert konten.main(["anfragen"]) == 0 and IDA in capsys.readouterr().out
    assert konten.main(["freischalten", IDA]) == 0 and konten.recht(konten.konto(k["id"]), "reise_anlegen")
    assert konten.main(["betreiber", IDA]) == 0 and konten.recht(konten.konto(k["id"]), "betreiber")
    assert konten.main(["einladen", "winterwoche", "karl", KARL, "einbringer", "Karl", "Ida"]) == 0
    assert konten.main(["liste"]) == 0 and "rechte: betreiber,reise_anlegen" in capsys.readouterr().out
    assert konten.main(["sperren", "niemand@beispiel.invalid"]) == 2 and "FEHLER" in capsys.readouterr().out
    assert konten.main(["quatsch"]) == 1


def test_konten_ordner_alt_und_neu(tmp_path, monkeypatch):
    """Die Datenbank liegt neben der Ablage in _konten; eine ältere unter <Ablage>/_konten gilt, bis am neuen Ort eine liegt."""
    import instanz
    for n in ("RM_SEITEN", "KN_SEITEN", "FR_SEITEN", "FR_KONTEN", "FR_EINSTELLUNGEN"):
        monkeypatch.delenv(n, raising=False)
    monkeypatch.setenv("RM_ABLAGE", str(tmp_path / "_rueckmeldungen"))
    monkeypatch.chdir(tmp_path)
    assert instanz.konten() == tmp_path / "_konten"                      # nichts vorhanden: neuer Ort
    alt = tmp_path / "_rueckmeldungen" / "_konten"
    alt.mkdir(parents=True)
    (alt / "konten.db").write_text("alt")
    (tmp_path / "_konten").mkdir()                                       # leerer neuer Ordner (deploy.sh legt ihn an)
    assert instanz.konten() == alt                                       # die Datenbank geht nicht verloren
    (tmp_path / "_konten" / "konten.db").write_text("neu")
    assert instanz.konten() == tmp_path / "_konten"
    (tmp_path / "_konten" / "konten.db").unlink()
    monkeypatch.setenv("FR_KONTEN", str(tmp_path / "woanders"))
    assert instanz.konten() == alt                                       # ausdrücklich gesetzter Ort ohne Datenbank: Rückfall
    (tmp_path / "woanders").mkdir()
    (tmp_path / "woanders" / "konten.db").write_text("x")
    assert instanz.konten() == tmp_path / "woanders"
