"""#269 (Teil von #215): Etappe ist eine Strecke einer Art mit summiert: true, kein Typ der Software
(Spec docs/specs/oberflaeche/etappe-als-art-269.md). Nur erfundene Daten: die beiden Beispielreisen."""
import json
import re
import shutil
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bauen  # noqa: E402
import neu  # noqa: E402
import routen  # noqa: E402
import texte_de  # noqa: E402
import texte_en  # noqa: E402

WURZEL = Path(__file__).resolve().parent.parent.parent
BEISPIELE = WURZEL / "beispiel" / "reisen"
KENNUNGEN = {"gehzeit", "aufstieg", "abstieg", "laenge"}
# Werte der Beispielreise vor der Umstellung (Eckdaten des Etappen-Dossiers): Minuten, Aufstieg, Abstieg, km
VORHER = {"E-01": (220, 485, 285, 8.1), "E-02": (240, 400, 390, 10.7), "E-03": (150, 200, 400, 7.4), "E-04": (135, 190, 350, 6.6)}


def kopie(name, tmp_path):
    ziel = tmp_path / name
    shutil.copytree(BEISPIELE / name, ziel)
    return ziel


def katalog(modul):
    return next(v for v in vars(modul).values() if isinstance(v, dict) and "pruefung.reise.20" in v)


def dateien(r):
    return {str(f): f.read_bytes() for f in r.rglob("*") if f.is_file()}


def strecken(reise, tmp_path):
    d = bauen.Bauer(reise, tmp_path / "dist").daten()
    return d, d["route"]["strecken"]


def test_1_strecken_tragen_titel_und_kennzahlen_mit_kennungen(tmp_path):
    """Test 1 / K1: jede wandern-Strecke hat Titel und Kennzahlen; kein Abschnitt vom Typ etappe mehr."""
    d, s = strecken(BEISPIELE / "beispielreise", tmp_path)
    for eid, (minuten, auf, ab, km) in VORHER.items():
        st = s[eid]
        assert st.get("titel")
        k = st["kennzahlen"]
        assert KENNUNGEN <= set(k), (eid, k)
        assert routen.minuten(k["gehzeit"]) == minuten and routen.zahl(k["aufstieg"]) == auf
        assert routen.zahl(k["abstieg"]) == ab and routen.zahl(k["laenge"]) == km
    assert not [a for a in d["abschnitte"] if a.get("typ") == "etappe"]
    assert not [x for x in s.values() if x.get("typ") == "etappe"]


def test_2_nachziehen_stellt_beispielreise_um_und_ist_idempotent(tmp_path):
    """Test 2 / K4: Altformat (Dossier „Etappe N: Name“, etappen_kennzahlen) wird ohne Handschritt umgestellt."""
    r = kopie("beispielreise", tmp_path)
    p = r / "plan/routen.yaml"
    alt_kz = {e: s["kennzahlen"] for e, s in yaml.safe_load(p.read_text(encoding="utf-8"))["strecken"].items() if e in VORHER}
    t = re.sub(r", kennzahlen: \{[^}]*\}", "", p.read_text(encoding="utf-8"))
    p.write_text(re.sub(r"(E-0[1-4]: \{)titel: \"[^\"]*\", ", r"\1", t), encoding="utf-8")
    dossier = r / "inhalt/etappen.md"
    t = dossier.read_text(encoding="utf-8")
    namen = {"gehzeit": "Gehzeit", "aufstieg": "Aufstieg (Hm)", "abstieg": "Abstieg (Hm)", "laenge": "Länge (km)"}
    for n in range(1, 5):
        # Altformat: Titel in der Überschrift, die Kennzahlen als Zeilen der Eckdaten-Tabelle (seit F001 nimmt nachziehen sie heraus)
        zeilen = "".join(f"| {namen[k]} | {v} |\n" for k, v in alt_kz[f"E-0{n}"].items())
        t = re.sub(rf"^## E-0{n} (.+?)$(.*?### Eckdaten\n\| Merkmal \| Wert \|\n\|---\|---\|\n)", lambda m: f"## Etappe {n}: {m.group(1)}{m.group(2)}{zeilen}",
                   t, count=1, flags=re.M | re.S)
    assert t.count("| Aufstieg (Hm) |") == 4
    dossier.write_text(t, encoding="utf-8")
    cfg = json.loads((r / "reise.json").read_text(encoding="utf-8"))
    cfg["etappen_kennzahlen"] = ["Gehzeit", "Aufstieg (Hm)", "Abstieg (Hm)", "Länge (km)"]
    cfg["etappen_muster"] = r"^Etappe\s+(\d+[a-z]?):\s*(.+)$"
    (r / "reise.json").write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    neu.nachziehen(r)
    _, s = strecken(r, tmp_path)
    for eid in VORHER:
        assert s[eid].get("titel") and KENNUNGEN <= set(s[eid]["kennzahlen"]), eid
    neue = json.loads((r / "reise.json").read_text(encoding="utf-8"))
    assert "etappen_kennzahlen" not in neue and "etappen_muster" not in neue
    # F001: die Kennzahl-Zeilen verlassen die Eckdaten (ein Wert steht einmal), alle anderen Zeilen bleiben; Ergebnis wie eingecheckt
    assert dossier.read_text(encoding="utf-8") == (BEISPIELE / "beispielreise/inhalt/etappen.md").read_text(encoding="utf-8")
    assert {e: x["kennzahlen"] for e, x in s.items() if e in VORHER} == alt_kz
    vorher = dateien(r)
    assert neu.nachziehen(r) == []
    assert dateien(r) == vorher


def test_3_stadtwochenende_bleibt_unveraendert(tmp_path):
    """Test 3 / K3: ohne Etappen ändert nachziehen nichts, der Bau meldet nichts, keine Etappenstrecke."""
    r = kopie("stadtwochenende", tmp_path)
    vorher = dateien(r)
    assert neu.nachziehen(r) == []
    assert dateien(r) == vorher
    d, s = strecken(r, tmp_path)
    assert not [a for a in d["abschnitte"] if a.get("typ") == "etappe"]
    assert not [x for x in s.values() if x.get("kennzahlen")]


def test_4_andere_summierte_art_ist_etappe(tmp_path):
    """Test 4 / K5: die Reise nennt ihre Art frei; summiert entscheidet, nicht der Name wandern."""
    r = kopie("beispielreise", tmp_path)
    a, p = r / "plan/arten.yaml", r / "plan/routen.yaml"
    a.write_text(a.read_text(encoding="utf-8").replace("\n  wandern:\n", "\n  spaziergang:\n"), encoding="utf-8")   # Symbol bleibt wandern
    p.write_text(p.read_text(encoding="utf-8").replace("art: wandern", "art: spaziergang"), encoding="utf-8")
    d, s = strecken(r, tmp_path)
    arten = d["route"]["arten"]
    summiert = sorted(k for k, v in s.items() if arten[v["art"]].get("summiert"))
    assert summiert == sorted(VORHER)
    assert all(not arten[v["art"]].get("summiert") for v in s.values() if v["art"] == "bahn")


def test_5_vorlage_ohne_namenssuche_und_typ_etappe():
    """Test 5 / K2: die Seite kennt weder Kennzahlnamen noch den Typ etappe; der Bau kein etappen_muster."""
    q = (WURZEL / "engine/vorlage.html").read_text(encoding="utf-8")
    for s in ("REGEL.gehzeit", "REGEL.aufstieg", "REGEL.abstieg", "REGEL.laenge", "kennzahlPaar", 'typ === "etappe"'):
        assert s not in q, s
    assert "etappen_muster" not in (WURZEL / "engine/bauen.py").read_text(encoding="utf-8")


def test_6_kennwerte_liest_kennungen():
    """Test 6: Summen aus Kennungen; Namen in Landessprache werden nicht mehr gesucht."""
    k = routen.kennwerte({"gehzeit": "3:30", "aufstieg": 380, "abstieg": 220, "laenge": 11.5})
    assert k == {"min": 210, "auf": 380, "ab": 220, "km": 11.5}
    assert routen.kennwerte({"Gehzeit": "3:30", "Aufstieg (Hm)": 380}) == {"min": None, "auf": None, "ab": None, "km": None}


def test_7_dossier_abschnitt_ohne_strecke_bricht_ab(tmp_path):
    """Test 7: ein Abschnitt mit unbekannter ID wird gemeldet, nicht still ignoriert (Text aus dem Katalog)."""
    r = kopie("beispielreise", tmp_path)
    d = r / "inhalt/etappen.md"
    d.write_text(d.read_text(encoding="utf-8") + "\n## E-99 Gibt es nicht\n\n### Zusammenfassung\nText.\n", encoding="utf-8")
    with pytest.raises(bauen.BauFehler) as e:
        bauen.Bauer(r, tmp_path / "dist").daten()
    assert "E-99" in "\n".join(e.value.meldungen)
    assert "pruefung.bauen.dossier_ohne_strecke" in katalog(texte_de)   # eigene Meldung, nicht die allgemeine „Abschnitt ohne ID“


def test_8_angaben_fehlen_im_katalog_aller_sprachen():
    """Test 8 / K7: der Text „Angaben fehlen“ am Tag mit summierter Strecke ohne Gehzeit steht in jeder Sprache und in der Seite."""
    for m in (texte_de, texte_en):
        assert "seite.tag.angaben_fehlen" in katalog(m)
    assert "seite.tag.angaben_fehlen" in (WURZEL / "engine/vorlage.html").read_text(encoding="utf-8")


def test_9_neue_schluessel_der_meldung_in_jeder_sprache():
    """Test 9: die neue Meldung „Dossier-Abschnitt ohne Strecke“ gibt es in jeder Sprache."""
    for m in (texte_de, texte_en):
        assert "pruefung.bauen.dossier_ohne_strecke" in katalog(m)


# ---------- Befunde des Adversary (docs/artifacts/etappe-als-art-269/adversary-dialog.md) ----------

def test_f001_eckdaten_ohne_kennzahl_zeilen_und_seite_filtert_nicht_nach_wert(tmp_path):
    """F001: Die Kennzahl-Zeilen stehen nach nachziehen nicht mehr in den Eckdaten (Test 2); die Seite blendet eine Zeile nur nach
    ihrem Merkmal aus, nie nach dem Wert: „Rastplätze | 400“ bleibt neben Aufstieg 400 stehen."""
    from test_seite_sprachen import PLAYWRIGHT, ausdruecke
    t = (BEISPIELE / "beispielreise/inhalt/etappen.md").read_text(encoding="utf-8")
    assert "\n| Aufstieg (Hm) |" not in t and "\n| Gehzeit |" not in t and "\n| Höchster Punkt |" in t
    q = (WURZEL / "engine/vorlage.html").read_text(encoding="utf-8")
    rt = q[q.index("function reiseText("):q.index("function einmal(")]
    assert "Object.values(kennzahlen" not in rt and '"dd"' not in rt
    if not PLAYWRIGHT.exists() or not shutil.which("node"):
        pytest.skip("Playwright fehlt")
    r = kopie("beispielreise", tmp_path)
    d = r / "inhalt/etappen.md"
    d.write_text(d.read_text(encoding="utf-8").replace("| Höchster Punkt | Waitzdorf", "| Rastplätze | 400 |\n| Höchster Punkt | Waitzdorf"),
                 encoding="utf-8")
    bauen.bauen(r, tmp_path / "web" / "reise")
    dt = ausdruecke(tmp_path / "web", ['JSON.stringify([...etappeTeil(proId.get("E-02")).querySelectorAll("dl.textmerkmale dt")].map(x => x.textContent))'])
    assert json.loads(dt[0]) == ["Rastplätze", "Höchster Punkt", "Herkunft"]


def test_f002_kennzahlen_unter_namen_in_routen_yaml_bekommen_kennungen(tmp_path):
    """F002: Trug eine Strecke ihre Kennzahlen schon in routen.yaml unter Namen (der Altstand las sie vor dem Dossier), stellt
    nachziehen die Schlüssel auf Kennungen um; Summen wie im Altstand (P-A 910 min, 45,5 km), eigene Namen bleiben; zweiter Lauf leer."""
    r = kopie("beispielreise", tmp_path)
    p = r / "plan/routen.yaml"
    p.write_text(p.read_text(encoding="utf-8").replace('kennzahlen: {gehzeit: "ca. 4:00 h", aufstieg: 400, abstieg: 390, laenge: "10,7 km"}',
                                                       'kennzahlen: {Gehzeit: 9:00 h, "Länge (km)": "30 km", Rastplätze: 3}'), encoding="utf-8")
    m = neu.nachziehen(r)
    assert any(x.startswith("E-02:") and "Gehzeit" in x for x in m), m
    d, s = strecken(r, tmp_path)
    assert s["E-02"]["kennzahlen"] == {"gehzeit": "9:00 h", "laenge": "30 km", "Rastplätze": 3}
    summe = next(x for x in d["route"]["plaene"] if x["id"] == "P-A")["summe"]
    assert (summe["min"], summe["km"], summe["fehlend"]) == (910, 45.5, ["ab", "auf"])
    assert 'gehzeit: "9:00 h"' in p.read_text(encoding="utf-8")   # in Anführungszeichen (F008)
    vorher = dateien(r)
    assert neu.nachziehen(r) == [] and dateien(r) == vorher


def test_f003_doppelte_etappennummer_wird_offen_gemeldet(tmp_path):
    """F003: Zwei Überschriften „Etappe 1: …“ sind nicht eindeutig: nachziehen meldet OFFEN (Katalog, jede Sprache), schreibt sie
    nicht um und behält die Einstellungen in reise.json."""
    r = kopie("beispielreise", tmp_path)
    d = r / "inhalt/etappen.md"
    d.write_text(d.read_text(encoding="utf-8").replace("## E-01 ", "## Etappe 1: ") + "\n## Etappe 1: Doppelt\nText.\n", encoding="utf-8")
    cfg = json.loads((r / "reise.json").read_text(encoding="utf-8"))
    cfg["etappen_kennzahlen"] = ["Gehzeit"]
    (r / "reise.json").write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
    m = neu.nachziehen(r)
    assert any(x.startswith("OFFEN E-01") for x in m), m
    assert all("pruefung.neu.nachziehen.etappe_doppelt" in katalog(x) for x in (texte_de, texte_en))
    assert d.read_text(encoding="utf-8").count("## Etappe 1: ") == 2
    assert "etappen_kennzahlen" in json.loads((r / "reise.json").read_text(encoding="utf-8"))


def test_f008_gehzeit_ohne_anfuehrungszeichen_wird_gemeldet(tmp_path):
    """F008: „gehzeit: 4:00“ ohne Anführungszeichen liest YAML als Zahl 240 (stille Fehlsumme): der Bau lehnt es mit Meldung ab."""
    r = kopie("beispielreise", tmp_path)
    p = r / "plan/routen.yaml"
    p.write_text(p.read_text(encoding="utf-8").replace('gehzeit: "ca. 4:00 h"', "gehzeit: 4:00"), encoding="utf-8")
    with pytest.raises(bauen.BauFehler) as e:
        bauen.Bauer(r, tmp_path / "dist").daten()
    assert "E-02" in "\n".join(e.value.meldungen)
    assert all("pruefung.routen.kennzahlen_gehzeit" in katalog(x) for x in (texte_de, texte_en))


E01_KZ = 'kennzahlen: {gehzeit: "ca. 3:40 h", aufstieg: 485, abstieg: 285, laenge: "8,1 km"}'
E01_ZEILEN = "| Gehzeit | ca. 3:40 h |\n| Aufstieg (Hm) | 485 |\n| Abstieg (Hm) | 285 |\n| Länge (km) | 8,1 km |\n"


def altform(r, zeilen=E01_ZEILEN, namen=("Gehzeit", "Aufstieg (Hm)", "Abstieg (Hm)", "Länge (km)"), kz=None, nur=False):
    """Etappe 1 der Beispielreise im Altformat: Überschrift „Etappe 1: …“, Kennzahl-Zeilen in den Eckdaten, etappen_kennzahlen;
    kz ersetzt die Kennzahlen der Strecke E-01 in routen.yaml (None: keine), nur: Eckdaten bestehen nur aus diesen Zeilen."""
    p = r / "plan/routen.yaml"
    p.write_text(p.read_text(encoding="utf-8").replace(E01_KZ + ", ", f"kennzahlen: {kz}, " if kz else ""), encoding="utf-8")
    d = r / "inhalt/etappen.md"
    t = d.read_text(encoding="utf-8").replace("## E-01 ", "## Etappe 1: ")
    kopf = "### Eckdaten\n| Merkmal | Wert |\n|---|---|\n"
    if nur:
        t = re.sub(r"(### Eckdaten\n\| Merkmal \| Wert \|\n\|---\|---\|\n)(?:\|.*\n)+", lambda m: m.group(1), t, count=1)
    d.write_text(t.replace(kopf, kopf + zeilen, 1), encoding="utf-8")
    cfg = json.loads((r / "reise.json").read_text(encoding="utf-8"))
    cfg["etappen_kennzahlen"] = list(namen)
    (r / "reise.json").write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
    return d


def plan_kz(r, sid="E-01"):
    return yaml.safe_load((r / "plan/routen.yaml").read_text(encoding="utf-8"))["strecken"][sid]["kennzahlen"]


def einstellungen(r):
    return json.loads((r / "reise.json").read_text(encoding="utf-8"))


def test_f101_vorhandene_teil_kennzahlen_werden_ergaenzt_nicht_ueberschrieben(tmp_path):
    """F101: Hat die Strecke nur gehzeit (gleicher Wert), kommen die drei fehlenden Kennungen dazu und alle Zeilen verlassen das
    Dossier; hat sie einen anderen Wert, bleibt dieser, die Zeile bleibt stehen, OFFEN-Meldung, die Einstellungen bleiben."""
    r = kopie("beispielreise", tmp_path / "a")
    d = altform(r, kz='{gehzeit: "ca. 3:40 h"}')
    m = neu.nachziehen(r)
    _, s = strecken(r, tmp_path / "a")
    assert s["E-01"]["kennzahlen"] == {"gehzeit": "ca. 3:40 h", "aufstieg": 485, "abstieg": 285, "laenge": "8,1 km"}
    assert d.read_text(encoding="utf-8") == (BEISPIELE / "beispielreise/inhalt/etappen.md").read_text(encoding="utf-8")
    assert "etappen_kennzahlen" not in einstellungen(r) and not [x for x in m if x.startswith("OFFEN")]
    assert any(x.startswith("E-01:") and "aufstieg" in x and "titel" not in x for x in m), m   # die Meldung sagt, was kam
    r = kopie("beispielreise", tmp_path / "b")
    d = altform(r, kz='{gehzeit: "ca. 5:00 h"}')
    m = neu.nachziehen(r)
    assert any(x.startswith("OFFEN E-01") and "ca. 5:00 h" in x and "ca. 3:40 h" in x for x in m), m
    assert plan_kz(r)["gehzeit"] == "ca. 5:00 h"   # es gilt der Wert an der Strecke (#357)
    t = d.read_text(encoding="utf-8")
    # die abweichende Zeile bleibt als Text stehen, die Überschrift bekommt ihre Kennung, nichts bleibt für die Hand offen
    assert "| Gehzeit | ca. 3:40 h |" in t and "## E-01 " in t and "## Etappe 1: " not in t and "etappen_kennzahlen" not in einstellungen(r)
    assert all("pruefung.neu.nachziehen.etappe_kennzahl_anders" in katalog(x) for x in (texte_de, texte_en))


def test_f102_fett_gesetzter_name_wird_uebertragen_bevor_er_geht(tmp_path):
    """F102: Ein Parser für Lesen und Entfernen: eine fett gesetzte Zeile verlässt das Dossier nur mit ihrem Wert an der Strecke."""
    r = kopie("beispielreise", tmp_path)
    d = altform(r, zeilen=E01_ZEILEN.replace("| Aufstieg (Hm) |", "| **Aufstieg (Hm)** |"))
    neu.nachziehen(r)
    _, s = strecken(r, tmp_path)
    assert s["E-01"]["kennzahlen"]["aufstieg"] == 485 and "Aufstieg" not in d.read_text(encoding="utf-8")


def test_f103_zwei_namen_einer_kennung_ueberschreiben_nicht(tmp_path):
    """F103: Gehzeit und Dauer gehören zu gehzeit: die erste gilt (wie im Altstand), Dauer bleibt im Dossier, OFFEN, Einstellungen
    bleiben. „Gehzeit mit Pausen“ ist keine Kennung, sondern ein eigener Name: er kommt so an die Strecke, die Summe bleibt."""
    r = kopie("beispielreise", tmp_path / "a")
    d = altform(r, zeilen=E01_ZEILEN + "| Dauer | 5:00 h |\n", namen=("Gehzeit", "Dauer", "Aufstieg (Hm)", "Abstieg (Hm)", "Länge (km)"))
    m = neu.nachziehen(r)
    assert any(x.startswith("OFFEN E-01") and "Dauer" in x for x in m), m
    assert plan_kz(r)["gehzeit"] == "ca. 3:40 h"
    assert "| Dauer | 5:00 h |" in d.read_text(encoding="utf-8") and "etappen_kennzahlen" not in einstellungen(r)   # bleibt als Text (#357)
    assert all("pruefung.neu.nachziehen.etappe_kennzahl_doppelt" in katalog(x) for x in (texte_de, texte_en))
    r = kopie("beispielreise", tmp_path / "b")
    altform(r, zeilen=E01_ZEILEN + "| Gehzeit mit Pausen | 5:00 h |\n",
            namen=("Gehzeit", "Gehzeit mit Pausen", "Aufstieg (Hm)", "Abstieg (Hm)", "Länge (km)"))
    m = neu.nachziehen(r)
    d2, s = strecken(r, tmp_path / "b")
    assert s["E-01"]["kennzahlen"]["Gehzeit mit Pausen"] == "5:00 h" and not [x for x in m if x.startswith("OFFEN")]
    d1, _ = strecken(BEISPIELE / "beispielreise", tmp_path / "c")
    summe = lambda d: next(x for x in d["route"]["plaene"] if x["id"] == "P-A")["summe"]
    assert summe(d2) == summe(d1)


def test_f104_name_neben_seiner_kennung_wird_offen_gemeldet(tmp_path):
    """F104: Steht „Gehzeit“ neben gehzeit an der Strecke, stellt nachziehen nichts um und meldet OFFEN mit beiden Werten."""
    r = kopie("beispielreise", tmp_path)
    p = r / "plan/routen.yaml"
    p.write_text(p.read_text(encoding="utf-8").replace('{gehzeit: "ca. 3:40 h",', '{gehzeit: "ca. 3:40 h", Gehzeit: "9:00 h",'), encoding="utf-8")
    vorher = p.read_text(encoding="utf-8")
    m = neu.nachziehen(r)
    assert any(x.startswith("OFFEN E-01") and "9:00 h" in x and "ca. 3:40 h" in x for x in m), m
    assert p.read_text(encoding="utf-8") == vorher
    assert all("pruefung.neu.nachziehen.kennzahl_kollision" in katalog(x) for x in (texte_de, texte_en))


@pytest.mark.parametrize("name", ["Km-Stand", "Kmh Schnitt", "Dauer der Pause", "Aufstiegshilfe", "Gehzeit mit Pausen"])
def test_f105_nur_ganze_namen_werden_kennungen(name):
    """F105: Nur der ganze Name des Katalogs (mit Einheit in Klammern) wird zur Kennung; ein Anfang reicht nicht."""
    assert neu.kennung_der_kennzahl(name) == name
    assert [neu.kennung_der_kennzahl(n) for n in ("Gehzeit", "aufstieg (Hm)", "Länge (km)", "km", "Descent")] == \
        ["gehzeit", "aufstieg", "laenge", "laenge", "abstieg"]


def test_f107_leere_eckdaten_verlieren_ihre_ueberschrift(tmp_path):
    """F107: Bestand die Eckdaten-Tabelle nur aus Kennzahlen, entfällt mit den Zeilen auch die Überschrift „Eckdaten“."""
    r = kopie("beispielreise", tmp_path)
    d = altform(r, nur=True)
    neu.nachziehen(r)
    t = d.read_text(encoding="utf-8")
    abschnitt = t[t.index("## E-01 "):t.index("## E-02 ")]
    assert "### Eckdaten" not in abschnitt and "| Merkmal |" not in abschnitt
    _, s = strecken(r, tmp_path)
    assert s["E-01"]["kennzahlen"]["aufstieg"] == 485
