"""Sicherheitsprüfung 12.11.2026: je geschlossener Lücke ein Test, der sie wieder öffnen würde.

Reiseseite (fremdes HTML und Skript aus Texten und Namen), Belege, Kalender, Push-Adressen, Meldungen ohne Reise,
Übernehmen aus fremden Reisen, Anmeldecodes."""
import json
import re
import sys
from pathlib import Path

import pytest

ENGINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE))

import bauen  # noqa: E402
import belege  # noqa: E402
import kalender  # noqa: E402
import konten  # noqa: E402


# ---------- Reiseseite ----------

@pytest.mark.parametrize("adresse", ["javascript:alert(1)", "JaVaScript:alert(1)", "java\tscript:alert(1)", " javascript:x",
                                     "data:text/html,<script>1</script>", "vbscript:x", "file:///etc/passwd"])
def test_reisetext_lehnt_adressen_mit_fremdem_schema_ab(adresse):
    assert not bauen.TextPruefung.adresse_erlaubt(adresse)
    p = bauen.TextPruefung()
    p.feed(f'<p><a href="{adresse}">Fahrplan</a></p>')
    assert p.fremd, adresse


@pytest.mark.parametrize("adresse", ["https://example.org/x", "http://example.org", "mailto:ida@example.org", "tel:+4930123",
                                     "medien/bild.jpg", "#E-01", "//example.org/x", "seite?a=b:c"])
def test_reisetext_laesst_uebliche_adressen_zu(adresse):
    assert bauen.TextPruefung.adresse_erlaubt(adresse)
    p = bauen.TextPruefung()
    p.feed(f'<p><a href="{adresse}">x</a></p>')
    assert not p.fremd


def test_reisetext_wird_gesaeubert_auch_wo_pythons_parser_nichts_sieht():
    """CDATA liest Pythons HTMLParser als Daten, der Browser als Kommentar bis zum ersten „>“: Die Prüfung allein sah das
    <img onerror> nicht. Gesäubert wird mit einem Parser, der wie ein Browser liest."""
    roh = '<p>Text</p>\n<![CDATA[><img src=x onerror=alert(document.domain)>]]>\n<p><a href="javascript:alert(1)">Link</a></p>'
    p = bauen.TextPruefung()
    p.feed('<![CDATA[><img src=x onerror=alert(document.domain)>]]>')
    assert not p.fremd                      # die Lücke der Prüfung, deshalb das Säubern
    h = bauen.text_saeubern(roh)
    assert "onerror" not in h and "javascript:" not in h and "<p>Text</p>" in h
    for boese in ("<script>alert(1)</script>", '<p onclick="x()">a</p>', '<iframe src="https://example.org"></iframe>',
                  '<svg onload=alert(1)>', '<p style="background:url(javascript:x)">a</p>', "<!-- x --><style>*{}</style>"):
        h = bauen.text_saeubern(boese)
        assert not re.search(r"<script|onclick|<iframe|<svg|onload|javascript:|<style|<!--", h), (boese, h)


def test_saeubern_laesst_stehen_was_markdown_erzeugt():
    h = ('<h2>Titel</h2><p>a <em>b</em> <strong>c</strong> <code>d</code><br>e</p><ul><li><a href="medien/x.jpg" title="t">Bild</a></li></ul>'
         '<table><thead><tr><th style="text-align: right;">x</th></tr></thead><tbody><tr><td>1</td></tr></tbody></table>'
         '<p><img src="medien/a.png" alt="A" title="B"></p><blockquote><p>z</p></blockquote><hr><pre><code>x</code></pre>')
    assert bauen.text_saeubern(h) == h.replace("text-align: right;", "text-align:right")     # nur die Schreibweise des Stils ändert sich


def test_daten_im_skript_koennen_das_skript_nicht_beenden():
    """„</script>“ beendete das Skript, „<!--<script>“ ließ den Browser das echte Ende übersehen (Seite leer)."""
    daten = {"name": "Hotel <!--<script> </script><script>alert(1)</script>", "z": "a b"}
    js = bauen.js_einbetten(json.dumps(daten, ensure_ascii=False))
    assert "<" not in js and " " not in js
    assert json.loads(js) == daten


def test_seite_traegt_schutzrichtlinie_mit_den_pruefsummen_ihrer_skripte(tmp_path):
    import base64
    import hashlib
    seite = "<html><head><title>x</title><script>eins()</script></head><body><script src=\"a.js\"></script><script>\nzwei()\n</script></body></html>"
    aus = bauen.skripte_festlegen(seite)
    m = re.search(r'<head>\n<meta http-equiv="Content-Security-Policy" content="([^"]+)">', aus)
    assert m, aus
    regel = m.group(1)
    for skript in ("eins()", "\nzwei()\n"):
        assert "'sha256-" + base64.b64encode(hashlib.sha256(skript.encode()).digest()).decode() + "'" in regel
    assert "script-src 'self'" in regel and "object-src 'none'" in regel and "base-uri 'none'" in regel
    assert "unsafe-inline" not in regel and "unsafe-eval" not in regel


def test_gebaute_seite_hat_die_richtlinie_und_kein_rohes_kleiner_zeichen_in_den_daten(tmp_path):
    bauen.bauen(ENGINE.parent / "beispiel" / "reisen" / "beispielreise", tmp_path / "beispielreise")
    seite = (tmp_path / "beispielreise" / "index.html").read_text(encoding="utf-8")
    assert seite.count('http-equiv="Content-Security-Policy"') == 1
    assert seite.index("Content-Security-Policy") < seite.index("<script")
    daten = re.search(r"\nconst D = (.*);\n", seite).group(1)
    assert len(daten) > 1000 and "<" not in daten and json.loads(daten)["reise"]


def test_vorlage_gibt_leaflet_keine_zeichenketten_aus_der_reise():
    """Leaflet setzt jede Zeichenkette als HTML ein (bindTooltip, divIcon html, Namensnennung, Ebenenwahl). Namen und Titel
    der Reise gehen deshalb als Textknoten (alsText) oder maskiert (maskiert) hinein."""
    v = (ENGINE / "vorlage.html").read_text(encoding="utf-8")
    assert "const alsText = " in v and "const maskiert = " in v
    for aufruf in re.findall(r"\.bindTooltip\(([^\n]{0,40})", v):
        assert aufruf.startswith("alsText("), aufruf
    for aufruf in re.findall(r"\.addAttribution\(([^\n]{0,40})", v):
        assert aufruf.startswith("maskiert("), aufruf
    assert not re.search(r"html: m\.name\b", v)
    assert "ebenen[maskiert(" in v and not re.search(r"ebenen\[`", v)


# ---------- Belege, Kalender, Push ----------

def test_zurueckgezogener_beleg_ist_auch_als_datei_nur_fuer_organisation_und_hochladende():
    b = {"sichtbar": "alle", "wer": "Karl", "zurueckgezogen": None}
    assert belege.darf_abrufen(b, None, "gast") and belege.darf_abrufen(b, "Lea", "mitwirkend")
    b["zurueckgezogen"] = "2026-11-12T10:00:00+00:00"
    assert not belege.darf_abrufen(b, None, "gast")           # mit dem Seitenlink allein
    assert not belege.darf_abrufen(b, "Lea", "mitwirkend")
    assert belege.darf_abrufen(b, "karl", "mitwirkend") and belege.darf_abrufen(b, "Ida", "organisator")
    assert not belege.darf_abrufen({"sichtbar": "beteiligte", "wer": "Karl"}, "Lea", "mitwirkend")


def test_abruf_einer_belegdatei_fragt_dieselbe_regel_wie_die_liste():
    quelle = (ENGINE / "rueckmeldungen.py").read_text(encoding="utf-8")
    assert "bl.darf_abrufen(b, name, rolle)" in quelle and "bl.darf_sehen(" not in quelle


@pytest.mark.parametrize("text", ["x\rATTACH:https://example.org/a", "x\rEND:VEVENT\rBEGIN:VEVENT", "a b", "a\x00b\x0bc", "a\r\nb"])
def test_kalender_laesst_kein_zeilenende_im_text_durch(text):
    aus = kalender._esc(text)
    assert not re.search(r"[\x00-\x1f\x7f\u0085  ]", aus), repr(aus)


def test_push_nur_an_push_dienste(monkeypatch):
    monkeypatch.delenv("FR_PUSH_DIENSTE", raising=False)
    for gut in ("https://fcm.googleapis.com/fcm/send/abc123456", "https://updates.push.services.mozilla.com/wpush/v2/abc",
                "https://web.push.apple.com/abo/eins", "https://db5p.notify.windows.com/w/?token=abc"):
        assert konten.push_endpunkt_erlaubt(gut), gut
    for boese in ("https://127.0.0.1/abo/eins", "https://example.org/abo/eins", "https://fcm.googleapis.com.example.org/abo/eins",
                  "https://evilfcm.googleapis.com/abo/eins", "https://user@fcm.googleapis.com/abo/eins",
                  "https://fcm.googleapis.com:8443/abo/eins", "http://fcm.googleapis.com/abo/eins",
                  "https://push.apple.com.example.org/abo/eins", None, 7):
        assert not konten.push_endpunkt_erlaubt(boese), boese
    with pytest.raises(konten.KontoFehler):
        konten.push_abo_speichern("K-0000000000000000", {"endpoint": "https://intern.example.org/abo/eins",
                                                         "keys": {"p256dh": "A" * 20, "auth": "B" * 20}})
    monkeypatch.setenv("FR_PUSH_DIENSTE", "push.example.org, .push.example.net")
    assert konten.push_endpunkt_erlaubt("https://push.example.org/abo/eins")
    assert konten.push_endpunkt_erlaubt("https://a.push.example.net/abo/eins")
    assert not konten.push_endpunkt_erlaubt("https://fcm.googleapis.com/fcm/send/abc123456")


def test_push_folgt_keiner_umleitung_und_sendet_nicht_an_fremde_adressen():
    quelle = (ENGINE / "push.py").read_text(encoding="utf-8")
    assert '"allow_redirects": False' in quelle and "requests_session=sitzung" in quelle
    assert "konten.push_endpunkt_erlaubt(abo[\"endpoint\"])" in quelle


# ---------- Muster ----------

def test_muster_fuer_ordner_und_kennungen_enden_am_ende():
    import reise
    import rueckmeldungen as rm
    import schreiben
    for muster in (rm.REISE_MUSTER, konten.REISE_MUSTER, schreiben.REISE_MUSTER, reise.PFAD_MUSTER, konten.PERSON_MUSTER,
                   belege.BID_MUSTER, belege.DID_MUSTER):
        gut = {"B": "B-12", "D": "D-12"}.get(muster.pattern[1], "beispielreise")
        assert muster.match(gut), muster.pattern
        assert not muster.match(gut + "\n"), muster.pattern


# ---------- Übernehmen aus einer anderen Reise ----------

def test_uebernehmen_aus_einer_reise_verlangt_die_mitgliedschaft_des_kontos(monkeypatch):
    """Der Personen-Schlüssel folgt aus dem Vornamen: „ida“ einer fremden Reise ist eine andere Person. Es zählt, ob das
    Konto dort Mitglied ist; die Antwort verrät nicht, ob es die Reise gibt."""
    import konnektor as kn
    fremd = {"reise": {"personen": [{"schluessel": "ida", "name": "Ida", "rolle": "organisator"}]}}
    hier = {"reise": {"personen": [{"schluessel": "ida", "name": "Ida", "rolle": "organisator"}]}, "route": {}}

    class Erreicht(Exception):
        pass

    def gesendet(*a, **k):
        raise Erreicht()
    monkeypatch.setattr(kn, "recht", lambda *a, **k: None)
    monkeypatch.setattr(kn, "schreibdienst", lambda: "http://127.0.0.1:9")
    monkeypatch.setattr(kn, "daten", lambda r: fremd if r == "fremde-reise" else None)
    monkeypatch.setattr(kn, "personen_der_reise", lambda r, d: d["reise"]["personen"])
    monkeypatch.setattr(kn, "schreib_anfrage", gesendet)
    wer, zugang = {"rolle": "organisator", "name": "Ida", "person": "ida"}, {"reise": "eigene", "person": "ida", "konto_id": "K-1"}
    monkeypatch.setattr(konten, "mitglied", lambda kid, reise: None)
    for werkzeug in ("packliste_uebernehmen", "arten_uebernehmen"):
        t, fehler = kn.ontologie_werkzeug("eigene", hier, wer, zugang, werkzeug, {"von_reise": "fremde-reise"})
        assert fehler
        t2, _ = kn.ontologie_werkzeug("eigene", hier, wer, zugang, werkzeug, {"von_reise": "gibt-es-nicht"})
        assert t.replace("fremde-reise", "X") == t2.replace("gibt-es-nicht", "X")      # dieselbe Antwort
    monkeypatch.setattr(konten, "mitglied", lambda kid, reise: "ida" if (kid, reise) == ("K-1", "fremde-reise") else None)
    with pytest.raises(Erreicht):
        kn.ontologie_werkzeug("eigene", hier, wer, zugang, "packliste_uebernehmen", {"von_reise": "fremde-reise"})
