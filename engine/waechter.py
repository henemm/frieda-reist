#!/usr/bin/env python3
"""Wächter und Erinnerer (Paket E, Issue #11; Baustein waechter, docs/produkt.md und docs/waechter.md).

Die KI wacht über das, was sich ändern kann, und meldet, was ansteht. Niemand muss selbst daran denken.

Wächter   Findet veränderliche Angaben (Merkmale mit veraenderlich: true) der Optionen im Plan und der Unterkünfte mit
          Nächten, die noch nie geprüft wurden oder deren Prüfdatum älter ist als regeln.waechter_frist_tage. Daraus
          wird ein Prüfauftrag (auftraege.jsonl, Name „Wächter“): Das Einarbeiten (Claude Code, im Betrieb)
          schlägt die Angaben nach und trägt Prüfdatum und Quelle ein. Weicht ein Wert ab, wird er NICHT still
          übernommen, sondern als offene Frage (F-…) gemeldet.
Erinnerer Meldet Fristen und „ab“-Termine der Aufgaben an die Zuständigen und erinnert die Organisator:innen an den
          Wechsel des Reisestatus am Start- und Enddatum (die KI wechselt nie selbst).

Beides gilt nur, wenn der Baustein waechter eingeschaltet ist und der Status es zulässt (fest, unterwegs; Aufgabenfristen
zählen erst ab fest). Meldungen gehen an meldungen.jsonl der Ablage; der Konnektor zeigt sie im Überblick und unter
rueckmeldungen (Kanal app). Eine Sammelnachricht für den Betreiber (Kanal nachricht) schreibt `lauf --bericht`.
Gleiche Meldungen werden nicht doppelt angelegt (schluessel).

Aufrufe:
  python3 engine/waechter.py zeige <reise> [--heute JJJJ-MM-TT]           zeigt, was anstünde, ändert nichts
  python3 engine/waechter.py lauf [<reise>…] [--heute JJJJ-MM-TT] [--bericht DATEI]
        legt Meldungen und den Prüfauftrag an (ohne Reise: alle Reisen der Ablage); --bericht schreibt die
        Sammelnachricht für den Betreiber in DATEI, falls es etwas zu melden gibt und eine Reise den Kanal
        nachricht hat
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
MAX_PRUEFUNGEN = 15                       # Angaben je Prüfauftrag (ein KI-Lauf kostet Geld)
PRUEF_ABSTAND_TAGE = 7                    # frühestens so lange nach dem letzten Prüfauftrag kommt der nächste
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
    kriterien = (r.get("merkmale") or {}).get("unterkunft")
    for uid, u in (r.get("unterkuenfte") or {}).items():
        if u.get("naechte"):
            pruefe(uid, u.get("name") or uid, u.get("merkmale"), kriterien, u.get("typ"))
    treffer.sort(key=lambda t: (t["alter_tage"] is not None, -(t["alter_tage"] or 0), t["bezug"], t["merkmal"]))
    return treffer


def pruefauftrag_text(items, frist_tage, heute):
    z = [f"Prüfauftrag des Wächters vom {datum_de(heute.isoformat())}: Diese veränderlichen Angaben sind noch nie geprüft "
         f"oder älter als {frist_tage} Tage. Jede nachschlagen (offizielle Quelle bevorzugen), danach:",
         "- Stimmt der Wert: Prüfdatum (heute) und Quelle (Link) an der Angabe eintragen.",
         "- Weicht er ab oder ist er nicht mehr zu finden: den bisherigen Wert NICHT ändern. Stattdessen eine offene Frage "
         "(F-…) anlegen, die alten und neuen Wert, Quelle und Datum nennt; die Organisator:innen entscheiden. Status rueckfrage.",
         "Angaben:"]
    z += [f"- {t['bezug']} {t['titel']}, {t['name']}: {t['wert']} ({t['grund']}"
          + (f"; bisherige Quelle: {t['quelle']}" if t.get("quelle") else "") + ")" for t in items]
    return "\n".join(z)


def pruefauftrag(reise, o, items, frist_tage, jetzt, trocken=False):
    """Prüfauftrag anlegen -> Auftrag oder None. Es gibt immer nur einen offenen Prüfauftrag, und frühestens
    PRUEF_ABSTAND_TAGE nach dem letzten."""
    if not items:
        return None
    frueher = [a for a in rm.auftraege(o) if (a.get("daten") or {}).get("pruefung")]
    if any(a["status"] == "neu" for a in frueher):
        return None
    if frueher and tage_zwischen(datetime.date.fromisoformat(frueher[0]["erstellt"][:10]), jetzt.date()) < PRUEF_ABSTAND_TAGE:
        return None
    items = items[:MAX_PRUEFUNGEN]
    e = {"id": f"A-{jetzt:%Y%m%d-%H%M%S}-{secrets.token_hex(2)}", "erstellt": jetzt.isoformat(timespec="seconds"),
         "name": "Wächter", "art": "Prüfung", "ziel": "allgemein", "text": pruefauftrag_text(items, frist_tage, jetzt.date()),
         "quelle": "Wächter", "daten": {"pruefung": [{k: t[k] for k in ("bezug", "merkmal", "wert", "geprueft", "quelle")}
                                                      for t in items], "frist_tage": frist_tage}}
    if not trocken:
        with (o / "auftraege.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
        rm.anstossen(o)
    return e


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
             "ziel": rg.REISE_ZIEL, "bezug": rg.REISE_ZIEL, "extra": {"status_bei": st},
             "text": f"{text} Soll er auf {ziel} wechseln? Das entscheidet ein:e Organisator:in (Auftrag an „reise“)."}]


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

def bericht_text(reise, d, neu, auftrag, items):
    titel = ((d or {}).get("reise") or {}).get("titel") or reise
    z = [f"{titel}:"]
    for m in neu:
        z.append(f"- {', '.join(m['an'])}: {m['text']}")
    if auftrag:
        z.append(f"- Wächter: {len(auftrag['daten']['pruefung'])} veränderliche Angaben werden nachgeschlagen"
                 + (f" (von {len(items)} zu prüfenden)" if len(items) > len(auftrag['daten']['pruefung']) else "") + ".")
    return "\n".join(z)


def lauf_reise(reise, heute=None, trocken=False):
    """Einen Durchgang für eine Reise -> {"aktiv", "grund", "meldungen", "auftrag", "zu_pruefen", "bericht", "nachricht"}."""
    jetzt = datetime.datetime.combine(heute, datetime.datetime.now().time(), datetime.timezone.utc) if heute \
        else datetime.datetime.now(datetime.timezone.utc)
    heute = heute or jetzt.date()
    d, o = veroeffentlicht(reise), rm.ordner(reise)
    ergebnis = {"aktiv": False, "grund": "", "meldungen": [], "auftrag": None, "zu_pruefen": [], "bericht": "", "nachricht": False}
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
    wunsch = erinnerungen(d, rm.aufgaben(o), heute, regel(d, "erinnerung_vorlauf_tage")) + statuswechsel(d, heute)
    ergebnis["meldungen"] = neue_meldungen(o, wunsch, jetzt, trocken)
    ergebnis["auftrag"] = pruefauftrag(reise, o, items, frist, jetzt, trocken)
    ergebnis["nachricht"] = "nachricht" in regel(d, "meldekanal")
    if ergebnis["meldungen"] or ergebnis["auftrag"]:
        ergebnis["bericht"] = bericht_text(reise, d, ergebnis["meldungen"], ergebnis["auftrag"], items)
    return ergebnis


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
    for m in erinnerungen(d, rm.aufgaben(o) if o else [], heute, regel(d, "erinnerung_vorlauf_tage")) + statuswechsel(d, heute):
        print(f"  Meldung an {', '.join(m['an']) or '–'}: {m['text']}")


def lauf(reisen, heute, bericht):
    texte = []
    for reise in reisen or alle_reisen():
        r = lauf_reise(reise, heute)
        if not r["aktiv"]:
            print(f"{reise}: {r['grund']}")
            continue
        print(f"{reise}: {len(r['meldungen'])} neue Meldung(en), {len(r['zu_pruefen'])} Angabe(n) zu prüfen"
              + (f", Prüfauftrag {r['auftrag']['id']}" if r["auftrag"] else ""))
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
