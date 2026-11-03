"""#267 (Teil 3 von #215), PR a: Eine Reise ohne reise.yaml gibt es nicht mehr (Spec docs/specs/betrieb/altformen-entfernen-267.md).

Nur erfundene Daten: die beiden Beispielreisen."""
import re
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bauen  # noqa: E402
import texte  # noqa: E402
import texte_de  # noqa: E402
import texte_en  # noqa: E402

WURZEL = Path(__file__).resolve().parent.parent.parent
BEISPIELE = ["beispielreise", "stadtwochenende"]
SCHLUESSEL = "pruefung.bauen.reise_yaml_fehlt"


def katalog(modul):
    """Der Textkatalog eines Sprachmoduls (Wörterbuch Schlüssel -> Text)."""
    return next(v for v in vars(modul).values() if isinstance(v, dict) and "pruefung.reise.20" in v)


@pytest.mark.parametrize("name", BEISPIELE)
def test_ohne_reise_yaml_bricht_der_bau_ab(name, tmp_path):
    """AC-1: fehlt reise.yaml, bricht der Bau mit BauFehler ab; der Text kommt aus dem Katalog."""
    reise = tmp_path / name
    shutil.copytree(WURZEL / "beispiel" / "reisen" / name, reise)
    (reise / "reise.yaml").unlink()
    with pytest.raises(bauen.BauFehler) as e:
        bauen.Bauer(reise, tmp_path / "dist")
    erwartet = str(texte.satz(SCHLUESSEL, pfad=reise / "reise.yaml"))
    assert erwartet != SCHLUESSEL and "docs/produkt.md" in erwartet
    assert erwartet in e.value.meldungen


@pytest.mark.parametrize("modul", [texte_de, texte_en])
def test_katalog_hat_neuen_schluessel_und_nicht_mehr_den_alten(modul):
    k = katalog(modul)
    assert SCHLUESSEL in k
    assert "pruefung.reise.2" not in k


def test_reise_alt_ist_aus_dem_quelltext_verschwunden():
    """AC-1: keine Zweige auf die alte Form mehr in engine/reise.py."""
    quelltext = (WURZEL / "engine" / "reise.py").read_text(encoding="utf-8")
    assert not re.search(r"\.alt\b", quelltext), "reise.py kennt noch .alt"
    assert "alte Form" not in quelltext, "reise.py nennt noch die alte Form"


@pytest.mark.parametrize("name", BEISPIELE)
def test_beispielreisen_bauen_weiter(name, tmp_path):
    """AC-2: die Beispielreisen mit reise.yaml bauen unverändert (Sicherung gegen zu strenge Umsetzung)."""
    b = bauen.Bauer(WURZEL / "beispiel" / "reisen" / name, tmp_path / "dist")
    assert b.reise_roh is not None
