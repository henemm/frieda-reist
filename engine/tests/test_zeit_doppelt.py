"""Uhrzeit nicht doppelt anzeigen (frieda-reist#619). Spec: docs/specs/oberflaeche/uhrzeit-doppelt-619.md

Hat ein Aufenthalt oder eine Unterkunft einen freien Zeittext (zeit) und ein Zeitfenster (beginn/ende aus dem Merkmal
zeitraum), steht die Uhrzeit auf Seite, im Konnektor und im Kalender genau einmal; der Freitext nur mit dem, was er
darüber hinaus sagt. Gespeichert bleibt alles unverändert. Alle Beispiele sind erfunden (beide Beispielreisen)."""
import datetime
import re
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bauen  # noqa: E402
import kalender  # noqa: E402
import konnektor as kn  # noqa: E402
import routen  # noqa: E402
import texte  # noqa: E402

WURZEL = Path(__file__).resolve().parents[2]
BEISPIELE = WURZEL / "beispiel" / "reisen"


def zou(zeit, beginn, ende, einheit="Uhr"):
    return routen.zeit_ohne_uhr(zeit, beginn, ende, einheit)


def einheit(sprache):
    """Einheitswort einer Sprache, so wie der Katalog es führt: der Text von seite.zeit.uhr ohne die Zeit."""
    return texte.t(sprache, "seite.zeit.uhr", zeit="").strip()


# ---------- Hilfsfunktion (AC-1 bis AC-3) ----------

def test_uhrzeit_hinter_freitext_entfaellt():
    """Test 1 (AC-1): „nach der Wanderung, 16–18 Uhr“ bei 16:00–18:00 → nur noch der Freitext."""
    assert zou("nach der Wanderung, 16–18 Uhr", "16:00", "18:00") == "nach der Wanderung"


def test_nur_uhrzeit_entfaellt_ganz():
    """Test 2 (AC-1): „13 Uhr“ bei 13:00–15:00 (eine Zeit gleich dem Beginn) → leer."""
    assert zou("13 Uhr", "13:00", "15:00") == ""
    assert zou("16 Uhr", "16:00", None) == ""


@pytest.mark.parametrize("zeit, beginn, ende, rest", [
    ("16:00–18:00 Uhr", "16:00", "18:00", ""),          # Minuten ausgeschrieben
    ("16.00–18.00 Uhr", "16:00", "18:00", ""),          # Punkt statt Doppelpunkt
    ("16-18 Uhr", "16:00", "18:00", ""),                # einfacher Bindestrich
    ("16–18", "16:00", "18:00", ""),                    # ohne Einheitswort
    ("13 Uhr, Treffpunkt am Tor", "13:00", "15:00", "Treffpunkt am Tor"),
    ("Sonntag · 13 Uhr", "13:00", "15:00", "Sonntag"),
    ("16:30 Uhr", "16:30", None, ""),
])
def test_weitere_schreibweisen_passend(zeit, beginn, ende, rest):
    assert zou(zeit, beginn, ende) == rest


@pytest.mark.parametrize("zeit, beginn, ende", [
    ("Sonntag Vormittag", "10:00", "12:00"),            # keine Uhrzeit im Text (Test 3)
    ("ab 16 Uhr", "16:00", "18:00"),                    # „ab“ trägt Bedeutung (Test 3)
    ("17–19 Uhr", "16:00", "18:00"),                    # widerspricht dem Fenster: nie verstecken (Test 4)
    ("16:30 Uhr", "16:00", "18:00"),                    # andere Minute
    ("16–19 Uhr", "16:00", "18:00"),                    # Ende passt nicht
    ("18 Uhr", "16:00", "18:00"),                       # eine Zeit, aber nicht der Beginn
])
def test_freitext_bleibt_unveraendert(zeit, beginn, ende):
    """Test 3 und 4 (AC-2)."""
    assert zou(zeit, beginn, ende) == zeit


def test_ohne_beginn_bleibt_alles():
    """Test 4 (AC-2): ohne Zeitfenster wird nichts verändert."""
    assert zou("nach der Wanderung, 16–18 Uhr", None, None) == "nach der Wanderung, 16–18 Uhr"
    assert zou("13 Uhr", "", "") == "13 Uhr"
    assert zou(None, "16:00", "18:00") in (None, "")
    assert zou("", "16:00", "18:00") == ""


def test_einheit_aus_dem_katalog_jeder_sprache(monkeypatch):
    """Test 5 (AC-3): Das Einheitswort kommt aus seite.zeit.uhr; en (leer) und die Pseudo-Sprache der Tests entfernen
    „16–18“ ebenso, ohne dass der Code eine Sprache beim Namen kennt."""
    monkeypatch.setenv("FR_TEXTE_ZUSATZ", "xx")
    assert "xx" in texte.sprachen()
    for k in texte.sprachen():
        e = einheit(k)
        assert zou("16–18", "16:00", "18:00", e) == "", (k, e)
        assert zou(f"Führung, 16–18 {e}".strip(), "16:00", "18:00", e) == "Führung", (k, e)
    assert einheit("de") == "Uhr" and einheit("en") == ""
    # Ohne Einheitswort ist „Uhr“ ein weiteres Wort: der Text bleibt stehen (dieselbe Regel, nur ohne Wort)
    assert zou("16–18 Uhr", "16:00", "18:00", "") == "16–18 Uhr"


def test_code_kennt_kein_einheitswort():
    """AC-3: Das Wort „Uhr“ steht nicht im Code der Hilfsfunktion, nur im Katalog."""
    import inspect
    quelle = inspect.getsource(routen.zeit_ohne_uhr)
    assert "Uhr" not in re.sub(r'""".*?"""', "", quelle, flags=re.S)


# ---------- Seite, Konnektor, Kalender an beiden Beispielreisen (AC-4) ----------

@pytest.fixture(scope="module")
def gebaut(tmp_path_factory):
    aus = {}
    for reise in ("beispielreise", "stadtwochenende"):
        ziel = tmp_path_factory.mktemp("web") / reise
        aus[reise] = bauen.bauen(BEISPIELE / reise, ziel)
    return aus


FAELLE = [   # Reise, Aufenthalt, Freitext gespeichert, Freitext angezeigt, Zeitfenster für den Konnektor
    ("beispielreise", "A-01", "nach der Wanderung, 16–18 Uhr", "nach der Wanderung", "16:00–18:00"),
    ("stadtwochenende", "A-01", "13 Uhr", "", "13:00–15:00"),
]


@pytest.mark.parametrize("reise, aid, zeit, rest, fenster", FAELLE)
def test_seitendaten_tragen_den_anzeigetext(gebaut, reise, aid, zeit, rest, fenster):
    """Test 6 (AC-4, AC-5): zeit_rest ist der Anzeigetext, zeit bleibt wie gespeichert."""
    a = gebaut[reise]["route"]["aufenthalte"][aid]
    assert a["zeit"] == zeit
    assert a["zeit_rest"] == rest


def test_jeder_freitext_bekommt_ein_anzeigefeld(gebaut):
    """Test 6: Jeder Aufenthalt und jede Unterkunft mit Freitext trägt das Anzeigefeld; ohne Zeitfenster gleich dem Freitext."""
    geprueft = 0
    for d in gebaut.values():
        r = d["route"]
        for x in list((r.get("aufenthalte") or {}).values()) + list((r.get("unterkuenfte") or {}).values()):
            if x.get("zeit"):
                geprueft += 1
                assert "zeit_rest" in x, x.get("name")
                if not x.get("beginn"):
                    assert x["zeit_rest"] == x["zeit"], x.get("name")
    assert geprueft >= 3
    # Stadtmuseum „Sonntag Vormittag“ hat kein Zeitfenster: bleibt
    assert gebaut["stadtwochenende"]["route"]["aufenthalte"]["A-02"]["zeit_rest"] == "Sonntag Vormittag"


def test_etiketten_der_vorlage_lesen_den_anzeigetext():
    """Test 6: Jedes Etikett, das das Zeitfenster zeigt (Aufenthaltszeile, Unterkunftskarte, Zeile ohne Tag), liest
    zeit_rest statt zeit; die Vorlage rechnet nichts."""
    q = (WURZEL / "engine" / "vorlage.html").read_text(encoding="utf-8")
    stellen = re.findall(r"\[[^\[\]]*uhrText\((\w+)\)\]", q)
    ganze = re.findall(r"\[[^\[\]]*uhrText\(\w+\)\]", q)
    assert len(ganze) >= 3, ganze
    for x, stelle in zip(stellen, ganze):
        assert f"{x}.zeit_rest ?? {x}.zeit" in stelle, stelle
        assert not re.search(rf"(?<![\w.]){x}\.zeit\s*,", stelle), stelle


@pytest.mark.parametrize("reise, aid, zeit, rest, fenster", FAELLE)
def test_konnektor_nennt_die_uhrzeit_einmal(gebaut, reise, aid, zeit, rest, fenster):
    """Test 7 (AC-4): show und Tagestext nennen die Uhrzeit je einmal."""
    h = kn.Handbuch(gebaut[reise])
    zeile = h.aufenthalt(aid)
    assert zeile.count("Uhr") == 1, zeile
    assert texte.t("de", "konnektor.ausgabe.uhr", w1=fenster) in zeile
    if rest:
        assert rest in zeile
    aus, fehler = h.zeige(aid)
    assert fehler is None
    if zeit != rest:
        assert zeit not in aus, aus
    tag = next(t for t in gebaut[reise]["route"]["tage"] if aid in (t.get("aufenthalte") or []))
    tt = h.tag_text(tag)
    assert zeile in tt
    if zeit != rest:
        assert zeit not in tt.replace(" um 13 Uhr (Beispiel)", ""), tt   # der Fixpunkt des Stadtwochenendes nennt die Zeit selbst


@pytest.mark.parametrize("reise, aid, zeit, rest, fenster", FAELLE)
def test_kalender_termin_ohne_doppelte_uhrzeit(gebaut, reise, aid, zeit, rest, fenster):
    """Test 8 (AC-4): Der Termin trägt die Uhrzeit selbst; der Termintext nennt sie nicht noch einmal."""
    e = [x for x in kalender.eintraege(gebaut[reise]) if x["id"] == aid and x["sorte"] == "aufenthalte"]
    assert e, aid
    for x in e:
        assert isinstance(x.get("beginn"), datetime.datetime), x
        assert zeit not in x["text"], x["text"]
        if rest:
            assert rest in x["text"], x["text"]


@pytest.mark.parametrize("reise", ["beispielreise", "stadtwochenende"])
def test_gespeicherte_daten_bleiben(tmp_path, reise):
    """Test 9 (AC-5): Das Bauen verändert die Reisedaten nicht; zeit, beginn und ende bleiben, kein nachziehen nötig."""
    q = tmp_path / reise
    shutil.copytree(BEISPIELE / reise, q)
    vorher = (q / "plan" / "routen.yaml").read_bytes()
    d = bauen.bauen(q, tmp_path / "web" / reise)
    assert (q / "plan" / "routen.yaml").read_bytes() == vorher
    a = d["route"]["aufenthalte"]["A-01"]
    zeit, fenster = next((f[2], f[4]) for f in FAELLE if f[0] == reise)
    assert a["zeit"] == zeit and f"{a['beginn']}–{a['ende']}" == fenster
    assert "zeit_rest" in a   # das Anzeigefeld steht nur in den Seitendaten
    assert "zeit_rest" not in (q / "plan" / "routen.yaml").read_text(encoding="utf-8")
