"""Mail-Rahmen: Text- und HTML-Teil der Code-Mail aus denselben Schlüsseln des Katalogs (#532).

Reine Funktionen ohne Datenbank und ohne Netz. Das Modul lädt nur texte und instanz, nie anmeldung oder konten
(Zirkel). Der HTML-Teil ist ein Gerüst aus Tabellen mit Inline-Stilen; der einzige Stilblock enthält nur den
Dunkelmodus. Keine Bilder, keine Zählpixel, keine externen Ressourcen, keine Webschriften. Jeder eingesetzte Wert geht
durch html.escape. Adressen erscheinen im HTML nur in href, und nur mit einer Basis, die mit http:// oder https://
beginnt. Der Code steht nie in einem Link. Betreiberangaben im Fuß kommen aus FR_BETREIBER_NAME und
FR_BETREIBER_ANSCHRIFT; fehlt eine, steht der Fuß ohne sie da."""
import html
import urllib.parse

import instanz
import texte

DUNKEL = ("@media (prefers-color-scheme: dark) {\n"
          "  .fr-grund { background-color: #1c1b19 !important; }\n"
          "  .fr-karte { background-color: #2a2825 !important; border-color: #3d3a35 !important; }\n"
          "  .fr-text { color: #ece8e1 !important; }\n"
          "  .fr-leise { color: #b5aea3 !important; }\n"
          "  .fr-code { background-color: #1c1b19 !important; color: #ffffff !important; border-color: #4a463f !important; }\n"
          "  .fr-knopf { background-color: #8fb3a0 !important; color: #10201a !important; }\n"
          "  .fr-fuss { border-top-color: #3d3a35 !important; }\n"
          "  .fr-link { color: #a9cbb9 !important; }\n"
          "}")
SCHRIFT = "font-family: -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;"


def esc(s):
    return html.escape(str(s), quote=True)


def gueltige_basis(basis):
    """Die Basisadresse, wenn sie mit http:// oder https:// beginnt, sonst leer (keine anderen Schemata)."""
    basis = (basis or "").strip().rstrip("/")
    return basis if basis.startswith(("http://", "https://")) else ""


def betreiber():
    """Name und Zeilen der Anschrift aus der Instanz; leer oder nur Leerraum zählt als fehlend."""
    name = (instanz.wert("FR_BETREIBER_NAME") or "").strip()
    anschrift = [z.strip() for z in (instanz.wert("FR_BETREIBER_ANSCHRIFT") or "").splitlines() if z.strip()]
    return name, anschrift


def fuss(sprache, basis):
    """Fuß der Mail -> (Text, HTML): Grund, Betreiberangaben (soweit gesetzt), Impressum und Datenschutz."""
    basis = gueltige_basis(basis)
    name, anschrift = betreiber()
    grund = texte.t(sprache, "mail.fuss.grund")
    recht = [(texte.t(sprache, "mail.fuss.impressum"), f"{basis}/impressum" if basis else ""),
             (texte.t(sprache, "mail.fuss.datenschutz"), f"{basis}/datenschutz" if basis else "")]
    zeilen = [grund, ""]
    if name or anschrift:
        zeilen += ([name] if name else []) + anschrift + [""]
    zeilen += [f"{wort}: {ziel}" if ziel else wort for wort, ziel in recht]
    leise = "color: #6b6459; font-size: 13px; line-height: 1.5;"
    teile = [f'<p class="fr-leise" style="margin: 0 0 12px 0; {leise}">{esc(grund)}</p>']
    if name or anschrift:
        absatz = "<br>".join(esc(z) for z in ([name] if name else []) + anschrift)
        teile.append(f'<p class="fr-leise" style="margin: 0 0 12px 0; {leise}">{absatz}</p>')
    links = " &middot; ".join(
        f'<a class="fr-link" href="{esc(ziel)}" style="color: #3f6b55; text-decoration: underline;">{esc(wort)}</a>'
        if ziel else esc(wort) for wort, ziel in recht)
    teile.append(f'<p class="fr-leise" style="margin: 0; {leise}">{links}</p>')
    return "\n".join(zeilen), "\n".join(teile)


def code_link(basis, adresse):
    """Link zur Code-Eingabe ohne Code; ohne gültige Basis keiner."""
    basis = gueltige_basis(basis)
    if not basis:
        return None
    return f"{basis}/anmelden?{urllib.parse.urlencode({'schritt': 'code', 'email': adresse})}"


def code_mail(sprache, zweck, code, minuten, link, basis=""):
    """Code-Mail -> (Betreff, Text, HTML). link ist None oder die fertige Adresse zur Code-Eingabe (nie mit Code)."""
    betreff = " ".join(texte.t(sprache, f"mail.code.betreff_{zweck}", code=code).split())
    titel = texte.t(sprache, f"mail.code.titel_{zweck}")
    eingabe = texte.t(sprache, "mail.code.zeile_eingabe", minuten=minuten)
    sicher_titel, sicher_text = texte.t(sprache, "mail.code.sicher_titel"), texte.t(sprache, "mail.code.sicher_text")
    fuss_text, fuss_html = fuss(sprache, basis)

    zeilen = [titel, "", texte.t(sprache, "mail.code.zeile_code", code=code), "", eingabe, ""]
    if link:
        zeilen += [texte.t(sprache, "mail.code.zeile_link"), link, ""]
    zeilen += [sicher_titel, sicher_text, "", "--", fuss_text]
    text = "\n".join(zeilen)

    knopf = ""
    if link:
        knopf = (f'<tr><td style="padding: 0 32px 24px 32px;">'
                 f'<a class="fr-knopf" href="{esc(link)}" style="display: inline-block; padding: 12px 20px; '
                 f'background-color: #3f6b55; color: #ffffff; border-radius: 8px; text-decoration: none; '
                 f'font-weight: 600; {SCHRIFT}">{esc(texte.t(sprache, "mail.code.zeile_link"))}</a></td></tr>')
    html_teil = f"""<!DOCTYPE html>
<html lang="{esc(sprache)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta name="supported-color-schemes" content="light dark">
<title>{esc(betreff)}</title>
<style>
{DUNKEL}
</style>
</head>
<body class="fr-grund" style="margin: 0; padding: 0; background-color: #f4f1ec;">
<div style="display: none; max-height: 0; overflow: hidden; opacity: 0; mso-hide: all;">{esc(texte.t(sprache, "mail.code.vorschau"))}</div>
<table role="presentation" class="fr-grund" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #f4f1ec;">
<tr><td align="center" style="padding: 24px 12px;">
<table role="presentation" class="fr-karte" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width: 520px; background-color: #ffffff; border: 1px solid #e3ddd3; border-radius: 12px; {SCHRIFT}">
<tr><td class="fr-text" style="padding: 32px 32px 8px 32px; color: #2b2925; font-size: 22px; font-weight: 600; line-height: 1.3; {SCHRIFT}">{esc(titel)}</td></tr>
<tr><td style="padding: 16px 32px;">
<table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>
<td class="fr-code" style="padding: 14px 20px; background-color: #f4f1ec; color: #1f1d1a; border: 1px solid #e3ddd3; border-radius: 8px; font-family: 'SFMono-Regular', Menlo, Consolas, 'Liberation Mono', monospace; font-size: 32px; font-weight: 700; letter-spacing: 6px;">{esc(code)}</td>
</tr></table>
</td></tr>
<tr><td class="fr-text" style="padding: 8px 32px 24px 32px; color: #2b2925; font-size: 16px; line-height: 1.5; {SCHRIFT}">{esc(eingabe)}</td></tr>
{knopf}
<tr><td class="fr-text" style="padding: 0 32px 24px 32px; color: #2b2925; font-size: 15px; line-height: 1.5; {SCHRIFT}"><strong>{esc(sicher_titel)}</strong><br>{esc(sicher_text)}</td></tr>
<tr><td class="fr-fuss" style="padding: 20px 32px 28px 32px; border-top: 1px solid #e3ddd3; {SCHRIFT}">
{fuss_html}
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>
"""
    return betreff, text, html_teil
