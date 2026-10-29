"""Kalender einer Reise (frieda-reist #77): die Reise als Kalenderdatei (iCalendar, RFC 5545) zum Herunterladen und als
persönliches Abo.

Was drin steht (Product Owner 29.10.2026): je Reisetag ein ganztägiger Eintrag mit Weg und Nacht, je Unterkunft ein
Eintrag über alle Nächte, Aufenthalte ohne Nacht, Bewegungen mit Uhrzeit (beginn, ende) und Fristen (Buchungen: Frist und
kostenloses Storno; Aufgaben: Frist). Nur Entschiedenes: Tage unter einer offenen Planungs-Wahlstelle (route.tage[].vorlaeufig)
und Nächte oder Strecken aus einer offenen Planungs-Wahlstelle fehlen, bis eine Organisator:in gewählt hat.

Uhrzeiten sind Ortszeit am Ort des Dings und stehen deshalb ohne Zeitzone in der Datei („floating“): Der Kalender zeigt
09:30 als 09:30, wo man gerade ist. Jeder Eintrag hat eine feste UID aus Reise und ID, damit ein Abo Änderungen ersetzt
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
# Kalender-Apps können sich nicht anmelden. Das Abo trägt deshalb ein geheimes Wort je Konto und Reise. Es wird nicht
# gespeichert, sondern aus dem Dienst-Geheimnis, Konto, Reise und einem Zähler berechnet (konten.py, Tabelle kalender):
# Erneuern zählt hoch, der alte Link gilt dann nicht mehr. Wer die Reise verlässt, verliert das Abo von selbst.

def token(geheimnis, konto, reise, stand):
    return hmac.new(geheimnis.encode(), f"kalender|{konto}|{reise}|{stand}".encode(), hashlib.sha256).hexdigest()[:40]


def abo_url(seite, tok):
    """Adresse des Abos: unter dem Link der Seite, beim Rückmeldedienst (nginx: <seite>/api/ -> Dienst)."""
    return f"{seite.rstrip('/')}/api/kalender/{tok}.ics"


def webcal(url):
    """Dieselbe Adresse als webcal:// (öffnet auf iPhone, Mac und in Outlook direkt „Abonnieren“)."""
    return "webcal://" + url.split("://", 1)[1] if "://" in url else url


# ---------- Einträge aus den Daten der Seite (daten.json) ----------

def _datum(t):
    try:
        return datetime.date.fromisoformat(str(t)[:10])
    except (TypeError, ValueError):
        return None


def _uhr(datum, hhmm):
    try:
        h, m = (int(x) for x in str(hhmm).split(":"))
        return datetime.datetime.combine(datum, datetime.time(h, m))
    except (TypeError, ValueError):
        return None


def _offen(route):
    """Offene Planungs-Wahlstellen (noch keine Option gewählt)."""
    return {w["id"] for w in route.get("wahlstellen") or []
            if w.get("art") == "planung" and not any(o.get("status") == "gewaehlt" for o in w.get("optionen") or [])}


def eintraege(daten, aufgaben=None):
    """-> Liste von Einträgen {id, uid, titel, tag, bis | beginn, ende, ort, text}. tag/bis: ganztägig (bis ausschließlich);
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
                  + (f", {s['beginn']}" + (f"–{s['ende']}" if s.get("ende") else "") + " Uhr" if s.get("beginn") else "")
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
        aus.append({"id": t["id"], "uid": t["id"], "titel": f"Tag {t.get('nr')}: {t.get('titel') or ''}".rstrip(": "),
                    "tag": tag, "bis": tag + datetime.timedelta(days=1), "ort": ort_name(t.get("end_ort")),
                    "text": "\n".join(zeilen)})
        for sid, s in weg:
            if s.get("beginn") and (b := _uhr(tag, s["beginn"])):
                e = _uhr(tag, s["ende"]) if s.get("ende") else None
                if e and e <= b:
                    e += datetime.timedelta(days=1)
                aus.append({"id": sid, "uid": f"{sid}-{tag.isoformat()}", "titel": s.get("titel") or sid, "beginn": b, "ende": e,
                            "ort": ort_name(s.get("von")), "text": f"{ort_name(s.get('von'))} → {ort_name(s.get('nach'))}"
                            + _buchung_text(r, s.get("buchung_id"))})
        for aid in t.get("aufenthalte") or []:
            a = aufenth.get(aid)
            if not a:
                continue
            text = "\n".join(x for x in (a.get("zeit"), a.get("hinweis")) if x) + _buchung_text(r, a.get("buchung_id"))
            e = {"id": aid, "uid": f"{aid}-{tag.isoformat()}", "titel": a.get("name") or aid, "ort": lage(a), "text": text.strip()}
            if a.get("beginn") and (b := _uhr(tag, a["beginn"])):
                ende = _uhr(tag, a["ende"]) if a.get("ende") else None
                if ende and ende <= b:
                    ende += datetime.timedelta(days=1)
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
            aus.append({"id": uid, "uid": uid if len(stuecke) == 1 else f"{uid}-{von.isoformat()}",
                        "titel": f"Übernachtung: {u.get('name', uid)}", "tag": von, "bis": bis, "ort": lage(u),
                        "text": (f"{n} Nacht" if n == 1 else f"{n} Nächte") + _buchung_text(r, u.get("buchung_id"))
                        + (f"\n{u['kontakt']}" if u.get("kontakt") else "") + (f"\n{u['hinweis']}" if u.get("hinweis") else "")})

    # Fristen: Buchungen (nicht storniert) und offene Aufgaben
    for bid, b in (r.get("buchungen") or {}).items():
        if b.get("status") == "storniert":
            continue
        titel = b.get("titel") or bid
        if (d := _datum(b.get("frist"))):
            aus.append({"id": bid, "uid": f"{bid}-frist", "titel": f"Frist: {b.get('frist_was') or 'Buchung'} – {titel}",
                        "tag": d, "bis": d + datetime.timedelta(days=1), "text": _buchung_text(r, bid).strip()})
        if (d := _datum(b.get("storno_bis"))):
            aus.append({"id": bid, "uid": f"{bid}-storno", "titel": f"Letzter Tag kostenlos stornieren – {titel}",
                        "tag": d, "bis": d + datetime.timedelta(days=1), "text": _buchung_text(r, bid).strip()})
    for a in aufgaben or []:
        if a.get("status") in AG_OFFEN and (d := _datum(a.get("frist"))):
            aus.append({"id": a["id"], "uid": f"{a['id']}-frist", "titel": f"Aufgabe fällig: {a.get('titel', a['id'])}",
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


def ics(daten, reise, aufgaben=None, nur=None, jetzt=None, name=None):
    """Kalenderdatei der Reise als Text. nur: nur die Einträge eines Dings (T-, U-, A-, E-, B-, AG-). -> str oder None,
    wenn nur gesetzt ist und das Ding keinen Eintrag hat (noch nicht entschieden oder ohne Datum)."""
    liste = [e for e in eintraege(daten, aufgaben) if nur is None or e["id"] == nur]
    if nur is not None and not liste:
        return None
    jetzt = (jetzt or datetime.datetime.now(datetime.timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    titel = name or ((daten or {}).get("reise") or {}).get("titel") or reise
    z = ["BEGIN:VCALENDAR", "VERSION:2.0", f"PRODID:{PRODID}", "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
         f"X-WR-CALNAME:{_esc(titel)}", f"REFRESH-INTERVAL;VALUE=DURATION:PT{ABO_STUNDEN}H", f"X-PUBLISHED-TTL:PT{ABO_STUNDEN}H"]
    for e in sorted(liste, key=lambda e: (str(e.get("tag") or e["beginn"].date()), e["uid"])):
        z += ["BEGIN:VEVENT", f"UID:{e['uid']}.{reise}@frieda", f"DTSTAMP:{jetzt}"]
        if e.get("beginn"):
            z.append("DTSTART:" + e["beginn"].strftime("%Y%m%dT%H%M%S"))
            if e.get("ende"):
                z.append("DTEND:" + e["ende"].strftime("%Y%m%dT%H%M%S"))
        else:
            z += ["DTSTART;VALUE=DATE:" + e["tag"].strftime("%Y%m%d"), "DTEND;VALUE=DATE:" + e["bis"].strftime("%Y%m%d"),
                  "TRANSP:TRANSPARENT"]
        z.append("SUMMARY:" + _esc(e["titel"]))
        if e.get("ort"):
            z.append("LOCATION:" + _esc(e["ort"]))
        if e.get("text"):
            z.append("DESCRIPTION:" + _esc(e["text"]))
        z.append("END:VEVENT")
    z.append("END:VCALENDAR")
    return "\r\n".join(_falten(x) for x in z) + "\r\n"
