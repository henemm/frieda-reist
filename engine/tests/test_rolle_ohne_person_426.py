"""Tests für #426: Der Konnektor kennt nur noch Zugänge mit Person (Konto-Weg seit #421). Der frühere interne Zugang
„Rolle ohne Person“, das Namensfeld der Werkzeuge und die Texte für „Link ohne Person“ sind entfernt."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import konnektor as kn  # noqa: E402
import rueckmeldungen as rm  # noqa: E402
import texte  # noqa: E402
from test_regeln import IDA, KARL, KIM, umgebung  # noqa: E402,F401  (umgebung: Fixture; Kim ist Gast als Person)
from conftest import meldet  # noqa: E402

WURZEL = Path(__file__).resolve().parent.parent.parent

ENTFERNTE_SCHLUESSEL = (
    "konnektor.einladen.6", "konnektor.entscheiden.2", "konnektor.ontologie_werkzeug.7", "konnektor.werkzeug.14",
    "konnektor.frage_beantworten.4", "konnektor.anleitung.du_ohne_name", "konnektor.anleitung.mit.vorname",
    "konnektor.feld.name_feld", "konnektor.werkzeug.rueckmeldung_geben.name",
)


def _sprachen():
    return sorted(p.stem.split("_", 1)[1] for p in (WURZEL / "engine").glob("texte_*.py"))


def _katalog(sprache):
    import importlib
    return importlib.import_module(f"texte_{sprache}").TEXTE


def test_zugang_ohne_person_hat_keinen_zugriff(umgebung):
    """AC-1: Ein Zugang nur mit Rolle (aus der Zeit der Links) gibt keinen Zugriff, und nichts läuft still als Gast."""
    u = umgebung()
    d = kn.daten("beispielreise")
    for rolle in ("mitreisend", "mitwirkend", "gast", "organisator"):
        assert kn.wer_spricht({"reise": "beispielreise", "rolle": rolle}, d) is None
    a = kn.antwort_fuer({"reise": "beispielreise", "rolle": "mitreisend"},
                        {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                         "params": {"name": "rueckmeldung_geben",
                                    "arguments": {"ziel": "T-01", "art": "Kommentar", "text": "Hallo", "name": "Anna"}}})
    r = a["result"]
    assert r["isError"] and meldet(r["content"][0]["text"], "konnektor.werkzeug.1")
    assert rm.eintraege(u.o) == [] and u.schreibweg == []


def test_tools_list_ohne_name_und_vorname_ausser_einladen(umgebung):
    """AC-2: Kein Werkzeugschema hat ein Feld name; vorname (first_name) nur beim Einladen."""
    u = umgebung()
    for token in (IDA, KARL, KIM):
        for w in u.rpc(token, "tools/list")["tools"]:
            felder = set((w.get("inputSchema") or {}).get("properties") or {})
            assert "name" not in felder, (token[:1], w["name"])
            if w["name"] != "person_einladen":
                assert not felder & {"vorname", "first_name"}, (token[:1], w["name"])
    einladen = next(w for w in u.rpc(IDA, "tools/list")["tools"] if w["name"] == "person_einladen")
    assert einladen["inputSchema"]["properties"].keys() & {"vorname", "first_name"}


def test_ueberzaehliges_namensargument_ohne_fehler(umgebung):
    """AC-3: Alte Clients schicken weiter name oder vorname mit: kein Fehler, der Name kommt aus der Person."""
    u = umgebung()
    for werkzeugname, args in (("rueckmeldung_geben", {"ziel": "T-01", "art": "Kommentar", "text": "Schön", "name": "Anna"}),
                               ("aufgabe_anlegen", {"titel": "Etwas tun", "vorname": "Anna"})):
        r = u.rpc(KARL, "tools/call", {"name": werkzeugname, "arguments": args})
        assert not r["isError"], (werkzeugname, r["content"][0]["text"])
    assert {e["name"] for e in rm.eintraege(u.o)} == {"Karl"}


def test_gast_als_person_kim_liest_schreibt_nicht(umgebung):
    """AC-4: Der Gast ist eine Person (Kim, nur in der Testvorbereitung): lesen ja, schreiben nein."""
    u = umgebung()
    for werkzeugname, args in (("ueberblick", {}), ("zeige", {"id": "T-01"})):
        t, f = u.werkzeug(KIM, werkzeugname, **args)
        assert not f, (werkzeugname, t)
    for werkzeugname, args in (("rueckmeldung_geben", {"ziel": "T-01", "art": "Kommentar", "text": "Hallo"}),
                               ("aufgabe_anlegen", {"titel": "Etwas tun"})):
        t, f = u.werkzeug(KIM, werkzeugname, **args)
        assert f, (werkzeugname, t)
    assert rm.eintraege(u.o) == [] and u.schreibweg == []
    assert "Kim" in u.rpc(KIM, "initialize")["instructions"]


def test_name_kommt_aus_der_person():
    """Datenrobustheit: Fehlt der Name im Eintrag einer Person, gilt ihr Schlüssel, nie None."""
    d = {"reise": {"personen": [{"schluessel": "kim", "rolle": "gast"}]}}
    wer = kn.wer_spricht({"reise": "gibtsnicht", "person": "kim"}, d)
    assert wer == {"rolle": "gast", "name": "kim"}
    assert kn.wer_spricht({"reise": "gibtsnicht", "person": "niemand"}, d) is None
    assert kn.wer_spricht({"reise": "gibtsnicht"}, d) is None


def test_anleitung_ohne_namensfrage(umgebung):
    """AC-6: Die Anleitung kennt die Person und fragt nie nach dem Vornamen, in jeder Sprache."""
    u = umgebung()
    for sprache in _sprachen():
        a = kn.antwort_fuer({"reise": "beispielreise", "person": "karl", "sprache": sprache},
                            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        anleitung = a["result"]["instructions"]
        assert "Karl" in anleitung
        alt = _katalog(sprache).get("konnektor.anleitung.mit.vorname")
        assert alt is None or alt.strip() not in anleitung, sprache
    assert "Vornamen" not in u.rpc(KARL, "initialize")["instructions"]


def test_einladen_vorname_bleibt(umgebung):
    """AC-6: Beim Einladen bleibt vorname der Name der eingeladenen Person."""
    u = umgebung()
    t, f = u.werkzeug(IDA, "person_einladen", vorname="Jörg", rolle="mitwirkend", email="joerg@beispiel.invalid")
    assert not f, t
    assert rm.einladungen_lesen(u.o)["joerg"]["name"] == "Jörg"


def test_entfernte_texte_fehlen_in_allen_sprachen():
    """AC-5: Die Texte für „Link ohne Person“ fehlen in jedem Katalog, und kein Code verweist mehr auf sie."""
    for sprache in _sprachen():
        katalog = _katalog(sprache)
        for s in ENTFERNTE_SCHLUESSEL:
            assert s not in katalog, (sprache, s)
        assert "{vorname}" not in katalog["konnektor.anleitung.mit"], sprache
    code = (WURZEL / "engine" / "konnektor.py").read_text(encoding="utf-8")
    for s in ENTFERNTE_SCHLUESSEL:
        assert not re.search(r'["@]' + re.escape(s) + '"', code), s
    assert "NAME_FELD" not in code
    assert texte  # Katalog lädt


def test_doku_nennt_keinen_zugang_ohne_namen():
    """AC-8: Die Doku beschreibt weder einen Zugang ohne Person noch die Frage nach dem eigenen Vornamen."""
    for pfad in ("docs/konnektor.md", "docs/auftraege/mehrsprachigkeit/M8.md"):
        doku = (WURZEL / pfad).read_text(encoding="utf-8")
        for verboten in ("NAME_FELD", "name_feld", "ohne festen Namen", "nach dem Vornamen", "du_ohne_name",
                         "Rolle ohne Person"):
            assert verboten not in doku, (pfad, verboten)


def test_tests_nutzen_keinen_zugang_ohne_person():
    """AC-7: In den Tests gibt es weder MITREISEND noch einen Kurznamen, der nur eine Rolle trägt."""
    tests = WURZEL / "engine" / "tests"
    for p in tests.glob("*.py"):
        if p.name == Path(__file__).name:
            continue
        inhalt = p.read_text(encoding="utf-8")
        assert "MITREISEND" not in inhalt, p.name
        # Zugang nur mit Rolle: {"reise": …, "rolle": …} oder zugang_dazu(…, rolle=…) ohne person
        assert not re.search(r'\{"reise": "[^"]*", "rolle": ', inhalt), p.name
        for aufruf in re.findall(r"zugang_dazu\([^)]*\)", inhalt):
            assert "rolle=" not in aufruf or "person=" in aufruf, (p.name, aufruf)
    conftest = (tests / "conftest.py").read_text(encoding="utf-8")
    assert '("reise", "person", "rolle", "sprache")' not in conftest
