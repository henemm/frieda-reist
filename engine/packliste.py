"""Packliste: Gegenstände (G-…) einer Reise, ihre Kategorien, Summen und der Packstand (ADR-0010, Issue #370).

Ein Gegenstand ist eine Grundform wie die Buchung oder der Aufenthalt: feste ID (G-01 …), Art, Titel, Merkmale, Verlauf. Seine
Art ist die Kategorie der Packliste (Kleidung, Schlafen, Küche …); sie gehört der Reise (plan/arten.yaml, grundform: gegenstand),
die Software kennt keine. Die Gegenstände stehen in plan/packliste.yaml der Reise:

  gegenstaende:
    - id: G-01
      art: kleidung               # Pflicht: eine Art mit Grundform gegenstand
      titel: Regenjacke           # Pflicht
      merkmale: {gewicht: 420}    # Werte der Merkmale der Art (wie bei jedem Ding; Herkunft und Prüfdatum, wo die Art es verlangt)
      an: E-04                    # Elternbezug (ADR-0007): Strecke, Aufenthalt, Unterkunft oder Ort, nie ein Tag
      wer: Ida                    # Person der Reise, die ihn packt; ohne wer packt ihn jede Person für sich
      notiz: "…"
      status: entfaellt           # nur, wenn er wegfällt; gelöscht wird nie
      verlauf: [{datum: …, wer: …, was: …, grund: …}]

Eine Herkunft (quelle) braucht ein Gegenstand nicht: eine Regenjacke hat keine (ausdrückliche Ausnahme von ADR-0001, Punkt 5, im
ADR-0010 begründet). Merkmale mit veraenderlich: true behalten ihr Prüfdatum.

Der Packstand (abgehakt, je Person) liegt nicht hier, sondern live beim Rückmeldedienst (packstand.json, engine/rueckmeldungen.py),
damit Abhaken ohne Netz ohne Verlaufseintrag je Haken geht.

Summen: Jedes Merkmal einer Art mit der Rolle summe (oder dem Alias kosten, Typ zahl oder geld) wird je Kategorie und gesamt
summiert, mit der Einheit des Merkmals (bei Geld mit der Währung des Werts). Gegenstände mit dem Status entfaellt zählen nicht.
Der Wert eines Eintrags gilt für den ganzen Eintrag („Socken, 240 g“), er wird nicht mit einer Anzahl multipliziert.
"""
import datetime
import re

import texte
from routen import SUMMEN_ROLLEN, ist

GEGENSTAND_STATUS = ("entfaellt",)       # aktiv ist, wer keinen Status hat
FELDER = ("id", "art", "titel", "merkmale", "an", "wer", "notiz", "status", "verlauf", "quelle")
ELTERN = ("strecke", "aufenthalt", "unterkunft", "ort")   # Elternbezug eines Gegenstands (kein Tag, ADR-0007)
DATEI = "packliste.yaml"
MAX_TITEL = 120
MAX_NOTIZ = 500


def betrag(text):
    """Geldbetrag aus einem Text („35 €“, „12,50 EUR“, „1.200 €“) -> (Zahl, Währung) oder None. Wie die Seite (betrag in der Vorlage):
    ohne Währung oder Zahl kein Betrag; bei einer Spanne gilt der erste Betrag nicht, sie ist keine Summe."""
    t = str(text).split("(")[0]
    w = re.search(r"[€$£¥₩]|\b(?:EUR|USD|JPY|KRW|CHF|GBP)\b", t)
    m = re.search(r"\d[\d.,]*", t)
    if not (w and m) or re.search(r"\d\s*[–-]\s*\d", t):
        return None
    z = m.group(0)
    z = re.sub(r"[.,](?=\d{3}(\D|$))", "", z).replace(",", ".")
    try:
        return float(z), w.group(0)
    except ValueError:
        return None


def zahl_von(typ, wert):
    """Beitrag eines Werts zur Summe -> (Zahl, Einheit aus dem Wert oder None) oder None (nicht lesbar)."""
    if typ == "geld":
        b = betrag(wert)
        return b if b else None
    try:
        return float(str(wert).replace(",", ".")), None
    except ValueError:
        return None


def zahl_text(z, sprache=None):
    """Summe als Text in der Schreibweise der Sprache (ganze Zahlen ohne Nachkommastellen, sonst höchstens zwei)."""
    z = round(float(z), 2)
    s = str(int(z)) if z == int(z) else f"{z:.2f}".rstrip("0")
    return s.replace(".", texte.t(sprache or texte.aufruf_sprache(), "seite.auto.dezimaltrenner"))


def summieren(gegenstaende, merkmale):
    """Summen eines Merkmals über Gegenstände -> [{wert, einheit}] (eine Zeile je Einheit; bei Geld je Währung).
    gegenstaende: Einträge mit merkmale {id: {wert}}; merkmale: Definition {id, typ, einheit}. Nicht lesbare Werte zählen nicht."""
    je = {}
    fehlt = 0
    for g in gegenstaende:
        if g.get("status") == "entfaellt":
            continue
        w = (g.get("merkmale") or {}).get(merkmale["id"])
        if w is None:
            continue
        z = zahl_von(merkmale["typ"], w.get("wert"))
        if z is None:
            fehlt += 1
            continue
        einheit = z[1] or merkmale.get("einheit") or ""
        je[einheit] = je.get(einheit, 0) + z[0]
    return [{"wert": round(v, 4), "einheit": e} for e, v in je.items()], fehlt


def summen_merkmale(katalog_art):
    """Merkmale einer Art, die summiert werden: [{id, name, typ, einheit}] in der Reihenfolge der Definition."""
    return [{"id": k, "name": d["name"], "typ": d["typ"], "einheit": d.get("einheit") or ""}
            for k, d in (katalog_art or {}).items() if d.get("rolle") in SUMMEN_ROLLEN]


def pruefen_und_bauen(r, roh, personen, fehl, id_anlegen, quelle):
    """plan/packliste.yaml prüfen und für Seite und Konnektor aufbereiten.

    r: das Routen-Objekt der Reise (Arten, Katalog, Dinge, werte()); roh: geladenes YAML oder None; personen: Namen der Personen der
    Reise; fehl(satz): Baufehler; id_anlegen(id, wo): Kennung eintragen (doppelte IDs melden). -> dict für daten.json oder None,
    wenn es keine Datei gibt und keine Art mit Grundform gegenstand."""
    arten = {a: d for a, d in r.arten.items() if d["grundform"] == "gegenstand"}
    if roh is None and not arten:
        return None
    roh = roh if roh is not None else {}
    wo0 = quelle

    def melde(schluessel, **werte):
        fehl(texte.Satz(f"{wo0}: ") + texte.satz(schluessel, **werte))

    q_alt, r.q = r.q, quelle   # Meldungen aus werte() nennen die Datei der Packliste
    try:
        return _bauen(r, roh, arten, personen, melde, id_anlegen, quelle)
    finally:
        r.q = q_alt


def _bauen(r, roh, arten, personen, melde, id_anlegen, quelle):

    if not isinstance(roh, dict) or set(roh) - {"gegenstaende"}:
        melde("pruefung.packliste.form")
        roh = {}
    liste = roh.get("gegenstaende") or []
    if not isinstance(liste, list):
        melde("pruefung.packliste.liste")
        liste = []
    namen = {str(p).casefold(): str(p) for p in personen}
    dinge = {"strecke": r.strecken, "aufenthalt": r.aufenthalte, "unterkunft": r.unterkuenfte, "ort": r.orte}
    gesehen, aus = set(), []
    for i, g in enumerate(liste, 1):
        gid = g.get("id") if isinstance(g, dict) else None
        wo = f"Gegenstand {gid or '#' + str(i)}"
        if not isinstance(g, dict):
            melde("pruefung.packliste.eintrag", nr=i)
            continue
        if not ist("gegenstand", gid):
            melde("pruefung.packliste.id", wo=wo)
            continue
        if gid in gesehen:
            melde("pruefung.packliste.doppelt", gid=gid)
            continue
        gesehen.add(gid)
        id_anlegen(gid, quelle)
        if set(g) - set(FELDER):
            melde("pruefung.packliste.felder", wo=wo, w1=", ".join(sorted(set(g) - set(FELDER))), w2=", ".join(FELDER))
        art = g.get("art")
        if art not in arten:
            melde("pruefung.packliste.art", wo=wo, a=art, w1=", ".join(arten) or "–")
            continue
        titel = g.get("titel")
        if not (isinstance(titel, str) and titel.strip()) or len(titel) > MAX_TITEL:
            melde("pruefung.packliste.titel", wo=wo)
            continue
        an = g.get("an")
        an_name = None
        an_verworfen = False
        if an is not None:
            art_an = next((a for a in ELTERN if ist(a, an)), None)
            if art_an is None:
                melde("pruefung.packliste.an_art", wo=wo, x=an, w1=", ".join(ELTERN))
            elif an not in dinge[art_an]:
                melde("pruefung.packliste.an_unbekannt", wo=wo, x=an)
            else:
                d = dinge[art_an][an]
                an_name = (d.get("name") or d.get("titel") or an) if isinstance(d, dict) else an
                an_verworfen = r.nur_in_verworfenen(art_an, an)
                if an_verworfen:
                    r.warne(gid, texte.satz("pruefung.packliste.an_verworfen", gid=gid, x=an))
        wer = g.get("wer")
        if wer is not None:
            if not isinstance(wer, str) or wer.casefold() not in namen:
                melde("pruefung.packliste.wer", wo=wo, x=wer, w1=", ".join(namen.values()) or "–")
                wer = None
            else:
                wer = namen[wer.casefold()]
        if g.get("status") is not None and g["status"] not in GEGENSTAND_STATUS:
            melde("pruefung.packliste.status", wo=wo, w1=", ".join(GEGENSTAND_STATUS))
        notiz = g.get("notiz")
        if notiz is not None and (not isinstance(notiz, str) or len(notiz) > MAX_NOTIZ):
            melde("pruefung.packliste.notiz", wo=wo, n=MAX_NOTIZ)
            notiz = None
        verlauf = []
        for e in g.get("verlauf") or []:
            if not isinstance(e, dict) or not isinstance(e.get("datum"), datetime.date) or not e.get("wer") or not e.get("was"):
                melde("pruefung.packliste.verlauf", wo=wo)
                break
            verlauf.append({k: (v.isoformat() if isinstance(v, datetime.date) else str(v)) for k, v in e.items()})
        mk = g.get("merkmale")
        if mk is not None and not isinstance(mk, dict):
            melde("pruefung.packliste.merkmale", wo=wo)
            mk = None
        werte = r.werte(wo, mk, r.katalog.get(art, {})) if mk else {}
        aus.append({"id": gid, "art": art, "titel": titel.strip(), "merkmale": werte, "an": an, "an_name": an_name,
                    **({"an_verworfen": True} if an_verworfen else {}), "wer": wer, "notiz": notiz, "quelle": g.get("quelle"),
                    "status": g.get("status") or "aktiv", "verlauf": verlauf})
    kategorien, gesamt = [], {}
    for a, d in arten.items():
        je = [g for g in aus if g["art"] == a]
        defs = [{"id": k, **m, **({"summe": True} if m.get("rolle") in SUMMEN_ROLLEN else {})}
                for k, m in r.katalog.get(a, {}).items() if m.get("rolle") != "hero" and not m.get("auto")]
        summen = []
        for m in summen_merkmale(r.katalog.get(a)):
            s, nicht_lesbar = summieren(je, m)
            summen.append({"merkmal": m["id"], "name": m["name"], "summen": s, **({"unleserlich": nicht_lesbar} if nicht_lesbar else {})})
            for z in s:
                k = (m["id"], z["einheit"])
                gesamt.setdefault(k, {"merkmal": m["id"], "name": m["name"], "wert": 0, "einheit": z["einheit"]})["wert"] += z["wert"]
        kategorien.append({"art": a, "name": d["name"], "farbe": d["farbe"], "symbol": d["symbol"], "merkmale": defs,
                           "summen": summen, "gegenstaende": [g["id"] for g in je]})
    return {"kategorien": kategorien, "gegenstaende": aus,
            "summen": [{**v, "wert": round(v["wert"], 4)} for v in gesamt.values()]}


def packstand_zeilen(packliste, stand, person=None):
    """Wie viel hat eine Person gepackt? -> (gepackt, gesamt) über die aktiven Gegenstände, die sie packen muss: die ihr zugewiesenen (wer) und
    die ohne wer (jede Person packt sie für sich). Ohne Person zählen nur die zugewiesenen, für ihre Person. stand: {G-ID: {Person: Zeit}}."""
    gepackt = gesamt = 0
    for g in (packliste or {}).get("gegenstaende") or []:
        if g.get("status") == "entfaellt":
            continue
        if g.get("wer"):
            wer = g["wer"]
            if person and wer.casefold() != person.casefold():
                continue
        elif person:
            wer = person
        else:
            continue
        gesamt += 1
        if any(p.casefold() == wer.casefold() for p in stand.get(g["id"]) or {}):
            gepackt += 1
    return gepackt, gesamt
