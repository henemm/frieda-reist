"""Anmeldeseiten für Konten (Paket J2, Issues #43 und #46). Der Konnektor-Dienst liefert sie unter Friedas eigener
Adresse aus (FR_BASIS): /anmelden, /einladung/<token>, /konto, /abmelden.

Ablauf: E-Mail-Adresse eingeben -> Code per Mail -> Code eingeben (beim ersten Mal auch den Namen) -> angemeldet.
Der Code ist der Hauptweg; der Link aus der Mail enthält keinen Code und öffnet nur die Code-Seite (Mailprogramme rufen
Links vorab auf, und Codes gehören nicht in Protokolle). Die Sitzung steht im Cookie __Host-frieda (HttpOnly, Secure,
SameSite=Lax, ein Jahr, rollierend). Jede Änderung (POST) muss von Friedas eigener Adresse kommen (Origin), sonst
403 (CSRF; SameSite trennt nicht von Nachbar-Subdomains). Rückkehradressen sind nur Pfade auf Friedas Adresse.

Reiseseiten bleiben zum Lesen über ihren geheimen Link offen; mitmachen geht nach dem Anmelden (Rückmeldedienst).
"""
import html
import re
import urllib.parse

import konten
import rueckmeldungen as rm

COOKIE = rm.COOKIE
JAHR = 365 * 86400
ROLLE_TEXT = {"reisend": "liest mit", "einbringer": "bringt ein", "bestimmer": "bestimmt"}
DATENSCHUTZ = ("Frieda speichert deine E-Mail-Adresse und deinen Namen nur, um dich anzumelden und dich zu Reisen "
               "einzuladen. Du kannst dein Konto jederzeit selbst löschen.")

CSS = """
:root{--bg:#f8f8f5;--fg:#1d2420;--mut:#5b645e;--card:#ffffff;--line:#e4e5df;--acc:#1f7a57;--acc2:#e3f1ea;
--warn:#9a5b00;--warnbg:#fbeed6;--bar:#22281f;--bar-fg:#c9cdbf}
@media (prefers-color-scheme:dark){:root{--bg:#151816;--fg:#eceee9;--mut:#a5aca6;--card:#1d211e;--line:#2c312d;
--acc:#6fd0a5;--acc2:#1f3329;--warn:#f0c46a;--warnbg:#3a3017;--bar:#2c3128;--bar-fg:#b9bdaf}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:1.0625rem/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",
Roboto,sans-serif}
header{background:var(--bar);color:var(--bar-fg);padding:.75rem 1rem;font:700 1.25rem -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
main{max-width:30rem;margin:1.5rem auto;padding:0 1rem}
.karte{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:1.25rem;margin-bottom:1rem}
h1{font-size:1.4rem;margin:0 0 .75rem}h2{font-size:1.1rem;margin:0 0 .5rem}
label{display:block;margin:.75rem 0 .25rem;font-weight:600}
input[type=email],input[type=text]{width:100%;min-height:2.75rem;padding:.5rem .75rem;font:inherit;color:var(--fg);
background:var(--bg);border:1px solid var(--line);border-radius:.375rem}
input.code{font-size:1.5rem;letter-spacing:.3em;text-align:center}
button{min-height:2.75rem;margin-top:1rem;padding:.5rem 1.25rem;font:600 1rem inherit;border:0;border-radius:.375rem;
background:var(--acc);color:var(--card);cursor:pointer}
button.leise{background:var(--acc2);color:var(--fg)}button.gefahr{background:var(--warnbg);color:var(--warn)}
.fehler{background:var(--warnbg);color:var(--warn);padding:.6rem .8rem;border-radius:.375rem;margin:.5rem 0}
.hinweis,.klein{color:var(--mut)}.klein{font-size:.875rem}
ul{padding-left:1.2rem}a{color:var(--acc)}form.zeile{display:inline}
"""


def esc(t):
    return html.escape(str(t or ""), quote=True)


def seite(titel, *teile):
    rumpf = "".join(teile)
    return (f'<!DOCTYPE html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" '
            f'content="width=device-width, initial-scale=1"><meta name="robots" content="noindex">'
            f'<title>{esc(titel)} – Frieda</title><style>{CSS}</style></head><body><header>Frieda</header>'
            f'<main>{rumpf}</main></body></html>')


def karte(*teile):
    return '<section class="karte">' + "".join(teile) + "</section>"


def fehler(t):
    return f'<p class="fehler" role="alert">{esc(t)}</p>' if t else ""


def verdeckt(**felder):
    return "".join(f'<input type="hidden" name="{esc(k)}" value="{esc(v)}">' for k, v in felder.items() if v)


def formular(ziel, inhalt, knopf, klasse=""):
    k = f' class="{klasse}"' if klasse else ""
    return f'<form method="post" action="{esc(ziel)}">{inhalt}<button{k}>{esc(knopf)}</button></form>'


def antwort(code, body, extra=()):
    return code, [("Content-Type", "text/html; charset=utf-8"), *extra], body.encode("utf-8")


def weiter(ziel, extra=()):
    return 303, [("Location", ziel), *extra], b""


def cookie_setzen(token):
    return ("Set-Cookie", f"{COOKIE}={token}; Path=/; Max-Age={JAHR}; Secure; HttpOnly; SameSite=Lax")


def cookie_loeschen():
    return ("Set-Cookie", f"{COOKIE}=; Path=/; Max-Age=0; Secure; HttpOnly; SameSite=Lax")


def rueckweg(roh):
    """Nur Pfade auf Friedas eigener Adresse (kein offener Umleiter). Lang genug für /authorize mit allen Angaben."""
    r = roh or ""
    if not r.startswith("/") or r.startswith("//") or "\\" in r or len(r) > 2000 or re.search(r"[\x00-\x1f]", r):
        return "/konto"
    return r


# ---------------------------------------------------------------- Seiten

def adress_seite(zurueck="", einladung="", email="", meldung=""):
    return seite("Anmelden", karte(
        "<h1>Bei Frieda anmelden</h1>",
        '<p>Gib deine E-Mail-Adresse ein. Du bekommst einen Code, ein Passwort brauchst du nicht.</p>',
        fehler(meldung),
        formular("/anmelden", verdeckt(schritt="adresse", zurueck=zurueck, einladung=einladung)
                 + '<label for="email">E-Mail-Adresse</label>'
                 f'<input id="email" type="email" name="email" value="{esc(email)}" autocomplete="email" required '
                 'autofocus>', "Code schicken"),
        f'<p class="klein">{esc(DATENSCHUTZ)}</p>'))


def code_seite(email, zurueck="", einladung="", code="", meldung="", name_noetig=False, name=""):
    name_feld = ('<label for="name">Wie heißt du?</label>'
                 f'<input id="name" type="text" name="name" value="{esc(name)}" maxlength="{konten.MAX_NAME}" '
                 'autocomplete="name" required>'
                 '<p class="klein">Der Name steht bei deinen Beiträgen, zum Beispiel deinen Wünschen.</p>'
                 if name_noetig else "")
    return seite("Code eingeben", karte(
        "<h1>Code eingeben</h1>",
        f"<p>Wir haben einen Code an <strong>{esc(email)}</strong> geschickt. Er gilt {konten.CODE_MINUTEN} Minuten.</p>"
        if not code else f"<p>Anmelden als <strong>{esc(email)}</strong>.</p>",
        fehler(meldung),
        formular("/anmelden", verdeckt(schritt="code", email=email, zurueck=zurueck, einladung=einladung)
                 + '<label for="code">Code aus der Mail</label>'
                 f'<input id="code" class="code" type="text" name="code" value="{esc(code)}" inputmode="numeric" '
                 'autocomplete="one-time-code" pattern="[0-9 ]{6,7}" maxlength="7" required'
                 f'{"" if code or name_noetig else " autofocus"}>' + name_feld, "Anmelden"),
        f'<p class="klein"><a href="/anmelden?{urllib.parse.urlencode({"zurueck": zurueck, "einladung": einladung})}">'
        'Andere Adresse oder neuen Code anfordern</a></p>'))


def konto_seite(k, reise_info, meldung="", hinweis="", adresse_neu=""):
    reisen = []
    for m in konten.mitgliedschaften(k["id"]):
        info = reise_info(m["reise"]) or {}
        z = rm.zustand(m["reise"]) or {}
        p = next((x for x in z.get("personen") or [] if x.get("schluessel") == m["schluessel"]), {})
        link = f' – <a href="{esc(info["seite"])}">öffnen</a>' if info.get("seite") else ""
        reisen.append(f'<li>{esc(info.get("titel") or m["reise"])} ({esc(ROLLE_TEXT.get(p.get("rolle"), "dabei"))})'
                      f"{link}</li>")
    reisen_html = f"<ul>{''.join(reisen)}</ul>" if reisen else (
        '<p class="hinweis">Noch keine Reisen. Wer eine Reise bestimmt, kann dich mit deiner Adresse einladen.</p>')
    if konten.recht(k, "reise_anlegen"):
        anlegen = "<p>Du darfst Reisen anlegen: in der Claude-App mit dem Konnektor „Frieda“.</p>"
    else:
        st = next((a["status"] for a in konten.anfragen(nur_offen=False) if a["konto"] == k["id"]), None)
        anlegen = {"offen": '<p class="hinweis">Deine Bitte, Reisen anlegen zu dürfen, liegt beim Betreiber.</p>',
                   "abgelehnt": '<p class="hinweis">Deine Bitte, Reisen anlegen zu dürfen, wurde abgelehnt.</p>'}.get(
            st, formular("/konto", verdeckt(aktion="anfragen"), "Ich möchte Reisen anlegen", "leise"))
    betreiber = ""
    if konten.recht(k, "betreiber"):
        offen = konten.anfragen()
        zeilen = "".join(
            f'<li>{esc(a["name"])} ({esc(a["email"])}) '
            + formular("/konto", verdeckt(aktion="freischalten", wer=a["konto"]), "Freischalten", "leise")
            + formular("/konto", verdeckt(aktion="ablehnen", wer=a["konto"]), "Ablehnen", "gefahr") + "</li>"
            for a in offen)
        betreiber = karte("<h2>Bitten „Reisen anlegen“</h2>",
                          f"<ul>{zeilen}</ul>" if zeilen else '<p class="hinweis">Keine offenen Bitten.</p>')
    geraete = "".join(f'<li>{esc(g["geraet"] or "Gerät")} <span class="klein">zuletzt {esc(g["zuletzt"][:10])}</span>'
                      f"</li>" for g in konten.geraete(k["id"]))
    adresse_teil = (
        formular("/konto", verdeckt(aktion="adresse", email=adresse_neu)
                 + f'<label for="code">Code an {esc(adresse_neu)}</label>'
                 '<input id="code" class="code" type="text" name="code" inputmode="numeric" '
                 'autocomplete="one-time-code" maxlength="7" required>', "Adresse ändern")
        if adresse_neu else
        formular("/konto", verdeckt(aktion="adresse_code")
                 + '<label for="neu">Neue E-Mail-Adresse</label>'
                 '<input id="neu" type="email" name="email" autocomplete="email" required>', "Code schicken", "leise"))
    return seite("Mein Konto",
                 karte(f"<h1>Hallo {esc(k['name'])}</h1>", fehler(meldung),
                       f'<p class="hinweis">{esc(hinweis)}</p>' if hinweis else "",
                       f"<p>Angemeldet als <strong>{esc(k['email'])}</strong>.</p>",
                       formular("/abmelden", "", "Abmelden", "leise")),
                 karte("<h2>Meine Reisen</h2>", reisen_html, anlegen),
                 betreiber,
                 karte("<h2>Name</h2>", formular("/konto", verdeckt(aktion="name")
                                                + '<label for="name">So steht dein Name bei deinen Beiträgen</label>'
                                                f'<input id="name" type="text" name="name" value="{esc(k["name"])}" '
                                                f'maxlength="{konten.MAX_NAME}" required>', "Speichern", "leise")),
                 karte("<h2>E-Mail-Adresse</h2>", adresse_teil),
                 karte("<h2>Geräte</h2>", f"<ul>{geraete}</ul>",
                       formular("/konto", verdeckt(aktion="alle_abmelden"), "Überall abmelden", "leise")),
                 karte("<h2>Konto löschen</h2>",
                       '<p class="klein">Löscht dein Konto und deine Adresse. Deine Beiträge in den Reisen bleiben mit '
                       "deinem Namen stehen.</p>",
                       formular("/konto", verdeckt(aktion="loeschen")
                                + '<label><input type="checkbox" name="sicher" value="ja" required> '
                                  "Ja, mein Konto löschen</label>", "Konto löschen", "gefahr")))


def einladungs_seite(e, token, k, reise_info, meldung=""):
    info = reise_info(e["reise"]) or {}
    titel = info.get("titel") or e["reise"]
    kopf = (f"<h1>Einladung</h1><p>{esc(e['von'])} hat {esc(e['name'])} zur Reise <strong>„{esc(titel)}“</strong> "
            f"eingeladen ({esc(ROLLE_TEXT.get(e['rolle'], e['rolle']))}).</p>")
    if e["eingeloest"]:
        return seite("Einladung", karte(kopf, '<p class="hinweis">Diese Einladung ist schon angenommen.</p>',
                                        '<p><a href="/konto">Zu meinem Konto</a></p>'))
    if k:
        return seite("Einladung", karte(
            kopf, fehler(meldung),
            formular(f"/einladung/{token}", "", f"Annehmen als {k['name']} ({k['email']})"),
            '<p class="klein">Lieber mit einem anderen Konto? Erst <a href="/konto">abmelden</a>, dann diesen Link '
            "noch einmal öffnen.</p>"))
    q = urllib.parse.urlencode({"einladung": token, "email": e["email"]})
    return seite("Einladung", karte(
        kopf, "<p>Melde dich an, um mitzumachen. Du kannst auch eine andere E-Mail-Adresse nehmen.</p>",
        f'<p><a href="/anmelden?{q}"><button type="button">Anmelden</button></a></p>',
        f'<p class="klein">{esc(DATENSCHUTZ)}</p>'))


# ---------------------------------------------------------------- Ablauf

def sitzung_aus(headers):
    t = rm.sitzungs_token(headers.get("Cookie"))
    return t, (konten.sitzung(t) if t else None)


def herkunft_ok(headers):
    return bool(konten.basis()) and headers.get("Origin") == konten.basis()


def geraet(headers):
    ua = headers.get("User-Agent", "")
    for muster, name in (("iPad", "iPad"), ("iPhone", "iPhone"), ("Android", "Android"), ("Macintosh", "Mac"),
                         ("Windows", "Windows"), ("Linux", "Linux")):
        if muster in ua:
            return name
    return "Gerät"


def ist_unsere(pfad):
    p = pfad.split("?", 1)[0]
    return p in ("/anmelden", "/konto", "/abmelden") or p.startswith("/einladung/")


def bearbeiten(methode, pfad, headers, body, ip, reise_info):
    """-> (code, kopfzeilen, body) für Friedas Anmeldeseiten. reise_info(reise) -> {titel, seite} oder None."""
    teile = urllib.parse.urlsplit(pfad)
    weg, q = teile.path, {k: v[0] for k, v in urllib.parse.parse_qs(teile.query).items()}
    f = {}
    if methode == "POST":
        if not herkunft_ok(headers):
            return antwort(403, seite("Nicht erlaubt", karte(
                "<h1>Nicht erlaubt</h1><p>Diese Anfrage kam nicht von Frieda selbst.</p>")))
        f = {k: v[0] for k, v in urllib.parse.parse_qs(body.decode("utf-8", "replace")).items()}
    token, k = sitzung_aus(headers)

    if weg == "/anmelden":
        zurueck, einl = rueckweg(f.get("zurueck") or q.get("zurueck")), f.get("einladung") or q.get("einladung", "")
        if methode == "GET":
            if q.get("schritt") == "code" and q.get("email"):    # Link aus der Mail: nur die Code-Seite
                return antwort(200, code_seite(q["email"], zurueck, einl))
            if k and not einl:
                return weiter(zurueck)
            return antwort(200, adress_seite(zurueck, einl, q.get("email", "")))
        if f.get("schritt") == "adresse":
            try:
                konten.code_anfordern(f.get("email"), ip=ip)
            except konten.KontoFehler as x:
                return antwort(200, adress_seite(zurueck, einl, f.get("email", ""), str(x)))
            return antwort(200, code_seite(konten.adresse(f["email"]), zurueck, einl))
        try:
            neu, konto = konten.anmelden(f.get("email"), f.get("code"), name=f.get("name"), geraet=geraet(headers),
                                         einladung=einl or None)
        except konten.NameNoetig as x:
            return antwort(200, code_seite(f.get("email", ""), zurueck, einl, code=f.get("code", ""), meldung=str(x),
                                           name_noetig=True))
        except konten.KontoFehler as x:
            return antwort(200, code_seite(f.get("email", ""), zurueck, einl, meldung=str(x),
                                           name_noetig=bool(f.get("name"))))
        if token:
            konten.abmelden(token)
        ziel = zurueck
        if einl and zurueck == "/konto":
            e = konten.einladung(einl)
            ziel = ((reise_info(e["reise"]) or {}).get("seite") if e else None) or "/konto"
        return weiter(ziel, [cookie_setzen(neu)])

    if weg == "/abmelden":
        if methode == "POST" and token:
            konten.abmelden(token)
        return weiter("/anmelden", [cookie_loeschen()])

    if weg.startswith("/einladung/"):
        et = weg.rsplit("/", 1)[1]
        e = konten.einladung(et)
        if not e:
            return antwort(404, seite("Einladung", karte(
                "<h1>Einladung abgelaufen</h1><p>Dieser Link gilt nicht mehr. Bitte die Person, die dich eingeladen "
                "hat, um eine neue Einladung.</p>")))
        if methode == "GET":
            return antwort(200, einladungs_seite(e, et, k, reise_info))
        if not k:
            return weiter("/anmelden?" + urllib.parse.urlencode({"einladung": et, "email": e["email"]}))
        try:
            reise = konten.einladung_einloesen(et, k["id"])
        except konten.KontoFehler as x:
            return antwort(200, einladungs_seite(e, et, k, reise_info, str(x)))
        return weiter((reise_info(reise) or {}).get("seite") or "/konto")

    if weg == "/konto":
        if not k:
            return weiter("/anmelden?zurueck=/konto")
        if methode == "GET":
            return antwort(200, konto_seite(k, reise_info))
        a = f.get("aktion")
        try:
            if a == "name":
                konten.name_setzen(k["id"], f.get("name"))
                return weiter("/konto")
            if a == "adresse_code":
                konten.code_anfordern(f.get("email"), ip=ip, zweck="adresse", konto=k["id"])
                return antwort(200, konto_seite(k, reise_info, adresse_neu=konten.adresse(f["email"]),
                                                hinweis="Wir haben einen Code an die neue Adresse geschickt."))
            if a == "adresse":
                konten.adresse_aendern(k["id"], f.get("email"), f.get("code"))
                return weiter("/konto")
            if a == "anfragen":
                if konten.reisen_anlegen_anfragen(k["id"]) == "offen":
                    betreiber_melden(k)
                return weiter("/konto")
            if a in ("freischalten", "ablehnen") and konten.recht(k, "betreiber"):
                konten.freischalten(f.get("wer"), ja=a == "freischalten")
                return weiter("/konto")
            if a == "alle_abmelden":
                konten.alle_abmelden(k["id"])
                return weiter("/anmelden", [cookie_loeschen()])
            if a == "loeschen" and f.get("sicher") == "ja":
                konten.loeschen(k["id"])
                return antwort(200, seite("Konto gelöscht", karte(
                    "<h1>Konto gelöscht</h1><p>Dein Konto und deine Adresse sind gelöscht.</p>")), [cookie_loeschen()])
        except konten.KontoFehler as x:
            return antwort(200, konto_seite(k, reise_info, meldung=str(x)))
        return antwort(400, konto_seite(k, reise_info, meldung="Das ging nicht. Bitte noch einmal versuchen."))

    return antwort(404, seite("Nicht gefunden", karte("<h1>Nicht gefunden</h1>")))


def betreiber_melden(k):
    """Bitte „Reisen anlegen“: Meldung an alle Betreiber (stehen in der Claude-App bei meine_reisen)."""
    with konten.closing(konten.db()) as v:
        namen = [z["name"] for z in v.execute("SELECT name, rechte FROM konten WHERE gesperrt = 0")
                 if "betreiber" in z["rechte"].split(",")]
    if namen:
        rm.meldung_anlegen(rm.ordner_neu(anlegen=True), namen, "anfrage_reisen", "reise",
                           f"{k['name']} ({k['email']}) bittet darum, Reisen anlegen zu dürfen. Entscheiden: auf der "
                           "Kontoseite oder mit „konten.py freischalten“.")
