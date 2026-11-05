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
    oder Formulare und zeichnen sich nicht auf einer anderen Seite (tagKachel ausgenommen)."""
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


def _funktion(name):
    """Rumpf einer Funktion der Vorlage (vom Kopf bis zur schließenden Klammer am Zeilenanfang)."""
    m = re.search(rf"^function {name}\(.*?^\}}", skript(), re.S | re.M)
    assert m, name
    return m.group(0)


def test_vorlage_ohne_eigene_tagessumme_und_summiert_nur_von_strecke():
    """#268, AC-6/AC-7: Kennzahlen rechnet nur das Routenmodell. Die Vorlage hat keine eigene Tagessumme (tagKm, tagMin),
    entscheidet „hat Kennzahlen“ über summe.mit_kennzahlen und „summiert“ über strecke.summiert; die Kartenlegende bleibt
    auf der Ebene der Art. Höhenmeter-Texte kommen aus dem Katalog."""
    js = skript()
    assert "tagKm" not in js and "tagMin" not in js
    assert "s.min || s.km || s.auf" not in js
    for name in ("summeText", "steckbrief", "reiseKennzahlen"):
        assert "mit_kennzahlen" in _funktion(name), name
    for name in ("streckeZeile", "wegVerlauf"):
        assert not re.search(r"artDef\([^)]*\)[^;]{0,20}\.summiert", _funktion(name)), name
    summiert = re.search(r"^const summiertArt = .*$", js, re.M)
    assert summiert and "artDef" not in summiert.group(0) and ".summiert" in summiert.group(0)
    assert "↑ ${v} m" not in js and "↓ ${v} m" not in js
    routen = (WURZEL / "engine/routen.py").read_text(encoding="utf-8")
    assert 'f"↑ {' not in routen and "↓ {s['ab']" not in routen


def _rumpfe():
    """-> Wörterbuch Name -> Rumpf ohne Kommentare, für jede Funktion und Konstante der Vorlage auf oberster Ebene."""
    js = skript()
    starts = [(m.start(), m.group(1) or m.group(2)) for m in re.finditer(r"(?m)^(?:function (\w+)\(|const (\w+) = )", js)]
    aus = {}
    for i, (anfang, name) in enumerate(starts):
        text = js[anfang:starts[i + 1][0] if i + 1 < len(starts) else len(js)]
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
        aus[name] = re.sub(r"(?m)(^|\s)//.*$", "", text)
    return aus


def test_kein_baustein_ruft_einen_baustein_hoeherer_ebene_auf():
    """ADR-0002, Punkt 1 (#332, Schritt A): Ein Baustein nutzt nur Bausteine derselben oder einer tieferen Ebene.
    Atome < Moleküle < Organismen < Vorlagen; geprüft wird der Rumpf jedes Bausteins ohne Kommentare."""
    rang = {n: i for i, e in enumerate(EBENEN) for n in bausteine()[e]}
    rumpf = _rumpfe()
    verstoesse = [f"{EBENEN[rang[n]]} {n} -> {EBENEN[rang[m]]} {m}" for n in rang if n in rumpf for m in rang
                  if rang[m] > rang[n] and re.search(rf"\b{m}\b", rumpf[n])]
    assert verstoesse == [], verstoesse


# Zeichner mit eigenen Klassen, die weder im Inventar stehen noch zu den Ansichten gehören (Bestand 5.11.2026, #332).
# Ein Zeichner kommt ins Inventar (Kopfkommentar, Stile, Bausteinseite, docs/design.md) oder wird auf einen Baustein
# zurückgeführt; die Liste darf nur kürzer werden (Muster test_texte.py).
EIGENE_FLAECHEN = {
    "abschnittInhalt", "aenderungenZeigen", "ansichtEtappen", "ansichtGruppe", "ansichtRueckmeldungen", "ansichtSuche",
    "ansichtVarianten", "artTabelle", "chips", "dingMarke", "etappeTeil",
    "etappenKarte", "festeTermine", "fuerDich", "heuteBlock", "jetztSenden", "kalenderChip",
    "karteZeichnen", "listenTitel", "naechsteFristen", "ontologieTabelle", "optionVerlauf", "ortChips",
    "ortKarte", "punktPopup", "regelZeilen", "releaseFuss", "tagKopf",
    "vergleichTabelle", "warnungen", "wegKurz", "wissenKarte", "wissenPopup",
    "zeigeReiter",
}


def test_dichte_ist_eine_regel_und_heimat_hat_keine_fallunterscheidung_je_grundform():
    """#332, Schritt B (ADR-0007, Punkt 2): Eine Funktion zeigt ein Ding in einer Dichte und wählt den Baustein nach der Grundform;
    jede Grundform mit eigener Karte steht in GRUNDFORMEN mit ihr (auch Bewegung, Ort, Buchung, Frage, Aufgabe). heimat() ist
    die Regel „Seite des Elternelements“ und fragt die Vorgabe je Grundform in vorgabeEltern ab."""
    js = skript()
    block = js[js.index("const GRUNDFORMEN = ["):js.index("];", js.index("const GRUNDFORMEN = ["))]
    for kennung in ("etappe", "ort", "buchung", "frage", "aufgabe"):
        zeile = re.search(rf'\["{kennung}",.*', block).group(0)
        assert "karte: [dingKurzKarte]" in zeile, kennung
    heimat = _funktion("heimat")
    assert "vorgabeEltern(" in heimat and "seiteVon(" in heimat
    assert not re.search(r"R\.(unterkuenfte|aufenthalte|buchungen|strecken)\[id\]", heimat), "heimat() liest keine Grundform, die Vorgabe tut es"
    for stelle in ("wahlAmElement", "aufenthalteAmElement", "uebersichtAmElement"):
        assert stelle not in js, stelle   # eine Stelle (amElement) wählt die Dichte nach dem Abstand
    assert "dichteHier(" in _funktion("amElement") and "zeigeDing(" in _funktion("amElement")


def test_tiefenregel_option_zeigt_tage_nie_als_karte_und_ein_kreis_endet_sichtbar():
    """#332, Schritt C (ADR-0003, Nachtrag Tiefe): Ein Ding steht höchstens zwei Ebenen tief voll (Seite, Karte); was in einer
    Karte steckt, ist eine Zeile mit Link. Eine Option zeigt ihre Tage nie als Karte (nur tagZeile), und eine zu lange Kette von
    Elternbezügen oder ein Kreis endet sichtbar ({kreis: true} mit Hinweis im Router), nicht still mit null."""
    for name in ("optionBlock", "optionEinzelheiten"):
        assert not re.search(r"\b(tagKarte|tagesKarte|tagKachel)\b", _funktion(name)), name
    assert "tagZeile(" in _funktion("optionBlock")
    heimat = _funktion("heimat")
    assert "HEIMAT_TIEFE" in heimat and "kreis: true" in heimat
    assert not re.search(r"tiefe\s*>\s*\d", heimat), "die Grenze heißt HEIMAT_TIEFE"
    assert "x.kreis" in skript() and "seite.kreis.hinweis" in skript()


def test_eigene_flaechen_ausserhalb_des_inventars_werden_nur_weniger():
    """ADR-0002 nennt eine Fläche mit eigenen Klassen neben den Bausteinen einen Fehler (#332, Schritt A): Wer Klassen
    zeichnet, steht im Inventar oder auf EIGENE_FLAECHEN. Ist ein Eintrag erledigt, muss er von der Liste."""
    inventar = {n for l in bausteine().values() for n in l}
    frei = {n for n, text in _rumpfe().items() if n not in inventar and re.search(r"\bclass: ", text)}
    assert frei - EIGENE_FLAECHEN == set(), f"neuer Zeichner mit eigenen Klassen, ins Inventar aufnehmen: {sorted(frei - EIGENE_FLAECHEN)}"
    assert EIGENE_FLAECHEN - frei == set(), f"erledigt, von EIGENE_FLAECHEN streichen: {sorted(EIGENE_FLAECHEN - frei)}"


# Seitenraster (#332, Schritt D; ADR-0002, Nachtrag): Hier folgt das Layout dem Fenster, weil es die Seite aufteilt (Ränder, Spalten,
# Navigation) und nicht ein Baustein, der überall stehen kann. Alle Organismen richten sich nach der Breite ihres Behälters
# (@container), das Zeigergerät (pointer, hover) bleibt eine Media-Query. Die Liste darf nur kürzer werden.
RASTER_BREITEN = {
    "details:not([open])>summary .zid-box,.vorschau .zid-box",   # Sprechblase unterwegs (Handy und Tablet) ausgeblendet
    ".ebene-unterwegs",                                          # gleicht den Rand von main aus
    ".achse .tagzeile",                                          # Zeitachse in der rechten Spalte des Seitenrasters
    "dialog#rm", ".reise-seite", ".tagseite", "nav a,#suchKnopf", ":root",
}


def test_breiten_media_queries_nur_fuers_seitenraster():
    css = VORLAGE[:VORLAGE.index("<script>")]
    benutzt = {m.group(2).strip() for m in re.finditer(r"@media\s*([^{]*(?:min|max)-width[^{]*)\{\s*(?:/\*.*?\*/\s*)?([^{}]*)\{", css, re.S)}
    assert benutzt - RASTER_BREITEN == set(), f"Breite im Organismus: @container statt @media verwenden: {sorted(benutzt - RASTER_BREITEN)}"
    assert RASTER_BREITEN - benutzt == set(), f"erledigt, von RASTER_BREITEN streichen: {sorted(RASTER_BREITEN - benutzt)}"
    assert not re.search(r"matchMedia\(\s*[\"'`][^\"'`]*(?:min|max)-width", skript()), "Breite im Skript: die Breite des Behälters messen"


def test_container_haben_namen_und_jede_anfrage_ihren_behaelter():
    """Eine unbenannte Anfrage träfe den nächsten Behälter, wer er auch sei; deshalb haben alle Behälter einen Namen."""
    css = VORLAGE[:VORLAGE.index("<script>")]
    behaelter = set(re.findall(r"container:\s*([a-z]+)\s*/\s*inline-size", css))
    assert not re.search(r"container-type\s*:", css), "benannt schreiben: container: name / inline-size"
    anfragen = set(re.findall(r"@container\s+([a-z]+)\s*\(", css))
    assert not re.search(r"@container\s*\(", css), "@container ohne Namen"
    assert anfragen <= behaelter, sorted(anfragen - behaelter)
