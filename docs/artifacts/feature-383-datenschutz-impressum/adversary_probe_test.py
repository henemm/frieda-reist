import sys
W = '.'  # Wurzel des Repos (Aufruf aus dem Repo-Ordner)
sys.path[:0] = [W + '/engine/tests', W + '/engine']
from test_anmeldung import welt, BASIS
import http.client, urllib.parse

def roh(url, m, h=None):
    t = urllib.parse.urlsplit(url); c = http.client.HTTPConnection(t.hostname, t.port, timeout=10)
    c.request(m, t.path + ('?' + t.query if t.query else ''), headers=h or {})
    r = c.getresponse(); return r.status, dict(r.getheaders()), r.read().decode()

def test_probe(welt, monkeypatch):
    u = welt()
    monkeypatch.setenv('FR_BETREIBER_NAME', '<script>alert(1)</script>"&')
    monkeypatch.setenv('FR_BETREIBER_ANSCHRIFT', 'Zeile1\nZeile2<img src=x onerror=1>')
    monkeypatch.setenv('FR_BETREIBER_KONTAKT', 'a@b.invalid')
    b = u.kurl
    out = []
    for p in ['/impressum', '/impressum?x=1&y=<b>', '/impressum/', '/impressum/x', '/Impressum', '/impressum.html', '/alpha/', '//impressum', '/impressum;a']:
        s, h, t = roh(b + p, 'GET', {'Accept-Language': 'en'}); out.append((p, s, len(t)))
    for m in ['HEAD', 'PUT', 'DELETE', 'OPTIONS', 'PATCH', 'PROPFIND', 'POST']:
        s, h, t = roh(b + '/impressum', m, {'Origin': BASIS, 'Content-Length': '0'}); out.append((m, s, h.get('Allow'), len(t)))
    s, h, t = roh(b + '/impressum', 'GET', {'Accept-Language': 'en'})
    out.append(('XSS', 'onerror=1>' in t, '&lt;img' in t, '&lt;script' in t))
    monkeypatch.setenv('FR_BETREIBER_NAME', '   ')
    s, h, t = roh(b + '/impressum', 'GET', {'Accept-Language': 'en'}); out.append(('whitespace-name', s, 'not been set up' in t, 'Address' in t, t[t.find('<h1>'):t.find('<h1>')+500]))
    for p in ['/warteliste', '/anmelden', '/konto', '/', '/datenschutz', '/alpha']:
        s, h, t = roh(b + p, 'GET'); out.append((p, s, '/impressum' in t, '/datenschutz' in t, '/alpha' in t))
    s, h, t = roh(b + '/datenschutz', 'GET', {'Accept-Language': 'en'}); out.append(('ds-en', s, 'Privacy policy' in t))
    open(W + '/docs/artifacts/feature-383-datenschutz-impressum/adversary-probe-output.txt', 'w').write(chr(10).join(map(str, out)))
