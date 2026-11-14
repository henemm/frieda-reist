# Umstellung der Instanz, 14.11.2026 (#552, AC-3 und AC-20 bis AC-22)

Protokoll ohne Pfade der Instanz: `<srv>` ist der Seitenordner, `<home>` das Home des Dienstbenutzers.
Software-Stand bei der Umstellung: `4feee4a`, danach `f8f9ba7` (Korrektur des Kartendienst-Umzugs, siehe unten).

## Ablauf

1. Rückweg gesichert (Units, sudoers, nginx-Bausteine, Helfer, Baseline des Integritätswächters), privat im Home des
   Betriebsbenutzers; vor der Installation gegen den Server verglichen: unverändert seit der Sicherung vom 13.11.
2. `einrichten.sh --installieren` im Software-Klon: Units, Zonendatei, `.inc`-Bausteine, Reise-Helfer, sudoers-Datei
   `<instanz>`, Karte-Benutzer, Umzug der Kartendaten, Karte-Skript, Units des Kartendienstes.
3. Units-Helfer und Orte-Helfer aus dem Ausgabeordner erneuert, alte sudoers-Dateien `<instanz>-units` und
   `<instanz>-nginx-orte` entfernt (`visudo -c` grün), `deploy.sh --dienste` (2723 Tests grün), Netzdienste neu gestartet,
   `nginx -t` und Reload.

## AC-3: Messlauf unter den Sandbox-Werten der installierten Einheit

Per `systemd-run` mit genau den Werten aus `<instanz>-schreiben.service` (User, `NoNewPrivileges`, `PrivateTmp`,
`ProtectSystem=strict`, `ProtectHome=read-only`, `InaccessiblePaths`, `ReadWritePaths`, Umgebungsdateien):

```
== Schreibziele (müssen schreibbar sein)
  ok        schreibbar: <srv>/_software
  ok        schreibbar: <srv>/_dienst
  ok        schreibbar: <srv>/_konten
  ok        schreibbar: <srv>
  ok        schreibbar: <srv>/_rueckmeldungen
== Gesperrte Ziele (dürfen nicht schreibbar sein)
  ok        gesperrt: <home>/.messprobe-552
  ok        gesperrt: <home>/.profile.messprobe
  ok        gesperrt: /etc/.messprobe-552
  ok        gesperrt: /usr/local/sbin/.messprobe-552
  ok        Docker-Socket nicht erreichbar
  ok        kein sudo (NoNewPrivileges)
== Messlauf (Werkzeugmix über den Eingang des Schreibwegs, Speicherweg)
nacheinander: Anzahl 6, Mittel 0.49 s, p50 0.54 s, p90 0.57 s, p99 0.63 s, Maximum 0.63 s; 504: 0, 429: 0, 5xx: 0, 200: 6, 422: 0
parallel: Anzahl 6, Mittel 0.62 s, p50 0.55 s, p90 0.62 s, p99 1.26 s, Maximum 1.26 s; 504: 0, 429: 0, 5xx: 0, 200: 6, 422: 0
Export: Anzahl 4, Mittel 0.003 s, Maximum 0.004 s
Probebau: Anzahl 4, Mittel 0.096 s, Maximum 0.187 s
  Ausgang Messlauf: 0
== Veröffentlichen (wie vom Schreibweg angestoßen)
  Ausgang Veröffentlichen: 0
== Ergebnis: 0 Fehler
```

Echte Schreibvorgänge über den Konnektor auf einer vorhandenen Testreise (Untertitel gesetzt und wieder geleert, Reise-Stände
13 und 14): beide 200, Stand 14 veröffentlicht. Journal des Schreibwegs und des Veröffentlichens: kein verweigerter
Schreibzugriff (`read-only file system`, `permission denied`). Dabei aufgefallen, unabhängig von der Sandbox: Der Schreibweg
stößt im Software-Klon das Veröffentlichen gar nicht an (falscher Skriptpfad seit #454), die Seite kommt erst mit dem Timer;
eigenes Issue #570.

## AC-20 bis AC-22

- `units.py pruefen` Ausgang 0, `nginx.py pruefen` Ausgang 0.
- Alle Bausteine der Instanz (`snippets/<instanz>-*`, `conf.d/<instanz>-zone.conf`) `0640 root:<gruppe>`.
- sudoers-Datei `<instanz>`: nur die drei Helfer und `systemctl restart` der vier Netzdienste.
- Docker-Socket in den Namensräumen von Konnektor, Rückmeldedienst, Push und Schreibweg: Modus `0` (unerreichbar);
  außerhalb antwortet er wie bisher.
- Kartendaten im Zustandsordner, an der alten Stelle ein root-eigener Verweis; `abdeckung.json` `0644` (Korrektur `4feee4a`).
- Kartenaktualisierung als Karte-Benutzer: Ergebnis `success` („up to date“). Probeabfrage am Kartendienst: gültige Antwort.
- Freischalten einer vorhandenen Testreise über den Reise-Helfer: Ausgang 0, Seite antwortet.

## Befund bei der Umstellung: Kartendienst startete nach dem Umzug nicht

Der Umzug gab die Datenbank rekursiv dem Karte-Benutzer. Der Abfragedienst im Container läuft als `overpass` (Kennung 1000)
und scheiterte beim Start an `osm3s_osm_base` (Permission denied). Sofortmaßnahme: Inhalt des Datenordners der Kennung 1000
zurückgegeben (wie vor dem Umzug), Dienst antwortet wieder. Ursache behoben in `f8f9ba7` (nur der Datenordner selbst wechselt
den Eigentümer), Test `test_umzug_laesst_eigentuemer_der_datenbank_unveraendert`. Ohne Folgen für Nutzer: Kartenpunkte fallen
in der Zeit auf den öffentlichen Dienst zurück.

## Integritätswächter

Die Abweichungen (Units, sudoers, Benutzer der Instanz, dazu ein SSH-Schlüssel eines anderen Projekts) hat der Product Owner
am 14.11. um 08:55 UTC per Telegram bestätigt, bevor das gezielte Bestätigen lief. Danach meldet der Wächter keine Abweichung.
