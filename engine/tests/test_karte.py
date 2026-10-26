"""Tests für GPX-Tracks (25.10.2026)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import gpx  # noqa: E402

GPX_TEXT = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1"><trk><trkseg>
{punkte}
</trkseg></trk></gpx>"""


def gpx_datei(pfad, punkte):
    pfad.write_text(GPX_TEXT.format(punkte="\n".join(f'<trkpt lat="{a}" lon="{b}"/>' for a, b in punkte)), encoding="utf-8")
    return pfad


def test_lesen_und_vereinfachen(tmp_path):
    # Gerade Linie mit 50 Punkten plus ein Knick: übrig bleiben Anfang, Knick, Ende
    gerade = [(39.7, 2.6 + i * 0.0002) for i in range(50)]
    knick = gerade + [(39.71, 2.61)]
    pts = gpx.lesen(gpx_datei(tmp_path / "a.gpx", knick))
    assert len(pts) == 51
    v = gpx.vereinfachen(pts)
    assert v[0] == pts[0] and v[-1] == pts[-1] and len(v) == 3


def test_einbauen_heftet_orte_und_punkte_an(tmp_path):
    k = {"orte": {"O-1": {"lage": [39.70, 2.60]}, "O-2": {"lage": [39.75, 2.70]}, "O-3": {"lage": [39.80, 2.80]}},
         "wege": {"E-1": [[39.70, 2.60], [39.75, 2.70]], "E-2": [[39.75, 2.70], [39.78, 2.75], [39.80, 2.80]]},
         "punkte": [{"name": "nah", "lage": [39.7255, 2.6505]}, {"name": "weit", "lage": [39.0, 2.0]}],
         "gpx": {"E-1": "e1.gpx"}}
    track = [(39.701, 2.601), (39.725, 2.65), (39.751, 2.701)]
    gpx_datei(tmp_path / "e1.gpx", track)
    strecken = {"E-1": {"von": "O-1", "nach": "O-2"}, "E-2": {"von": "O-2", "nach": "O-3"}}
    assert gpx.einbauen(k, strecken, lambda rel: gpx.lesen(tmp_path / rel)) == []
    assert k["wege"]["E-1"] == [list(p) for p in track]
    assert k["orte"]["O-1"]["lage"] == [39.701, 2.601] and k["orte"]["O-2"]["lage"] == [39.751, 2.701]
    # Weg ohne Track folgt dem verschobenen Ort
    assert k["wege"]["E-2"][0] == [39.751, 2.701] and k["wege"]["E-2"][-1] == [39.80, 2.80]
    # Wegpunkt nahe der Linie sitzt jetzt exakt auf einem Linienpunkt, ferner bleibt
    assert k["punkte"][0]["lage"] == [39.725, 2.65] and k["punkte"][1]["lage"] == [39.0, 2.0]


def test_einbauen_meldet_fehlende_datei(tmp_path):
    k = {"orte": {}, "wege": {}, "gpx": {"E-1": "fehlt.gpx"}}
    m = gpx.einbauen(k, {}, lambda rel: gpx.lesen(tmp_path / rel))
    assert len(m) == 1 and "fehlt.gpx" in m[0]
