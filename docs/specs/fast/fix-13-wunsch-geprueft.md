# Mini-Spec: fix-13-wunsch-geprueft

Issue #13 (Wunsch-Brett), letzter offener Prüfpunkt: Prüfung je Wunsch durch die KI.

## Befund (Abnahme-Lauf 15.11.2026, Wegwerf-Instanz, Beispielreise)

Karl bringt einen Wunsch ein, Idas AI-Client prüft ihn und trägt mit `wunsch_vorschlagen` einen Vorschlag ein (bezug T-02, T-05, Notiz mit Herkunft). Der Vorschlag kommt an (plan/wuensche.yaml, das Brett zeigt „Vorschlag: passt zu …“), der Wunsch bleibt aber in der Spalte „eingebracht“. Die Werkzeugbeschreibung sagt: „Das Brett zeigt ihn unter ‚geprüft‘“.

Ursache: `engine/rueckmeldungen.py` `spalte()` setzt „geprüft“ nur beim Rückmeldestatus `uebernommen` (feedback_resolve), nicht bei vorhandenem Vorschlag.

## Was ändert sich

- `spalte()`: Ein Wunsch mit Vorschlag (aus `wunsch_vorschlaege`) steht unter „geprüft“, auch wenn die Rückmeldung noch nicht abgeschlossen ist. Status `uebernommen` ohne Vorschlag bleibt wie bisher „geprüft“.
- Reiseseite (`engine/vorlage.html`, `wuSpalte`/`wuAlle`): Die Seite rechnet die Spalte selbst nach (für ohne Netz Abgehaktes) und muss dieselbe Regel wie der Dienst anwenden: ein Vorschlag heißt „geprüft“, und die Spalte wird auch bei leerem Rückmeldestatus nach dem Vorrang berechnet (Fund in Phase 6: sonst bliebe der Fehler auf der Seite bestehen, nur der Konnektor zeigte „geprüft“).

## Was darf sich nicht ändern

- Vorrang: passt nicht (verworfen) > erlebt > eingeplant (bestätigt oder Option gewählt) > geprüft > eingebracht.
- Bilanz, Punkte, Kontingent unverändert; ein Vorschlag ist nie eine Entscheidung (eingeplant setzt nur eine Organisator:in).

## Manuelle Test-Schritte

1. Wegwerf-Instanz: Karl `rueckmeldung_geben` (Art Wunsch), Ida `wunsch_vorschlagen` mit bezug und Notiz.
2. `wuensche` zeigt den Wunsch unter „Geprüft“ mit Vorschlag; Bilanz unverändert.
3. Ida `wunsch_aendern` eingeplant → „Eingeplant“; Karl erlebt → „Erlebt“.

## Inline-Test

- [ ] test_brett: Wunsch mit Vorschlag ohne Status uebernommen → Spalte geprueft; verworfen mit Vorschlag → passt_nicht; Vorschlag mit gewählter Option → eingeplant.
- [ ] test_seite (Brett im Browser): der Wunsch der Beispielreise mit Vorschlag (R-20261021-091500-a1b2) ohne abgeschlossene Rückmeldung steht auf der Seite unter „geprüft“; ohne Netz abgehakt weiterhin „erlebt“.
