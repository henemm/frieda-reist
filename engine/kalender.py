"""Kalender einer Reise (frieda-reist #77): die Reise als Kalenderdatei (iCalendar, RFC 5545) zum Herunterladen und als
persönliches Abo.

Was drin steht (Product Owner 29.10.2026): je Reisetag ein ganztägiger Eintrag mit Weg und Nacht, je Unterkunft ein
Eintrag über alle Nächte, Aufenthalte ohne Nacht (Uhrzeit beginn, ende), Bewegungen mit Abfahrt (ab, an; #135) und Fristen
(Buchungen: Frist, kostenloses Storno, ab wann etwas geht; Aufgaben: Frist). Nur Entschiedenes: Tage unter einer offenen Planungs-Wahlstelle (route.tage[].vorlaeufig)
und Nächte oder Strecken aus einer offenen Planungs-Wahlstelle fehlen, bis eine Organisator:in gewählt hat.

Uhrzeiten HH:MM sind Ortszeit am Ort des Dings und stehen deshalb ohne Zeitzone in der Datei („floating“): Der Kalender
zeigt 09:30 als 09:30, wo man gerade ist. Ein Zeitpunkt mit Zeitzone (ab/an „2027-05-13T09:30+02:00“) steht als UTC darin. Jeder Eintrag hat eine feste UID aus Reise und ID, damit ein Abo Änderungen ersetzt
statt verdoppelt.

Nur Standardbibliothek: Rückmeldedienst und Konnektor laufen mit dem Python des Systems (docs/betrieb.md).
"""
import datetime
import hashlib
import hmac

PRODID = "-//Frieda Reist//Kalender//DE"
AG_OFFEN = ("offen", "in_arbeit")
ABO_STUNDEN = 6   # so oft fragt eine Kalender-App nach (wenn sie den Hinweis beachtet)


# ---------- Persönlicher Abo-Link ----------
# Ein Abo je Person über alle ihre Reisen (Product Owner 30.10.2026). Kalender-Apps können sich nicht anmelden; das Abo
# trägt deshalb ein geheimes Wort je Konto. Es wird nicht gespeichert, sondern aus dem Dienst-Geheimnis, dem Konto und einem
# Zähler berechnet (konten.py, Tabelle kalender_abo): Erneuern zählt hoch, der alte Link gilt dann nicht mehr. Wer eine
# Reise verlässt, hat sie im Abo nicht mehr. Ausgeliefert wird es vom Konnektor unter seiner Adresse (KN_BASIS).

def token(geheimnis, konto, stand):
    return hmac.new(geheimnis.encode(), f"kalender|{konto}|{stand}".encode(), hashlib.sha256).hexdigest()[:40]


def abo_url(basis, tok):
    """Adresse des Abos beim Konnektor (nginx: <FR_KN_ADRESSE>/ -> Konnektor)."""
    return f"{basis.rstrip('/')}/kalender/{tok}.ics"


def webcal(url):
    """Dieselbe Adresse als webcal:// (öffnet auf iPhone, Mac und in Outlook direkt „Abonnieren“)."""
    return "webcal://" + url.split("://", 1)[1] if "://" in url else url


# ---------- Einträge aus den Daten der Seite (daten.json) ----------

def _datum(t):
    try:
        return datetime.date.fromisoformat(str(t)[:10])
    except (TypeError, ValueError):
        return None


def _uhr(datum, text):
    """HH:MM am Tag oder JJJJ-MM-TTTHH:MM[Zeitzone] (Form wie routen.zeitpunkt) -> datetime (mit Zeitzone nur, wenn angegeben)."""
    t = str(text or "").strip()
    try:
        if "T" in t:
            return datetime.datetime.fromisoformat(t.replace("Z", "+00:00"))
        h, m = (int(x) for x in t.split(":"))
        return datetime.datetime.combine(datum, datetime.time(h, m))
    except (TypeError, ValueError):
        return None


def _spanne(tag, a, e):
    """Beginn und Ende; ein Ende ohne Zeitzone vor dem Beginn liegt am Tag danach, Ende und Beginn verschiedener Form passen nicht."""
    b = _uhr(tag, a) if a else None
    ende = _uhr(tag, e) if b and e else None
    if ende and (ende.tzinfo is None) != (b.tzinfo is None):
        ende = None
    if ende and ende <= b and ende.tzinfo is None:
        ende += datetime.timedelta(days=1)
    return b, ende


def _offen(route):
    """Offene Planungs-Wahlstellen (noch keine Option gewählt)."""
    return {w["id"] for w in route.get("wahlstellen") or []
            if w.get("wann", w.get("art")) == "planung" and not any(o.get("status") == "gewaehlt" for o in w.get("optionen") or [])}


def eintraege(daten, aufgaben=None):
    """-> Liste von Einträgen {sorte, id, uid, titel, tag, bis | beginn, ende, ort, text}. tag/bis: ganztägig (bis ausschließlich);
    beginn/ende: mit Uhrzeit. id ist das Ding, zu dem der Eintrag gehört (T-, U-, A-, E-, B-, AG-)."""
    r = (daten or {}).get("route") or {}
    orte, strecken = r.get("orte") or {}, r.get("strecken") or {}
    unterk, aufenth = r.get("unterkuenfte") or {}, r.get("aufenthalte") or {}
    offen = _offen(r)
    ort_name = lambda oid: (orte.get(oid) or {}).get("name") or oid or ""
    aus = []

    def lage(d):
        a = d.get("adresse")
        return (a.get("wert") if isinstance(a, dict) else a) or ort_name(d.get("ort"))

    tage = [t for t in r.get("tage") or [] if not t.get("vorlaeufig") and _datum(t.get("datum"))]
    naechte = {}   # Unterkunft -> [Datum]
    for t in tage:
        tag = _datum(t["datum"])
        weg = [(x["id"], strecken.get(x["id"]) or {}) for x in t.get("strecken") or [] if x.get("wahl") not in offen]
        n = t.get("nacht") or {}
        uid = n.get("unterkunft") if n.get("wahl") not in offen else None
        zeilen = [f"{s.get('titel') or sid} ({ort_name(s.get('von'))} → {ort_name(s.get('nach'))})"
                  + "".join(f", {w} {s[k]}" for k, w in (("ab", "ab"), ("an", "an")) if s.get(k))
                  for sid, s in weg]
        zeilen += [f"{a.get('name', aid)}" + (f", {a['zeit']}" if a.get("zeit") else "")
                   for aid in t.get("aufenthalte") or [] if (a := aufenth.get(aid))]
        zeilen += list(t.get("fixpunkte") or [])
        if uid and uid in unterk:
            zeilen.append("Nacht: " + unterk[uid].get("name", uid))
            naechte.setdefault(uid, []).append(tag)
        elif n.get("ort") and not n.get("wahl"):
            zeilen.append("Nacht in " + ort_name(n["ort"]))
        if t.get("text"):
            zeilen += ["", t["text"]]
        aus.append({"sorte": "tage", "id": t["id"], "uid": t["id"], "titel": f"Tag {t.get('nr')}: {t.get('titel') or ''}".rstrip(": "),
                    "tag": tag, "bis": tag + datetime.timedelta(days=1), "ort": ort_name(t.get("end_ort")),
                    "text": "\n".join(zeilen)})
        for sid, s in weg:
            b, e = _spanne(tag, s.get("ab"), s.get("an"))
            if b:
                aus.append({"sorte": "fahrten", "id": sid, "uid": f"{sid}-{tag.isoformat()}", "titel": s.get("titel") or sid, "beginn": b, "ende": e,
                            "ort": ort_name(s.get("von")), "text": f"{ort_name(s.get('von'))} → {ort_name(s.get('nach'))}"
                            + _buchung_text(r, s.get("buchung_id"))})
        for aid in t.get("aufenthalte") or []:
            a = aufenth.get(aid)
            if not a:
                continue
            text = "\n".join(x for x in (a.get("zeit"), a.get("hinweis")) if x) + _buchung_text(r, a.get("buchung_id"))
            e = {"sorte": "aufenthalte", "id": aid, "uid": f"{aid}-{tag.isoformat()}", "titel": a.get("name") or aid, "ort": lage(a), "text": text.strip()}
            b, ende = _spanne(tag, a.get("beginn"), a.get("ende"))
            if b:
                e.update(beginn=b, ende=ende)
            else:
                e.update(tag=tag, bis=tag + datetime.timedelta(days=1))
            aus.append(e)

    # Unterkünfte: ein Eintrag je Aufenthalt am Stück (Anreise bis Abreise)
    for uid, tage_ in naechte.items():
        u = unterk[uid]
        stuecke, an = [], None
        for d in sorted(tage_):
            if an and d == an[1]:
                an[1] = d + datetime.timedelta(days=1)
            else:
                an = [d, d + datetime.timedelta(days=1)]
                stuecke.append(an)
        for von, bis in stuecke:
            n = (bis - von).days
            aus.append({"sorte": "unterkuenfte", "id": uid, "uid": uid if len(stuecke) == 1 else f"{uid}-{von.isoformat()}",
                        "titel": f"Übernachtung: {u.get('name', uid)}", "tag": von, "bis": bis, "ort": lage(u),
                        "text": (f"{n} Nacht" if n == 1 else f"{n} Nächte") + _buchung_text(r, u.get("buchung_id"))
                        + (f"\n{u['kontakt']}" if u.get("kontakt") else "") + (f"\n{u['hinweis']}" if u.get("hinweis") else "")})

    # Fristen: Buchungen (nicht storniert) und offene Aufgaben
    for bid, b in (r.get("buchungen") or {}).items():
        if b.get("status") == "storniert":
            continue
        titel = b.get("titel") or bid
        if (d := _datum(b.get("frist"))):
            aus.append({"sorte": "buchungen", "id": bid, "uid": f"{bid}-frist", "titel": f"Frist: {b.get('frist_was') or 'Buchung'} – {titel}",
                        "tag": d, "bis": d + datetime.timedelta(days=1), "text": _buchung_text(r, bid).strip()})
        if (d := _datum(b.get("ab"))):
            aus.append({"sorte": "buchungen", "id": bid, "uid": f"{bid}-ab", "titel": f"Ab heute: {b.get('ab_was') or 'Buchung'} – {titel}",
                        "tag": d, "bis": d + datetime.timedelta(days=1), "text": _buchung_text(r, bid).strip()})
        if (d := _datum(b.get("storno_bis"))):
            aus.append({"sorte": "buchungen", "id": bid, "uid": f"{bid}-storno", "titel": f"Letzter Tag kostenlos stornieren – {titel}",
                        "tag": d, "bis": d + datetime.timedelta(days=1), "text": _buchung_text(r, bid).strip()})
    for a in aufgaben or []:
        if a.get("status") in AG_OFFEN and (d := _datum(a.get("frist"))):
            aus.append({"sorte": "aufgaben", "zustaendig": a.get("zustaendig") or "", "id": a["id"], "uid": f"{a['id']}-frist", "titel": f"Aufgabe fällig: {a.get('titel', a['id'])}",
                        "tag": d, "bis": d + datetime.timedelta(days=1),
                        "text": "\n".join(x for x in (f"Zuständig: {a['zustaendig']}" if a.get("zustaendig") else "", a.get("notiz")) if x)})
    return aus


def _buchung_text(r, bid):
    b = (r.get("buchungen") or {}).get(bid) if bid else None
    if not b:
        return ""
    teile = [f"Buchung {b.get('status')}" + (f", Nummer {b['nummer']}" if b.get("nummer") else "")
             + (f", bei {b['bei']}" if b.get("bei") else "")]
    if b.get("storno") or b.get("storno_bis"):
        teile.append("Storno: " + " · ".join(x for x in (b.get("storno"), f"bis {b['storno_bis']}" if b.get("storno_bis") else "") if x))
    return "\n" + "\n".join(teile)


# ---------- iCalendar schreiben (RFC 5545) ----------

def _esc(t):
    return str(t).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\r\n", "\n").replace("\n", "\\n")


def _falten(zeile):
    """Zeilen über 75 Byte falten (Fortsetzung beginnt mit einem Leerzeichen), ohne ein Zeichen zu zerteilen."""
    aus, stueck, laenge = [], "", 0
    for z in zeile:
        n = len(z.encode("utf-8"))
        if laenge + n > (75 if not aus else 74):
            aus.append(stueck)
            stueck, laenge = "", 0
        stueck += z
        laenge += n
    aus.append(stueck)
    return "\r\n ".join(aus)


def _zeit(t):
    """Ortszeit ohne Zeitzone („floating“) oder, mit Zeitzone, als UTC."""
    if t.tzinfo is not None:
        return t.astimezone(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return t.strftime("%Y%m%dT%H%M%S")


def ics(daten, reise, aufgaben=None, nur=None, jetzt=None, name=None):
    """Kalenderdatei der Reise als Text. nur: nur die Einträge eines Dings (T-, U-, A-, E-, B-, AG-). -> str oder None,
    wenn nur gesetzt ist und das Ding keinen Eintrag hat (noch nicht entschieden oder ohne Datum)."""
    liste = [(reise, e) for e in eintraege(daten, aufgaben) if nur is None or e["id"] == nur]
    if nur is not None and not liste:
        return None
    return _kalender(liste, name or ((daten or {}).get("reise") or {}).get("titel") or reise, jetzt)


# ---------- Persönlicher Kalender über alle Reisen (Abo und Download auf „Mein Konto“) ----------
# Jede Person stellt ihren Kalender selbst ein (Product Owner 30.10.2026): welche Einträge, nur eigene Aufgaben, Erinnerungen,
# welche Reisen. Die Einstellungen liegen am Konto (konten.py, Tabelle kalender_abo) und gelten für Abo und Download.

SORTEN = {"tage": "Reisetage mit Weg und Nacht", "unterkuenfte": "Unterkünfte", "aufenthalte": "Besichtigungen, Essen, Besuche",
          "fahrten": "Fahrten mit Uhrzeit", "buchungen": "Fristen von Buchungen", "aufgaben": "Fristen von Aufgaben"}
# Erinnerung vor Fristen (ganztägig, Beginn 0 Uhr: -PT15H ist 9 Uhr am Vortag) und vor Terminen mit Uhrzeit
ERINNERUNG_FRISTEN = {"": "keine", "-PT15H": "am Vortag um 9 Uhr", "-P2DT15H": "3 Tage vorher um 9 Uhr",
                      "-P6DT15H": "1 Woche vorher um 9 Uhr"}
ERINNERUNG_TERMINE = {"": "keine", "-PT15M": "15 Minuten vorher", "-PT30M": "30 Minuten vorher", "-PT1H": "1 Stunde vorher",
                      "-PT2H": "2 Stunden vorher"}
VORGABE = {"sorten": list(SORTEN), "nur_meine_aufgaben": False, "erinnerung_fristen": "", "erinnerung_termine": "", "reisen_aus": []}


def einstellungen(roh):
    """Einstellungen eines Kontos, bereinigt (Unbekanntes fällt weg, Fehlendes nimmt die Vorgabe)."""
    roh = roh if isinstance(roh, dict) else {}
    e = dict(VORGABE)
    if isinstance(roh.get("sorten"), list):
        e["sorten"] = [x for x in SORTEN if x in roh["sorten"]]
    e["nur_meine_aufgaben"] = roh.get("nur_meine_aufgaben") is True
    if roh.get("erinnerung_fristen") in ERINNERUNG_FRISTEN:
        e["erinnerung_fristen"] = roh["erinnerung_fristen"]
    if roh.get("erinnerung_termine") in ERINNERUNG_TERMINE:
        e["erinnerung_termine"] = roh["erinnerung_termine"]
    if isinstance(roh.get("reisen_aus"), list):
        e["reisen_aus"] = sorted({x for x in roh["reisen_aus"] if isinstance(x, str)})
    return e


def ics_person(reisen, e, name="Frieda – meine Reisen", jetzt=None):
    """Kalender einer Person: reisen = [(reise, daten, aufgaben, name der person)], e = einstellungen()."""
    e = einstellungen(e)
    liste = []
    for reise, daten, aufgaben, person in reisen:
        if reise in e["reisen_aus"]:
            continue
        titel = ((daten or {}).get("reise") or {}).get("titel") or reise
        for x in eintraege(daten, aufgaben):
            if x["sorte"] not in e["sorten"]:
                continue
            if x["sorte"] == "aufgaben" and e["nur_meine_aufgaben"] and \
                    (not person or (x.get("zustaendig") or "").casefold() != person.casefold()):
                continue
            alarm = e["erinnerung_fristen"] if x["sorte"] in ("buchungen", "aufgaben") else \
                e["erinnerung_termine"] if x.get("beginn") else ""
            liste.append((reise, {**x, "titel": f"{x['titel']} ({titel})" if len(reisen) > 1 else x["titel"], "alarm": alarm}))
    return _kalender(liste, name, jetzt)


def _kalender(liste, titel, jetzt=None):
    """liste: [(reise, eintrag)] -> iCalendar als Text."""
    jetzt = (jetzt or datetime.datetime.now(datetime.timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    z = ["BEGIN:VCALENDAR", "VERSION:2.0", f"PRODID:{PRODID}", "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
         f"X-WR-CALNAME:{_esc(titel)}", f"REFRESH-INTERVAL;VALUE=DURATION:PT{ABO_STUNDEN}H", f"X-PUBLISHED-TTL:PT{ABO_STUNDEN}H"]
    for reise, e in sorted(liste, key=lambda x: (str(x[1].get("tag") or x[1]["beginn"].date()), x[0], x[1]["uid"])):
        z += ["BEGIN:VEVENT", f"UID:{e['uid']}.{reise}@frieda", f"DTSTAMP:{jetzt}"]
        if e.get("beginn"):
            z.append("DTSTART:" + _zeit(e["beginn"]))
            if e.get("ende"):
                z.append("DTEND:" + _zeit(e["ende"]))
        else:
            z += ["DTSTART;VALUE=DATE:" + e["tag"].strftime("%Y%m%d"), "DTEND;VALUE=DATE:" + e["bis"].strftime("%Y%m%d"),
                  "TRANSP:TRANSPARENT"]
        z.append("SUMMARY:" + _esc(e["titel"]))
        if e.get("ort"):
            z.append("LOCATION:" + _esc(e["ort"]))
        if e.get("text"):
            z.append("DESCRIPTION:" + _esc(e["text"]))
        if e.get("alarm"):
            z += ["BEGIN:VALARM", "ACTION:DISPLAY", "DESCRIPTION:" + _esc(e["titel"]), f"TRIGGER:{e['alarm']}", "END:VALARM"]
        z.append("END:VEVENT")
    z.append("END:VCALENDAR")
    return "\r\n".join(_falten(x) for x in z) + "\r\n"
