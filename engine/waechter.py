#!/usr/bin/env python3
"""Wächter und Erinnerer (Paket E, Issue #11; Baustein waechter, docs/produkt.md und docs/waechter.md).

Die KI wacht über das, was sich ändern kann, und meldet, was ansteht. Niemand muss selbst daran denken.

Wächter   Findet veränderliche Angaben (Merkmale mit veraenderlich: true) der Optionen im Plan und der Unterkünfte mit
          Nächten, die noch nie geprüft wurden oder deren Prüfdatum älter ist als regeln.waechter_frist_tage, und
          meldet jede den Organisator:innen (Art pruefung). Nachschlagen tut der AI-Client im Gespräch; Frieda hat
          keine eigene KI (ADR-0001, Paket O-4). Weicht ein Wert ab, wird er NICHT still übernommen.
Erinnerer Meldet Fristen und „ab“-Termine der Aufgaben an die Zuständigen und erinnert die Organisator:innen an den
          Wechsel des Reisestatus am Start- und Enddatum (die KI wechselt nie selbst).

Beides gilt nur, wenn der Baustein waechter eingeschaltet ist und der Status es zulässt (fest, unterwegs; Aufgabenfristen
zählen erst ab fest). Meldungen gehen an meldungen.jsonl der Ablage; der Konnektor zeigt sie im Überblick und unter
rueckmeldungen (Kanal app). Eine Sammelnachricht für den Betreiber (Kanal nachricht) schreibt `lauf --bericht`.
Gleiche Meldungen werden nicht doppelt angelegt (schluessel).

Aufrufe:
  python3 engine/waechter.py zeige <reise> [--heute JJJJ-MM-TT]           zeigt, was anstünde, ändert nichts
  python3 engine/waechter.py lauf [<reise>…] [--heute JJJJ-MM-TT] [--bericht DATEI]
        legt Meldungen an (ohne Reise: alle Reisen der Ablage); --bericht schreibt die
        Sammelnachricht für den Betreiber in DATEI, falls es etwas zu melden gibt und eine Reise den Kanal
        nachricht hat
  python3 engine/waechter.py rot-melden --reisen <a,b> --seit JJJJ-MM-TTTHH:MM:SSZ
        Meldung an die Organisator:innen jeder Reise, die seit diesem Zeitpunkt nicht veröffentlicht werden kann
        (betrieb/veroeffentlichen.sh, Issue #142); je Reise und Zeitpunkt nur einmal
Umgebung: RM_ABLAGE, RM_SEITEN oder KN_SEITEN (Standard aus engine/instanz.py)
"""
import datetime
import json
import os
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reise as rg  # noqa: E402
import rueckmeldungen as rm  # noqa: E402

UNGUELTIG = ("verworfen", "ersetzt")      # Optionen, die niemand mehr nachschlagen muss
MAX_PRUEFUNGEN = 15                       # Prüfmeldungen je Lauf, damit der Überblick lesbar bleibt
WIEDERHOLEN_TAGE = 7                      # überfällige Aufgaben und ein verpasster Statuswechsel melden sich so oft neu


def datum_de(iso):
    d = datetime.date.fromisoformat(str(iso)[:10])
    return f"{d.day}.{d.month}.{d.year}"


def tage_zwischen(von, bis):
    return (bis - von).days


def veroeffentlicht(reise):
    """Die veröffentlichte Seite (daten.json) oder None."""
    try:
        return json.loads((rm.seiten() / reise / "daten.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def aktiv(d):
    """Arbeitet der Wächter bei dieser Reise? -> (True, "") oder (False, Grund)."""
    rs = (d or {}).get("reise") or {}
    bausteine = rs.get("bausteine")
    if bausteine is not None and "waechter" not in bausteine:
        return False, "Der Baustein waechter ist ausgeschaltet."
    status = (rs.get("status") or {}).get("wert")
    if not rg.verhalten(status)["waechter"]:
        return False, f"Beim Status {status or 'planung'} wacht der Wächter nicht (erst ab fest)."
    return True, ""


def regel(d, name):
    return (((d or {}).get("reise") or {}).get("regeln") or {}).get(name, rg.VORGABEN[name])


# ---------- Wächter: veränderliche Angaben ----------

def zu_pruefen(d, heute, frist_tage):
    """Veränderliche Angaben, die noch nie oder zu lange nicht geprüft wurden -> Liste, zuerst die nie geprüften, dann die
    ältesten: {bezug, titel, merkmal, name, wert, geprueft, quelle, alter_tage, grund}."""
    r = (d or {}).get("route") or {}
    treffer = []

    def stufe(d, typ):   # wie routen.stufe_von: Stufe je Reise, ggf. je Unterkunftstyp („*“ für alle übrigen)
        s = d.get("stufe", "empfohlen")
        return s.get(str(typ or "").strip().lower(), s.get("*", "empfohlen")) if isinstance(s, dict) else s

    def pruefe(bezug, titel, merkmale, kriterien, typ=None):
        defs = {k["id"]: k for k in kriterien or []}
        for k, m in (merkmale or {}).items():
            if not defs.get(k, {}).get("veraenderlich") or m.get("auto") or stufe(defs[k], typ) == "aus":
                continue
            # Werte je Datum (docs/alternativen.md): der Hauptwert und jeder Eintrag mit „gilt“ hat sein eigenes Prüfdatum
            for e in [m] + list(m.get("je_datum") or []):
                g = e.get("geprueft")
                alter = tage_zwischen(datetime.date.fromisoformat(g), heute) if g else None
                if alter is not None and alter <= frist_tage:
                    continue
                gilt = ", ".join(datum_de(x) for x in e.get("gilt") or [])
                treffer.append({"bezug": bezug, "titel": titel, "merkmal": k,
                                "name": defs[k]["name"] + (f" am {gilt}" if gilt else ""), "wert": e.get("wert"),
                                "geprueft": g, "quelle": e.get("quelle"), "alter_tage": alter,
                                "grund": "noch nie geprüft" if g is None else f"zuletzt geprüft {datum_de(g)} (vor {alter} Tagen)"})

    for w in r.get("wahlstellen") or []:
        for o in w["optionen"]:
            if o["aktiv"] and o["status"] not in UNGUELTIG:
                pruefe(o["id"], f"{w['titel']} › {o['titel']}", o.get("merkmale"), w.get("kriterien"))
    def lage(bezug, titel, d):   # Lage (ADR-0004): Adresse und Punkt sind Aussagen mit Prüfdatum
        for feld, name in (("adresse", "Adresse"), ("punkt", "Koordinaten")):
            v = d.get(feld)
            if not isinstance(v, dict) or not v.get("wert"):
                continue
            g = v.get("geprueft")
            alter = tage_zwischen(datetime.date.fromisoformat(g), heute) if g else None
            if alter is not None and alter <= frist_tage:
                continue
            treffer.append({"bezug": bezug, "titel": titel, "merkmal": feld, "name": name, "wert": str(v["wert"]), "geprueft": g,
                            "quelle": v.get("quelle"), "alter_tage": alter,
                            "grund": "noch nie geprüft" if g is None else f"zuletzt geprüft {datum_de(g)} (vor {alter} Tagen)"})

    for uid, u in (r.get("unterkuenfte") or {}).items():
        if u.get("naechte"):   # Merkmale der Art der Unterkunft (plan/arten.yaml)
            pruefe(uid, u.get("name") or uid, u.get("merkmale"), (r.get("merkmale") or {}).get(u.get("art")), u.get("art"))
            lage(uid, u.get("name") or uid, u)
    # Aufenthalte ohne Nacht und Strecken im Plan: dieselben Regeln (Abgleich 29.10.2026)
    for aid, a in (r.get("aufenthalte") or {}).items():
        if a.get("tage"):
            pruefe(aid, a.get("name") or aid, a.get("merkmale"), (r.get("merkmale") or {}).get(a.get("art")), a.get("art"))
            lage(aid, a.get("name") or aid, a)
    for sid in r.get("aktiv_strecken") or []:
        s_ = (r.get("strecken") or {}).get(sid) or {}
        if s_.get("merkmale"):
            pruefe(sid, s_.get("titel") or sid, s_.get("merkmale"), (r.get("merkmale") or {}).get(s_.get("art_schluessel")), s_.get("art_schluessel"))
    treffer.sort(key=lambda t: (t["alter_tage"] is not None, -(t["alter_tage"] or 0), t["bezug"], t["merkmal"]))
    return treffer


def pruefmeldungen(d, items, frist_tage):
    """Je zu prüfender Angabe eine Meldung an die Organisator:innen (ADR-0001, Paket O-4: der Wächter meldet, der
    AI-Client schlägt nach; kein KI-Lauf in Frieda). Höchstens MAX_PRUEFUNGEN je Lauf, die ältesten zuerst; dieselbe
    Angabe wird frühestens nach frist_tage wieder gemeldet."""
    an = organisator_von(d)
    aus = []
    for t in items[:MAX_PRUEFUNGEN]:
        text = (f"{t['bezug']} {t['titel']}, {t['name']}: {t['wert']} ist {t['grund']}"
                + (f"; bisherige Quelle: {t['quelle']}" if t.get("quelle") else "")
                + ". Bitte im Gespräch nachschlagen und mit Prüfdatum und Quelle eintragen. Weicht der Wert ab, "
                "entscheidet ein:e Organisator:in; nichts wird still übernommen.")
        aus.append({"an": an, "art": "pruefung", "ziel": t["bezug"], "bezug": t["bezug"], "text": text,
                    "schluessel": f"pruefung:{t['bezug']}:{t['merkmal']}:{t['name']}", "wiederholen": frist_tage})
    return aus


# ---------- Erinnerer: Fristen, „ab“-Termine, Statuswechsel ----------

def organisator_von(d):
    return [p["name"] for p in ((d or {}).get("reise") or {}).get("personen") or [] if rg.rolle_neu(p.get("rolle")) == "organisator"]


def empfaenger(d, zustaendig):
    """Zuständige Person (Vorname wie in reise.yaml) oder alle Organisator:innen, wenn niemand oder jemand Unbekanntes zuständig ist."""
    for p in ((d or {}).get("reise") or {}).get("personen") or []:
        if zustaendig and p["name"].casefold() == zustaendig.strip().casefold():
            return [p["name"]]
    return organisator_von(d)


def erinnerungen(d, aufgaben, heute, vorlauf):
    """Meldungen zu Fristen und „ab“-Terminen offener Aufgaben -> [{schluessel, an, art, ziel, text, bezug, wiederholen}].
    Nur wenn der Status Fristen zählen lässt (fest, unterwegs)."""
    if not rg.verhalten(((d or {}).get("reise") or {}).get("status", {}).get("wert"))["fristen"]:
        return []
    aus = []
    for a in aufgaben or []:
        if a["status"] not in ("offen", "in_arbeit"):
            continue
        an = empfaenger(d, a.get("zustaendig"))
        if a.get("frist"):
            rest = tage_zwischen(heute, datetime.date.fromisoformat(a["frist"]))
            if rest < 0:
                aus.append({"schluessel": f"ueberfaellig:{a['id']}:{a['frist']}", "wiederholen": WIEDERHOLEN_TAGE,
                            "text": f"Überfällig seit {-rest} Tag(en): {a['id']} {a['titel']} (Frist {datum_de(a['frist'])})."})
            elif rest <= vorlauf:
                aus.append({"schluessel": f"frist:{a['id']}:{a['frist']}", "wiederholen": None,
                            "text": f"Frist {'heute' if rest == 0 else 'in ' + str(rest) + ' Tag(en)'}: {a['id']} {a['titel']} "
                                    f"(Frist {datum_de(a['frist'])})."})
        if a.get("ab") and datetime.date.fromisoformat(a["ab"]) <= heute:
            aus.append({"schluessel": f"ab:{a['id']}:{a['ab']}", "wiederholen": None,
                        "text": f"Jetzt möglich (ab {datum_de(a['ab'])}): {a['id']} {a['titel']}."})
        for m in aus:
            m.setdefault("an", an)
            m.setdefault("art", "erinnerung")
            m.setdefault("ziel", a["id"])
            m.setdefault("bezug", a["id"])
    return aus


def buchungsfristen(d, heute, vorlauf):
    """Fristen und Stornofristen der Buchungen (B-…, #76) wie Aufgabenfristen: an die Person, die gebucht hat, sonst an die
    Organisator:innen. Nur ab Status fest."""
    if not rg.verhalten(((d or {}).get("reise") or {}).get("status", {}).get("wert"))["fristen"]:
        return []
    aus = []
    for b in (((d or {}).get("route") or {}).get("buchungen") or {}).values():
        if b.get("status") == "storniert":
            continue
        an = empfaenger(d, b.get("wer"))
        titel = f"{b['id']} {b.get('titel') or ''}".strip()
        neu = []
        if b.get("frist"):
            rest = tage_zwischen(heute, datetime.date.fromisoformat(b["frist"]))
            was = b.get("frist_was") or "Frist"
            if rest < 0:
                neu.append({"schluessel": f"ueberfaellig:{b['id']}:{b['frist']}", "wiederholen": WIEDERHOLEN_TAGE,
                            "text": f"Überfällig seit {-rest} Tag(en): {was} zur Buchung {titel} (Frist {datum_de(b['frist'])})."})
            elif rest <= vorlauf:
                neu.append({"schluessel": f"frist:{b['id']}:{b['frist']}", "wiederholen": None,
                            "text": f"Frist {'heute' if rest == 0 else 'in ' + str(rest) + ' Tag(en)'}: {was} zur Buchung {titel} "
                                    f"(Frist {datum_de(b['frist'])})."})
        if b.get("ab") and datetime.date.fromisoformat(b["ab"]) <= heute:   # Issue #135: ab wann etwas geht (Check-in, Sitzplatzwahl)
            neu.append({"schluessel": f"ab:{b['id']}:{b['ab']}", "wiederholen": None,
                        "text": f"Jetzt möglich (ab {datum_de(b['ab'])}): {b.get('ab_was') or 'etwas'} zur Buchung {titel}."})
        if b.get("storno_bis"):
            rest = tage_zwischen(heute, datetime.date.fromisoformat(b["storno_bis"]))
            if 0 <= rest <= vorlauf:
                neu.append({"schluessel": f"storno:{b['id']}:{b['storno_bis']}", "wiederholen": None,
                            "text": f"Kostenlos stornieren geht nur noch {'heute' if rest == 0 else 'bis ' + datum_de(b['storno_bis'])}: "
                                    f"Buchung {titel}" + (f" ({b['storno']})" if b.get("storno") else "") + "."})
        for m in neu:
            m.update({"an": an, "art": "erinnerung", "ziel": b["id"], "bezug": b["id"]})
        aus += neu
    return aus


def statuswechsel(d, heute):
    """Erinnert die Organisator:innen, wenn der Status nicht mehr zu den Reisetagen passt. Die KI wechselt den Status nie selbst."""
    tage = ((d or {}).get("route") or {}).get("tage") or []
    st = (((d or {}).get("reise") or {}).get("status") or {}).get("wert")
    if not tage or st not in ("fest", "unterwegs"):
        return []
    start, ende = datetime.date.fromisoformat(tage[0]["datum"]), datetime.date.fromisoformat(tage[-1]["datum"])
    if heute > ende:
        ziel, text = "danach", f"Die Reise war am {datum_de(ende.isoformat())} zu Ende, der Status steht noch auf {st}."
    elif st == "fest" and heute >= start:
        ziel, text = "unterwegs", f"Die Reise hat am {datum_de(start.isoformat())} begonnen, der Status steht noch auf fest."
    else:
        return []
    return [{"schluessel": f"status:{st}:{ziel}", "wiederholen": WIEDERHOLEN_TAGE, "an": organisator_von(d), "art": "status",
             "ziel": "reise", "bezug": "reise", "extra": {"status_bei": st},
             "text": f"{text} Soll er auf {ziel} wechseln? Das entscheidet ein:e Organisator:in (reise_status_setzen in der Claude-App)."}]


def neue_meldungen(o, meldungen, jetzt, trocken=False):
    """Meldungen anlegen, die es (innerhalb ihrer Wiederholfrist) noch nicht gibt -> angelegte."""
    vorhanden = rm.meldungen(o)
    neu = []
    for m in meldungen:
        if not m["an"]:
            continue
        gleiche = [v for v in vorhanden if v.get("schluessel") == m["schluessel"]]
        if gleiche:
            if m["wiederholen"] is None:
                continue
            letzte = datetime.date.fromisoformat(gleiche[0]["erstellt"][:10])   # neueste zuerst
            if tage_zwischen(letzte, jetzt.date()) < m["wiederholen"]:
                continue
        if not trocken:
            rm.meldung_anlegen(o, m["an"], m["art"], m["ziel"], m["text"], schluessel=m["schluessel"], bezug=m["bezug"],
                               zeit=jetzt, extra=m.get("extra"))
        neu.append(m)
    return neu


# ---------- Lauf ----------

def bericht_text(reise, d, neu, items):
    titel = ((d or {}).get("reise") or {}).get("titel") or reise
    z = [f"{titel}:"]
    for m in neu:
        z.append(f"- {', '.join(m['an'])}: {m['text']}")
    offen = len(items) - sum(1 for m in neu if m["art"] == "pruefung")
    if offen > 0 and any(m["art"] == "pruefung" for m in neu):
        z.append(f"- Wächter: {offen} weitere veränderliche Angaben sind zu prüfen (gemeldet oder folgen im nächsten Lauf).")
    return "\n".join(z)


def lauf_reise(reise, heute=None, trocken=False):
    """Einen Durchgang für eine Reise -> {"aktiv", "grund", "meldungen", "zu_pruefen", "bericht", "nachricht"}."""
    jetzt = datetime.datetime.combine(heute, datetime.datetime.now().time(), datetime.timezone.utc) if heute \
        else datetime.datetime.now(datetime.timezone.utc)
    heute = heute or jetzt.date()
    d, o = veroeffentlicht(reise), rm.ordner(reise)
    ergebnis = {"aktiv": False, "grund": "", "meldungen": [], "zu_pruefen": [], "bericht": "", "nachricht": False}
    if d is None or o is None:
        ergebnis["grund"] = "Reise ist nicht veröffentlicht oder nimmt keine Eingaben an."
        return ergebnis
    ok, grund = aktiv(d)
    ergebnis["grund"] = grund
    if not ok:
        return ergebnis
    ergebnis["aktiv"] = True
    frist = regel(d, "waechter_frist_tage")
    items = zu_pruefen(d, heute, frist)
    ergebnis["zu_pruefen"] = items
    wunsch = (erinnerungen(d, rm.aufgaben(o), heute, regel(d, "erinnerung_vorlauf_tage"))
              + buchungsfristen(d, heute, regel(d, "erinnerung_vorlauf_tage")) + statuswechsel(d, heute)
              + pruefmeldungen(d, items, frist))
    ergebnis["meldungen"] = neue_meldungen(o, wunsch, jetzt, trocken)
    ergebnis["nachricht"] = "nachricht" in regel(d, "meldekanal")
    if ergebnis["meldungen"]:
        ergebnis["bericht"] = bericht_text(reise, d, ergebnis["meldungen"], items)
    return ergebnis


def rot_melden(reisen, seit):
    """Issue #142: Kann eine Reise seit `seit` (UTC, JJJJ-MM-TTTHH:MM:SSZ, Beginn der Rot-Phase) nicht veröffentlicht werden
    (Baufehler), bekommen ihre Organisator:innen eine Meldung (Art betrieb: unabhängig vom Baustein waechter). Der Schlüssel enthält seit: je Reise und Rot-Phase genau eine
    Meldung, jeder weitere Aufruf ist gefahrlos. Aufgerufen von betrieb/veroeffentlichen.sh -> angelegte Meldungen."""
    zeit = datetime.datetime.strptime(seit, "%Y-%m-%dT%H:%M:%SZ")
    jetzt = datetime.datetime.now(datetime.timezone.utc)
    neu = []
    for reise in reisen:
        d, o = veroeffentlicht(reise), rm.ordner(reise)
        if d is None or o is None:
            continue
        titel = ((d.get("reise") or {}).get("titel")) or reise
        text = (f"„{titel}“ kann seit {datum_de(seit)} um {zeit:%H:%M} Uhr (UTC) nicht veröffentlicht werden: Beim Bauen der "
                f"Seite ist ein Fehler aufgetreten, ein Eintrag passt nicht zu den Regeln der Prüfung. Der Betrieb ist informiert. "
                f"Bis das behoben ist, bleibt die Seite auf dem letzten guten Stand.")
        neu += neue_meldungen(o, [{"schluessel": f"veroeffentlichen-rot:{reise}:{seit}", "wiederholen": None,
                                   "an": organisator_von(d), "art": "betrieb", "ziel": "reise", "bezug": "reise",
                                   "text": text}], jetzt)
    return neu


def alle_reisen():
    return sorted(p.name for p in rm.ablage().iterdir() if p.is_dir() and rm.REISE_MUSTER.match(p.name)) \
        if rm.ablage().is_dir() else []


def zeige(reise, heute):
    d = veroeffentlicht(reise)
    if d is None:
        print(f"{reise}: nicht veröffentlicht.")
        return
    ok, grund = aktiv(d)
    print(f"{reise}: " + ("Wächter aktiv" if ok else grund))
    if not ok:
        return
    items = zu_pruefen(d, heute, regel(d, "waechter_frist_tage"))
    print(f"Zu prüfen ({len(items)}, Frist {regel(d, 'waechter_frist_tage')} Tage):")
    for t in items:
        print(f"  {t['bezug']} {t['name']}: {t['wert']} – {t['grund']}")
    o = rm.ordner(reise)
    vorlauf = regel(d, "erinnerung_vorlauf_tage")
    for m in erinnerungen(d, rm.aufgaben(o) if o else [], heute, vorlauf) + buchungsfristen(d, heute, vorlauf) + statuswechsel(d, heute):
        print(f"  Meldung an {', '.join(m['an']) or '–'}: {m['text']}")


def lauf(reisen, heute, bericht):
    texte = []
    for reise in reisen or alle_reisen():
        r = lauf_reise(reise, heute)
        if not r["aktiv"]:
            print(f"{reise}: {r['grund']}")
            continue
        print(f"{reise}: {len(r['meldungen'])} neue Meldung(en), {len(r['zu_pruefen'])} Angabe(n) zu prüfen")
        if r["bericht"] and r["nachricht"]:
            texte.append(r["bericht"])
    if bericht and texte:
        Path(bericht).write_text("\n\n".join(texte) + "\n", encoding="utf-8")


def main(a):
    heute = None
    if "--heute" in a:
        i = a.index("--heute")
        try:
            heute = datetime.date.fromisoformat(a[i + 1])
        except (IndexError, ValueError):
            sys.exit("--heute braucht ein Datum JJJJ-MM-TT.")
        a = a[:i] + a[i + 2:]
    bericht = None
    if "--bericht" in a:
        i = a.index("--bericht")
        if i + 1 >= len(a):
            sys.exit("--bericht braucht eine Datei.")
        bericht = a[i + 1]
        a = a[:i] + a[i + 2:]
    if a[:1] == ["rot-melden"]:
        try:
            reisen = [r for r in a[a.index("--reisen") + 1].split(",") if r]
            seit = a[a.index("--seit") + 1]
            datetime.datetime.strptime(seit, "%Y-%m-%dT%H:%M:%SZ")
        except (ValueError, IndexError):
            sys.exit("rot-melden braucht --reisen <a,b> und --seit JJJJ-MM-TTTHH:MM:SSZ.")
        for m in rot_melden(reisen, seit):
            print(f"Meldung an {', '.join(m['an'])}: {m['schluessel']}")
        return 0
    if a[:1] == ["zeige"] and len(a) == 2:
        zeige(a[1], heute or datetime.date.today())
    elif a[:1] == ["lauf"]:
        lauf(a[1:], heute, bericht)
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
