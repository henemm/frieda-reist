"""Lesetext am Ort (ADR-0008, Schritt e, frieda-reist #334/#335): lesetext_schreiben nimmt O-…, der Text steht oben auf der
Ortsseite (unter „## O-… Name“ im Ortsdossier, vor den Unterabschnitten), gegliedert nach den Rubriken der Art des Orts; ohne
Art oder Gliederung freier Text. Erfundene Testdaten beider Beispielreisen."""
import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bauen  # noqa: E402
import konnektor as kn  # noqa: E402
import schreiben as sb  # noqa: E402
from conftest import meldet  # noqa: E402

BEISPIELE = Path(__file__).resolve().parent.parent.parent / "beispiel" / "reisen"
IDA = {"name": "Ida"}


def kopie(tmp_path, reise="beispielreise"):
    q = tmp_path / reise
    shutil.copytree(BEISPIELE / reise, q)
    return q


def schreib(q, ziel, text, quelle="erfunden (Test)"):
    return sb.lesetext_schreiben(q, IDA, {"ziel": ziel, "text": text, "quelle": quelle})


def test_ort_mit_gliederung_ersetzt_den_text_oben_und_laesst_unterabschnitte(tmp_path):
    q = kopie(tmp_path)
    titel, antwort = schreib(q, "o-03", "**Ankommen.** Über den Markt zur Pension (Test).\n\n**Versorgung.** Ein kleiner Laden am Markt (Test).")
    assert meldet(titel, "schreiben.titel.lesetext_ersetzt") and meldet(antwort, "schreiben.antwort.lesetext.ort_ersetzt")
    t = (q / "inhalt" / "orte.md").read_text(encoding="utf-8")
    assert "## O-03 Hohnstein\n\n**Ankommen.** Über den Markt zur Pension (Test).\n\n**Versorgung.** Ein kleiner Laden am Markt (Test).\n\n*Herkunft: erfunden (Test); geschrieben am" in t
    assert "Kleine Stadt mit Burg" not in t
    assert "### Ankommen\nDie gewählte Pension Burgblick" in t and "### Frauenkirche" in t and "[^1]: Frauenkirche" in t
    d = bauen.bauen(q, tmp_path / "web")
    o3 = next(a for a in d["abschnitte"] if a["id"] == "O-03")
    assert "<strong>Ankommen.</strong>" in o3["intro"] and [b["titel"] for b in o3["bloecke"]] == ["Ankommen"]
    # zweimal schreiben ersetzt, statt anzuhängen
    schreib(q, "O-03", "**Umschauen.** Burg über dem Tal (Test).")
    t = (q / "inhalt" / "orte.md").read_text(encoding="utf-8")
    assert t.count("*Herkunft: erfunden (Test); geschrieben am") == 1 and "Laden am Markt" not in t


def test_fremdes_stichwort_wird_abgelehnt_ohne_gliederung_frei(tmp_path):
    q = kopie(tmp_path)
    vorher = (q / "inhalt" / "orte.md").read_text(encoding="utf-8")
    with pytest.raises(sb.Ablehnung) as e:
        schreib(q, "O-03", "**Essen.** Gut (Test).")
    assert meldet(str(e.value), "schreiben.lesetext_schreiben.4") and "Ankommen, Versorgung, Umschauen" in str(e.value)
    assert (q / "inhalt" / "orte.md").read_text(encoding="utf-8") == vorher
    # Dresden: Art stadt ohne Gliederung, jedes Stichwort erlaubt
    schreib(q, "O-01", "**Essen.** Sächsische Küche (Test).")
    assert "## O-01 Dresden\n\n**Essen.** Sächsische Küche (Test)." in (q / "inhalt" / "orte.md").read_text(encoding="utf-8")


def test_ort_ohne_abschnitt_bekommt_einen(tmp_path):
    q = kopie(tmp_path)
    titel, antwort = schreib(q, "O-05", "**Ankommen.** Mit der Fähre über die Elbe (Test).")
    assert meldet(titel, "schreiben.titel.lesetext_angelegt") and meldet(antwort, "schreiben.antwort.lesetext.ort_angelegt")
    t = (q / "inhalt" / "orte.md").read_text(encoding="utf-8")
    assert t.rstrip().endswith("geschrieben am " + t.rstrip().rsplit("geschrieben am ", 1)[1]) and "\n## O-05 Bad Schandau\n\n**Ankommen.**" in t
    d = bauen.bauen(q, tmp_path / "web")
    assert any(a["id"] == "O-05" and "Fähre" in a["intro"] for a in d["abschnitte"])
    o3 = next(a for a in d["abschnitte"] if a["id"] == "O-03")
    assert "Burgblick" in o3["bloecke"][0]["html"]   # Fußnote und Text des vorigen Orts unberührt


def test_stadtwochenende_ohne_ortsdossier_legt_es_an(tmp_path):
    q = kopie(tmp_path, "stadtwochenende")
    with pytest.raises(sb.Ablehnung):
        schreib(q, "O-02", "**Abendessen.** Spät (Test).")
    schreib(q, "O-02", "**Essen.** Man isst spät zu Abend (Test).\n\n**Unterwegs.** Zu Fuß und mit der Tram (Test).")
    cfg = json.loads((q / "reise.json").read_text(encoding="utf-8"))
    assert cfg["orte_dossiers"] == ["inhalt/orte.md"]
    assert (q / "inhalt" / "orte.md").read_text(encoding="utf-8").startswith("## O-02 Beispielstadt\n\n**Essen.** Man isst spät")
    d = bauen.bauen(q, tmp_path / "web")
    assert any(a["id"] == "O-02" and a["typ"] == "ort" and "Tram" in a["intro"] for a in d["abschnitte"])
    # O-01 hat keine Art: freier Text
    schreib(q, "O-01", "Von hier fährt der Zug (Test).")
    assert "\n## O-01 Heimatstadt\n\nVon hier fährt der Zug (Test)." in (q / "inhalt" / "orte.md").read_text(encoding="utf-8")


def test_unbekannter_ort_und_falsches_ziel(tmp_path):
    q = kopie(tmp_path)
    with pytest.raises(sb.Ablehnung) as e:
        schreib(q, "O-99", "x")
    assert meldet(str(e.value), "schreiben.lesetext_schreiben.ort_fehlt")
    with pytest.raises(sb.Ablehnung) as e:
        schreib(q, "T-01", "x")
    assert meldet(str(e.value), "schreiben.lesetext_schreiben.1")


def test_bau_meldet_fremdes_stichwort_am_ort_als_hinweis(tmp_path):
    q = kopie(tmp_path)
    p = q / "inhalt" / "orte.md"
    p.write_text(p.read_text(encoding="utf-8").replace("Kleine Stadt mit Burg", "**Wetter.** Kleine Stadt mit Burg"), encoding="utf-8")
    b = bauen.Bauer(q, tmp_path / "web")
    b.daten()
    assert meldet(b.hinweise, "pruefung.bauen.72") and any("O-03" in str(h) and "Wetter" in str(h) for h in b.hinweise)
    b = bauen.Bauer(kopie(tmp_path / "rein"), tmp_path / "web2")
    b.daten()
    assert not meldet(b.hinweise, "pruefung.bauen.72")


def test_konnektor_zeigt_die_gliederung_des_orts(tmp_path):
    h = kn.Handbuch(bauen.bauen(kopie(tmp_path), tmp_path / "web"))
    _, t3 = h.eintraege["O-03"]
    _, t1 = h.eintraege["O-01"]
    assert meldet(t3, "konnektor.lesetext_zeilen.1") and "- Versorgung: Einkaufen, Essen" in t3
    assert not meldet(t1, "konnektor.lesetext_zeilen.1")   # Stadt ohne Gliederung
    h = kn.Handbuch(bauen.bauen(kopie(tmp_path / "s", "stadtwochenende"), tmp_path / "s" / "web"))
    assert "- Essen: Küche der Gegend" in h.eintraege["O-02"][1]
