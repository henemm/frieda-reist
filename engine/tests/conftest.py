"""Jeder Test läuft ohne die Umgebung einer echten Instanz. Die Betriebsskripte rufen die Tests mit ihren Einstellungen
auf (FR_SEITEN …); sonst leitete instanz.py Ordner wie die Konten-Datenbank aus den Ordnern des Servers ab, und Tests
schrieben dorthin. Werte, die ein Test braucht, setzt er selbst."""
import os

import pytest

PRAEFIXE = ("FR_", "RM_", "KN_", "EA_", "VF_", "FS_", "WA_")


def instanz_leeren(monkeypatch, tmp_path):
    """Entfernt die Umgebung der Instanz und setzt die Ordner, in die Tests schreiben dürfen, unter tmp_path."""
    for name in list(os.environ):
        if name.startswith(PRAEFIXE):
            monkeypatch.delenv(name)
    monkeypatch.setenv("FR_WURZEL", str(tmp_path / "keine-instanz"))   # keine betrieb/einstellungen.env
    monkeypatch.setenv("FR_KONTEN", str(tmp_path / "_konten"))
    monkeypatch.setenv("FR_DIENST", str(tmp_path / "_dienst"))   # Reise-Stände (engine/stand.py) nie in den Ordner des Servers
    monkeypatch.setenv("FR_SPEICHER", str(tmp_path / "_speicher"))   # Reisespeicher (engine/reisespeicher.py, #346)


@pytest.fixture(scope="session", autouse=True)
def ohne_instanz_im_lauf(tmp_path_factory):
    """Einmal je Lauf, vor allen Fixtures mit größerem Geltungsbereich (scope="module" baut etwa die Beispielreise):
    sie sehen nie die Umgebung des Servers (sonst griffe z. B. FR_UMZUG_NACH, #204). Eine neue Modul-Fixture braucht
    dafür nichts selbst zu tun."""
    with pytest.MonkeyPatch.context() as mp:
        instanz_leeren(mp, tmp_path_factory.mktemp("lauf"))
        yield


@pytest.fixture(autouse=True)
def ohne_instanz(tmp_path, monkeypatch):
    """Je Test eigene Ordner, damit kein Test die Konten oder Stände eines anderen sieht."""
    instanz_leeren(monkeypatch, tmp_path)


@pytest.fixture(autouse=True)
def rueckfall_deutsch(request, monkeypatch):
    """Die meisten Tests prüfen deutsche Wortlaute und setzen die Sprache nicht selbst: für sie gilt als Rückfall Deutsch.
    Tests mit der Marke @pytest.mark.echter_rueckfall laufen mit dem Rückfall der Software (Englisch)."""
    if request.node.get_closest_marker("echter_rueckfall"):
        return
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    import texte
    monkeypatch.setattr(texte, "VORGABE_REISE", "de")


def pytest_configure(config):
    config.addinivalue_line("markers", "echter_rueckfall: läuft mit dem Rückfall der Software (texte.VORGABE_REISE), nicht mit Deutsch")


# ---------- Bedeutung statt Wortlaut (#204) ----------
# Tests prüfen Meldungen über ihren Schlüssel im Katalog, nicht über den Wortlaut: Wer einen Text in texte_de.py
# umformuliert, muss keinen Test anfassen. Neue Tests nutzen meldet() und text() statt kopierter Sätze.

def _katalog():
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import texte
    return texte


def text(schluessel, /, sprache="de", **werte):
    """Der Text zu einem Schlüssel, wie die Software ihn zeigt."""
    return _katalog().t(sprache, schluessel, **werte)


def meldet(ausgabe, schluessel, /, sprache="de"):
    """Enthält die Ausgabe den Text zu diesem Schlüssel? Die festen Teile der Vorlage müssen alle vorkommen, die
    Platzhalter ({datum} …) dürfen beliebig gefüllt sein; HTML-Maskierung zählt mit. Bei einer Liste genügt ein Eintrag."""
    import html
    import re
    if isinstance(ausgabe, (list, tuple, set)):
        return any(meldet(a, schluessel, sprache) for a in ausgabe)
    ausgabe = str(ausgabe)
    vorlage = _katalog().t(sprache, schluessel)
    assert vorlage != schluessel, f"Schlüssel {schluessel} fehlt im Katalog"
    teile = [t for t in re.split(r"\{[^{}]*\}", vorlage) if len(t.strip()) >= 2] or [vorlage]
    return all(t in ausgabe or html.escape(t, quote=False) in ausgabe or html.escape(t) in ausgabe for t in teile)


def mcp_intern(token, nachricht):
    """Den Konnektor als eine Person einer Reise aufrufen, ohne Anmeldung über OAuth. Die Tests geben Personen Kurznamen in
    einer Datei (KN_ZUGAENGE, {kurzname: {"reise", "person"} oder {"reise", "rolle"}}); das waren bis #421 die geheimen
    Links, heute gibt es sie nur noch hier. Aufgerufen wird intern (konnektor.antwort_fuer), so wie der Konnektor „Frieda“
    je Aufruf aus Konto und Angabe reise einen Zugang bildet. -> (HTTP-Code, Antwort) wie früher über HTTP."""
    import json
    from pathlib import Path
    import konnektor as kn
    try:
        z = json.loads(Path(os.environ["KN_ZUGAENGE"]).read_text(encoding="utf-8")).get(token)
    except (KeyError, OSError, ValueError, AttributeError):
        z = None
    if not isinstance(z, dict) or "reise" not in z:
        return 404, {"fehler": "unbekannt"}
    a = kn.antwort_fuer({k: v for k, v in z.items() if k in ("reise", "person", "rolle", "sprache")}, nachricht)
    return (200, a) if a else (202, None)


def zugaenge_datei():
    """Die Datei der Kurznamen für mcp_intern (nur in Tests)."""
    from pathlib import Path
    return Path(os.environ["KN_ZUGAENGE"])


def zugang_dazu(kurzname, **zugang):
    """Einen Kurznamen für mcp_intern ergänzen, etwa für eine eben eingeladene Person: zugang_dazu("j" * 32, reise=…, person=…)."""
    import json
    p = zugaenge_datei()
    alle = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    alle[kurzname] = zugang
    p.write_text(json.dumps(alle), encoding="utf-8")
    return kurzname
