"""ADR-0002, Pflicht „vier Stellen“: Ein Baustein steht im Kopfkommentar der Vorlage, in docs/design.md, auf der Bausteinseite
und, wenn er eine Grundform zeigt, in GRUNDFORMEN. Diese Prüfung liest die eine Liste aus dem Kopfkommentar von
engine/vorlage.html und gleicht die anderen Stellen damit ab (Abgleich 29.10.2026, docs/abgleich-2026-10-29.md)."""
import re
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[2]
VORLAGE = (WURZEL / "engine/vorlage.html").read_text(encoding="utf-8")
DESIGN = (WURZEL / "docs/design.md").read_text(encoding="utf-8")
EBENEN = ("Atome", "Moleküle", "Organismen", "Vorlagen")


def bausteine():
    """-> {Ebene: [Name]} aus dem Kopfkommentar „Bausteine nach Ebenen“; Einträge mit Klammer (etikett (CSS)) sind kein Skript."""
    kopf = VORLAGE[VORLAGE.index("/* Bausteine nach Ebenen"):VORLAGE.index("   Regeln: docs/adr/0002-atomic-design.md")]
    aus = {}
    for ebene in EBENEN:
        zeile = re.search(rf"^\s*{ebene}: (.*)$", kopf, flags=re.M).group(1)
        aus[ebene] = [n.strip() for n in zeile.split(",") if "(" not in n]
    return aus


def skript():
    return VORLAGE[VORLAGE.index("<script>"):VORLAGE.rindex("</script>")]


def test_jeder_baustein_ist_eine_funktion_der_vorlage():
    js = skript()
    fehlt = [n for l in bausteine().values() for n in l if not re.search(rf"(?m)^(?:function {n}\(|const {n} = )", js)]
    assert fehlt == [], fehlt


def test_jeder_baustein_steht_in_design_md_und_umgekehrt():
    namen = {n for l in bausteine().values() for n in l}
    tabelle = DESIGN[DESIGN.index("| Ebene | Bausteine"):DESIGN.index("## Ontologie und Bausteine")]
    im_doku = set(re.findall(r"`([a-zA-Z]+)`", tabelle)) - {"etikett"}
    assert namen - im_doku == set(), sorted(namen - im_doku)
    # In der Tabelle der Ebenen stehen nur Bausteine (Tokens stehen in der Zeile Tokens, kein Skript)
    fremd = {n for n in im_doku if n not in namen and not n.startswith("--")}
    assert fremd == set(), sorted(fremd)
    # und auf derselben Ebene
    for ebene, liste in bausteine().items():
        zeile = re.search(rf"^\| {ebene[:-1] if ebene != 'Vorlagen' else 'Vorlagen'}[^|]*\| (.*)\|$", tabelle, flags=re.M)
        assert zeile, ebene
        in_zeile = set(re.findall(r"`([a-zA-Z]+)`", zeile.group(1)))
        assert set(liste) - in_zeile == set(), (ebene, sorted(set(liste) - in_zeile))


def test_bausteinseite_zeichnet_jeden_baustein():
    """Atome, Moleküle und Organismen werden auf #bausteine mit ihrer Funktion gezeichnet; Vorlagen sind ganze Ansichten
    oder Formulare und zeichnen sich nicht auf einer anderen Seite (tagKachel und leseAbschnitt ausgenommen)."""
    js = skript()
    start = js.index("function ansichtBausteine(")
    ende = js.index("\nfunction ", start + 10)
    seite = js[start:ende]
    pflicht = [n for ebene, l in bausteine().items() for n in l if ebene != "Vorlagen" or n in ("tagKachel",)]
    fehlt = [n for n in pflicht if n + "(" not in seite]
    assert fehlt == [], fehlt


def test_grundformen_nennen_nur_bausteine_der_liste():
    namen = {n for l in bausteine().values() for n in l}
    js = skript()
    block = js[js.index("const GRUNDFORMEN = ["):js.index("];", js.index("const GRUNDFORMEN = ["))]
    genannt = set(re.findall(r"\[([a-zA-Z, ]+)\]", block))
    genannt = {x.strip() for g in genannt for x in g.split(",") if x.strip()}
    assert genannt - namen == set(), sorted(genannt - namen)
    # und die Tabelle in docs/design.md nennt dieselben Grundformen (Kennungen) wie der Code
    kennungen_code = re.findall(r'^\s*\["\w+", "[^"]+", "([^"]+)"', block, flags=re.M)
    tabelle = DESIGN[DESIGN.index("| Grundform | Kennung |"):DESIGN.index("Dichten:")]
    kennungen_doku = [z.split("|")[2].strip() for z in tabelle.splitlines() if z.startswith("| ") and not z.startswith("| Grundform")]
    assert kennungen_doku == kennungen_code, (kennungen_doku, kennungen_code)


def test_keine_art_der_reise_in_der_vorlage():
    """ADR-0001, Frage 2: Die Seite kennt keine Art einer Reise (bis 29.10.2026 stand „wandern“ an sieben Stellen);
    Bewegungen aus eigener Kraft erkennt sie am Merkmal summiert der Art."""
    js = re.sub(r"//[^\n]*", "", skript())
    for wort in ('"wandern"', '"bahn"', '"flug"', '"faehre"', '"hotel"', '"refugi"', '"preis"', '"fruehstueck"'):
        assert wort not in js, wort


def test_radien_und_schatten_aus_tokens():
    """ADR-0002, Punkt 4: Radien und Schatten kommen aus Tokens. Ausnahmen: die Karte (Leaflet, px), das Rückmeldefenster
    (abgerundet nur oben), die Leiste unten (Rahmen) und runde Formen (50 %)."""
    css = VORLAGE[VORLAGE.index("<style>"):VORLAGE.index("</style>")]
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    frei = []
    for sel, inhalt in re.findall(r"([^{}]*)\{([^{}]*)\}", css):
        if "leaflet" in sel or ".rh-" in sel or "dialog#rm" in sel or re.search(r"(^|[\s,>])(nav|\.leiste|\.glas|\.hinweis)(\b|$)", sel) or "a.kp" in sel:
            continue
        for wert in re.findall(r"border-radius:\s*([^;]+)", inhalt):
            if "var(--r" in wert or wert.strip() in ("50%", "0", "4px", "3px", "6px", "10px"):   # kleine Rundungen an Feldern, Bildern, Marken
                continue
            frei.append(f"{sel.strip()[-50:]}: border-radius {wert}")
        for wert in re.findall(r"box-shadow:\s*([^;]+)", inhalt):
            if "var(--schatten" in wert or wert.strip() in ("none",) or "inset" in wert or "0 0 0" in wert or "1px 0 0 var(--line)" in wert:   # Linie als Schatten
                continue
            frei.append(f"{sel.strip()[-50:]}: box-shadow {wert}")
    assert frei == [], frei


def test_konnektor_md_nennt_jedes_werkzeug():
    """ADR-0001, Frage 4 und 10: Jedes Werkzeug, das der Konnektor anbietet, steht in docs/konnektor.md; was dort als Werkzeug
    steht, gibt es im Code (person_schreiben ist intern, ein Werkzeug des Schreibwegs)."""
    import sys
    sys.path.insert(0, str(WURZEL / "engine"))
    import konnektor as kn
    im_code = {w["name"] for w in kn.WERKZEUGE}
    for name, wert in vars(kn).items():
        if isinstance(wert, dict) and "name" in wert and "inputSchema" in wert:
            im_code.add(wert["name"])
    im_code |= {"meine_reisen", "reise_anlegen", "reisen_anlegen_anfragen", "anfrage_entscheiden"}
    doku = (WURZEL / "docs/konnektor.md").read_text(encoding="utf-8")
    fehlt = sorted(n for n in im_code if f"`{n}`" not in doku)
    assert fehlt == [], fehlt
    # Werkzeuge des Schreibwegs, die der Konnektor anbietet, sind vollständig registriert
    import schreiben as sb
    assert set(sb.WERKZEUGE) - {"person_schreiben"} == set(kn.ONTOLOGIE_WERKZEUGE) - {"entscheiden", "tag_aendern"} | (set(sb.WERKZEUGE) & {"entscheiden", "tag_aendern"}) - {"person_schreiben"}
    assert set(kn.ONTOLOGIE_WERKZEUGE) <= set(sb.WERKZEUGE) and set(kn.ONTOLOGIE_WERKZEUGE) == set(kn.ONTOLOGIE_AKTION)


def test_kein_katalog_in_der_engine():
    """ADR-0001, Frage 2: Die Software führt keine Art und kein Merkmal ein und setzt keines voraus. Kein Modul in engine/
    nimmt eine Art als Vorgabe („wandern“) oder fragt nach einem Merkmalnamen einer Reise; engine/neu.py nachziehen ist die
    Ausnahme (Migration eines Bestands), vendor/ und tests/ zählen nicht."""
    verboten = (re.compile(r'(?:get\("art",|\bor|\bin\s*\(|==|!=)\s*"(?:wandern|hotel|refugi|bahn|bus|flug|faehre)"'),
                re.compile(r'\.get\("(?:fruehstueck|geoeffnet|abendessen|gehzeit)"\)'))   # preis ist ein Feld der Grundform Buchung
    funde = []
    for pfad in sorted((WURZEL / "engine").glob("*.py")):
        if pfad.name == "neu.py":
            continue
        for nr, zeile in enumerate(pfad.read_text(encoding="utf-8").splitlines(), 1):
            code = zeile.split("#")[0]
            if any(m.search(code) for m in verboten):
                funde.append(f"{pfad.name}:{nr}: {zeile.strip()[:100]}")
    assert funde == [], funde


def test_gedrueckt_ist_tinte_nicht_akzent():
    """#38: Ein gedrückter Knopf ist keine Entscheidung (Regel 4 in docs/design.md: Akzentgrün heißt entschieden). Kein
    Stil für aria-pressed nimmt den Akzent; Vergleich und Darstellung im Wahl-Modul und die Regionen der Karte sind
    der Baustein umschalter, nicht eigene Knopfleisten."""
    css = VORLAGE[VORLAGE.index("<style>"):VORLAGE.index("</style>")]
    gedrueckt = [inhalt for sel, inhalt in re.findall(r"([^{}]*)\{([^{}]*)\}", css) if 'aria-pressed="true"' in sel]
    assert gedrueckt and not [x for x in gedrueckt if "--acc" in x], gedrueckt
    js = skript()
    # Die Titel kommen aus dem Katalog (ADR-0006)
    for titel, klasse in (("seite.vergleich.moeglichkeiten", "wm-wahl"), ("seite.vergleich.darstellung", "wm-ansicht"), ("seite.karte.region", "regionen")):
        assert re.search(rf'umschalter\(T\("{titel}"\),.{{0,300}}?"{klasse}"\)', js, flags=re.S), klasse
    assert 'el("fieldset", {class: "wm-' not in js and 'el("div", {class: "regionen"' not in js
