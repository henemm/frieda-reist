# Mini-Spec: fix-634-status-archiv

Issue #634: Die Reiseseite zeigt bei einer archivierten Reise den Rohschlüssel `seite.reise_status.archiv` statt eines Wortes, und daneben „noch n Tage“.

## Was ändert sich
- Neuer Seitentext `seite.reise_status.archiv` in allen Sprachen (`engine/texte_de.py`: „Archiviert“, `engine/texte_en.py`: „Archived“). Das Etikett unter dem Titel zeigt bei einer archivierten Reise dieses Wort.
- Der Zähler im Kopf des Plans („noch n Tage“, „Tag x von n“) entfällt bei archivierten Reisen (`reiseZaehler` in `engine/vorlage.html`). Begründung (technische Entscheidung des Tech Leads): Eine archivierte Reise ist beiseitegelegt und nur noch lesbar; ein Countdown suggeriert, sie finde statt. Für „danach“ entfällt er schon heute, weil die Daten vorbei sind.
- Neuer Test: Für jeden Status, den die Software kennt (`reise.STATUS`, zugleich Enum von `trip_status_set`), gibt es in jeder Sprache einen Seitentext `seite.reise_status.<status>`. Ein künftiger Status ohne Text macht den Test rot.
- Test: Die Seite einer archivierten Beispielreise zeigt „Archiviert“ und keinen Rohschlüssel, und keinen Zähler.

## Was darf sich nicht ändern
- Die Auswahl zum Umstellen des Status bleibt bei den fünf Status (idee … danach); „archiv“ wird dort nicht angeboten (Archivieren läuft wie bisher über die Claude-App).
- Zähler bei allen anderen Status unverändert.
- Keine weiteren Texte, keine Änderung an Konnektor oder Reisedaten.

## Manuelle Test-Schritte
1. Beispielreise mit Status `archiv` bauen, Seite öffnen: Etikett „Archiviert“, kein „noch n Tage“.
2. Dieselbe Reise mit Status `planung`: Etikett „Planung“, Zähler wie bisher.

## Inline-Test (wird während Implementierung geschrieben)
- [ ] Jeder Wert aus `reise.STATUS` hat `seite.reise_status.<wert>` in jeder Sprache
- [ ] Seite einer archivierten Reise: Text statt Rohschlüssel, kein Zähler (Playwright, wie die bestehenden Seitentests)
