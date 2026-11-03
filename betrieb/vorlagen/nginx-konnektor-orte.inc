# nginx-Baustein für den Konnektor „Frieda“ (Claude-App, Anmeldung, Konto), einmal je Instanz; erzeugt von
# betrieb/einrichten.sh. Gehört in den server-Block von FR_KN_ADRESSE (Vorgabe: dieselbe Adresse wie die Reiseseiten,
# FR_ADRESSE): <FR_NGINX_SNIPPETS>/__INSTANZ__-konnektor-orte.inc, im Block mit einer eigenen Zeile eingebunden (include ...;).
# Endet auf .inc, nicht auf .conf: Der Stern „include <instanz>-*.conf“ für die Reise-Bausteine bindet ihn nicht mit ein (er stünde sonst
# in jedem Block, der die Reiseseiten einbindet, und die Orte doppelt).
#
# Der Konnektor steht an der Wurzel der Adresse (Paket J, #43, #163): /mcp für die Claude-App, Anmeldung und „Mein
# Konto“ (engine/anmeldung.py), OAuth (engine/oauth.py), Kalender-Abo, Friedas Zeichen und Schrift. Die Seiten verweisen
# mit Pfaden ab der Wurzel (/anmelden, /konto, /schrift/…), die OAuth-Metadaten liegen unter /.well-known/. Die Sitzung
# (Cookie __Host-frieda) gilt nur für diese Adresse; die Reiseseiten brauchen sie für „api/ich“ und liegen deshalb auf
# derselben Adresse.
#
# Gemeinsames (Weiterleitung, Lesefrist, Kopfzeilen) steht in __INSTANZ__-konnektor.inc daneben. Kein Referrer-Policy
# „no-referrer“ hier: Der Dienst setzt „same-origin“, sonst schicken Browser „Origin: null“ und jede Anmeldung scheitert
# an der Prüfung der Herkunft. Cache-Control, Content-Security-Policy und nosniff setzt ebenfalls der Dienst.
# Präfix-Orte (^~) und genaue Orte (=) gehen allgemeinen Regeln für Dateiendungen im server-Block vor.

# Drosseln (Zonen aus nginx-zone.conf, je Adresse; eigene Adressen zählen nicht): /mcp großzügig, weil die Claude-App von
# gemeinsamen Adressen aus aufruft; Anmelden streng; Konto und Seiten im Browser 30/min. /token, /register und die
# OAuth-Metadaten kommen ebenfalls von den gemeinsamen Adressen der Claude-App: kein Limit je Adresse, sonst träfe es alle
# Nutzer zusammen; der Dienst prüft PKCE, Weiterleitungsadressen und Codes selbst.
location = /mcp {
    limit_req zone=__ZONE_MCP__ burst=40 nodelay;
    limit_req_status 429;
    include __SNIPPETS__/__INSTANZ__-konnektor.inc;
    # Streamable HTTP: Antworten ungepuffert, Lesefrist lang (über dem längsten Schreibvorgang, ein Test prüft das)
    proxy_buffering off;
    proxy_read_timeout 300s;
}
location = /anmelden {
    limit_req zone=__ZONE_ANMELDEN__ burst=10 nodelay;
    limit_req_status 429;
    include __SNIPPETS__/__INSTANZ__-konnektor.inc;
}
location = /token                  { include __SNIPPETS__/__INSTANZ__-konnektor.inc; }
location = /register               { include __SNIPPETS__/__INSTANZ__-konnektor.inc; }
location ^~ /.well-known/oauth-    { include __SNIPPETS__/__INSTANZ__-konnektor.inc; }
# Startseite (/ führt zu Mein Konto, #41), Konto, Abmelden, Zustimmung, Bereitschaft (ohne Dateiendung, deshalb trifft keine Regel für Endungen)
location ~ ^/(konto|abmelden|authorize|gesund)?$ {
    limit_req zone=__ZONE_KONTO__ burst=20 nodelay;
    limit_req_status 429;
    include __SNIPPETS__/__INSTANZ__-konnektor.inc;
}
location ^~ /einladung/ {
    limit_req zone=__ZONE_KONTO__ burst=20 nodelay;
    limit_req_status 429;
    include __SNIPPETS__/__INSTANZ__-konnektor.inc;
}
# Kalender-Abo je Person (engine/kalender.py): Kalender-Apps fragen regelmäßig, ohne Anmeldung
location ^~ /kalender/ {
    limit_req zone=__ZONE_KONTO__ burst=20 nodelay;
    limit_req_status 429;
    include __SNIPPETS__/__INSTANZ__-konnektor.inc;
}
# Schrift und Zeichen der Anmeldeseiten; claude.ai zeigt das Favicon der Adresse am Konnektor. Ohne Drossel (eine Seite
# lädt mehrere Dateien), der Dienst liefert nur diese festen Dateien.
location ^~ /schrift/              { include __SNIPPETS__/__INSTANZ__-konnektor.inc; }
location = /favicon.ico            { include __SNIPPETS__/__INSTANZ__-konnektor.inc; }
location = /favicon.svg            { include __SNIPPETS__/__INSTANZ__-konnektor.inc; }
location = /apple-touch-icon.png   { include __SNIPPETS__/__INSTANZ__-konnektor.inc; }
location = /icon-192.png           { include __SNIPPETS__/__INSTANZ__-konnektor.inc; }
location = /icon-512.png           { include __SNIPPETS__/__INSTANZ__-konnektor.inc; }
# Frieda-App (#21): Manifest, Worker nur für Push (Scope /, muss an der Wurzel liegen), Skript von Mein Konto
location = /manifest.webmanifest   { include __SNIPPETS__/__INSTANZ__-konnektor.inc; }
location = /sw.js                  { include __SNIPPETS__/__INSTANZ__-konnektor.inc; }
location = /konto.js               { include __SNIPPETS__/__INSTANZ__-konnektor.inc; }

# Übergang (Paket J): geheime Links je Reise und Person aus der Zeit vor den Konten. An der Wurzel ausgestellt
# (<FR_KN_ADRESSE>/<token>, freischalten.sh --person) …
location ~ "^/[A-Za-z0-9_-]{20,100}$" {
    limit_req zone=__ZONE_KONTO__ burst=20 nodelay;
    limit_req_status 429;
    include __SNIPPETS__/__INSTANZ__-konnektor.inc;
}
# … und unter dem früheren Pfad /__INSTANZ__-mcp/<token>, der bis 1.11.2026 die Vorgabe war. Der Präfix fällt weg.
# Unbekannte Tokens beantwortet der Dienst mit 404. Entfällt, sobald alle Personen ein Konto haben.
location ^~ /__INSTANZ__-mcp/ {
    limit_req zone=__ZONE_KONTO__ burst=20 nodelay;
    limit_req_status 429;
    client_max_body_size 64k;
    proxy_pass http://127.0.0.1:__KN_PORT__/;
    proxy_http_version 1.1;
    proxy_buffering off;
    proxy_read_timeout 60s;
    proxy_set_header Host              $host;
    proxy_set_header X-Forwarded-For   $remote_addr;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Real-IP         $remote_addr;
    proxy_set_header X-Frieda-Dienst   "";
    add_header X-Robots-Tag "noindex, nofollow" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
}
