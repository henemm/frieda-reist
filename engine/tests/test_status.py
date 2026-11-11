"""Status der Reise von der Reiseseite (#513): Organisator:innen stellen ihn um, der Rückmeldedienst reicht die Wahl an den
Schreibweg weiter (nachgestellt in test_regeln.Umgebung). Personen erfunden: Ida organisiert, Karl wirkt mit."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import rueckmeldungen as rm  # noqa: E402
from test_anmeldung import abruf, welt  # noqa: E402,F401  (welt: Fixture)
from test_push import reise  # noqa: E402,F401  (Fixture)
from conftest import meldet  # noqa: E402


def setzen(u, token, status, origin=True):
    kw = {} if origin else {"origin": None}
    s, _, t = abruf(f"{u.rurl}/beispielreise/status", "POST", cookie=token, json_body={"status": status}, **kw)
    return s, json.loads(t)


def test_organisatorin_stellt_den_status_auf_der_seite_um(reise):
    u = reise
    s, o = setzen(u, u.ida, "fest")
    assert s == 200 and o["ok"] and o["status"] == "fest"
    (pfad, body), = u.schreibweg
    assert pfad == "/beispielreise/reise_status_setzen"
    assert body == {"person": "ida", "name": "Ida", "rolle": "organisator",
                    "args": {"status": "fest", "grund": "auf der Reiseseite umgestellt"}}


def test_nur_organisatorinnen_angemeldet_und_bekannte_status(reise):
    u = reise
    s, o = setzen(u, u.karl, "fest")                         # Karl wirkt mit
    assert s == 403 and meldet(o["fehler"], "dienst.status.recht")
    s, o = setzen(u, None, "fest")                           # nicht angemeldet
    assert s == 401
    s, o = setzen(u, u.ida, "fest", origin=False)            # fremde Seite (CSRF)
    assert s == 403
    for falsch in ("archiv", "erfunden", ""):
        s, o = setzen(u, u.ida, falsch)
        assert s == 400 and meldet(o["fehler"], "dienst.status.unbekannt")
    assert u.schreibweg == []


def test_ablehnung_und_ausfall_des_schreibwegs(reise, monkeypatch):
    u = reise
    monkeypatch.setenv("KN_SCHREIBDIENST", "http://127.0.0.1:9")   # nichts hört dort
    s, o = setzen(u, u.ida, "fest")
    assert s == 503 and o["fehler_code"] == "dienst.status.nicht_erreichbar"
    assert rm.schreibdienst() == "http://127.0.0.1:9"
    monkeypatch.delenv("KN_SCHREIBDIENST")
    monkeypatch.delenv("RM_SCHREIBDIENST", raising=False)
    monkeypatch.setenv("FR_SB_PORT", "8999")
    assert rm.schreibdienst() == "http://127.0.0.1:8999"
