"""Versuchsaufbau #656: hält den Faden von vorgang_speicher unmittelbar vor dem mkdir in exportieren an, bis der nächste Test sein tmp_path hat. Aufruf: PYTHONPATH=docs/artifacts/fix-656-vorab-ordner-faden <python der venv> -m pytest -s -p verzoegern656b engine/tests/test_schreiben.py -k vorab_ordner_wird -p no:cacheprovider. Stand vor der Änderung: 3 von 3 Läufen rot, FileExistsError in [ausnahme]."""
import sys, threading, time, pytest, pathlib
los = threading.Event(); spur = []; AKTIV = [False]
orig = pathlib.Path.mkdir
def mkdir(self, *a, **k):
    f = threading.current_thread()
    if AKTIV[0] and f is not threading.main_thread() and "frieda-schreiben-" in str(self) and not spur:
        spur.append("angehalten"); los.wait(20); spur.append("weiter")
        r = orig(self, *a, **k); spur.append("angelegt"); return r
    return orig(self, *a, **k)
pathlib.Path.mkdir = mkdir
@pytest.fixture(autouse=True)
def zz_los(request, tmp_path):
    if "[frist]" in request.node.name: AKTIV[0] = True
    elif AKTIV[0]:
        los.set(); time.sleep(0.5)
        print("SPUR", tmp_path.name, spur, sorted(p.name for p in tmp_path.iterdir()))
    yield
