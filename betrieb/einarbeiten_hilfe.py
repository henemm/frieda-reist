#!/usr/bin/env python3
"""Hilfen für betrieb/einarbeiten.sh und betrieb/veroeffentlichen.sh: Neues finden, Sammelzeit, Versuche, Kosten,
Protokoll, Regelprüfung, neue Reisen (docs/betrieb.md).

Die Logik steckt hier statt in der Shell, damit sie getestet werden kann (engine/tests/test_betrieb_einarbeiten.py).
Aufruf:  einarbeiten_hilfe.py <befehl> ...   (mit dem Python der Software, weil reise.yaml gelesen wird)
<wurzel> ist die Wurzel des Reisen-Repos (engine/ darin ist die Software).

  neu <wurzel> <gesehen>             Rückmeldungen und Aufträge mit Status „neu“, die kein Lauf gesehen hat:
                                     je Zeile „<reise> <id> <erstellt>“
  warten <wurzel> <gesehen>          Sekunden, die noch zu sammeln sind (0 = jetzt starten)
  versuch <datei> <max> <id>…        zählt einen gescheiterten Versuch je ID, gibt die IDs aus, die <max> erreicht haben
  kosten <claude.log>                Kosten in USD aus der JSON-Ausgabe von claude -p (leer, wenn unbekannt);
                                     Rückgabe 3, wenn Claude einen Fehler gemeldet hat
  protokoll <datei> <feld=wert>…     hängt eine JSON-Zeile mit Zeitstempel an (Zahlen bleiben Zahlen)
  regeln <wurzel> <arbeit> <reise/id>…  prüft nach dem Lauf, was sonst nur die Anleitung verlangt (Konflikt wird offene
                                     Frage, Prüfauftrag ändert keinen Wert); gibt Verstöße aus, Rückgabe 4 bei Verstoß
  neue_reisen <wurzel> <arbeit> <aus.jsonl> <A-…>…  legt neue Reisen aus Aufträgen der Claude-App (Konto-Link, Ablage
                                     _neu) in der Arbeitskopie an (Paket H): je Zeile „angelegt <ordner> <A-…>“ oder
                                     „fehler <A-…> <Grund>“; Angelegtes als JSON-Zeile {ordner, aid, name, person} nach aus
  ausstehend <wurzel> <datei>        stellt die Links neuer, inzwischen veröffentlichter Reisen zu: freischalten.sh mit
                                     --person, dann Meldung an die Person (meine_reisen); Erledigtes fällt aus der Datei

Umgebung: RM_ABLAGE (Rückmelde-Ablage), KN_SEITEN (veröffentlichte Seiten), EA_SEKUNDEN_JE_MINUTE (60, nur für Tests
kleiner), FR_MAX_WARTEN_MIN (20: so lange wartet die Sammelzeit höchstens auf die älteste neue Eingabe).
"""
import datetime
import json
import os
import sys
from pathlib import Path


def _engine(wurzel):
    sys.path.insert(0, str(Path(wurzel) / "engine"))
    import rueckmeldungen as rm  # noqa: E402
    return rm


def _gesehen(pfad):
    p = Path(pfad)
    return set(p.read_text(encoding="utf-8").split()) if p.exists() else set()


def reisen(wurzel):
    return sorted(p.parent.name for p in (Path(wurzel) / "reisen").glob("*/reise.json"))


def sammelzeit_minuten(wurzel, reise):
    """regeln.sammelzeit_minuten aus reise.yaml, sonst die Vorgabe der Software."""
    import yaml
    sys.path.insert(0, str(Path(wurzel) / "engine"))
    import reise as modell  # noqa: E402
    datei = Path(wurzel) / "reisen" / reise / "reise.yaml"
    roh = yaml.safe_load(datei.read_text(encoding="utf-8")) if datei.exists() else {}
    wert = ((roh or {}).get("regeln") or {}).get("sammelzeit_minuten", modell.VORGABEN["sammelzeit_minuten"])
    return wert if isinstance(wert, int) and not isinstance(wert, bool) and wert >= 0 else modell.VORGABEN["sammelzeit_minuten"]


NEU = "_neu"   # Ablage der Anfragen nach neuen Reisen (rueckmeldungen.NEU), gehört zu keiner Reise


def neu(wurzel, gesehen):
    """[(reise, id, erstellt)], älteste zuerst. Anfragen nach neuen Reisen stehen mit reise „_neu“ darin."""
    rm = _engine(wurzel)
    schon = _gesehen(gesehen)
    zeilen = []
    for reise in reisen(wurzel):
        o = rm.ordner(reise)
        if o is None:
            continue
        for e in rm.eintraege(o) + rm.auftraege(o):
            if e["status"] in ("neu", "konflikt") and e["id"] not in schon:
                zeilen.append((reise, e["id"], e.get("erstellt", "")))
    o = rm.ordner_neu() if hasattr(rm, "ordner_neu") else None
    if o is not None:
        zeilen += [(NEU, e["id"], e.get("erstellt", "")) for e in rm.auftraege(o)
                   if e["status"] == "neu" and e["id"] not in schon and (e.get("daten") or {}).get("neue_reise")]
    return sorted(zeilen, key=lambda z: z[2])


def neue_reisen(wurzel, arbeit, aids):
    """Neue Reisen aus Aufträgen der Claude-App in der Arbeitskopie anlegen (ohne KI: alles ist im Dienst geprüft).
    -> (angelegt [{ordner, aid, name, person}], fehler [(aid, grund)]). Was die Prüfung vor dem Bau nicht besteht, wird
    wieder entfernt und als Fehler gemeldet."""
    import shutil
    rm = _engine(wurzel)
    sys.path.insert(0, str(Path(arbeit) / "engine"))
    import neu as neumod  # noqa: E402
    o = rm.ordner_neu()
    alle = {e["id"]: e for e in rm.auftraege(o)} if o else {}
    angelegt, fehler = [], []
    for aid in aids:
        a = alle.get(aid)
        n = ((a or {}).get("daten") or {}).get("neue_reise")
        if not n:
            fehler.append((aid, "Den Auftrag gibt es nicht oder er beschreibt keine neue Reise."))
            continue
        try:
            ordner = neumod.aus_auftrag(Path(arbeit) / "reisen", a)
        except neumod.Fehler as e:
            fehler.append((aid, str(e)))
            continue
        ok, meldungen = neumod.pruefen(ordner)
        if not ok:
            shutil.rmtree(ordner)
            fehler.append((aid, "Die Reise baut nicht: " + " ".join(meldungen)))
            continue
        person = next(k for k, p in n["personen"].items() if p["name"] == n["wer"])
        angelegt.append({"ordner": ordner.name, "aid": aid, "name": n["wer"], "person": person})
    return angelegt, fehler


def ausstehend(wurzel, datei, seiten=None, freischalten=None):
    """Links neuer Reisen zustellen, sobald die Seite veröffentlicht ist -> Zahl der Fehlschläge. Einträge (JSON-Zeilen):
    {ordner, aid, name, person}. Noch nicht Veröffentlichtes und Fehlgeschlagenes bleibt für den nächsten Lauf stehen.
    Kam der Auftrag aus dem Konnektor „Frieda“ (konto_id, Paket J): kein App-Link, sondern das Konto wird mit der Reise
    verknüpft, und wer eine Adresse hat, bekommt die Einladung per Mail. Die Adressen stehen nur im Auftrag in der Ablage,
    nie in dieser Datei oder im Protokoll; schon Eingeladene merkt sich der Eintrag (eingeladen)."""
    import subprocess
    rm = _engine(wurzel)
    import konten  # noqa: E402  (liegt neben rueckmeldungen.py)
    p = Path(datei)
    if not p.exists():
        return 0
    seiten = Path(seiten or os.environ["KN_SEITEN"])
    freischalten = freischalten or str(Path(__file__).resolve().with_name("freischalten.sh"))
    o_neu = rm.ordner_neu()
    auftraege = {a["id"]: a for a in rm.auftraege(o_neu)} if o_neu else {}
    rest, fehlschlaege = [], 0
    for zeile in p.read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(zeile)
        except json.JSONDecodeError:
            continue
        daten = seiten / e["ordner"] / "daten.json"
        if not daten.exists():
            rest.append(zeile)
            continue
        auftrag = auftraege.get(e["aid"]) or {}
        mit_konto = bool(auftrag.get("konto_id"))
        aufruf = [freischalten, e["ordner"]] + ([] if mit_konto else ["--person", e["person"]])
        r = subprocess.run(aufruf, capture_output=True, text=True)
        links = dict(z.split(": ", 1) for z in r.stdout.splitlines() if z.startswith(("Seite: ", "Claude-App: ")))
        if r.returncode != 0 or not ({"Seite"} if mit_konto else {"Seite", "Claude-App"}) <= set(links):
            fehlschlaege += 1
            # Links sind geheim: nur die Fehlerzeilen ins Protokoll
            fehler = [z for z in (r.stdout + r.stderr).splitlines() if not z.startswith(("Seite: ", "Claude-App: "))]
            print(f"FEHLER: {e['ordner']} nicht freigeschaltet: {' '.join(fehler)[-300:]}")
            rest.append(zeile)
            continue
        titel = (json.loads(daten.read_text(encoding="utf-8")).get("reise") or {}).get("titel", e["ordner"])
        if mit_konto:
            try:
                konten.verknuepfen(auftrag["konto_id"], e["ordner"], e["person"])
                eingeladen = set(e.get("eingeladen") or [])
                for x in auftrag.get("einladen") or []:
                    if x["schluessel"] in eingeladen:
                        continue
                    konten.einladen(e["ordner"], x["schluessel"], x["email"], x["rolle"], x["name"], e["name"],
                                    titel=titel, seite=links["Seite"])
                    eingeladen.add(x["schluessel"])
                    e["eingeladen"] = sorted(eingeladen)
            except konten.KontoFehler as f:
                fehlschlaege += 1
                print(f"FEHLER: {e['ordner']}: Konto oder Einladung: {f}")
                rest.append(json.dumps(e, ensure_ascii=False))
                continue
            n = len(auftrag.get("einladen") or [])
            rm.meldung_anlegen(rm.ordner_neu(anlegen=True), [e["name"]], "neue_reise", e["ordner"],
                               f"Deine neue Reise „{titel}“ ist angelegt (Status Idee) und steht in meine_reisen. "
                               f"Seite: {links['Seite']}"
                               + (f" · Einladungen per Mail an {n} {'Person' if n == 1 else 'Personen'} verschickt."
                                  if n else ""), auftraege=[e["aid"]])
        else:
            rm.meldung_anlegen(rm.ordner_neu(anlegen=True), [e["name"]], "neue_reise", e["ordner"],
                               f"Deine neue Reise „{titel}“ ist angelegt (Status Idee). Seite: {links['Seite']} · Link für "
                               f"die Claude-App, nur für dich, einmal als eigenen Konnektor eintragen: {links['Claude-App']}",
                               auftraege=[e["aid"]])
        print(f"Zugestellt: {e['ordner']} an {e['name']}")
    p.write_text("".join(z + "\n" for z in rest), encoding="utf-8")
    return fehlschlaege


def _werte(routen, bezug, merkmal):
    """Werte eines Merkmals an einer Unterkunft (U-…), Strecke oder Option in routen.yaml -> Liste (je Datum mehrere)."""
    def suche(x):
        if isinstance(x, dict):
            if x.get("id") == bezug:
                return x
            if isinstance(x.get(bezug), dict):
                return x[bezug]
            for v in x.values():
                if (t := suche(v)) is not None:
                    return t
        elif isinstance(x, list):
            for v in x:
                if (t := suche(v)) is not None:
                    return t
        return None
    knoten = suche(routen) or {}
    m = (knoten.get("merkmale") or {}).get(merkmal)
    if m is None:
        # Eine Option ohne eigenen Wert zeigt den Wert der verknüpften Unterkunft oder Strecke (routen.py)
        for feld in ("unterkuenfte", "strecken"):
            if isinstance(knoten.get(feld), list) and knoten[feld]:
                return _werte(routen, knoten[feld][0], merkmal)
    return [e.get("wert") if isinstance(e, dict) else e for e in (m if isinstance(m, list) else [m])]


def regeln(wurzel, arbeit, paare, alt=None):
    """Regeln, die sonst nur in der Anleitung für Claude stehen, nach dem Lauf maschinell prüfen -> Liste der Verstöße.
    paare: [(reise, id)] dieses Laufs; alt(pfad): Inhalt vor dem Lauf (Vorgabe: git show HEAD:pfad in der Arbeitskopie).
    - Konflikt (Auftrag mit Status konflikt): es muss eine neue offene Frage (neue F-ID) dazukommen, die die Auftrags-ID nennt.
    - Prüfauftrag des Wächters: die geprüften Werte bleiben, wie sie waren (bei Abweichung kommt eine offene Frage)."""
    import re
    import subprocess
    import yaml
    rm = _engine(wurzel)
    arbeit = Path(arbeit)

    def vorher(pfad):
        if alt:
            return alt(pfad)
        r = subprocess.run(["git", "-C", str(arbeit), "show", f"HEAD:{pfad}"], capture_output=True, text=True)
        return r.stdout if r.returncode == 0 else ""

    def nachher(pfad):
        p = arbeit / pfad
        return p.read_text(encoding="utf-8") if p.exists() else ""

    verstoesse = []
    for reise, aid in paare:
        o = rm.ordner(reise)
        a = next((x for x in rm.auftraege(o) if x["id"] == aid), None) if o else None
        if a is None:
            continue
        if a["status"] == "konflikt":
            pfad = f"reisen/{reise}/offene-fragen.md"
            v, n = vorher(pfad), nachher(pfad)
            neue_f = set(re.findall(r"\bF-\d+\b", n)) - set(re.findall(r"\bF-\d+\b", v))
            dazu = "\n".join(set(n.splitlines()) - set(v.splitlines()))
            if not neue_f or aid not in dazu:
                verstoesse.append(f"{reise} {aid}: Konflikt ohne neue offene Frage, die {aid} nennt.")
        pruefung = (a.get("daten") or {}).get("pruefung") or []
        if pruefung:
            pfad = f"reisen/{reise}/plan/routen.yaml"
            v, n = (yaml.safe_load(t) or {} for t in (vorher(pfad), nachher(pfad)))
            for t in pruefung:
                w1, w2 = _werte(v, t["bezug"], t["merkmal"]), _werte(n, t["bezug"], t["merkmal"])
                if w1 != w2:
                    verstoesse.append(f"{reise} {aid}: {t['bezug']} {t['merkmal']} wurde geändert ({w1} → {w2}); bei einem "
                                      "Prüfauftrag bleibt der Wert, eine Abweichung wird eine offene Frage.")
    return verstoesse


def _zeit(text):
    try:
        t = datetime.datetime.fromisoformat(text)
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=datetime.timezone.utc)


def wartezeit(wurzel, gesehen, jetzt=None):
    """Sekunden bis zum Start: je Reise ‚neueste neue Eingabe + Sammelzeit‘, aber nie später als
    ‚älteste neue Eingabe + Obergrenze‘, damit ein stetiger Strom von Eingaben nicht ewig aufschiebt.
    Gilt das Maximum über die Reisen mit Neuem."""
    jetzt = jetzt or datetime.datetime.now(datetime.timezone.utc)
    je_minute = float(os.environ.get("EA_SEKUNDEN_JE_MINUTE", "60"))
    obergrenze = float(os.environ.get("FR_MAX_WARTEN_MIN", "20")) * je_minute
    je_reise = {}
    for reise, _id, erstellt in neu(wurzel, gesehen):
        t = _zeit(erstellt)
        if t is not None:
            je_reise.setdefault(reise, []).append(t)
    rest = 0.0
    for reise, zeiten in je_reise.items():
        ziel = min(max(zeiten) + datetime.timedelta(seconds=sammelzeit_minuten(wurzel, reise) * je_minute),
                   min(zeiten) + datetime.timedelta(seconds=obergrenze))
        rest = max(rest, (ziel - jetzt).total_seconds())
    return max(0, int(rest + 0.999))


def versuch(datei, maximal, ids):
    p = Path(datei)
    zaehler = {}
    if p.exists():
        for zeile in p.read_text(encoding="utf-8").splitlines():
            teile = zeile.split()
            if len(teile) == 2 and teile[1].isdigit():
                zaehler[teile[0]] = int(teile[1])
    for i in ids:
        zaehler[i] = zaehler.get(i, 0) + 1
    p.write_text("".join(f"{k} {v}\n" for k, v in sorted(zaehler.items())), encoding="utf-8")
    return [i for i in ids if zaehler[i] >= maximal]


def kosten(logdatei):
    """-> (usd oder None, fehler)"""
    try:
        d = json.loads(Path(logdatei).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None, False
    if not isinstance(d, dict):
        return None, False
    usd = d.get("total_cost_usd")
    return (usd if isinstance(usd, (int, float)) else None), bool(d.get("is_error"))


def protokoll(datei, felder):
    zeile = {"zeit": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
    for f in felder:
        k, _, v = f.partition("=")
        try:
            zeile[k] = int(v)
        except ValueError:
            try:
                zeile[k] = float(v)
            except ValueError:
                zeile[k] = v
    with open(datei, "a", encoding="utf-8") as f:
        f.write(json.dumps(zeile, ensure_ascii=False) + "\n")


def main(a):
    if a[:1] == ["neu"] and len(a) == 3:
        for z in neu(a[1], a[2]):
            print(*z)
    elif a[:1] == ["warten"] and len(a) == 3:
        print(wartezeit(a[1], a[2]))
    elif a[:1] == ["versuch"] and len(a) >= 4:
        for i in versuch(a[1], int(a[2]), a[3:]):
            print(i)
    elif a[:1] == ["kosten"] and len(a) == 2:
        usd, fehler = kosten(a[1])
        print("" if usd is None else usd)
        return 3 if fehler else 0
    elif a[:1] == ["protokoll"] and len(a) >= 3:
        protokoll(a[1], a[2:])
    elif a[:1] == ["neue_reisen"] and len(a) >= 4:
        angelegt, fehler = neue_reisen(a[1], a[2], a[4:])
        with open(a[3], "a", encoding="utf-8") as f:
            for z in angelegt:
                f.write(json.dumps(z, ensure_ascii=False) + "\n")
                print("angelegt", z["ordner"], z["aid"])
        for aid, grund in fehler:
            print("fehler", aid, " ".join(grund.split()))
    elif a[:1] == ["ausstehend"] and len(a) == 3:
        return 5 if ausstehend(a[1], a[2]) else 0
    elif a[:1] == ["regeln"] and len(a) >= 3:
        v = regeln(a[1], a[2], [tuple(x.split("/", 1)) for x in a[3:]])
        for x in v:
            print(x)
        return 4 if v else 0
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
