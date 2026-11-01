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
    muster = re.compile(r"^(seite|konnektor|schreiben|dienst|konto|mail|kalender|waechter|inhalt|pruefung)(\.[a-z0-9_]+)+$")
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
    assert schreiben.GRUNDFORM_WORT == {"aufenthalt": "Aufenthalt", "bewegung": "Bewegung", "folge": "Folge"}
    assert schreiben.BUCHUNG_WORTE["bei"] == "Gebucht bei"
    assert schreiben.BUCHUNG_WORTE["preise"] == "Preise je Ding"
    assert len(schreiben.BUCHUNG_WORTE) == 19
    assert routen.STUFEN_WORTE == {"pflicht": "nötig", "empfohlen": "gut zu wissen", "angeboten": "zusätzlich", "aus": "aus"}


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
              "routen.py", "bauen.py", "neu.py", "reise.py"]
ALLE_DATEIEN = ["vorlage.html"] + PY_DATEIEN

# Erlaubte Zahl deutscher Literale je Datei. Jedes Paket der Mehrsprachigkeit kürzt seinen Bereich; Einträge dürfen nur
# kleiner werden, nie größer (docs/auftraege/mehrsprachigkeit/README.md, Regel 5). Am Ende steht überall 0.
AUSNAHMEN = {
    "vorlage.html": 2, "konnektor.py": 5, "schreiben.py": 4, "rueckmeldungen.py": 17, "anmeldung.py": 0, "konten.py": 1,
    "kalender.py": 0, "waechter.py": 5, "routen.py": 6, "bauen.py": 11, "neu.py": 21, "reise.py": 4,
}
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


def literale(datei):
    quelltext, versatz = _quelltext(datei)
    funde = js_literale(quelltext) if datei.endswith(".html") else py_literale(quelltext)
    return [(z + versatz, t) for z, t in _ohne_entwicklerseite(funde, quelltext)]


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
    assert s.text("en") == "“titel” is missing."
    texte.aufruf_sprache("en")
    try:
        assert f"{s}" == "“titel” is missing."
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
