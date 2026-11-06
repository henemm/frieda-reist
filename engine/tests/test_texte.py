"""Textkataloge und Leitplanken der Mehrsprachigkeit (ADR-0006, docs/mehrsprachigkeit.md).

Aufruf zum Auflisten der deutschen Literale einer Datei:  python engine/tests/test_texte.py engine/vorlage.html
"""
import ast
import datetime
import re
import sys
from pathlib import Path

import pytest

ENGINE = Path(__file__).resolve().parent.parent
BETRIEB = ENGINE.parent / "betrieb"
sys.path.insert(0, str(ENGINE))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import texte  # noqa: E402

UMLAUT = re.compile(r"[äöüÄÖÜß]")
PLATZHALTER = re.compile(r"\{(\w+)\}")
# Deutsche Funktionswörter: ein Text ohne Umlaut gilt als deutsch, wenn mindestens zwei davon vorkommen
DEUTSCHE_WOERTER = re.compile(r"\b(der|die|das|den|dem|des|und|oder|nicht|kein|keine|ist|sind|wird|werden|kann|ein|eine|einen|einer|"
                              r"mit|ohne|fuer|von|vom|zu|zum|zur|auf|bei|beim|nach|noch|nur|aber|wenn|alle|aus|im|am|an|es|sie|wir|du|dein|deine)\b",
                              re.I)


def ist_deutsch(text):
    return bool(UMLAUT.search(text)) or len({w.lower() for w in DEUTSCHE_WOERTER.findall(text)}) >= 2


def _sprachen():
    return texte.SPRACHEN


# ---------- Katalog ----------

def test_basis_sprachen_und_reihenfolge():
    assert texte.SPRACHEN[:2] == ("de", "en")
    assert texte.VORGABE == "en"


@pytest.mark.parametrize("kuerzel", ["de", "en"])
def test_pflichtfelder_jeder_sprachdatei(kuerzel):
    modul = texte.sprache(kuerzel)
    for feld in texte.PFLICHTFELDER:
        assert hasattr(modul, feld), f"texte_{kuerzel}.py: Feld {feld} fehlt"
    assert modul.RICHTUNG in ("ltr", "rtl")
    assert isinstance(modul.TEXTE, dict) and modul.TEXTE
    for n in (0, 1, 2, 3, 5, 11, 100, 101):
        assert modul.PLURAL(n) in texte.KATEGORIEN


def test_paritaet_schluessel_und_platzhalter():
    """Alle Sprachen haben dieselben Schlüssel und je Schlüssel dieselben Platzhalter wie Deutsch."""
    de = texte.sprache("de").TEXTE
    for k in _sprachen():
        andere = texte.sprache(k).TEXTE
        fehlt = sorted(set(de) - set(andere))
        zuviel = sorted(set(andere) - set(de))
        assert not fehlt, f"{k}: Schlüssel fehlen: {fehlt[:5]}"
        assert not zuviel, f"{k}: Schlüssel zu viel: {zuviel[:5]}"
        for s, text in andere.items():
            assert set(PLATZHALTER.findall(text)) == set(PLATZHALTER.findall(de[s])), f"{k}: Platzhalter von {s} weichen ab"


@pytest.mark.parametrize("kuerzel", ["de", "en"])
def test_reise_yaml_ist_pflicht_im_katalog(kuerzel):
    """#267, PR a: Ohne reise.yaml bricht der Bau ab; der Hinweis auf die alte Form ist weg."""
    katalog = texte.sprache(kuerzel).TEXTE
    assert "{pfad}" in katalog["pruefung.bauen.reise_yaml_fehlt"] and "docs/produkt.md" in katalog["pruefung.bauen.reise_yaml_fehlt"]
    assert "pruefung.reise.2" not in katalog


def test_leerzeichen_am_rand_wie_im_deutschen():
    """Texte, die der Code aneinanderhängt, tragen ihre Leerzeichen am Rand in jeder Sprache gleich (", geprüft " und ", checked"
    ergab „checked2026-…“)."""
    de = texte.sprache("de").TEXTE
    for k in _sprachen():
        for s, text in texte.sprache(k).TEXTE.items():
            assert (text[:1].isspace(), text[-1:].isspace()) == (de[s][:1].isspace(), de[s][-1:].isspace()), f"{k}: Leerzeichen am Rand von {s}"


def test_satz_statt_fragment_beim_freischalten():
    """Das Freischalten sagt ganze Sätze; ein Fragment als Platzhalter („may still no create trips“) lässt sich nicht übersetzen."""
    for k in _sprachen():
        for s in ("jetzt", "weiterhin_keine"):
            assert "{w1}" in texte.sprache(k).TEXTE[f"konnektor.ausgabe.frieda_werkzeug.{s}"], f"{k}: {s} ist kein ganzer Satz"
    assert "konnektor.ausgabe.frieda_werkzeug.1" not in texte.sprache("de").TEXTE


def test_vorlage_vergleicht_nie_mit_anzeigetext_und_haelt_einheiten_im_katalog():
    """Ein übersetzter Text ist keine Bedingung (bst.text !== "nicht gebucht" war auf Englisch immer wahr); die Einheit km steht im Katalog."""
    vorlage = (ENGINE / "vorlage.html").read_text(encoding="utf-8")
    vergleiche = re.findall(r"\.text\s*[!=]==?\s*[\"']", vorlage)
    assert not vergleiche, f"Vergleich mit Anzeigetext in der Vorlage: {vergleiche}"
    assert not re.findall(r"\}\s+km`", vorlage), "km steht fest in der Vorlage (seite.einheit.km)"
    assert "seite.einheit.km" in texte.sprache("en").TEXTE


def test_schluessel_form():
    muster = re.compile(r"^(?:(?:seite|konnektor|schreiben|dienst|konto|mail|kalender|waechter|push|inhalt|pruefung)(?:\.[a-z0-9_]+)+|(?:wert|symbol)\.[\wÄÖÜäöüß]+)$")
    for s in texte.sprache("de").TEXTE:
        assert muster.match(s), f"Schlüssel {s} hält die Form nicht ein"


def test_t_platzhalter_plural_rueckfall(monkeypatch):
    modul = texte.sprache("en")
    monkeypatch.setitem(modul.TEXTE, "seite.test.tage.one", "1 day")
    monkeypatch.setitem(modul.TEXTE, "seite.test.tage.other", "{n} days")
    monkeypatch.setitem(modul.TEXTE, "seite.test.gruss", "Hello {name}")
    assert texte.t("en", "seite.test.tage", n=1) == "1 day"
    assert texte.t("en", "seite.test.tage", n=2) == "2 days"
    assert texte.t("en", "seite.test.gruss", name="Ida") == "Hello Ida"
    # fehlt der Schlüssel in der Sprache, gilt Englisch
    assert texte.t("de", "seite.test.gruss", name="Karl") == "Hello Karl"
    # unbekannter Schlüssel und unbekannte Sprache stürzen nie ab
    assert texte.t("de", "seite.gibt.es.nicht") == "seite.gibt.es.nicht"
    assert texte.t("zz", "seite.test.gruss", name="X") == "Hello X"
    # fehlender Platzhalterwert: Text unverändert statt Absturz
    assert texte.t("en", "seite.test.gruss") == "Hello {name}"


def test_deutsch_wortlaut_der_vorhandenen_zuordnungen():
    """Die Wörter, die der Code früher selbst trug, stehen wörtlich im Katalog."""
    import konnektor
    import routen
    import schreiben
    assert konnektor.WORT == {"gewaehlt": "gewählt", "verworfen": "verworfen", "ersetzt": "ersetzt"}
    assert schreiben.WORT == konnektor.WORT
    assert schreiben.GRUNDFORM_WORT == {"aufenthalt": "Aufenthalt", "bewegung": "Bewegung", "folge": "Folge", "ort": "Ort"}
    assert schreiben.BUCHUNG_WORTE["bei"] == "Gebucht bei"
    assert schreiben.BUCHUNG_WORTE["preise"] == "Preise je Ding"
    assert len(schreiben.BUCHUNG_WORTE) == 19


def test_stufe_satz_in_beiden_sprachen():
    """stufe_satz liefert je Sprache den Katalogtext; unbekannte Werte bleiben Text (#267 c1, AC-8)."""
    import routen
    erwartet = {
        "de": {"pflicht": "nötig (pflicht)", "empfohlen": "gut zu wissen (empfohlen)", "angeboten": "zusätzlich (angeboten)", "aus": "aus"},
        "en": {"pflicht": "needed (required)", "empfohlen": "good to know (recommended)", "angeboten": "additional (optional)", "aus": "off"},
    }
    for sprache, stufen in erwartet.items():
        for schluessel, text in stufen.items():
            assert routen.stufe_satz(schluessel).text(sprache) == text, (sprache, schluessel)
        assert routen.stufe_satz("unbekannt").text(sprache) == "unbekannt"
    assert routen.stufe_satz({"*": "aus", "refugi": "empfohlen"}).text("de") == "sonst: gilt nicht, refugi: gut zu wissen (empfohlen)"
    assert routen.stufe_satz({"*": "aus", "refugi": "empfohlen"}).text("en") == "otherwise: does not apply, refugi: good to know (recommended)"


def test_stufen_konstante_der_bestandssprache_ist_weg():
    """Die Konstante mit den Wörtern des Bestands ist aus engine/ verschwunden (#267 c1, AC-8); der Name wird zusammengesetzt,
    damit der Test sich nicht selbst findet."""
    name = "STUFEN" + "_WORTE"
    treffer = [str(p.relative_to(ENGINE)) for p in ENGINE.rglob("*.py")
               if ".venv" not in p.parts and "vendor" not in p.parts and "tests" not in p.parts and name in p.read_text(encoding="utf-8")]
    assert not treffer, treffer


def test_text_62_nennt_art_und_nachziehen():
    """pruefung.routen.62 (Art fehlt an Unterkunft, Aufenthalt, Nacht) nennt nur noch art, nicht „typ oder art“, und den Weg über
    neu.py nachziehen; {wo} ist der einzige Platzhalter, der Befehl bleibt unübersetzt (#267 d, AC-10)."""
    erwartet = {
        "de": "{wo}: braucht art (eine Art aus plan/arten.yaml). Steht noch der frühere Schlüssel typ, stellt „neu.py nachziehen“ ihn auf art um.",
        "en": '{wo}: needs art (a kind from plan/arten.yaml). If the old key typ is still there, "neu.py nachziehen" converts it to art.',
    }
    for k, text in erwartet.items():
        assert texte.sprache(k).TEXTE["pruefung.routen.62"] == text, k
    for k in _sprachen():
        text = texte.sprache(k).TEXTE["pruefung.routen.62"]
        assert set(PLATZHALTER.findall(text)) == set(PLATZHALTER.findall("{wo}")), k
        assert "neu.py nachziehen" in text and "art" in text, k


def test_bestand_reise_kommt_nicht_mehr_vor():
    """Die Bestandssprache (Reise ohne Feld sprache gilt als deutsch) ist aus engine/ verschwunden (#267 c2, AC-4); der Name
    wird zusammengesetzt, damit der Test sich nicht selbst findet."""
    name = "BESTAND" + "_REISE"
    treffer = [str(p.relative_to(ENGINE)) for p in ENGINE.rglob("*.py")
               if ".venv" not in p.parts and "vendor" not in p.parts and "tests" not in p.parts and name in p.read_text(encoding="utf-8")]
    assert not treffer, treffer
    assert not hasattr(texte, name)


def _rand():
    import schnittstelle  # noqa: F401  (trägt die englischen Namen der Schnittstelle in texte._RAND ein)
    assert texte._RAND
    return texte._RAND


def test_einzeln_de_liefert_deutsche_namen():
    """Die Namen der Schnittstelle sind deutsche Wörter: Deutsch bekommt nie ihren englischen Namen aus _RAND, sondern den
    Katalogtext wert.<w> oder None (das Wort bleibt) (#267 c2, AC-5; Sicherungstest: grün vor und nach dem Paket)."""
    de = texte.sprache("de").TEXTE
    for w, englisch in _rand().items():
        ergebnis = texte._einzeln("de", w)
        assert ergebnis == de.get("wert." + w), (w, ergebnis)
        assert englisch == w or ergebnis != englisch, (w, ergebnis)


def test_einzeln_en_und_pseudo_fallen_auf_rand_zurueck(monkeypatch):
    """Sprachen, in denen die Namen der Schnittstelle keine Wörter sind, fallen ohne Katalogtext auf den englischen Namen zurück
    (#267 c2, AC-5): unverändert für en und die Pseudo-Sprache der Tests."""
    monkeypatch.setenv("FR_TEXTE_ZUSATZ", "xx")
    for kuerzel in ("en", "xx"):
        katalog = texte.sprache(kuerzel).TEXTE
        for w, englisch in _rand().items():
            if "wert." + w not in katalog:
                assert texte._einzeln(kuerzel, w) == englisch, (kuerzel, w)


def test_namen_der_schnittstelle_steht_in_der_sprachdatei(monkeypatch):
    """Ob die Namen der Schnittstelle Wörter einer Sprache sind, sagt deren Sprachdatei (NAMEN_DER_SCHNITTSTELLE), nicht der Code
    (#267 c2, AC-5, ADR-0006): nur texte_de.py trägt das Feld, es ist kein Pflichtfeld."""
    monkeypatch.setenv("FR_TEXTE_ZUSATZ", "xx")
    mit = [k for k in texte.SPRACHEN if getattr(texte.sprache(k), "NAMEN_DER_SCHNITTSTELLE", False) is True]
    assert mit == ["de"], mit
    assert "NAMEN_DER_SCHNITTSTELLE" not in texte.PFLICHTFELDER
    quelle = (ENGINE / "texte.py").read_text(encoding="utf-8")
    assert "NAMEN_DER_SCHNITTSTELLE" in quelle   # _einzeln liest das Feld aus der Sprachdatei


def test_datenwerte_paritaet_de_en():
    """Die Datenwerte (wert.*) sind in jeder Sprache dieselben; _datenwerte() liest sie aus texte.VORGABE (#267 c2, AC-6)."""
    de = {k for k in texte.sprache("de").TEXTE if k.startswith("wert.")}
    en = {k for k in texte.sprache("en").TEXTE if k.startswith("wert.")}
    assert de == en, de ^ en
    assert _datenwerte() == {k[len("wert."):] for k in de}


def test_neue_schluessel_der_sprachpflicht(monkeypatch):
    """Die Meldung „Feld sprache fehlt“ und „nicht gesetzt“ stehen in jeder Sprache, mit denselben Platzhaltern (#267 c2, AC-10)."""
    monkeypatch.setenv("FR_TEXTE_ZUSATZ", "xx")
    for kuerzel in texte.SPRACHEN:
        katalog = texte.sprache(kuerzel).TEXTE
        assert "pruefung.reise.sprache_fehlt" in katalog, kuerzel
        assert "schreiben.antwort.einstellung.sprache_ungesetzt" in katalog, kuerzel
        assert PLATZHALTER.findall(katalog["pruefung.reise.sprache_fehlt"]) == ["bekannt"], kuerzel
    assert "neu.py nachziehen" in texte.t("de", "pruefung.reise.sprache_fehlt")


def test_aus_header():
    assert texte.aus_header("de-AT,de;q=0.9,en;q=0.8") == "de"
    assert texte.aus_header("en-GB,en;q=0.9,de;q=0.8") == "en"
    assert texte.aus_header("fr,de;q=0.5") == "de"      # q-Wert zählt, nicht die Reihenfolge
    assert texte.aus_header("de;q=0.4, en;q=0.9") == "en"
    assert texte.aus_header("fr") == "en"
    assert texte.aus_header("") == "en"
    assert texte.aus_header(None) == "en"
    assert texte.aus_header("*") == "en"


def test_datum_und_zeit():
    d = datetime.date(2027, 5, 13)
    assert texte.datum(d, "de") == "13.5.2027" and texte.datum_kurz(d, "de") == "13.5."
    assert texte.datum(d, "en") == "13/5/2027" and texte.datum_kurz("2027-05-13", "en") == "13/5"
    assert texte.wochentag(d, "de") == "Do" and texte.wochentag("2027-05-13", "en") == "Thu"
    assert texte.zeit(datetime.time(5, 30), "de") == "5:30" and texte.zeit(datetime.time(5, 30), "en") == "05:30"


def test_seite_liefert_nur_seitentexte():
    s = texte.seite()
    assert list(s)[:2] == ["de", "en"]
    assert s["de"]["locale"] == "de-DE" and s["en"]["richtung"] == "ltr"
    assert s["de"]["texte"] and all(k.startswith(("seite.", "dienst.")) for k in s["de"]["texte"])
    assert s["de"]["texte"]["seite.status.gewaehlt"] == "gewählt"


def test_inhaltswoerter_nimmt_alle_sprachen(monkeypatch):
    monkeypatch.setitem(texte.sprache("de").TEXTE, "inhalt.test.wort", "geklärt")
    monkeypatch.setitem(texte.sprache("en").TEXTE, "inhalt.test.wort", "resolved")
    assert texte.inhaltswoerter("inhalt.test.wort") == {"geklärt", "resolved"}


# ---------- Pseudo-Sprache (andere Ziffern, rtl, sechs Pluralkategorien) ----------

def test_pseudo_sprache_laedt_ueber_umgebungsvariable(monkeypatch):
    assert "xx" not in texte.SPRACHEN
    ohne = texte.SPRACHEN   # Deutsch, Englisch und was sonst als Datei neben texte.py liegt
    monkeypatch.setenv("FR_TEXTE_ZUSATZ", "xx")
    assert texte.SPRACHEN == ohne + ("xx",)
    assert texte.plural("xx", 3) == "few" and texte.plural("xx", 0) == "zero" and texte.plural("xx", 11) == "many"
    assert texte.t("xx", "seite.status.gewaehlt") == "[xx chosen]"
    s = texte.seite()
    assert s["xx"]["locale"] == "ar-EG" and s["xx"]["richtung"] == "rtl"


def test_pseudo_sprache_haelt_die_paritaet(monkeypatch):
    monkeypatch.setenv("FR_TEXTE_ZUSATZ", "xx")
    xx = texte.sprache("xx").TEXTE
    de = texte.sprache("de").TEXTE
    assert set(de) <= set(xx)   # alle Schlüssel (die Pseudo-Sprache hat zusätzlich Pluralkategorien)
    assert all(PLATZHALTER.findall(v) == PLATZHALTER.findall(texte.sprache("en").TEXTE[k]) for k, v in xx.items() if k in texte.sprache("en").TEXTE)


def test_plural_waehlt_kategorie_der_sprache(monkeypatch):
    monkeypatch.setenv("FR_TEXTE_ZUSATZ", "xx")
    modul = texte.sprache("xx")
    monkeypatch.setitem(modul.TEXTE, "seite.test.tage.few", "[xx few {n}]")
    monkeypatch.setitem(modul.TEXTE, "seite.test.tage.other", "[xx other {n}]")
    assert texte.t("xx", "seite.test.tage", n=3) == "[xx few 3]"
    assert texte.t("xx", "seite.test.tage", n=200) == "[xx other 200]"   # fehlende Kategorie: Rückfall auf other


# ---------- Betrieb ----------

from test_betrieb import _deploy_liste  # noqa: E402  (löst $SPRACHDATEIEN in die Dateien der Sprachen auf)


def test_jede_sprache_steht_in_den_modullisten_des_deploys():
    dateien = {"texte.py"} | {f"texte_{k}.py" for k in texte._dateien()}
    for liste in ("RM_MODULE", "KN_MODULE", "SB_MODULE"):
        fehlt = dateien - _deploy_liste(liste)
        assert not fehlt, f"deploy.sh {liste} kopiert nicht: {sorted(fehlt)}"
    import konnektor
    assert dateien <= set(konnektor.CODE_DATEIEN) | set(konnektor.SPRACHDATEIEN)


# ---------- Leitplanken: keine deutschen Literale und keine Sprachweichen im Code ----------

PY_DATEIEN = ["konnektor.py", "schreiben.py", "rueckmeldungen.py", "anmeldung.py", "konten.py", "kalender.py", "waechter.py",
              "routen.py", "bauen.py", "neu.py", "reise.py", "belege.py", "instanz.py", "gpx.py", "oauth.py", "schnittstelle.py", "texte.py", "push.py"]
ALLE_DATEIEN = ["vorlage.html", "sw.vorlage.js", "app/konto.js", "app/sw.js"] + PY_DATEIEN

# Erlaubte Zahl deutscher Literale je Datei. Jedes Paket der Mehrsprachigkeit kürzt seinen Bereich; Einträge dürfen nur
# kleiner werden, nie größer (docs/auftraege/mehrsprachigkeit/README.md, Regel 5). Am Ende steht überall 0.
AUSNAHMEN = {
    "vorlage.html": 0, "konnektor.py": 0, "schreiben.py": 0, "rueckmeldungen.py": 0, "anmeldung.py": 0, "konten.py": 0,
    "kalender.py": 0, "waechter.py": 0, "routen.py": 0, "bauen.py": 0, "neu.py": 0, "reise.py": 0,
    "belege.py": 0, "instanz.py": 0, "gpx.py": 0, "oauth.py": 0, "sw.vorlage.js": 0, "schnittstelle.py": 1, "texte.py": 0, "push.py": 0,
    "app/konto.js": 0, "app/sw.js": 0,
}   # schnittstelle.py: ein Muster für deutsche Wörter (mit/nur … entscheiden), die Übersetzung deutscher Werkzeugnamen im Fließtext
# Treffer von Sprachweichen und festen Locale-Strings (Grep-Test); ebenfalls nur kleiner werdend
WEICHEN_AUSNAHMEN = {datei: 0 for datei in ALLE_DATEIEN}
# (keine Ausnahmen mehr: die Kontoseite nimmt lang aus der Sprachdatei, M7)
WEICHE = re.compile(r"""(?:[!=]=\s*["'](?:de|en)["'])|["'](?:de|en)-(?:DE|GB|US|AT)["']|lang=["'](?:de|en)["']""")


def py_literale(quelltext):
    """Python-Stringliterale mit deutschem Text (Umlaut, ß oder Funktionswörter), ohne Docstrings und ohne Aufrufe von t(...)/texte.t(...): [(Zeile, Text)]."""
    baum = ast.parse(quelltext)
    gefunden = []

    def ist_t_aufruf(knoten):
        f = knoten.func
        return (isinstance(f, ast.Name) and f.id == "t") or (isinstance(f, ast.Attribute) and f.attr == "t")

    def besuche(knoten, docstring=False):
        if isinstance(knoten, ast.Call) and ist_t_aufruf(knoten):
            return
        if isinstance(knoten, ast.JoinedStr):
            teile = "".join(w.value for w in knoten.values if isinstance(w, ast.Constant))
            if ist_deutsch(teile):
                gefunden.append((knoten.lineno, teile))
            return
        if isinstance(knoten, ast.Constant) and isinstance(knoten.value, str) and not docstring:
            if ist_deutsch(knoten.value):
                gefunden.append((knoten.lineno, knoten.value))
            return
        ist_koerper = isinstance(knoten, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        for i, kind in enumerate(ast.iter_child_nodes(knoten)):
            erster = ist_koerper and isinstance(kind, ast.Expr) and isinstance(kind.value, ast.Constant) and isinstance(kind.value.value, str)
            if erster and kind is knoten.body[0]:
                continue   # Docstring
            besuche(kind)

    besuche(baum)
    return gefunden


_REGEX_VOR = set("(,=:[!&|?{};+-*%<>~^") | {""}


def js_literale_mit_ort(code, nur_deutsch=True):
    """Wie js_literale, jeweils (Zeile, Text, Anfang, Ende, Anführungszeichen) mit Stelle im Quelltext. Stringliterale ('…', "…", `…`) mit deutschem Text in JavaScript, ohne Kommentare und ohne Aufrufe t(…): [(Zeile, Text)].
    Ein Template-Literal zählt als ein Literal. Regex-Literale werden an ihrem Vorgänger erkannt und übersprungen."""
    gefunden, i, n, zeile = [], 0, len(code), 1
    letztes = ""   # letztes bedeutsames Zeichen vor der Position
    letztes_wort = ""
    while i < n:
        c = code[i]
        if c == "\n":
            zeile += 1
            i += 1
            continue
        if c.isspace():
            i += 1
            continue
        if code.startswith("//", i):
            j = code.find("\n", i)
            i = n if j < 0 else j
            continue
        if code.startswith("/*", i):
            j = code.find("*/", i + 2)
            j = n if j < 0 else j + 2
            zeile += code.count("\n", i, j)
            i = j
            continue
        if c in "'\"`":
            j, tiefe = i + 1, 0
            while j < n:
                d = code[j]
                if d == "\\":
                    j += 2
                    continue
                if c == "`" and code.startswith("${", j):
                    tiefe += 1
                    j += 2
                    continue
                if c == "`" and d == "}" and tiefe:
                    tiefe -= 1
                    j += 1
                    continue
                if d == c and not tiefe:
                    break
                j += 1
            text = code[i + 1:j]
            vor = code[max(0, i - 12):i].rstrip()
            if (not nur_deutsch or ist_deutsch(text)) and not re.search(r"(?<![\w$.])[tT]\($", vor):
                gefunden.append((zeile, text, i, j + 1, c))
            zeile += code.count("\n", i, j)
            i = j + 1
            letztes, letztes_wort = c, ""
            continue
        if c == "/" and (letztes in _REGEX_VOR or letztes_wort in ("return", "typeof", "case")):
            j, klasse = i + 1, False
            while j < n:
                d = code[j]
                if d == "\\":
                    j += 2
                    continue
                if d == "[":
                    klasse = True
                elif d == "]":
                    klasse = False
                elif d == "/" and not klasse:
                    break
                elif d == "\n":
                    break
                j += 1
            i = j + 1
            letztes, letztes_wort = ")", ""
            continue
        if c.isalnum() or c in "_$":
            j = i
            while j < n and (code[j].isalnum() or code[j] in "_$"):
                j += 1
            letztes_wort = code[i:j]
            letztes = code[j - 1]
            i = j
            continue
        letztes, letztes_wort = c, ""
        i += 1
    return gefunden


def js_literale(code):
    """Stringliterale mit deutschem Text in JavaScript (siehe js_literale_mit_ort): [(Zeile, Text)]."""
    return [(z, t) for z, t, *_ in js_literale_mit_ort(code)]


def _quelltext(datei):
    text = (ENGINE / datei).read_text(encoding="utf-8")
    if datei.endswith(".html"):
        anfang = text.index("<script>") + len("<script>")
        return text[anfang:text.index("</script>", anfang)], text[:anfang].count("\n")
    return text, 0


def _ohne_entwicklerseite(funde, quelltext):
    """Literale zwischen ENTWICKLERSEITE-ANFANG und -ENDE (Bausteinseite der Vorlage) zählen nicht: sie ist Werkzeug der Entwicklung."""
    if "ENTWICKLERSEITE-ANFANG" not in quelltext:
        return funde
    a = quelltext.index("ENTWICKLERSEITE-ANFANG")
    b = quelltext.index("ENTWICKLERSEITE-ENDE")
    von, bis = quelltext.count("\n", 0, a) + 1, quelltext.count("\n", 0, b) + 1
    return [(z, t) for z, t in funde if not von <= z <= bis]


def _datenwerte():
    """Gespeicherte Datenwerte der Reise (Schlüssel wert.<Wert> des Katalogs): Sie stehen unverändert in den Dateien und sind kein Text (ADR-0006)."""
    return {k[len("wert."):] for k in texte.sprache(texte.VORGABE).TEXTE if k.startswith("wert.")}


def literale(datei):
    quelltext, versatz = _quelltext(datei)
    funde = js_literale(quelltext) if datei.endswith((".html", ".js")) else py_literale(quelltext)
    daten = _datenwerte()
    return [(z + versatz, t) for z, t in _ohne_entwicklerseite(funde, quelltext) if t not in daten]


@pytest.mark.parametrize("datei", ALLE_DATEIEN)
def test_keine_neuen_deutschen_literale(datei):
    funde = literale(datei)
    erlaubt = AUSNAHMEN[datei]
    assert len(funde) <= erlaubt, (
        f"{datei}: {len(funde)} deutsche Literale, erlaubt {erlaubt}. Neue Texte gehören in engine/texte_<sprache>.py (ADR-0006).\n"
        + "\n".join(f"  Zeile {z}: {t[:70]!r}" for z, t in funde[-5:]))


def test_ausnahmen_sind_ausgeschoepft_oder_zu_hoch():
    """Eine Ausnahmeliste, die größer ist als der Bestand, wird gekürzt (sie darf nur schrumpfen)."""
    zu_hoch = {d: (AUSNAHMEN[d], len(literale(d))) for d in ALLE_DATEIEN if len(literale(d)) < AUSNAHMEN[d]}
    assert not zu_hoch, f"AUSNAHMEN kürzen (erlaubt, Bestand): {zu_hoch}"


@pytest.mark.parametrize("datei", ALLE_DATEIEN)
def test_keine_sprachweichen_im_code(datei):
    """Kein if sprache == "de", keine festen Locale-Strings, kein lang="de" fest im Code (ADR-0006, Punkt 9)."""
    quelltext, _ = _quelltext(datei)
    treffer = [m.group(0) for m in WEICHE.finditer(quelltext)]
    assert len(treffer) <= WEICHEN_AUSNAHMEN[datei], f"{datei}: Sprachweichen {treffer}"


def test_python_scanner_erkennt_literale():
    quelltext = 'def f():\n    """Doku mit Übung."""\n    a = "Größe"\n    b = f"Nacht in {x} üben"\n    c = t("de", "Größe")\n    return a, b, c  # Ärger\n'
    assert [t for _, t in py_literale(quelltext)] == ["Größe", "Nacht in  üben"]


def test_js_scanner_erkennt_literale():
    code = 'const a = "Größe"; // Ärger\n/* Müll */ const b = `Nacht in ${x} für`; const c = t("Größe"); const r = /["ä]/; const d = \'ok\';'
    assert [t for _, t in js_literale(code)] == ["Größe", "Nacht in ${x} für"]


if __name__ == "__main__":
    for z, t in literale(sys.argv[1]):
        print(f"{z}: {t[:100]!r}")


# ---------- Sätze mit Schlüssel (Fehler, ADR-0006 Punkt 6) ----------

def test_satz_ist_deutsch_als_text_und_sprachfaehig_in_fstrings():
    s = texte.satz("schreiben.text_wert.1", feld="titel")
    assert str(s) == "„titel“ fehlt." and s.schluessel == "schreiben.text_wert.1" and s.werte == {"feld": "titel"}
    assert s.text("en") == "“title” is missing."
    texte.aufruf_sprache("en")
    try:
        assert f"{s}" == "“title” is missing."
    finally:
        texte.aufruf_sprache(texte.VORGABE_REISE)
    assert f"{s}" == "„titel“ fehlt."


def test_ablehnung_traegt_schluessel_und_werte():
    import schreiben
    a = schreiben.Ablehnung("schreiben.entscheiden.3", oid="V-99.z")
    assert str(a) == "Die Option V-99.z gibt es nicht." and a.text("en") == "The option V-99.z does not exist."
    assert a.schluessel == "schreiben.entscheiden.3" and a.werte == {"oid": "V-99.z"}
    alt = schreiben.Ablehnung("Ein fertiger Satz bleibt, wie er ist.")      # alte Aufrufe gelten weiter
    assert str(alt) == alt.text("en") == "Ein fertiger Satz bleibt, wie er ist." and alt.schluessel is None
    import reise
    ok, grund = reise.erlaubt("alternative", "gast", "planung", None)
    assert not ok and schreiben.Ablehnung(grund).text("en").startswith("This access is read-only")


def test_dienstfehler_tragen_den_code(tmp_path):
    import rueckmeldungen as rm
    k = texte.satz("dienst.wunsch_aendern.1")
    assert str(k) == "Diesen Wunsch gibt es nicht." and k.text("en") == "This wish does not exist."


# Einheitliche Fachwörter im englischen Katalog (docs/sprachen.md „Fachwörter“): diese Wörter sind für ein Ding der Reise
# bereits an anderer Stelle vergeben (Merkmal = attribute, Strecke = leg, Wahlstelle = choice, Ding = thing, Prüfdatum = check date,
# verworfen = rejected, übernehmen = copy oder adopt). Schlüssel in AUSNAHMEN sind Beispiele oder ein anderes deutsches Wort.
VERBOTENE_FACHWOERTER = {
    r"\bfeatures?\b": "Merkmal heißt attribute",
    r"\bjourneys?\b": "Strecke heißt leg",
    r"choice points?": "Wahlstelle heißt choice",
    r"discard": "verworfen heißt rejected",
    r"checked date|date checked": "Prüfdatum heißt check date",
    r"taken over": "Arten werden copied, Entscheidungen adopted",
    r"(?<!feedback )\bitems?\b": "Ding heißt thing",
}
AUSNAHMEN_FACHWOERTER = {
    ("konnektor.werkzeug.art_definieren", r"\bjourneys?\b"),   # „train journey“ als Beispiel einer Art
    ("kalender.sorte.fahrten", r"\bjourneys?\b"),               # Fahrten, nicht Strecken
}


def test_englische_fachwoerter_sind_einheitlich():
    import texte_en
    falsch = [f"{k}: {grund}" for k, v in texte_en.TEXTE.items() if isinstance(v, str)
              for muster, grund in VERBOTENE_FACHWOERTER.items()
              if re.search(muster, v, re.I) and (k, muster) not in AUSNAHMEN_FACHWOERTER]
    assert not falsch, "\n".join(falsch)


def test_stufen_werden_in_jeder_sprache_gelesen():
    """Die Wörter, die der Katalog für eine Stufe zeigt, nimmt die Eingabe in jeder Sprache an (nicht nur die deutschen)."""
    import routen
    for wort, schluessel in (("needed", "pflicht"), ("good to know", "empfohlen"), ("Additional", "angeboten"), ("off", "aus"),
                             ("required", "pflicht"), ("optional", "angeboten"), ("nötig", "pflicht"), ("noetig", "pflicht"),
                             ("gut zu wissen", "empfohlen"), ("zusätzlich", "angeboten"), ("pflicht", "pflicht")):
        assert routen.stufe_schluessel(wort) == schluessel, wort
    assert routen.stufe_schluessel("unbekannt") is None
    assert routen.stufe_wort("pflicht", "en") == "needed (required)"
    assert routen.stufe_wort("pflicht", "de") == "nötig (pflicht)"


def test_englische_mengenangaben_im_singular():
    """Zahlen vor Hauptwörtern des Konnektors laufen über die Pluralkategorien („1 day“, nicht „1 days“)."""
    import konnektor
    import texte
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(texte, "aufruf_sprache", lambda sprache=None: sprache or "en")
        assert konnektor.Handbuch.summe(None, {"tage": 1, "naechte": 0, "min": 90, "auf": 120.4, "ab": 80.6, "km": 12.5,
                                               "mit_kennzahlen": True, "fehlend": []}) \
            == "1 day, 0 nights; Walking time 1:30 h, ↑ 120 m, ↓ 81 m, 12.5 km"
        assert konnektor.tk("konnektor.brett_text.3", n=1) == "at most 1 wish per person"
        assert konnektor.tk("konnektor.brett_text.3", n=3) == "at most 3 wishes per person"
        assert konnektor.tk("konnektor.ausgabe.werkzeug.6", n=1) == "1 point"


# ---------- Kennzahlen an einer Stelle (#268) ----------
def test_handbuch_summe_mit_und_ohne_kennzahlen():
    """AC-10: Ob eine Gehzeit-Zeile steht, entscheidet summe.mit_kennzahlen aus dem Routenmodell, nicht der Wert min."""
    import konnektor
    basis = {"tage": 2, "naechte": 1, "min": 0, "auf": 0, "ab": 0, "km": 0, "fehlend": [], "unvollstaendig": False}
    ohne = konnektor.Handbuch.summe(None, {**basis, "mit_kennzahlen": False, "min": 90})
    assert konnektor.tk("konnektor.summe.gehzeit", zeit="1:30 h", auf="0", ab="0", km="0") not in ohne
    assert "1:30" not in ohne
    voll = konnektor.Handbuch.summe(None, {**basis, "mit_kennzahlen": True, "min": 90, "auf": 120, "ab": 80, "km": 12.5})
    assert konnektor.tk("konnektor.summe.gehzeit", zeit=konnektor.stunden(90), auf="120", ab="80",
                        km="12" + konnektor.tk("seite.auto.dezimaltrenner") + "5") in voll


def test_handbuch_summe_angaben_fehlen():
    """AC-5: Hat ein Plan summierte Strecken ohne Angaben, steht dort der Katalogtext „Angaben fehlen“ statt nichts oder 0:00."""
    import konnektor
    s = {"tage": 2, "naechte": 1, "min": 0, "auf": 0, "ab": 0, "km": 0, "mit_kennzahlen": True,
         "fehlend": ["ab", "auf", "km", "min"], "unvollstaendig": True}
    aus = konnektor.Handbuch.summe(None, s)
    assert konnektor.tk("konnektor.summe.angaben_fehlen") in aus, aus
    assert "0:00" not in aus


def test_neue_kennzahl_schluessel_in_allen_sprachen():
    """AC-7: Die Texte für Höhenmeter (Seite, auto_werte) und „Angaben fehlen“ (Konnektor) stehen in jeder Sprache."""
    for k in texte.SPRACHEN:
        katalog = texte.sprache(k).TEXTE
        for s in ("seite.kennzahl.hoehe_auf", "seite.kennzahl.hoehe_ab", "seite.auto.hoehenmeter", "konnektor.summe.angaben_fehlen"):
            assert s in katalog, (k, s)
    assert texte.t("de", "seite.kennzahl.hoehe_auf", v=480) == "↑ 480 m"
    assert texte.t("de", "seite.auto.hoehenmeter", auf=400, ab=100) == "↑ 400 m, ↓ 100 m"


def test_handbuch_summe_teilweise_angaben():
    """Fehlen nur einige Angaben, bleiben die bekannten Summen sichtbar, ein Feld ohne jede Angabe trägt einen Strich statt einer
    Null (keine „0:00“), und der Zusatz „unvollständig“ steht dabei – wie auf der Seite (seite.summe.unvollstaendig)."""
    import konnektor
    basis = {"tage": 2, "naechte": 1, "min": 210, "auf": 400, "ab": 100, "km": 10.5, "mit_kennzahlen": True, "unvollstaendig": True}
    zusatz = konnektor.tk("seite.summe.unvollstaendig")
    teil = konnektor.Handbuch.summe(None, {**basis, "fehlend": ["km"]})
    assert konnektor.stunden(210) in teil and zusatz in teil, teil
    assert konnektor.tk("konnektor.summe.angaben_fehlen") not in teil
    ohne_zeit = konnektor.Handbuch.summe(None, {**basis, "min": 0, "fehlend": ["min"]})
    strich = konnektor.tk("konnektor.summe.fehlt")
    assert konnektor.tk("konnektor.summe.gehzeit", zeit=strich, auf="400", ab="100",
                        km="10" + konnektor.tk("seite.auto.dezimaltrenner") + "5") + zusatz in ohne_zeit, ohne_zeit
    assert "0:00" not in ohne_zeit


def test_neue_schluessel_der_orte_in_allen_sprachen():
    """#353, Schritt 2 (AC-17): Orte als Möglichkeit haben ihre Texte in jeder Sprache; die geänderten Ablehnungen nennen die
    neue Sorte orte und die änderbaren Felder aufenthalte und orte."""
    for k in texte.SPRACHEN:
        katalog = texte.sprache(k).TEXTE
        for s in ("konnektor.feld.option_felder.orte", "konnektor.ausgabe.option_text.orte",
                  "pruefung.routen.option_ort", "pruefung.routen.nacht_nur_orte"):
            assert s in katalog, (k, s)
        for s in ("schreiben.option_bauen.2", "schreiben.option_aendern.5", "schreiben.option_aendern.8"):
            assert re.search(r"\borte\b", katalog[s]), (k, s, katalog[s])
        assert re.search(r"\baufenthalte\b", katalog["schreiben.option_aendern.8"]), (k, katalog["schreiben.option_aendern.8"])
