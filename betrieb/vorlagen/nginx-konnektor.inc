# Gemeinsame Einstellungen der Orte des Konnektors (eingebunden von __INSTANZ__-konnektor.conf, erzeugt von
# betrieb/einrichten.sh). Endet auf .inc, damit „include <instanz>-*.conf“ im server-Block sie nicht selbst einbindet.
client_max_body_size 64k;
# Ohne Pfad: der Dienst bekommt die Adresse, wie sie kam (/mcp, /anmelden …)
proxy_pass http://127.0.0.1:__KN_PORT__;
proxy_http_version 1.1;
proxy_buffering off;
# Lesefrist: Der langsamste Weg ist der Schreibweg mit höchstens 28 s (engine/schreiben.py, ZEIT_GESAMT + ZEIT_PRUEFUNG,
# #118; ein Test prüft die Summe gegen diesen Wert). 60 s lassen dafür doppelten Spielraum und halten hängende
# Verbindungen trotzdem kurz (Vorlage bis 1.11.2026: 30 s, zu knapp neben 28 s).
proxy_read_timeout 60s;
proxy_set_header Host              $host;
proxy_set_header X-Forwarded-For   $remote_addr;
proxy_set_header X-Forwarded-Proto $scheme;
# Client-Adresse für die Begrenzung im Dienst; nginx setzt sie selbst, ein mitgeschickter Wert zählt nicht
proxy_set_header X-Real-IP         $remote_addr;
# Das Dienst-Geheimnis schickt nur der Konnektor intern, nie ein Browser
proxy_set_header X-Frieda-Dienst   "";
add_header X-Robots-Tag "noindex, nofollow" always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
