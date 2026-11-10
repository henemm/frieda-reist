"""Rückmeldung mit Kontext (frieda-reist#449; Spec docs/specs/oberflaeche/rueckmeldung-kontext-449.md).

Die Seite hält beim Tippen auf die Sprechblase fest, wo sie war (ansicht, abschnitt, stand); der Dienst legt nur gültige Teile ab,
ein ungültiger Kontext wird verworfen, nie abgewiesen; der Konnektor und die Befehlszeile zeigen eine Zeile „Ort“. Nur erfundene
Beispielreisen; die Browsertests brauchen Playwright."""
import functools
import http.server
import inspect
import json
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bauen  # noqa: E402
import konnektor  # noqa: E402
import rueckmeldungen as rm  # noqa: E402
import texte  # noqa: E402
from playwright_pfad import PLAYWRIGHT  # noqa: E402
from test_rueckmeldungen import GUT, anfrage, dienst, post  # noqa: E402,F401

WURZEL = Path(__file__).resolve().parents[2]
BEISPIELE = WURZEL / "beispiel" / "reisen"
SKRIPT = Path(__file__).parent / "seiten_rueckmeldung_kontext_449.mjs"
browser = pytest.mark.skipif(not PLAYWRIGHT.exists() or not shutil.which("node"), reason="Playwright fehlt")
GUTER_KONTEXT = {"ansicht": "T-03", "abschnitt": "weg", "stand": 12}
RS_ALT = "const RS = D.reise_stand && D.reise_stand.nummer ? D.reise_stand : null;"
SCHLUESSEL = ("konnektor.rueckmeldungen.kontext", "konnektor.rueckmeldungen.kontext_ansicht",
              "konnektor.rueckmeldungen.kontext_abschnitt", "konnektor.rueckmeldungen.kontext_stand")


def eintraege_der_ablage(ablage):
    return [json.loads(z) for z in (ablage / "beispielreise/eingang.jsonl").read_text(encoding="utf-8").splitlines()]


# ---------- Dienst (AC-4 bis AC-6) ----------

def test_gueltiger_kontext_wird_abgelegt(dienst):   # AC-4
    basis, ablage = dienst
    code, e = post(basis, kontext=GUTER_KONTEXT)
    assert code == 201 and e["kontext"] == GUTER_KONTEXT
    assert eintraege_der_ablage(ablage)[0]["kontext"] == GUTER_KONTEXT


UNGUELTIG = [
    ("kein_objekt_text", "T-03", None),
    ("kein_objekt_liste", ["T-03"], None),
    ("kein_objekt_zahl", 5, None),
    ("fremder_schluessel", {"ansicht": "T-03", "person": "Ida"}, {"ansicht": "T-03"}),
    ("nur_fremde_schluessel", {"person": "Ida", "url": "x"}, None),
    ("muster_verletzt", {"ansicht": "../etc", "abschnitt": "weg"}, {"abschnitt": "weg"}),
    ("muster_leerzeichen", {"abschnitt": "mit Leerzeichen", "stand": 3}, {"stand": 3}),
    ("ansicht_zu_lang", {"ansicht": "a" * 81, "stand": 3}, {"stand": 3}),
    ("ansicht_grenze_ok", {"ansicht": "a" * 80}, {"ansicht": "a" * 80}),
    ("abschnitt_zu_lang", {"abschnitt": "a" * 41, "ansicht": "heute"}, {"ansicht": "heute"}),
    ("abschnitt_grenze_ok", {"abschnitt": "a" * 40}, {"abschnitt": "a" * 40}),
    ("stand_text", {"stand": "12", "ansicht": "heute"}, {"ansicht": "heute"}),
    ("stand_null", {"stand": 0, "ansicht": "heute"}, {"ansicht": "heute"}),
    ("stand_negativ", {"stand": -1, "ansicht": "heute"}, {"ansicht": "heute"}),
    ("stand_zu_gross", {"stand": 1000000, "ansicht": "heute"}, {"ansicht": "heute"}),
    ("stand_grenze_ok", {"stand": 999999}, {"stand": 999999}),
    ("stand_kommazahl", {"stand": 1.5, "ansicht": "heute"}, {"ansicht": "heute"}),
    ("stand_wahrheitswert", {"stand": True, "ansicht": "heute"}, {"ansicht": "heute"}),
    ("verschachtelt", {"ansicht": {"a": "b"}, "abschnitt": ["weg"], "stand": 4}, {"stand": 4}),
    ("leer", {}, None),
    ("zeilenumbruch_am_ende", {"ansicht": "heute\n", "abschnitt": "weg\n", "stand": 3}, {"stand": 3}),
]


@pytest.mark.parametrize("roh,erwartet", [u[1:] for u in UNGUELTIG], ids=[u[0] for u in UNGUELTIG])
def test_kontext_pruefen(roh, erwartet):   # AC-5, Einheit
    assert rm.kontext_pruefen(roh) == erwartet


@pytest.mark.parametrize("roh,erwartet", [u[1:] for u in UNGUELTIG], ids=[u[0] for u in UNGUELTIG])
def test_ungueltiger_kontext_wird_verworfen_nicht_abgewiesen(dienst, roh, erwartet):   # AC-5
    basis, ablage = dienst
    code, e = post(basis, kontext=roh)
    ohne_code, ohne = anfrage(basis + "/beispielreise/rueckmeldungen", "POST", {**GUT, "text": "ganz anderer Text"})
    assert code == ohne_code == 201
    assert set(e) - {"kontext"} == set(ohne)   # gleiche Antwort wie ohne Kontext, nur das Feld kontext darf dazukommen
    assert e.get("kontext") == erwartet
    assert eintraege_der_ablage(ablage)[0].get("kontext") == erwartet


def test_doppelt_trotz_anderem_kontext(dienst):   # AC-6
    basis, ablage = dienst
    c1, e1 = post(basis, kontext={"ansicht": "T-01"})
    c2, e2 = post(basis, kontext={"ansicht": "varianten", "stand": 7})
    assert (c1, c2) == (201, 200) and e1["id"] == e2["id"]
    assert len(eintraege_der_ablage(ablage)) == 1 and eintraege_der_ablage(ablage)[0]["kontext"] == {"ansicht": "T-01"}
    assert rm.INHALT == ("name", "art", "ziel", "text", "quelle")


# ---------- Alte Einträge und Anzeige (AC-7, AC-9, AC-10) ----------

ALT = {"name": "Ida", "art": "Frage", "ziel": "T-01", "text": "Wann landen wir?", "quelle": "", "id": "R-20260101-000000-abcd",
       "erstellt": "2026-01-01T00:00:00+00:00", "status": "neu", "kommentar": ""}


def ablegen(ablage, *eintraege):
    (ablage / "beispielreise" / "eingang.jsonl").write_text("".join(json.dumps(e) + "\n" for e in eintraege), encoding="utf-8")


def liste_in(kuerzel):
    texte.aufruf_sprache(kuerzel)
    try:
        return konnektor.liste_text("beispielreise", False)
    finally:
        texte.aufruf_sprache(texte.VORGABE_REISE)


def test_alter_eintrag_ausgabe_unveraendert(dienst, capsys):   # AC-7
    _, ablage = dienst
    ablegen(ablage, ALT)
    assert [e["id"] for e in rm.eintraege(ablage / "beispielreise")] == [ALT["id"]]
    assert konnektor.liste_text("beispielreise", False) == "\n".join([
        texte.t(texte.VORGABE_REISE, "konnektor.ausgabe.liste_text.2", w1=ALT["id"], w2="2026-01-01", w3="Ida", w4="Frage", w5="T-01", w6="neu"),
        "  Wann landen wir?"])
    rm.main(["liste", "beispielreise"])
    assert capsys.readouterr().out == (
        "R-20260101-000000-abcd  2026-01-01 00:00 UTC  Ida  [neu]\n"
        "  T-01 (ID not on the page) [Frage]:\n"
        "    Wann landen wir?\n"
        "\n1 feedback item(s).\n")


def test_ort_zeile_im_konnektor(dienst, monkeypatch):   # AC-9
    _, ablage = dienst
    monkeypatch.setenv("FR_TEXTE_ZUSATZ", "xx")
    ablegen(ablage, {**ALT, "kontext": GUTER_KONTEXT},
            {**ALT, "id": "R-20260102-000000-abcd", "erstellt": "2026-01-02T00:00:00+00:00", "kontext": {"stand": 5}})
    for kuerzel in ("de", "en", "xx"):
        a = texte.sprache(kuerzel).TEXTE
        assert all(s in a for s in SCHLUESSEL), kuerzel
        zeilen = liste_in(kuerzel).splitlines()
        teile = ", ".join([a["konnektor.rueckmeldungen.kontext_ansicht"].format(w1="T-03"),
                           a["konnektor.rueckmeldungen.kontext_abschnitt"].format(w1="weg"),
                           a["konnektor.rueckmeldungen.kontext_stand"].format(w1=12)])
        voll = a["konnektor.rueckmeldungen.kontext"].format(w1=teile)
        nur_stand = a["konnektor.rueckmeldungen.kontext"].format(w1=a["konnektor.rueckmeldungen.kontext_stand"].format(w1=5))
        assert voll in zeilen and nur_stand in zeilen, (kuerzel, zeilen)
        assert zeilen[zeilen.index(voll) - 1].strip() == "Wann landen wir?"   # direkt unter der Textzeile


def test_ort_zeile_in_der_befehlszeile(dienst, capsys):   # AC-9
    _, ablage = dienst
    ablegen(ablage, {**ALT, "kontext": GUTER_KONTEXT})
    rm.main(["liste", "beispielreise"])
    assert "  Place: view T-03, section weg, trip version 12\n" in capsys.readouterr().out


def test_feedback_give_ohne_kontext():   # AC-10: Werkzeug rueckmeldung_geben (englisch feedback_give) bleibt ohne Kontext-Parameter
    w = next(x for x in konnektor.WERKZEUGE if x["name"] == "rueckmeldung_geben")
    assert set(w["inputSchema"]["properties"]) == {"ziel", "art", "text", "name", "quelle"}


# ---------- Seite (AC-1 bis AC-3, AC-8) ----------

def gebaut(tmp_path, reise, rs_null=False):
    # Der Reise-Stand kommt aus dem Git-Verlauf der Reise: eine eigene kleine Kopie als Git-Repo, unabhängig vom Ort des Repos (CI)
    repo = tmp_path / "repo"
    shutil.copytree(BEISPIELE / reise, repo / "reisen" / reise)
    for z in (["init", "-q", "-b", "main"], ["config", "user.email", "test@example.invalid"], ["config", "user.name", "Ida Beispiel"],
              ["add", "-A"], ["commit", "-qm", "Reise angelegt"]):
        subprocess.run(["git", "-C", str(repo), *z], check=True, capture_output=True)
    bauen.bauen(repo / "reisen" / reise, tmp_path / "web" / "r")
    index = tmp_path / "web" / "r" / "index.html"
    if rs_null:
        html = index.read_text(encoding="utf-8")
        assert RS_ALT in html
        index.write_text(html.replace(RS_ALT, "const RS = null;"), encoding="utf-8")


def lauf(tmp_path, hash_, selektor, modus="online"):
    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(tmp_path / "web")))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        aus = subprocess.run(["node", str(SKRIPT), str(PLAYWRIGHT), f"http://127.0.0.1:{s.server_address[1]}/r/", hash_, selektor, modus],
                             capture_output=True, text=True, timeout=120, env={**os.environ, "RH_BROWSER": "chromium"})
    finally:
        s.shutdown()
    assert aus.returncode == 0, aus.stderr[-2000:]
    return json.loads(aus.stdout.strip().splitlines()[-1])


@browser
def test_kontext_tagesseite_weg_und_varianten(tmp_path):   # AC-1
    gebaut(tmp_path, "beispielreise")
    a = lauf(tmp_path, "T-02", ".ebene-weg button.zid[data-rm]")
    assert not a["fehler"] and len(a["bodys"]) == 1
    k = a["bodys"][0]["kontext"]
    assert k["ansicht"] == "T-02" and k["abschnitt"] == "weg" and k["stand"] == a["rs"] and isinstance(a["rs"], int)
    v = lauf(tmp_path, "varianten", "#main button[data-rm]")
    k = v["bodys"][0]["kontext"]
    assert k["ansicht"] == "varianten" and k.get("abschnitt") not in {"weg", "unterwegs", "hintergrund", "quellen", "nacht", "orte"}


@browser
def test_kontext_stadtwochenende_und_allgemein(tmp_path):   # AC-2
    gebaut(tmp_path, "stadtwochenende")
    a = lauf(tmp_path, "T-01", ".tagseite button.zid[data-rm]")
    assert not a["fehler"] and a["bodys"][0]["kontext"]["ansicht"] == "T-01"
    g = lauf(tmp_path, "rueckmeldungen", "[data-rm=allgemein]")
    k = g["bodys"][0]["kontext"]
    assert not g["fehler"] and k["ansicht"] == "rueckmeldungen" and "abschnitt" not in k and k["stand"] == g["rs"]


@browser
def test_ohne_reise_stand_kein_stand(tmp_path):   # AC-3
    gebaut(tmp_path, "beispielreise", rs_null=True)
    a = lauf(tmp_path, "T-02", ".ebene-weg button.zid[data-rm]")
    assert not a["fehler"] and a["rs"] is None
    assert "stand" not in a["bodys"][0]["kontext"] and a["bodys"][0]["kontext"]["ansicht"] == "T-02"


@browser
def test_offline_nachgereicht_traegt_kontext_vom_klick(tmp_path):   # AC-8
    gebaut(tmp_path, "beispielreise")
    a = lauf(tmp_path, "T-02", ".ebene-weg button.zid[data-rm]", "offline")
    assert not a["fehler"] and len(a["bodys"]) == 1
    k = a["bodys"][0]["kontext"]
    assert k["ansicht"] == "T-02" and k["abschnitt"] == "weg"   # nicht „wissen“, wo die Person beim Nachreichen war
