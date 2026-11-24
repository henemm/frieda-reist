"""Tests für #648: Sperre gegen Schreiben über den Konnektor des Product Owners in Claude-Code-Sitzungen dieses Repos.
Spec: docs/specs/betrieb/testkonto-648.md (Tests 8 bis 11, AC-6, AC-7).

Der Hook `.claude/hooks/frieda_sperre.py` (PreToolUse, nur Standardbibliothek) liest das Hook-Ereignis als JSON auf stdin.
Für `mcp__claude_ai_Frieda__<werkzeug>` lässt er genau die Werkzeuge zu, die der Konnektor mit `readOnlyHint: true`
ausweist (Name so, wie tools/list ihn zeigt); alles andere, auch Unbekanntes, lehnt er mit Exit-Code 2 und einem Hinweis
auf `frieda-test` ab. Werkzeuge anderer Server greift er nicht an (Exit-Code 0).

Die Erlaubnisliste steht im Hook als Menge `ERLAUBT`; dieser Test hält sie gegen die Werkzeugliste des Konnektors
synchron (keine Handpflege, AC-7).
"""
import ast
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]
WURZEL = ENGINE.parent
HOOK = WURZEL / ".claude" / "hooks" / "frieda_sperre.py"
PRAEFIX = "mcp__claude_ai_Frieda__"
sys.path.insert(0, str(ENGINE))
import konnektor as kn  # noqa: E402
import schnittstelle  # noqa: E402


def _ist_werkzeug(w):
    return isinstance(w, dict) and "name" in w and "inputSchema" in w


def werkzeuge_des_konnektors():
    """Alle Werkzeuge, die der Konnektor in tools/list zeigen kann (Konto- und Reisewerkzeuge, je Rolle), mit dem Namen
    nach außen. Aliase stehen nicht in tools/list und sind hier nicht dabei."""
    alle = {}
    for wert in vars(kn).values():
        if _ist_werkzeug(wert):
            alle.setdefault(wert["name"], wert)
        elif isinstance(wert, list) and wert and all(_ist_werkzeug(x) for x in wert):
            for x in wert:
                alle.setdefault(x["name"], x)
    for w in (kn.sprache_setzen_werkzeug("de"), kn.an_frieda_melden_werkzeug("de", ["beispielreise"])):
        alle.setdefault(w["name"], w)
    alias = {w["name"] for w in kn.ALIAS_WERKZEUGE}
    return {w["name"]: w for w in schnittstelle.aussen([w for n, w in alle.items() if n not in alias])}


def nur_lesen(w):
    return (w.get("annotations") or {}).get("readOnlyHint") is True


def hook_modul():
    spec = importlib.util.spec_from_file_location("frieda_sperre", HOOK)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def fragen(werkzeug):
    """Hook wie Claude Code aufrufen. -> (returncode, stderr)"""
    ereignis = {"session_id": "pytest", "hook_event_name": "PreToolUse", "tool_name": werkzeug, "tool_input": {},
                "cwd": str(WURZEL)}
    p = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(ereignis), capture_output=True, text=True, timeout=30)
    return p.returncode, p.stderr


# ---------- Test 8: Erlaubnisliste gleich den Lesewerkzeugen des Konnektors ----------

def test_erlaubnisliste_entspricht_den_lesewerkzeugen():
    w = werkzeuge_des_konnektors()
    lesen = {n for n, x in w.items() if nur_lesen(x)}
    assert lesen, "der Konnektor zeigt keine Lesewerkzeuge?"
    assert set(hook_modul().ERLAUBT) == lesen


def test_hook_entscheidet_fuer_jedes_werkzeug_des_konnektors():
    for name, w in sorted(werkzeuge_des_konnektors().items()):
        rc, err = fragen(PRAEFIX + name)
        if nur_lesen(w):
            assert rc == 0, (name, err)
        else:
            assert rc == 2, name
            assert "frieda-test" in err, name


# ---------- Test 9: unbekanntes Werkzeug ----------

def test_unbekanntes_werkzeug_wird_abgelehnt():
    rc, err = fragen(PRAEFIX + "neu_erfunden")
    assert rc == 2
    assert "frieda-test" in err


def test_kaputtes_ereignis_wird_abgelehnt():
    p = subprocess.run([sys.executable, str(HOOK)], input="kein json", capture_output=True, text=True, timeout=30)
    assert p.returncode == 2


# ---------- Test 10: andere Server unberührt ----------

def test_andere_server_und_werkzeuge_bleiben_unberuehrt():
    for name in ("mcp__frieda-test__item_create", "mcp__frieda-test__trip_create", "Bash", "Read",
                 "mcp__claude_ai_Gmail__search_threads"):
        rc, err = fragen(name)
        assert rc == 0, (name, err)


# ---------- Test 11: nur Standardbibliothek ----------

def test_hook_nutzt_nur_standardbibliothek():
    baum = ast.parse(HOOK.read_text(encoding="utf-8"))
    for k in ast.walk(baum):
        if isinstance(k, ast.Import):
            for a in k.names:
                assert a.name.split(".")[0] in sys.stdlib_module_names, a.name
        elif isinstance(k, ast.ImportFrom):
            assert not k.level and (k.module or "").split(".")[0] in sys.stdlib_module_names, k.module
