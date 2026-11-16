"""Textformen (#594, Product Owner 16.11.2026): Kurztext, Langtext, Dokument. Register engine/textform.py; der Schreibweg prüft
danach, der Konnektor beschreibt jedes Feld daraus, die Seite zeigt Langtext mit dem Atom langtext, Kalender und Meldungen
nehmen Klartext. Erfundene Testdaten beider Beispielreisen."""
import functools
import http.server
import json
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bauen  # noqa: E402
import konnektor as kn  # noqa: E402
import packliste  # noqa: E402
import rueckmeldungen as rm  # noqa: E402
import schnittstelle  # noqa: E402
import schreiben as sb  # noqa: E402
import texte  # noqa: E402
import textform  # noqa: E402

BEISPIELE = Path(__file__).resolve().parent.parent.parent / "beispiel" / "reisen"
IDA = {"name": "Ida", "rolle": "organisator"}


def kopie(tmp_path, reise="beispielreise"):
    q = tmp_path / reise
    shutil.copytree(BEISPIELE / reise, q)
    return q


def routen(q):
    return yaml.safe_load((q / "plan" / "routen.yaml").read_text(encoding="utf-8"))


def alle_werkzeuge():
    """Jedes Werkzeug, das ein Zugang sehen kann (wie werkzeuge_fuer, ohne Rollenfilter)."""
    namen = [n for n in dir(kn) if n.isupper()]
    gesehen, aus = set(), []
    for n in namen:
        w = getattr(kn, n)
        for x in (w if isinstance(w, list) else [w]):
            if isinstance(x, dict) and "inputSchema" in x and "name" in x and x["name"] not in gesehen:
                gesehen.add(x["name"])
                aus.append(x)
    assert len(aus) > 50
    return aus


def eigenschaften(schema, pfad=""):
    for k, e in (schema.get("properties") or {}).items():
        if isinstance(e, dict):
            yield pfad + k, e
            if e.get("type") == "object":
                yield from eigenschaften(e, pfad + k + ".")
            if isinstance(e.get("items"), dict) and e["items"].get("type") == "object":
                yield from eigenschaften(e["items"], pfad + k + "[].")


# ---------- Register ----------

def test_register_form_und_laenge():
    for feld, (form, n) in textform.FELDER.items():
        assert form in (textform.KURZ, textform.LANG, textform.DOKUMENT) and isinstance(n, int) and n > 0, feld
    assert textform.EINZEILIG <= set(textform.FELDER)
    # Dienste prüfen mit denselben Längen
    assert rm.LAENGE["text"] == textform.laenge("rueckmeldung.text")
    assert rm.AG_LAENGE["notiz"] == textform.laenge("aufgabe.notiz") and rm.AG_LAENGE["kommentar"] == textform.laenge("aufgabe.kommentar")
    assert rm.AG_LAENGE["kommentar"] == textform.laenge("wunsch.kommentar")   # Wunsch-Kommentar prüft der Dienst mit derselben Grenze
    assert packliste.MAX_NOTIZ == textform.laenge("gegenstand.notiz")


@pytest.mark.parametrize("text, fund", [
    ("## Abschnitt\nText", "ueberschrift"), ("| a | b |\n|---|---|", "tabelle"), ("Siehe ![x](BI-01)", "bild"),
    ("Hallo <b>fett</b>", "html"), ("```\ncode\n```", "code"),
    ("**fett**, *kursiv*, [Link](https://example.invalid)\n\n- eins\n- zwei", None), ("3 < 4 und 5 > 2", None),
])
def test_langtext_fund(text, fund):
    f = textform.langtext_fund(text)
    assert (f[0] if f else None) == fund


@pytest.mark.parametrize("text, klar", [
    ("**Früh los**, *kursiv* und __auch__", "Früh los, kursiv und auch"),
    ("Mitnehmen:\n* Wasser\n- Lampe", "Mitnehmen:\n- Wasser\n- Lampe"),
    ("[Bahn](https://example.invalid/fahrplan)", "Bahn (https://example.invalid/fahrplan)"),
    ("Preis 3 * 4 = 12, Datei_name_x", "Preis 3 * 4 = 12, Datei_name_x"),
    ("Stern \\* bleibt", "Stern * bleibt"),
])
def test_klartext(text, klar):
    assert textform.klartext(text) == klar


def test_klartext_eine_zeile():
    assert textform.klartext("**Kostenlos** bis 7 Tage vorher.\n\nDanach 1 Nacht.", eine_zeile=True) == "Kostenlos bis 7 Tage vorher. · Danach 1 Nacht."


# ---------- Konnektor: jedes Feld sagt, was es kann ----------

@pytest.mark.parametrize("sprache", texte.SPRACHEN)
def test_jede_eigenschaft_hat_eine_beschreibung(sprache):
    aussen = schnittstelle.aussen(kn.lokalisiert(alle_werkzeuge(), sprache))
    assert "x-textform" not in json.dumps(aussen)
    ohne = [f"{w['name']}.{p}" for w in aussen for p, e in eigenschaften(w["inputSchema"]) if not e.get("description") and "." not in p]
    assert not ohne, ohne


# Textfelder, die bewusst kurz bleiben: Profil (Konto), Beleg (Dateiname), Notiz einer Einladung und eines Werts (eine Zeile in
# der Herkunft), Ausnahme-Hinweis eines Dings
KURZ_BLEIBT = {"profil_eintrag_setzen.text", "beleg_anlegen.text", "person_einladen.notiz", "reise_anlegen.notiz",
               "reise_anlegen.personen[].notiz", "an_frieda_melden.text", "wert_eintragen.notiz", "wert_eintragen.werte[].notiz"}


def test_lange_textfelder_haben_eine_form():
    """Felder namens text, notiz, storno, antwort, kommentar sind Langtext oder Dokument aus dem Register, außer den kurzen."""
    fehlt = []
    for w in alle_werkzeuge():
        for p, e in eigenschaften(w["inputSchema"]):
            if p.split(".")[-1].split("[")[0] in ("text", "notiz", "storno", "antwort", "kommentar") and e.get("type") == "string" \
                    and "x-textform" not in e and f"{w['name']}.{p}" not in KURZ_BLEIBT and "." not in p.replace("[].", "#"):
                fehlt.append(f"{w['name']}.{p}")
    assert not fehlt, fehlt


@pytest.mark.parametrize("sprache", texte.SPRACHEN)
def test_beschreibung_nennt_form_und_laenge_des_registers(sprache):
    intern = {w["name"]: w for w in kn.lokalisiert(alle_werkzeuge(), sprache)}
    roh = {w["name"]: w for w in alle_werkzeuge()}
    geprueft = 0
    for name, w in roh.items():
        for p, e in eigenschaften(w["inputSchema"]):
            if "x-textform" in e and "." not in p:
                b = intern[name]["inputSchema"]["properties"][p]["description"]
                feld = e["x-textform"]
                form = "einzeilig" if feld in textform.EINZEILIG else textform.form(feld)
                assert texte.t(sprache, "konnektor.textform." + form, n=textform.laenge(feld)) in b, (name, p, b)
                assert str(textform.laenge(feld)) in b
                geprueft += 1
    assert geprueft >= 20


def test_anleitung_nennt_die_textformen():
    for sp in texte.SPRACHEN:
        assert "**" in texte.t(sp, "konnektor.anleitung.grenzen")


# ---------- Schreibweg ----------

def test_tagestext_als_langtext_behaelt_absaetze_und_listen(tmp_path):
    q = kopie(tmp_path)
    text = "**Früh los**, die Aussicht ist morgens leer.\n\nMitnehmen:\n- 2 Liter Wasser je Person\n- Stirnlampe   \n\n\n\nEnde."
    sb.tag_aendern(q, IDA, {"ziel": "T-03", "text": text})
    t = routen(q)["tage"]["T-03"]["text"]
    assert t == "**Früh los**, die Aussicht ist morgens leer.\n\nMitnehmen:\n- 2 Liter Wasser je Person\n- Stirnlampe\n\nEnde."
    bauen.Bauer(q, tmp_path / "web").daten()   # die Datei bleibt baubar


@pytest.mark.parametrize("text, wort", [("## Morgens\nLos", "Überschriften"), ("<b>fett</b>", "HTML"), ("| a | b |", "Tabellen")])
def test_langtext_lehnt_ab_was_er_nicht_kann(tmp_path, text, wort):
    q = kopie(tmp_path)
    with pytest.raises(sb.Ablehnung, match=wort):
        sb.tag_aendern(q, IDA, {"ziel": "T-03", "text": text})


def test_langtext_ist_sauber(tmp_path):
    """Saubere Daten (#476) gelten auch in jeder Zeile eines Langtexts: keine Kennungen im sichtbaren Text."""
    q = kopie(tmp_path)
    with pytest.raises(sb.Ablehnung):
        sb.tag_aendern(q, IDA, {"ziel": "T-03", "text": "Erst lesen\n- siehe V-01.a"})


def test_langtext_laenge_aus_dem_register(tmp_path):
    q = kopie(tmp_path)
    with pytest.raises(sb.Ablehnung, match=str(textform.laenge("tag.text"))):
        sb.tag_aendern(q, IDA, {"ziel": "T-03", "text": "x" * (textform.laenge("tag.text") + 1)})


def test_frage_bleibt_eine_zeile(tmp_path):
    q = kopie(tmp_path)
    sb.frage_anlegen(q, IDA, {"text": "Nehmen wir den **frühen** Zug\noder den späten?"})
    zeilen = (q / "offene-fragen.md").read_text(encoding="utf-8").splitlines()
    assert any("Nehmen wir den **frühen** Zug oder den späten?" in z for z in zeilen)


def test_buchung_storno_und_notiz_als_langtext(tmp_path):
    q = kopie(tmp_path, "stadtwochenende")
    r = routen(q)
    fuer = next(iter(r.get("unterkuenfte") or {}))
    sb.buchung_anlegen(q, IDA, {"fuer": [fuer], "status": "gebucht", "quelle": "erfunden (Test)",
                                "storno": "**kostenlos** bis 7 Tage vorher\n- danach 1 Nacht",
                                "notiz": "Schlüssel:\n- beim Nachbarn\n- Code 1234 (erfunden)"})
    b = next(b for b in routen(q)["buchungen"].values() if b.get("notiz", "").startswith("Schlüssel"))
    assert b["storno"] == "**kostenlos** bis 7 Tage vorher\n- danach 1 Nacht" and "\n- beim Nachbarn" in b["notiz"]
    bauen.Bauer(q, tmp_path / "web").daten()


# ---------- Kalender ----------

def test_kalender_zeigt_tagestext_ohne_auszeichnung(tmp_path):
    import kalender
    q = kopie(tmp_path)
    d = bauen.Bauer(q, tmp_path / "web").daten()
    tag = next(e for e in kalender.eintraege(d) if e.get("id") == "T-02")
    assert "**" not in tag["text"] and "Erster Wandertag." in tag["text"] and "- 2 Liter Wasser je Person" in tag["text"]


# ---------- Seite ----------

def _browser():
    from playwright_pfad import PLAYWRIGHT
    return PLAYWRIGHT.exists() and shutil.which("node")


@pytest.mark.skipif(not _browser(), reason="Playwright fehlt")
def test_seite_zeigt_langtext_als_markdown_ohne_html(tmp_path):
    """Tagestext der Beispielreise (Beispielwert mit Liste und Fettem), dazu eine Frage mit Fettem und ein eingeschleustes Tag
    in einer Option: die Seite zeigt Liste und Fettes, das Tag nur als Text; Links öffnen in neuem Fenster."""
    from playwright_pfad import PLAYWRIGHT
    q = kopie(tmp_path)
    r = (q / "plan" / "routen.yaml").read_text(encoding="utf-8")
    r = r.replace('text: "Beide Wege beginnen in Altendorf',
                  'text: "Siehe [Fahrplan](https://example.invalid/fahrplan) <img src=x onerror=alert(1)> **Beide** Wege beginnen in Altendorf', 1)
    (q / "plan" / "routen.yaml").write_text(r, encoding="utf-8")
    sb.frage_anlegen(q, IDA, {"text": "Nehmen wir den **frühen** Zug?"})
    bauen.bauen(q, tmp_path / "seiten" / "r")

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(tmp_path / "seiten")))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        aus = subprocess.run(["node", str(Path(__file__).parent / "seiten_langtext.mjs"), str(PLAYWRIGHT),
                              f"http://127.0.0.1:{s.server_address[1]}/r/", "T-02", "fragen", "V-01", "bausteine"],
                             capture_output=True, text=True, timeout=300, env={**os.environ, "RH_BROWSER": "chromium"})
    finally:
        s.shutdown()
    assert aus.returncode == 0, aus.stderr[-2000:]
    e = json.loads(aus.stdout.strip().splitlines()[-1])
    assert e["fehler"] == []
    assert e["T-02"]["li"] >= 2 and e["T-02"]["fett"] >= 1 and not e["T-02"]["sterne"], e["T-02"]
    assert e["fragen"]["fett"] >= 1 and not e["fragen"]["sterne"], e["fragen"]
    v = e["V-01"]
    assert v["fremd"] == 0 and "<img" in v["text"] and ["_blank", "noopener"] in v["links"], v
    assert e["bausteine"]["li"] >= 2 and e["bausteine"]["fett"] >= 1
