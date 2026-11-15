"""Profile je Person (#12, Paket F, Meilenstein M6). Spec: docs/specs/konnektor/profile-12.md (AC-1 bis AC-13).

Ein reiseübergreifendes Profil je Konto in konten.db: Einträge mit Bereich (freier Text), Text, Herkunft (Pflicht) und Datum
(setzt Frieda). Geschrieben wird nur über den AI-Client und nur Bestätigtes; die Person sieht, ändert und löscht ihr Profil
auf Mein Konto. Niemand sonst sieht es (Art. 9 DSGVO).

Nur erfundene Daten: beispielreise (Ida Organisatorin, Karl mitwirkend), stadtwochenende (Tom Organisator, Lea mitwirkend).

Schnittstelle, die diese Tests festlegen (Entscheidung des Tech Leads in Phase 5):
  konten.profil_liste(kid) -> [{"id": "PR-<n>", "bereich", "text", "herkunft", "datum"}]   nach Nummer aufsteigend
  konten.profil_setzen(kid, bereich, text, herkunft, id=None) -> Eintrag   neu oder Ändern eines eigenen Eintrags
  konten.profil_aendern(kid, id, text) -> Eintrag                           nur der Text (Mein Konto), Datum neu
  konten.profil_entfernen(kid, id)                                          echtes Löschen
  Fehler als KontoFehler: konto.fehler.profil_leer, .profil_zu_lang, .profil_voll, .profil_unbekannt
  instanz.grenze_profil_eintraege() (FR_GRENZE_PROFIL_EINTRAEGE), grenze_profil_bereich() (FR_GRENZE_PROFIL_BEREICH),
  grenze_profil_text() (FR_GRENZE_PROFIL_TEXT)
  Konnektor intern mein_profil, profil_eintrag_setzen, profil_eintrag_entfernen (außen my_profile, profile_entry_set,
  profile_entry_remove); Parameter bereich (area), text, herkunft (origin), bestaetigt (confirmed), id
  Mein Konto: POST aktion=profil_aendern (id, text), aktion=profil_loeschen (id)
"""
import json
import re
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

import pytest

ENGINE = Path(__file__).resolve().parents[1]
WURZEL = ENGINE.parent
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import anmeldung  # noqa: E402
import instanz  # noqa: E402
import konnektor as kn  # noqa: E402
import konten  # noqa: E402
import reise as reise_modul  # noqa: E402
import schnittstelle  # noqa: E402
import texte  # noqa: E402
from conftest import meldet  # noqa: E402
from test_anmeldung import abruf, anmelden, welt  # noqa: E402,F401  (welt: Fixture)
from test_trennung import zwei, IDA, KARL, TOM  # noqa: E402,F401  (zwei: Fixture)

LEA = "lea@beispiel.invalid"
MARKE = "Zwiebelallergie-7f3q"           # Suchmarke: darf nur im Profil der Person und in ihrem Export stehen
WERKZEUGE = {"mein_profil": "my_profile", "profil_eintrag_setzen": "profile_entry_set",
             "profil_eintrag_entfernen": "profile_entry_remove"}


def alle(u):
    """Karl und Lea zusätzlich zu Ida und Tom anmelden. -> (ida, karl, tom, lea) als Konten."""
    anmelden(u, KARL)
    konten.einladen("stadtwochenende", "lea", LEA, "mitwirkend", "Lea", "Tom")
    anmelden(u, LEA)
    return (konten.konto_per_email(IDA), konten.konto_per_email(KARL), konten.konto_per_email(TOM),
            konten.konto_per_email(LEA))


def setzen(k, bereich="Essen", text="Isst kein Fleisch", herkunft="Gespräch in der Claude-App", **kw):
    return konten.profil_setzen(k["id"], bereich, text, herkunft, **kw)


def nr(eintrag):
    return int(re.fullmatch(r"PR-(\d+)", eintrag["id"]).group(1))


def werkzeug(k, name, **args):
    return kn.frieda_werkzeug(konten.konto(k["id"]), name, args)


def db_ohne_profil():
    """Alle Werte aller Tabellen der Kontendatenbank außer profil als ein Text."""
    teile = []
    with closing(konten.db()) as v:
        for (t,) in v.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"):
            if t != "profil":
                teile += [str(x) for z in v.execute(f"SELECT * FROM {t}") for x in tuple(z)]
    return "\n".join(teile)


def ordner_text(*ordner):
    teile = []
    for o in ordner:
        for f in sorted(Path(o).rglob("*")):
            if f.is_file():
                teile.append(f.read_bytes().decode("utf-8", "replace"))
    return "\n".join(teile)


# ---------- Konten-Funktionen (AC-1, AC-8) ----------

def test_eintrag_bekommt_nummer_herkunft_und_datum(zwei):
    """Test 1"""
    u = zwei()
    e1 = setzen(u.a)
    assert e1["id"] == "PR-1" and e1["herkunft"] == "Gespräch in der Claude-App"
    assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", e1["datum"]), e1
    e2 = setzen(u.a, "Tempo", "Lieber kurze Etappen")
    assert nr(e2) == nr(e1) + 1
    assert [e["id"] for e in konten.profil_liste(u.a["id"])] == [e1["id"], e2["id"]]
    assert {k for k in konten.profil_liste(u.a["id"])[0]} >= {"id", "bereich", "text", "herkunft", "datum"}


def test_nummer_wird_nie_wiederverwendet(zwei):
    """Test 2"""
    u = zwei()
    setzen(u.a)
    e2 = setzen(u.a, "Tempo", "gemütlich")
    konten.profil_entfernen(u.a["id"], e2["id"])
    e3 = setzen(u.a, "Unterkunft", "Hütten")
    assert nr(e3) == nr(e2) + 1
    assert [e["id"] for e in konten.profil_liste(u.a["id"])] == ["PR-1", e3["id"]]


@pytest.mark.parametrize("sprache", ["de", "en"])
def test_pruefungen_ohne_speichern(zwei, monkeypatch, sprache):
    """Test 3: leere Pflichtfelder, zu lange Werte, Obergrenze je Konto; Fehler mit Text je Sprache, nichts gespeichert."""
    u = zwei()
    falsch = [("", "x", "Gespräch"), ("  ", "x", "Gespräch"), ("Essen", " ", "Gespräch"), ("Essen", "x", ""),
              ("Essen", "x", "   "), ("E" * (instanz.grenze_profil_bereich() + 1), "x", "Gespräch"),
              ("Essen", "x" * (instanz.grenze_profil_text() + 1), "Gespräch")]
    for bereich, text, herkunft in falsch:
        with pytest.raises(konten.KontoFehler) as f:
            konten.profil_setzen(u.a["id"], bereich, text, herkunft)
        assert f.value.schluessel in ("konto.fehler.profil_leer", "konto.fehler.profil_zu_lang"), (bereich, text, herkunft)
        assert f.value.text(sprache) != f.value.schluessel
    assert konten.profil_liste(u.a["id"]) == []
    monkeypatch.setenv("FR_GRENZE_PROFIL_EINTRAEGE", "2")
    setzen(u.a)
    e = setzen(u.a, "Tempo", "gemütlich")
    with pytest.raises(konten.KontoFehler) as f:
        setzen(u.a, "Budget", "eher sparsam")
    assert f.value.schluessel == "konto.fehler.profil_voll" and meldet(f.value.text(sprache), "konto.fehler.profil_voll", sprache)
    assert len(konten.profil_liste(u.a["id"])) == 2
    setzen(u.a, "Tempo", "zügig", id=e["id"])        # Ändern eines vorhandenen Eintrags geht auch an der Grenze
    assert konten.profil_liste(u.a["id"])[1]["text"] == "zügig"


def test_grenzen_aus_der_instanz(monkeypatch):
    for f in (instanz.grenze_profil_eintraege, instanz.grenze_profil_bereich, instanz.grenze_profil_text):
        assert isinstance(f(), int) and f() >= 1
    monkeypatch.setenv("FR_GRENZE_PROFIL_EINTRAEGE", "7")
    monkeypatch.setenv("FR_GRENZE_PROFIL_BEREICH", "20")
    monkeypatch.setenv("FR_GRENZE_PROFIL_TEXT", "90")
    assert (instanz.grenze_profil_eintraege(), instanz.grenze_profil_bereich(), instanz.grenze_profil_text()) == (7, 20, 90)
    monkeypatch.setenv("FR_GRENZE_PROFIL_EINTRAEGE", "abc")
    assert instanz.grenze_profil_eintraege() >= 1


def test_fremder_eintrag_nicht_gefunden(zwei):
    """Test 4"""
    u = zwei()
    ida, karl, _, _ = alle(u)
    e = setzen(ida)
    for tun in (lambda: konten.profil_setzen(karl["id"], "Essen", "anders", "Gespräch", id=e["id"]),
                lambda: konten.profil_aendern(karl["id"], e["id"], "anders"),
                lambda: konten.profil_entfernen(karl["id"], e["id"])):
        with pytest.raises(konten.KontoFehler) as f:
            tun()
        assert f.value.schluessel == "konto.fehler.profil_unbekannt"
    assert konten.profil_liste(ida["id"]) == [e]
    assert konten.profil_liste(karl["id"]) == []


def test_profil_geht_mit_dem_konto(zwei):
    """Test 5"""
    u = zwei()
    ida, karl, _, _ = alle(u)
    setzen(karl, text=MARKE)
    e = setzen(ida)
    konten.loeschen(karl["id"])
    with closing(konten.db()) as v:
        assert v.execute("SELECT COUNT(*) FROM profil WHERE konto = ?", (karl["id"],)).fetchone()[0] == 0
        assert MARKE not in json.dumps([tuple(z) for z in v.execute("SELECT * FROM profil")], ensure_ascii=False)
    assert konten.profil_liste(ida["id"]) == [e]
    assert "profil" in __import__("inspect").getsource(konten.loeschen)


def test_zusammenfuehren_nimmt_das_profil_mit(zwei, monkeypatch):
    """Test 6: Kennungen bleiben, keine Kollision, die Obergrenze gilt dabei nicht."""
    u = zwei()
    ida, karl, _, _ = alle(u)
    a = [setzen(karl, "Essen", "vegetarisch"), setzen(karl, "Tempo", "gemütlich")]
    b = [setzen(ida, "Unterkunft", "Hütten")]
    monkeypatch.setenv("FR_GRENZE_PROFIL_EINTRAEGE", "2")
    konten.zusammenfuehren(karl["id"], ida["id"])
    liste = konten.profil_liste(ida["id"])
    assert sorted(e["id"] for e in liste) == sorted(e["id"] for e in a + b)
    assert len({e["id"] for e in liste}) == 3
    assert {e["text"] for e in liste} == {"vegetarisch", "gemütlich", "Hütten"}


def test_alte_datenbank_bekommt_die_tabelle(welt):
    """Test 7: eine Datenbank von vor der Einführung (ohne Tabelle profil) behält ihre Daten."""
    welt()
    with closing(konten.db()) as v, v:
        v.execute("DROP TABLE IF EXISTS profil")
        v.execute("INSERT INTO konten (id, email, name, angelegt) VALUES ('k-alt', 'alt@beispiel.invalid', 'Alt', '2026-01-01')")
    with closing(sqlite3.connect(konten.pfad())) as v:
        assert not v.execute("SELECT name FROM sqlite_master WHERE name = 'profil'").fetchone()
    with closing(konten.db()) as v:
        assert v.execute("SELECT name FROM sqlite_master WHERE name = 'profil'").fetchone()
    assert konten.konto("k-alt")["name"] == "Alt"
    assert konten.profil_liste("k-alt") == []


# ---------- Konnektor-Werkzeuge (AC-2, AC-3, AC-4) ----------

def test_lesen_deutsch_und_englisch_nur_eigenes(zwei):
    """Test 8"""
    u = zwei()
    ida, karl, _, _ = alle(u)
    setzen(ida, text=MARKE)
    setzen(karl, text="Karl mag Bergkäse")
    text, fehler = werkzeug(ida, "mein_profil")
    assert not fehler and MARKE in text and "PR-1" in text and "Bergkäse" not in text, text
    name, args = kn.aufruf_intern(kn.frieda_werkzeuge(ida), "my_profile", {})
    assert name == "mein_profil"
    assert kn.frieda_werkzeug(ida, name, args)[0] == text
    text, fehler = werkzeug(karl, "mein_profil")
    assert not fehler and MARKE not in text and "Bergkäse" in text, text


def test_setzen_nur_bestaetigt_und_mit_herkunft(zwei):
    """Test 9"""
    u = zwei()
    for args in ({"bereich": "Essen", "text": "vegetarisch", "herkunft": "Gespräch"},
                 {"bereich": "Essen", "text": "vegetarisch", "herkunft": "Gespräch", "bestaetigt": False},
                 {"bereich": "Essen", "text": "vegetarisch", "herkunft": "Gespräch", "bestaetigt": "ja"},
                 {"bereich": "Essen", "text": "vegetarisch", "bestaetigt": True},
                 {"bereich": "Essen", "text": "vegetarisch", "herkunft": " ", "bestaetigt": True}):
        text, fehler = werkzeug(u.a, "profil_eintrag_setzen", **args)
        assert fehler, (args, text)
    assert meldet(werkzeug(u.a, "profil_eintrag_setzen", bereich="Essen", text="x", herkunft="Gespräch")[0],
                  "konnektor.profil.nicht_bestaetigt")
    assert konten.profil_liste(u.a["id"]) == []
    text, fehler = werkzeug(u.a, "profil_eintrag_setzen", bereich="Essen", text="vegetarisch", herkunft="Gespräch",
                            bestaetigt=True, datum="1999-01-01")
    assert not fehler and "PR-1" in text, text
    e = konten.profil_liste(u.a["id"])[0]
    assert e["text"] == "vegetarisch" and not e["datum"].startswith("1999"), e
    # Ändern über id: derselbe Eintrag, kein neuer
    text, fehler = werkzeug(u.a, "profil_eintrag_setzen", id="PR-1", bereich="Essen", text="vegan", herkunft="Gespräch",
                            bestaetigt=True)
    assert not fehler and [x["text"] for x in konten.profil_liste(u.a["id"])] == ["vegan"], text
    # außen englisch: confirmed, origin, area
    name, args = kn.aufruf_intern(kn.frieda_werkzeuge(u.a), "profile_entry_set",
                                  {"area": "Tempo", "text": "gemütlich", "origin": "Gespräch", "confirmed": True})
    assert name == "profil_eintrag_setzen" and args.get("bestaetigt") is True and args.get("herkunft") == "Gespräch"
    text, fehler = kn.frieda_werkzeug(konten.konto(u.a["id"]), name, args)
    assert not fehler and len(konten.profil_liste(u.a["id"])) == 2, text


def test_schreibgrenze_setzen_ja_entfernen_nie(zwei, monkeypatch):
    """Test 10"""
    u = zwei()
    monkeypatch.setenv("FR_GRENZE_SCHREIBEN", "2")
    text, fehler = werkzeug(u.a, "profil_eintrag_setzen", bereich="Essen", text="vegetarisch", herkunft="Gespräch",
                            bestaetigt=True)
    assert not fehler, text
    with closing(konten.db()) as v:
        assert v.execute("SELECT COUNT(*) FROM schreibvorgaenge WHERE konto = ?", (u.a["id"],)).fetchone()[0] == 1
    konten.schreiben_vormerken(u.a)
    text, fehler = werkzeug(u.a, "profil_eintrag_setzen", bereich="Tempo", text="gemütlich", herkunft="Gespräch",
                            bestaetigt=True)
    assert fehler and meldet(text, "konnektor.grenze.schreiben"), text
    assert len(konten.profil_liste(u.a["id"])) == 1
    text, fehler = werkzeug(u.a, "profil_eintrag_entfernen", id="PR-1")
    assert not fehler, text
    assert konten.profil_liste(u.a["id"]) == []
    with closing(konten.db()) as v:
        assert v.execute("SELECT COUNT(*) FROM schreibvorgaenge WHERE konto = ?", (u.a["id"],)).fetchone()[0] == 2
    text, fehler = werkzeug(u.a, "mein_profil")
    assert not fehler, text


@pytest.mark.parametrize("sprache", ["de", "en"])
def test_werkzeugliste(zwei, sprache):
    """Test 11: drei Konto-Werkzeuge ohne reise, englischer Name, deutscher Alias, Beschreibung in beiden Sprachen."""
    u = zwei()
    konten.sprache_setzen(u.a["id"], sprache)
    k = konten.konto(u.a["id"])
    intern = {w["name"]: w for w in kn.frieda_werkzeuge(k)}
    for name in WERKZEUGE:
        assert name in intern, name
        assert "reise" not in intern[name]["inputSchema"].get("properties", {}), name
    assert {"bereich", "text", "herkunft", "bestaetigt", "id"} <= set(intern["profil_eintrag_setzen"]["inputSchema"]["properties"])
    assert {"bereich", "text", "herkunft", "bestaetigt"} <= set(intern["profil_eintrag_setzen"]["inputSchema"].get("required", []))
    assert intern["profil_eintrag_entfernen"]["inputSchema"].get("required") == ["id"]
    aussen = {w["name"]: w for w in schnittstelle.aussen(kn.lokalisiert(kn.frieda_werkzeuge(k), sprache))}
    for name, englisch in WERKZEUGE.items():
        assert schnittstelle.NAMEN[englisch] == name and englisch in aussen
        assert aussen[englisch]["description"] and not aussen[englisch]["description"].startswith("@")
        assert f"konnektor.werkzeug.{name}" in texte.sprache(sprache).TEXTE
    eig = aussen["profile_entry_set"]["inputSchema"]["properties"]
    assert {"area", "text", "origin", "confirmed", "id"} <= set(eig), eig
    assert "profile" not in aussen, "Werkzeugname darf nicht mit dem Baustein profile verwechselt werden"


def test_unbekannte_nummer_verraet_nichts(zwei):
    """Test 12"""
    u = zwei()
    ida, karl, _, _ = alle(u)
    e = setzen(ida, text=MARKE)
    fremd, _ = werkzeug(karl, "profil_eintrag_entfernen", id=e["id"])
    leer, _ = werkzeug(karl, "profil_eintrag_entfernen", id="PR-999")
    assert meldet(fremd, "konto.fehler.profil_unbekannt") and fremd == leer.replace("PR-999", e["id"])
    text, fehler = werkzeug(karl, "profil_eintrag_setzen", id=e["id"], bereich="Essen", text="x", herkunft="Gespräch",
                            bestaetigt=True)
    assert fehler and MARKE not in text and "Ida" not in text and IDA not in text
    assert konten.profil_liste(ida["id"]) == [e]


# ---------- Anleitung (AC-5, AC-6) ----------

@pytest.mark.parametrize("sprache", ["de", "en"])
def test_anleitung_frieda_nur_bestaetigtes(zwei, sprache):
    """Test 13"""
    u = zwei()
    text = kn.anleitung_frieda(konten.konto(u.a["id"]), sprache)
    assert meldet(text, "konnektor.anleitung.frieda.profil", sprache), text[-2000:]
    satz = texte.t(sprache, "konnektor.anleitung.frieda.profil")
    assert re.search(r"\b(etwa|zum Beispiel|such as|for example|e\.g\.)", satz), satz   # Bereiche nur als Beispiele


@pytest.mark.parametrize("bausteine,erwartet", [
    (None, "konnektor.anleitung.profil_nutzen"),
    (["plan", "profile"], "konnektor.anleitung.profil_nutzen"),
    (["plan"], "konnektor.anleitung.profil_nicht_nutzen"),
])
def test_anleitung_je_reise_nach_baustein(zwei, bausteine, erwartet):
    """Test 14: an oder ohne bausteine: nutzen und an Wahlstellen als Grund nennen; aus: nicht nutzen. Beide Reisetypen."""
    u = zwei(**({"bausteine": bausteine, "stadt_bausteine": bausteine} if bausteine else {}))
    for k, reise in ((u.a, "beispielreise"), (u.b, "stadtwochenende")):
        d = kn.daten(reise)
        schl = konten.mitglied(k["id"], reise)
        schl = schl["schluessel"] if isinstance(schl, dict) else schl
        text = kn.anleitung({"reise": reise, "person": schl, "konto_id": k["id"], "sprache": "de"}, d)
        anders = ({"konnektor.anleitung.profil_nutzen", "konnektor.anleitung.profil_nicht_nutzen"} - {erwartet}).pop()
        assert meldet(text, erwartet), (reise, text[-1500:])
        assert not meldet(text, anders), reise
    nutzen = texte.t("de", "konnektor.anleitung.profil_nutzen")
    assert "Grund" in nutzen and "Wahlstelle" in nutzen, nutzen


def test_baustein_profile_ohne_hinweis_noch_nicht_gebaut():
    """Test 15"""
    assert reise_modul.NOCH_NICHT_GEBAUT == {}
    assert "profile" in reise_modul.BAUSTEINE


# ---------- Mein Konto (AC-7) ----------

@pytest.mark.parametrize("sprache", ["de", "en"])
def test_karte_mein_profil_nur_eigene(zwei, sprache):
    """Test 16"""
    u = zwei()
    ida, karl, _, _ = alle(u)
    karl_keks, _ = anmelden(u, KARL)
    konten.sprache_setzen(ida["id"], sprache)
    konten.sprache_setzen(karl["id"], sprache)
    setzen(ida, "Essen", MARKE, "Gespräch in der Claude-App")
    s, _, t = abruf(f"{u.kurl}/konto", cookie=u.a_keks)
    assert s == 200 and meldet(t, "konto.profil.titel", sprache) and MARKE in t and "PR-1" in t, t[-3000:]
    assert "Gespräch in der Claude-App" in t
    s, _, t = abruf(f"{u.kurl}/konto", cookie=karl_keks)
    assert s == 200 and meldet(t, "konto.profil.titel", sprache) and meldet(t, "konto.profil.leer", sprache)
    assert MARKE not in t


def test_text_aendern_und_loeschen(zwei):
    """Test 17"""
    u = zwei()
    e = setzen(u.a, "Essen", "vegetarisch", "Gespräch")
    with closing(konten.db()) as v, v:
        v.execute("UPDATE profil SET datum = '2026-01-01T00:00:00+00:00'")
    s, _, t = abruf(f"{u.kurl}/konto", "POST", {"aktion": "profil_aendern", "id": e["id"], "text": "vegan"}, cookie=u.a_keks)
    assert s in (200, 303), t
    neu = konten.profil_liste(u.a["id"])[0]
    assert neu["text"] == "vegan" and neu["herkunft"] == "Gespräch" and neu["bereich"] == "Essen"
    assert not neu["datum"].startswith("2026-01-01")
    s, _, t = abruf(f"{u.kurl}/konto", "POST", {"aktion": "profil_aendern", "id": e["id"],
                                                 "text": "x" * (instanz.grenze_profil_text() + 1)}, cookie=u.a_keks)
    assert meldet(t, "konto.fehler.profil_zu_lang") and konten.profil_liste(u.a["id"])[0]["text"] == "vegan"
    s, _, t = abruf(f"{u.kurl}/konto", "POST", {"aktion": "profil_loeschen", "id": e["id"]}, cookie=u.a_keks)
    assert s in (200, 303), t
    assert konten.profil_liste(u.a["id"]) == []


def test_fremd_ohne_herkunft_und_get_aendern_nichts(zwei):
    """Test 18"""
    u = zwei()
    ida, karl, _, _ = alle(u)
    karl_keks, _ = anmelden(u, KARL)
    e = setzen(ida, "Essen", "vegetarisch", "Gespräch")
    for felder in ({"aktion": "profil_aendern", "id": e["id"], "text": "geändert"}, {"aktion": "profil_loeschen", "id": e["id"]}):
        abruf(f"{u.kurl}/konto", "POST", felder, cookie=karl_keks)                       # fremdes Konto
        s, _, _ = abruf(f"{u.kurl}/konto", "POST", felder, cookie=u.a_keks, origin="https://boese.invalid")
        assert s == 403
        s, h, _ = abruf(f"{u.kurl}/konto", "POST", felder)                                # ohne Sitzung
        assert s in (302, 303)
        abruf(f"{u.kurl}/konto?" + __import__("urllib.parse").parse.urlencode(felder), cookie=u.a_keks)   # GET
    assert konten.profil_liste(ida["id"]) == [e]


def test_kein_formular_zum_neuanlegen(zwei):
    """Test 19"""
    u = zwei()
    setzen(u.a)
    s, _, t = abruf(f"{u.kurl}/konto", cookie=u.a_keks)
    assert s == 200 and "profil_loeschen" in t and "profil_aendern" in t
    assert not re.search(r'value="profil_(anlegen|setzen|neu)"', t)
    assert not re.search(r'name="(bereich|herkunft)"', t)


# ---------- Isolation und Art. 9 (AC-9 bis AC-12) ----------

def test_niemand_sonst_sieht_das_profil(zwei):
    """Test 20: Karl (mitwirkend) und Organisatorin Ida, Tom (Organisator) und Lea in stadtwochenende."""
    u = zwei()
    ida, karl, tom, lea = alle(u)
    setzen(karl, "Essen", MARKE, "Gespräch")           # Karl ist mitwirkend: Organisatorin Ida sieht nichts
    setzen(lea, "Essen", MARKE + "-lea", "Gespräch")   # Lea ist mitwirkend: Organisator Tom sieht nichts
    for leser in (ida, tom):
        k = konten.konto(leser["id"])
        ausgaben = [kn.anleitung_frieda(k), kn.frieda_werkzeug(k, "meine_reisen", {})[0],
                    kn.frieda_werkzeug(k, "mein_profil", {})[0]]
        for w in kn.frieda_werkzeuge(k):
            if "reise" in w["inputSchema"].get("properties", {}) and w["name"] not in (
                    set(kn.SCHREIB_WERKZEUGE) | set(kn.SCHREIB_AKTION) | set(kn.ONTOLOGIE_WERKZEUGE)):
                for reise in w["inputSchema"]["properties"]["reise"].get("enum", []):
                    ausgaben.append(str(kn.frieda_werkzeug(k, w["name"], {"reise": reise, "begriff": "Essen"})[0]))
        s, _, t = abruf(f"{u.kurl}/konto", cookie=u.a_keks if leser is ida else u.b_keks)
        ausgaben.append(t)
        assert not [a for a in ausgaben if MARKE in a], leser["name"]
    assert MARKE not in ordner_text(u.seiten, u.ablage)


def test_profiltext_nie_in_logs_mails_meldungen(zwei, capfd):
    """Test 21"""
    u = zwei()
    ida, karl, _, _ = alle(u)
    text, fehler = werkzeug(ida, "profil_eintrag_setzen", bereich="Essen", text=MARKE, herkunft="Gespräch", bestaetigt=True)
    assert not fehler, text
    werkzeug(ida, "profil_eintrag_setzen", id="PR-1", bereich="Essen", text=MARKE + " neu", herkunft="Gespräch", bestaetigt=True)
    abruf(f"{u.kurl}/konto", "POST", {"aktion": "profil_aendern", "id": "PR-1", "text": MARKE + " drei"}, cookie=u.a_keks)
    werkzeug(ida, "profil_eintrag_setzen", bereich="Tempo", text=MARKE + " vier", herkunft="Gespräch", bestaetigt=True)
    werkzeug(ida, "profil_eintrag_setzen", bereich="x" * 999, text=MARKE + " zu lang", herkunft="Gespräch", bestaetigt=True)
    werkzeug(ida, "profil_eintrag_entfernen", id="PR-1")
    abruf(f"{u.kurl}/konto", "POST", {"aktion": "profil_loeschen", "id": "PR-2"}, cookie=u.a_keks)
    karl_export = anmeldung.export_person(konten.konto(karl["id"]), [], lambda r: None)
    aus, err = capfd.readouterr()
    assert MARKE not in err and MARKE not in aus
    assert MARKE not in (u.mails.read_text(encoding="utf-8") if u.mails.exists() else "")
    assert MARKE not in db_ohne_profil()
    assert MARKE not in ordner_text(u.seiten, u.ablage)
    assert MARKE not in json.dumps(karl_export, ensure_ascii=False)


def test_export_enthaelt_nur_das_eigene_profil(zwei):
    """Test 22"""
    u = zwei()
    ida, karl, _, _ = alle(u)
    e = setzen(ida, "Essen", MARKE, "Gespräch in der Claude-App")
    setzen(karl, "Tempo", "Karl mag es zügig", "Gespräch")
    p = anmeldung.export_person(konten.konto(ida["id"]), [], lambda r: None)
    assert p["profil"] == [{"id": e["id"], "bereich": "Essen", "text": MARKE, "herkunft": "Gespräch in der Claude-App",
                            "datum": e["datum"]}]
    k = anmeldung.export_person(konten.konto(karl["id"]), [], lambda r: None)
    assert MARKE not in json.dumps(k, ensure_ascii=False) and [x["text"] for x in k["profil"]] == ["Karl mag es zügig"]
    assert any("Profil" in texte.t("de", p_) for p_ in anmeldung.EXPORT_PUNKTE)
    assert any("profile" in texte.t("en", p_).lower() for p_ in anmeldung.EXPORT_PUNKTE)


@pytest.mark.parametrize("sprache", ["de", "en"])
def test_datenschutz_art9(zwei, sprache):
    """Test 23"""
    u = zwei()
    s, _, t = abruf(f"{u.kurl}/datenschutz", kopf={"Accept-Language": sprache})
    assert s == 200 and meldet(t, "recht.datenschutz.profil", sprache), t[-3000:]
    absatz = texte.t(sprache, "recht.datenschutz.profil")
    woerter = {"de": ("Gesundheit", "ausdrücklich", "Einwilligung", "löschen", "Export"),
               "en": ("health", "explicit", "consent", "delete", "export")}[sprache]
    assert all(w.lower() in absatz.lower() for w in woerter), absatz
    assert ("Profil" if sprache == "de" else "profile") in texte.t(sprache, "recht.datenschutz.konto_loeschen")


# ---------- Texte, Betrieb, Doku (AC-13) ----------

NEUE_SCHLUESSEL = [
    "konnektor.werkzeug.mein_profil", "konnektor.werkzeug.profil_eintrag_setzen", "konnektor.werkzeug.profil_eintrag_entfernen",
    "konnektor.profil.nicht_bestaetigt", "konnektor.anleitung.frieda.profil", "konnektor.anleitung.profil_nutzen",
    "konnektor.anleitung.profil_nicht_nutzen", "konto.fehler.profil_leer", "konto.fehler.profil_zu_lang",
    "konto.fehler.profil_voll", "konto.fehler.profil_unbekannt", "konto.profil.titel", "konto.profil.leer",
    "recht.datenschutz.profil",
]


def test_neue_schluessel_in_allen_sprachen():
    """Test 24"""
    for sprache in texte.SPRACHEN:
        fehlen = [s for s in NEUE_SCHLUESSEL if s not in texte.sprache(sprache).TEXTE]
        assert not fehlen, (sprache, fehlen)


def test_deploy_ohne_neues_modul():
    """Test 25: kein neues Modul, also keine neue Zeile in betrieb/deploy.sh."""
    assert not (ENGINE / "profil.py").exists()
    assert "profil" not in (WURZEL / "betrieb" / "deploy.sh").read_text(encoding="utf-8")


def test_doku_nachgezogen():
    """Test 26 und Doku aus AC-13"""
    kern = (WURZEL / "docs" / "adr" / "0001-kern.md").read_text(encoding="utf-8")
    assert re.search(r"Profil\w*.{0,200}lösch|lösch\w*.{0,200}Profil", kern, re.S | re.I), "Verlaufszeile fehlt"
    konnektor_doku = (WURZEL / "docs" / "konnektor.md").read_text(encoding="utf-8")
    assert all(n in konnektor_doku for n in WERKZEUGE.values())
    produkt = (WURZEL / "docs" / "produkt.md").read_text(encoding="utf-8")
    assert not re.search(r"profile[^\n]{0,80}nicht gebaut|nicht gebaut[^\n]{0,80}profile", produkt, re.I)
