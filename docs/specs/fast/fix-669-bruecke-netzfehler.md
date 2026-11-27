# Mini-Spec: Testzugang-Brücke beantwortet Netzfehler, statt abzubrechen (#669)

## Was ändert sich
- `betrieb/testzugang.py`, Befehl `dienst`: Scheitert die Weiterleitung einer Nachricht an den Konnektor an einem
  Netzfehler (`OSError`, darunter `URLError`, abgelehnte Verbindung, Zeitüberschreitung, sowie
  `http.client.HTTPException`) oder an einer gescheiterten Token-Erneuerung (`Abbruch` aus `erneuern`), antwortet die
  Brücke auf diese Anfrage mit einer JSON-RPC-Fehlerantwort `-32603` und der ID der Anfrage. Sie läuft weiter; die
  nächste Anfrage versucht es erneut. Eine Benachrichtigung (ohne `id`) bleibt auch im Fehlerfall ohne Antwort.
- Ist der Konnektor schon beim Start nicht erreichbar (Netzfehler während der Kontoprüfung), endet die Brücke nicht.
  Sie beantwortet jede Anfrage mit `-32603` und wiederholt die Kontoprüfung vor der nächsten Weiterleitung, bis sie
  gelingt. Erst nach bestandener Prüfung wird etwas weitergeleitet.
- Der Fehlertext nennt nur die Art des Fehlers (etwa `Connector unreachable (ConnectionRefusedError)`), keine
  Tokens, keine Pfade der Ablage. Er ist englisch wie die übrigen Meldungen der Brücke (Betriebswerkzeug, nur
  Standardbibliothek, ohne Textkatalog der Engine).
- Befund F002 (Sperre nur für `mcp__claude_ai_Frieda__*`): geprüft, keine Änderung. In Claude-Code-Sitzungen dieses
  Repos erscheint von der Instanz nur der Konnektor `Frieda`; weitere Konnektoren derselben Instanz gibt es nicht.
  Kommt einer hinzu, wird die Sperre in einem eigenen Issue erweitert.

## Was darf sich nicht ändern
- Gehört der Zugang nicht zum Testkonto oder ist das Testkonto Betreiber, bricht die Brücke wie bisher ab, ohne etwas
  weiterzuleiten (Exit-Code ungleich 0, keine Antworten).
- Fehlt die Ablage oder ein Instanzwert, bricht die Brücke wie bisher beim Start ab.
- Erneuern bei Ablauf und bei 401, die Dateisperre für parallele Sitzungen und alle übrigen Antworten bleiben gleich.
- Nur Standardbibliothek.

## Manuelle Test-Schritte
1. Brücke mit einer nicht erreichbaren Konnektoradresse starten, `initialize` und `tools/list` schicken: zwei
   Fehlerantworten `-32603` mit den IDs 1 und 2, Exit-Code 0, kein Traceback.
2. Brücke normal starten, `initialize` beantworten lassen, dann den Konnektor unerreichbar machen und `tools/list`
   schicken: Fehlerantwort mit ID 2, danach eine weitere Anfrage wieder mit Fehlerantwort, die Brücke läuft weiter.

## Inline-Test (wird während Implementierung geschrieben)
- [ ] Test: Brücke mit Adresse eines geschlossenen lokalen Ports beantwortet Anfragen mit `-32603` und richtiger ID,
      Benachrichtigungen ohne Antwort, endet mit 0, ohne Traceback auf stderr.
- [ ] Test: Netzfehler mitten im Lauf (Adresse nach bestandener Prüfung umgebogen) ergibt eine Fehlerantwort, die
      Brücke bleibt am Leben und beantwortet die folgende Anfrage.
- [ ] Test: Wird der Konnektor nach einem Netzfehler beim Start wieder erreichbar, prüft die Brücke das Konto und leitet
      dann weiter; mit einem Zugang eines anderen Kontos bricht sie auch dann ohne Weiterleitung ab.
- [ ] Test: Scheitert die Token-Erneuerung, antwortet die Brücke mit `-32603` und läuft weiter.
