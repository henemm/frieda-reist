# Kontext: Warteliste mit Freigabe (#382)

Stand 6.11.2026. Meilenstein M5a „Alpha-Start“, Spur A.

## Vorhandenes, das wir nutzen
- `engine/konten.py`: `mail_senden` (SMTP oder `FR_MAIL_DATEI`), `_begrenzt` (Tabelle `versand`), `adresse` (Prüfung), Tabelle `anfragen` und `freischalten` (Recht `reise_anlegen`), Recht `betreiber`, Befehle in `main`.
- `engine/anmeldung.py`: öffentliche Seiten (`ist_unsere`, `bearbeiten`), Herkunftsprüfung bei POST, Betreiber-Abschnitt auf `/konto` mit Knöpfen „Freigeben/Ablehnen“, `betreiber_melden`.
- `betrieb/vorlagen/nginx-konnektor-orte.inc`: Pfade, die an den Dienst gehen.
- Textkataloge `engine/texte_de.py`, `engine/texte_en.py` (ADR-0006).

## Festlegungen
- Freie Anmeldung bleibt offen (Product Owner, 6.11.2026); die Warteliste steuert nur das Recht „Reisen anlegen“.
- Betreiber: Befehl und Abschnitt auf `/konto`.
- Keine Reise-Einladung: die Freigabe lädt zum Dienst ein.

## Abgrenzung
- #381 Löschen/Exportieren, #383 Datenschutz/Impressum, #380 Trennung der Tester (Spur B).
- Sitzung `packliste` arbeitet an #348 und ändert `betrieb/deploy.sh`, `docs/betrieb.md`; bei Überschneidung nach dem Vorspulen neu aufsetzen.
