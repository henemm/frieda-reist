# Sprachen

Frieda spricht Deutsch und Englisch, und jede Person kann in ihrer Sprache mit Frieda arbeiten. Die Reise selbst bleibt dabei in der Sprache, in der sie geschrieben ist: Frieda übersetzt keine Inhalte.

**Auf einen Blick:** Wo: Gespräch · Reiseseite · Mein Konto · Wer: Sprache der Reise Organisator:innen; Sprache des Kontos jede Person · Baustein: immer da

## Was du damit tun kannst

- Für jede Reise eine Sprache festlegen, in der die Seite startet und in der Frieda in die Reise schreibt.
- Für dein Konto eine eigene Sprache wählen, in der Frieda im Gespräch, auf Mein Konto und in Mails mit dir spricht.
- Als Gast ohne Konto die Beschriftungen der Reiseseite in eine andere Sprache umstellen.
- Datum, Zahlen und Sortierung in der gewählten Sprache sehen.

## So geht's

Drei Dinge sind getrennt:

| Was | gilt für | ändern |
|---|---|---|
| Sprache der Reise | Startsprache der Seite, Einträge im Kalender, Wortlaut der Meldungen des Wächters, alles, was Frieda in die Reise schreibt (Verlauf, Herkunftszeilen), Einladungen an Adressen ohne Konto | beim Anlegen, später im Gespräch (nur Organisator:innen, mit Grund) |
| Sprache des Kontos | Frieda im Gespräch (Anleitung, Antworten, Fehler), Mein Konto, Mails und Push-Nachrichten an dich (Betreff, Anrede, Hinweise; die Meldung selbst steht in der Sprache der Reise), Name des Kalender-Abos, die Hülle der Reiseseite, wenn du angemeldet bist | Mein Konto oder im Gespräch |
| Umschalter im Fuß der Seite | nur die Beschriftungen der Seite auf diesem Gerät | nur für Gäste ohne Konto |

### Im Gespräch

> „Antworte mir bitte auf Englisch, und stell mein Konto auch so ein.“

> „Die Reise soll ab jetzt englisch sein, weil Freunde aus Irland mitkommen.“

| Werkzeug | wofür |
|---|---|
| `language_set` | Sprache des Kontos |
| `trip_create` | neue Reise mit `language` (Vorgabe: Sprache deines Kontos) |
| `setting_set` | Sprache einer bestehenden Reise |

### Auf der Reiseseite

Angemeldet zeigt die Seite die Sprache deines Kontos. Gäste ohne Konto finden ganz unten im Fuß die Zeile „Sprache: Deutsch · English“; die Wahl merkt sich das Gerät.

### Auf Mein Konto

Unter „Einstellungen“ steht „Sprache“. Die Änderung gilt sofort für Mein Konto, Mails und das Gespräch.

## Regeln und Grenzen

- **Inhalte werden nie übersetzt.** Wissen, Namen von Arten und Merkmalen, Fragen, Gründe und alles, was eine Person eingibt, bleiben in ihrer Sprache. Liest du eine deutsche Reise mit englischer Hülle, sind Knöpfe und Datum englisch, die Texte der Reise deutsch.
- Claude kann Inhalte beim Vorlesen im Gespräch für dich übersetzen, schreibt sie aber unverändert in die Reise.
- Die Namen der Werkzeuge in der Claude-App sind englisch, egal welche Sprache du sprichst.
- Nie übersetzt werden auch die Kennungen (T-, E-, U- …) und feste Werte in den Dateien der Reise.
- Ein neues Konto bekommt die Sprache deines Browsers, wenn Frieda sie kennt, sonst Englisch.
- Weitere Sprachen sind vorgesehen: Jede ist eine einzelne Datei in der Software, ohne Umbau. Wie das geht, steht in [Sprachen: eine Sprache hinzufügen](../sprachen.md#eine-sprache-hinzufügen).

## Siehe auch

- [Konto](konto.md), [Reiseseite](reiseseite.md), [Lebenszyklus](lebenszyklus.md), [Planen im Gespräch](gespraech.md)
- Referenz: [Sprachen der Software](../sprachen.md), [ADR-0006: Mehrsprachigkeit](../adr/0006-mehrsprachigkeit.md), [Konnektor: Englische Namen der Schnittstelle](../konnektor.md#englische-namen-der-schnittstelle-adr-0006-stand-31102026)
