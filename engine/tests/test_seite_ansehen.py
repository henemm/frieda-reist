"""Frieda sieht die Seite (#618): Das Werkzeug seite_ansehen (page_view) gibt ein Bild der veröffentlichten Seite an der Stelle
einer Kennung zurück, am Handy oder am Rechner, und sagt in Worten, wo sie steht (Reiter, Ansicht, Klappen). Den Ort bestimmt
die Seite selbst (engine/seitenbild.mjs steuert #<kennung> an). Erfundene Daten beider Beispielreisen."""
import base64
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bauen  # noqa: E402
import konnektor as kn  # noqa: E402
import schnittstelle  # noqa: E402
import stand  # noqa: E402
from conftest import meldet  # noqa: E402

ENGINE = Path(__file__).resolve().parent.parent
BEISPIELE = ENGINE.parent / "beispiel" / "reisen"
REISEN = {"beispielreise": ("ida", "A-01"), "stadtwochenende": ("lea", "U-01")}


def _playwright():
    from playwright_pfad import PLAYWRIGHT
    if not PLAYWRIGHT.exists() or not shutil.which("node"):
        pytest.skip("Playwright oder node fehlt")
    return PLAYWRIGHT


@pytest.fixture
def seiten(tmp_path, monkeypatch):
    """Beide Beispielreisen gebaut, Konnektor liest sie; Dienstordner leer (kein Reise-Stand)."""
    ordner = tmp_path / "seiten"
    for reise in REISEN:
        q = tmp_path / "quelle" / reise
        shutil.copytree(BEISPIELE / reise, q)
        bauen.bauen(q, ordner / reise)
    monkeypatch.setenv("KN_SEITEN", str(ordner))
    monkeypatch.setenv("FR_DIENST", str(tmp_path / "_dienst"))
    return ordner


def _bild_ok(t):
    assert isinstance(t, kn.MitBild), t
    (typ, b64), = t.bilder
    roh = base64.b64decode(b64)
    assert typ == "image/jpeg" and roh[:3] == b"\xff\xd8\xff" and len(roh) > 5000
    return t.text


# ---------- mit Browser: beide Beispielreisen ----------

@pytest.mark.parametrize("reise", sorted(REISEN))
def test_bild_und_ort_einer_kennung(seiten, monkeypatch, reise):
    monkeypatch.setenv("PLAYWRIGHT_MODUL", str(_playwright()))
    person, kennung = REISEN[reise]
    t, fehler = kn.werkzeug({"reise": reise, "person": person}, "seite_ansehen", {"id": kennung})
    assert fehler is False, t
    text = _bild_ok(t)
    assert meldet(text, "konnektor.seitenbild.kopf_handy") and meldet(text, "konnektor.seitenbild.ort")
    assert meldet(text, "konnektor.seitenbild.markiert") and meldet(text, "konnektor.seitenbild.live")
    assert "„–“" not in text   # Reiter und Ansicht hat die Seite genannt


def test_beispielreise_tag_und_rechner(seiten, monkeypatch):
    """A-01 wohnt am Tag 2 (Reiter Varianten); W-01 hat eine eigene Ansicht im Reiter Wissen; ohne id die Startseite."""
    monkeypatch.setenv("PLAYWRIGHT_MODUL", str(_playwright()))
    zugang = {"reise": "beispielreise", "person": "karl"}
    t, _ = kn.werkzeug(zugang, "seite_ansehen", {"id": "A-01"})
    assert "Tag 2" in t.text and "Varianten" in t.text
    t, fehler = kn.werkzeug(zugang, "seite_ansehen", {"id": "W-01", "geraet": "rechner"})
    assert fehler is False and meldet(t.text, "konnektor.seitenbild.kopf_rechner")
    assert meldet(t.text, "konnektor.seitenbild.eigene_ansicht") and "Wissen" in t.text
    t, fehler = kn.werkzeug(zugang, "seite_ansehen", {})
    assert fehler is False and not meldet(t.text, "konnektor.seitenbild.markiert")
    _bild_ok(t)


def test_ein_bild_sagt_dass_es_nur_ein_bildschirm_ist(seiten, monkeypatch):
    """Ohne ganze_ansicht zeigt das Bild einen Bildschirm; die Antwort sagt es und nennt den Weg zur ganzen Ansicht."""
    monkeypatch.setenv("PLAYWRIGHT_MODUL", str(_playwright()))
    t, _ = kn.werkzeug({"reise": "beispielreise", "person": "ida"}, "seite_ansehen", {"id": "A-01"})
    assert len(t.bilder) == 1 and meldet(t.text, "konnektor.seitenbild.ein_bildschirm")


@pytest.mark.parametrize("reise", sorted(REISEN))
def test_ganze_ansicht_in_teilen_mit_stelle_und_weiter(seiten, monkeypatch, reise):
    """ganze_ansicht: die ganze Ansicht von oben in Teilen von je einem Bildschirm (höchstens 4 je Aufruf); die Antwort nennt die
    Zahl der Teile, den Teil mit der Stelle und wie es weitergeht; ab_teil blättert."""
    monkeypatch.setenv("PLAYWRIGHT_MODUL", str(_playwright()))
    person, kennung = REISEN[reise]
    zugang = {"reise": reise, "person": person}
    t, fehler = kn.werkzeug(zugang, "seite_ansehen", {"id": kennung, "ganze_ansicht": True})
    assert fehler is False, t
    teile = int(re.search(r"Teil 1 bis \d+ von (\d+)", t.text).group(1))
    assert 1 <= len(t.bilder) <= 4 and len(t.bilder) == min(4, teile) and meldet(t.text, "konnektor.seitenbild.teile")
    assert meldet(t.text, "konnektor.seitenbild.stelle_teil") and not meldet(t.text, "konnektor.seitenbild.ein_bildschirm")
    for _, b64 in t.bilder:
        assert base64.b64decode(b64)[:3] == b"\xff\xd8\xff"
    assert meldet(t.text, "konnektor.seitenbild.weiter") == (teile > 4)
    t, fehler = kn.werkzeug(zugang, "seite_ansehen", {"id": kennung, "ganze_ansicht": True, "ab_teil": teile})
    assert fehler is False and len(t.bilder) == 1 and f"Teil {teile} bis {teile} von {teile}" in t.text
    t, fehler = kn.werkzeug(zugang, "seite_ansehen", {"id": kennung, "ganze_ansicht": True, "ab_teil": teile + 1})
    assert fehler and meldet(t, "konnektor.seitenbild.ab_teil_zu_gross")


def test_bild_nennt_stand_und_neueren_gesicherten(seiten, monkeypatch):
    monkeypatch.setenv("PLAYWRIGHT_MODUL", str(_playwright()))
    d = json.loads((seiten / "beispielreise" / "daten.json").read_text(encoding="utf-8"))
    d["reise_stand"] = {**(d.get("reise_stand") or {}), "nummer": 5}
    (seiten / "beispielreise" / "daten.json").write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    stand.gesichert_schreiben("beispielreise", 7)
    t, _ = kn.werkzeug({"reise": "beispielreise", "person": "ida"}, "seite_ansehen", {"id": "U-01"})
    assert meldet(t.text, "konnektor.seitenbild.stand") and meldet(t.text, "konnektor.zeige.seite_zurueck")


def test_klappen_teil_und_kuerzung_kommen_aus_der_seite(tmp_path):
    """Das Skript merkt sich, was die Seite beim Ansteuern öffnen musste (zugeklappte Klappen, ausgeblendeter Teil, gekürzter
    Text). Kleine Testseite mit derselben Schnittstelle wie vorlage.html (route über hashchange, zumZiel, #nav a.on)."""
    pw = _playwright()
    (tmp_path / "s").mkdir()
    (tmp_path / "s" / "index.html").write_text("""<!DOCTYPE html><html><body>
<nav id="nav"><a class="on" href="#plan"><span>Reise</span></a></nav>
<main id="main"><h2>Tag 9 · Beispielwert</h2>
<details><summary>Einzelheiten</summary><details><summary>Aus der Planung</summary><p id="X-01">Beispiel</p></details></details>
<div class="reiter"><button role="tab" data-teil="b">Unterkunft</button><div role="tabpanel" data-teil="b" hidden>
<div class="weg-text kurz"><p id="X-02">Beispiel</p></div></div></div></main>
<script>
function zumZiel(id) { const e = document.getElementById(id); for (let p = e; p; p = p.parentElement) if (p.tagName === "DETAILS") p.open = true;
  const t = e.closest("[role=tabpanel]"); if (t) t.hidden = false; e.scrollIntoView(); }
window.addEventListener("hashchange", () => zumZiel(decodeURIComponent(location.hash.slice(1))));
</script></body></html>""", encoding="utf-8")
    ort = {}
    for k in ("X-01", "X-02"):
        aus = subprocess.run(["node", str(ENGINE / "seitenbild.mjs"), str(pw), str(tmp_path / "s"), k, "handy"],
                             capture_output=True, text=True, timeout=120)
        assert aus.returncode == 0, aus.stdout[-500:] + aus.stderr[-1500:]
        ort[k] = json.loads(aus.stdout.strip().splitlines()[-1])["ort"]
    assert ort["X-01"]["klappen"] == ["Einzelheiten", "Aus der Planung"] and ort["X-01"]["markiert"]
    assert ort["X-01"]["reiter"] == "Reise" and ort["X-01"]["ansicht"] == "Tag 9 · Beispielwert"
    assert ort["X-02"]["teil"] == "Unterkunft" and ort["X-02"]["gekuerzt"] and not ort["X-02"]["klappen"]
    kn.texte.aufruf_sprache("de")
    text = kn.seitenbild_ort(ort["X-01"], "X-01")
    assert meldet(text, "konnektor.seitenbild.klappe") and "Aus der Planung" in text


def test_skript_laedt_nichts_von_aussen(tmp_path):
    """Nur der eigene kleine Server: Eine Seite, die eine fremde Adresse oder /api/ lädt, bekommt nichts (keine geheimen
    Links, keine Live-Daten, nichts nach außen)."""
    pw = _playwright()
    (tmp_path / "s").mkdir()
    (tmp_path / "s" / "index.html").write_text("""<!DOCTYPE html><html><body><main id="main"><h2 id="k">-</h2></main><script>
Promise.all([fetch("https://example.invalid/x").then(() => "durch", () => "gesperrt"),
             fetch("/api/ich").then(r => r.ok ? "durch" : "fehlt", () => "gesperrt")])
  .then(([a, b]) => { document.getElementById("k").textContent = a + "," + b; });
</script></body></html>""", encoding="utf-8")
    aus = subprocess.run(["node", str(ENGINE / "seitenbild.mjs"), str(pw), str(tmp_path / "s"), "-", "rechner"],
                         capture_output=True, text=True, timeout=120)
    assert aus.returncode == 0, aus.stderr[-1500:]
    assert json.loads(aus.stdout.strip().splitlines()[-1])["ort"]["ansicht"] == "gesperrt,gesperrt"


# ---------- ohne Browser: Ablehnungen und Betrieb ----------

def test_ablehnungen(seiten, monkeypatch, tmp_path):
    zugang = {"reise": "beispielreise", "person": "ida"}
    t, fehler = kn.werkzeug(zugang, "seite_ansehen", {"id": "U-99"})
    assert fehler and meldet(t, "konnektor.zeige.2")
    t, fehler = kn.werkzeug(zugang, "seite_ansehen", {"id": "U-01\"><script>"})
    assert fehler and meldet(t, "konnektor.zeige.2")
    t, fehler = kn.werkzeug(zugang, "seite_ansehen", {"id": "U-01", "geraet": "tablet"})
    assert fehler and meldet(t, "konnektor.seitenbild.geraet")
    t, fehler = kn.werkzeug(zugang, "seite_ansehen", {"id": "U-01", "ganze_ansicht": True, "ab_teil": "zwei"})
    assert fehler and meldet(t, "konnektor.seitenbild.ab_teil")
    monkeypatch.setenv("PLAYWRIGHT_MODUL", str(tmp_path / "gibt-es-nicht.mjs"))
    t, fehler = kn.werkzeug(zugang, "seite_ansehen", {"id": "U-01"})
    assert fehler and meldet(t, "konnektor.seitenbild.kein_browser")
    (seiten / "beispielreise" / "index.html").unlink()
    t, fehler = kn.werkzeug(zugang, "seite_ansehen", {"id": "U-01"})
    assert fehler and meldet(t, "konnektor.seitenbild.keine_seite")


def test_hoechstens_ein_bild_zugleich(seiten, monkeypatch, tmp_path):
    modul = tmp_path / "pw.mjs"
    modul.write_text("")
    monkeypatch.setenv("PLAYWRIGHT_MODUL", str(modul))
    monkeypatch.setattr(kn, "SEITENBILD_WARTEN", 0.1)
    assert kn.SEITENBILD_SPERRE.acquire(timeout=5)
    try:
        t, fehler = kn.werkzeug({"reise": "beispielreise", "person": "ida"}, "seite_ansehen", {"id": "U-01"})
    finally:
        kn.SEITENBILD_SPERRE.release()
    assert fehler and meldet(t, "konnektor.seitenbild.besetzt")


def test_fehlender_browser_kommt_als_grund_zurueck(tmp_path):
    """Startet der Browser nicht (hier: Browser-Ordner leer), antwortet das Skript trotzdem mit einer JSON-Zeile und dem Grund."""
    pw = _playwright()
    (tmp_path / "s").mkdir()
    (tmp_path / "s" / "index.html").write_text("<!DOCTYPE html><main id=main><p>x</p></main>", encoding="utf-8")
    (tmp_path / "leer").mkdir()
    aus = subprocess.run(["node", str(ENGINE / "seitenbild.mjs"), str(pw), str(tmp_path / "s"), "-", "handy"], capture_output=True,
                         text=True, timeout=120, env={**os.environ, "PLAYWRIGHT_BROWSERS_PATH": str(tmp_path / "leer")})
    erg = json.loads(aus.stdout.strip().splitlines()[-1])
    assert aus.returncode == 1 and "bild" not in erg and erg["fehler"] and "\n" not in erg["fehler"][0]


def test_gescheitertes_bild_sagt_den_grund(seiten, monkeypatch, tmp_path):
    modul = tmp_path / "pw.mjs"
    modul.write_text("")
    monkeypatch.setenv("PLAYWRIGHT_MODUL", str(modul))
    monkeypatch.setattr(kn.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 1, '{"fehler": ["Beispielfehler"]}\n', ""))
    t, fehler = kn.werkzeug({"reise": "beispielreise", "person": "ida"}, "seite_ansehen", {"id": "U-01"})
    assert fehler and meldet(t, "konnektor.seitenbild.gescheitert") and "Beispielfehler" in t

    def zu_lange(*a, **k):
        raise subprocess.TimeoutExpired(a, 1)
    monkeypatch.setattr(kn.subprocess, "run", zu_lange)
    t, fehler = kn.werkzeug({"reise": "beispielreise", "person": "ida"}, "seite_ansehen", {"id": "U-01"})
    assert fehler and meldet(t, "konnektor.seitenbild.zu_lange")
    assert kn.SEITENBILD_SPERRE.acquire(timeout=0)   # nach Fehlern wieder frei
    kn.SEITENBILD_SPERRE.release()


def test_umgebung_des_browsers(tmp_path, monkeypatch):
    """Der Konnektor läuft mit ProtectHome: eigener HOME, die Browser der Instanz unter <FR_DIENST>/playwright/browser."""
    monkeypatch.setenv("FR_DIENST", str(tmp_path / "dienst"))
    monkeypatch.delenv("PLAYWRIGHT_BROWSERS_PATH", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path / "alt"))
    umg = kn.seitenbild_umgebung(str(tmp_path / "heim"))
    assert umg["HOME"] == str(tmp_path / "heim") and "PLAYWRIGHT_BROWSERS_PATH" not in umg
    # Browser im Zwischenspeicher des bisherigen Heimatverzeichnisses (Vorgabe von Playwright, so in CI): der neue HOME verdeckt
    # ihn nicht
    (tmp_path / "alt" / ".cache" / "ms-playwright").mkdir(parents=True)
    assert kn.seitenbild_umgebung("/x")["PLAYWRIGHT_BROWSERS_PATH"] == str(tmp_path / "alt" / ".cache" / "ms-playwright")
    (tmp_path / "dienst" / "playwright" / "browser").mkdir(parents=True)
    (tmp_path / "dienst" / "playwright" / "node_modules" / "playwright").mkdir(parents=True)
    (tmp_path / "dienst" / "playwright" / "node_modules" / "playwright" / "index.mjs").write_text("")
    assert kn.seitenbild_umgebung("/x")["PLAYWRIGHT_BROWSERS_PATH"] == str(tmp_path / "dienst" / "playwright" / "browser")
    monkeypatch.delenv("PLAYWRIGHT_MODUL", raising=False)
    assert kn.playwright_modul() == tmp_path / "dienst" / "playwright" / "node_modules" / "playwright" / "index.mjs"


def test_deploy_kopiert_das_skript():
    deploy = (ENGINE.parent / "betrieb" / "deploy.sh").read_text(encoding="utf-8")
    zeile = next(z for z in deploy.splitlines() if z.startswith("KN_MODULE="))
    assert kn.SEITENBILD.name in zeile.split()


# ---------- Schnittstelle, Anleitung, Veröffentlichung ----------

def test_werkzeug_fuer_alle_rollen_englisch_page_view(seiten):
    for reise, (person, _) in REISEN.items():
        namen = {w["name"] for w in kn.werkzeuge_fuer({"reise": reise, "person": person})}
        assert "seite_ansehen" in namen
    w = next(w for w in schnittstelle.aussen(kn.lokalisiert(kn.WERKZEUGE, "en")) if w["name"] == "page_view")
    assert w["annotations"]["readOnlyHint"] is True
    assert w["inputSchema"]["properties"]["device"]["enum"] == ["phone", "desktop"]
    assert schnittstelle.parameter_zu_intern("seite_ansehen")["device"] == "geraet"
    assert {"whole_view", "from_part"} <= set(w["inputSchema"]["properties"])
    assert "ganze_ansicht" not in w["description"] and "whole_view" in w["description"] and "from_part" in w["description"]


@pytest.mark.parametrize("sprache", ["de", "en"])
def test_anleitung_und_veroeffentlichung_nennen_das_werkzeug(seiten, monkeypatch, sprache):
    konto = {"id": "K-1", "name": "Ida", "email": "ida@example.invalid", "sprache": sprache}
    monkeypatch.setattr(kn, "reisen_des_kontos", lambda k: [("beispielreise", "ida", kn.daten("beispielreise"))])
    assert meldet(kn.anleitung_frieda(konto, sprache), "konnektor.anleitung.seite_ansehen", sprache)
    z = {"zustand": "veroeffentlicht", "gesichert": {"nummer": 3}, "veroeffentlicht": {"nummer": 3}, "seit": None}
    monkeypatch.setattr(kn.reisestand, "enthalten", lambda z_, n: True)
    assert meldet(kn.veroeffentlichung_text("beispielreise", 3, z), "konnektor.veroeffentlichung.ansehen")
    monkeypatch.setattr(kn.reisestand, "enthalten", lambda z_, n: False)
    assert not meldet(kn.veroeffentlichung_text("beispielreise", 3, z), "konnektor.veroeffentlichung.ansehen")
