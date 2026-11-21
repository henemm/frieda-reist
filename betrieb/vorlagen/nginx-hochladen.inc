# nginx-Baustein für den Hochlade-Link eigener Fotos aus dem Chat (#582, Spec docs/specs/oberflaeche/bilder-582-eigene-fotos.md),
# einmal je Instanz; erzeugt von betrieb/einrichten.sh als <FR_NGINX_SNIPPETS>/__INSTANZ__-hochladen.inc und mit
# einrichten.sh --installieren installiert. Gehört in den server-Block von FR_KN_ADRESSE (dort, wo die Orte des Konnektors
# stehen) mit einer eigenen Zeile:  include __SNIPPETS__/__INSTANZ__-hochladen.inc;
# Nicht in der Orte-Datei des Konnektors: deren Hilfsprogramm (nginx-orte-installieren, #445) erlaubt mit Absicht weder
# proxy_pass noch client_max_body_size (#552). Endet auf .inc, damit „include <instanz>-*.conf“ ihn nicht mit einbindet.
#
# Die Seite hinter dem Link und das Hochladen liefert der Rückmeldedienst (GET und POST /hochladen/<token>): Fotos bis 12 MB,
# 13m lässt Kopf und Rahmen zu. Der Link ist ohne Anmeldung nutzbar, deshalb gedrosselt wie Konto und Seiten; der Dienst
# drosselt zusätzlich je Adresse und begrenzt jeden Link auf 10 Fotos. Das Dienst-Geheimnis schickt nie ein Browser.
location ^~ /hochladen/ {
    client_max_body_size 13m;
    limit_req zone=__ZONE_KONTO__ burst=20 nodelay;
    limit_req_status 429;
    proxy_pass http://127.0.0.1:__RM_PORT__/hochladen/;
    proxy_set_header Host              $host;
    proxy_set_header X-Forwarded-For   $remote_addr;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Real-IP         $remote_addr;
    proxy_set_header X-Frieda-Dienst   "";

    add_header X-Robots-Tag "noindex, nofollow" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
}
