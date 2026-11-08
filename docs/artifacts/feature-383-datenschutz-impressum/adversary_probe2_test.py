import sys
W = '.'  # Wurzel des Repos (Aufruf aus dem Repo-Ordner)
sys.path[:0] = [W + '/engine/tests', W + '/engine']
from test_anmeldung import welt, abruf, anmelden, IDA
import pytest

FEHLT = ['nicht eingerichtet', 'not been set up']
ALL = ['FR_BETREIBER_NAME', 'FR_BETREIBER_ANSCHRIFT', 'FR_BETREIBER_KONTAKT']

def zeile(t):
    return t.count('<p class="recht">')

def test_leerraum(welt, monkeypatch):
    u = welt()
    out = []
    for leer in ['   ', chr(9), chr(10), chr(32)+chr(9)+chr(13)+chr(10)+chr(32), chr(160), chr(0x200b)]:
        for fehlt in ALL:
            for n in ALL:
                monkeypatch.setenv(n, leer if n == fehlt else 'X-' + n[-4:])
            s, h, t = abruf(u.kurl + '/impressum', kopf={'Accept-Language': 'en'})
            out.append((repr(leer), fehlt[-6:], s, 'hinweis' if 'not been set up' in t else 'FELDER', '<strong>' in t))
    for n in ALL:
        monkeypatch.setenv(n, ' Wert ' + n[-4:] + ' ')
    s, h, t = abruf(u.kurl + '/impressum')
    out.append(('gesetzt mit Rand', s, 'Wert' in t and '<p style="margin:.2rem 0 0">Wert' in t))
    for n in ALL:
        monkeypatch.delenv(n)
    s, h, t = abruf(u.kurl + '/impressum'); out.append(('alle fehlen', s, 'nicht eingerichtet' in t))
    s, h, t = abruf(u.kurl + '/warteliste'); out.append(('warteliste', s, zeile(t)))
    # Seiten mit Rechtszeile, Anzahl der Zeilen
    seiten = ['/warteliste', '/anmelden', '/anmelden?schritt=code&email=a@b.invalid', '/datenschutz', '/impressum', '/alpha', '/einladung/gibt-es-nicht', '/warteliste/bestaetigen/unbekannt', '/kalender/xyz', '/nirgends']
    for p in seiten:
        s, h, t = abruf(u.kurl + p); out.append((p, s, zeile(t), t.count('href="/impressum"')))
    ida, _ = anmelden(u, IDA, name='Ida')
    for p in ['/konto', '/konto?loeschen=1']:
        s, h, t = abruf(u.kurl + p, cookie=ida); out.append((p, s, zeile(t), t.count('href="/impressum"')))
    s, h, t = abruf(u.kurl + '/konto', 'POST', {'aktion': 'loeschen'}, cookie=ida); out.append(('loeschen ohne Haken', s, zeile(t)))
    s, h, t = abruf(u.kurl + '/konto', 'POST', {'aktion': 'loeschen', 'sicher': 'ja'}, cookie=ida); out.append(('konto geloescht', s, zeile(t), t.count('href="/impressum"')))
    s, h, t = abruf(u.kurl + '/anmelden', 'POST', {'schritt': 'adresse', 'email': 'x'}, origin='https://evil.invalid'); out.append(('403 Herkunft', s, zeile(t)))
    s, h, t = abruf(u.kurl + '/impressum', 'POST'); out.append(('405', s, zeile(t)))
    open(W + '/docs/artifacts/feature-383-datenschutz-impressum/adversary-probe2-output.txt', 'w').write(chr(10).join(map(str, out)))
