"""#269 (Teil von #215): Etappe ist eine Strecke einer Art mit summiert: true, kein Typ der Software
(Spec docs/specs/oberflaeche/etappe-als-art-269.md). Nur erfundene Daten: die beiden Beispielreisen."""
import json
import re
import shutil
import sys
from pathlib import Path

import pytest

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
    t = re.sub(r", kennzahlen: \{[^}]*\}", "", p.read_text(encoding="utf-8"))
    p.write_text(re.sub(r"(E-0[1-4]: \{)titel: \"[^\"]*\", ", r"\1", t), encoding="utf-8")
    dossier = r / "inhalt/etappen.md"
    t = dossier.read_text(encoding="utf-8")
    for n in range(1, 5):
        t = re.sub(rf"^## E-0{n} (.+)$", rf"## Etappe {n}: \1", t, flags=re.M)
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
