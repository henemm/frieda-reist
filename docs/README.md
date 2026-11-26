# Dokumentation von Frieda Reist

Frieda hält eine Reise als geprüfte Wahrheit, die Reisenden planen sie im Gespräch mit Claude, und eine Reiseseite zeigt sie unterwegs, auch ohne Netz. Diese Seite ist der Einstieg in die Dokumentation. Sie ist nach Zweck gegliedert: erst verstehen und ausprobieren, dann Funktionen, Anleitungen, Nachschlagen und die Entscheidungen dahinter.

*English: a short summary is in [README.en.md](../README.en.md); the detailed documentation is in German.*

## Einstieg

| Wenn du … | dann lies |
|---|---|
| wissen willst, was Frieda ist | [README](../README.md) und [Der Kern (ADR-0001)](adr/0001-kern.md) |
| sehen willst, was Frieda kann | „Alle Funktionen“ auf der Webseite einer Frieda-Instanz (`/info/funktionen/`); Wegweiser für Entwickler:innen: [Funktionen](funktionen/README.md) |
| die Beispielreise auf dem eigenen Rechner bauen willst | [README, „Ausprobieren“](../README.md#ausprobieren) und [Beispielreisen](../beispiel/README.md) |
| Frieda in der Claude-App nutzen willst | die Infoseite einer Frieda-Instanz (`/info/`) und dort „Planen im Gespräch“, „Gute Gespräche mit Frieda“ und „Konto und Datenschutz“ |
| Frieda auf einem eigenen Server betreiben willst | [Betrieb einer Instanz](betrieb.md) (Überblick für Interessierte: „Selbst betreiben“ unter `/info/funktionen/betrieb/` einer Instanz) |
| an der Software mitarbeiten willst | [Arbeitsregeln](../CLAUDE.md), [Architektur-Entscheidungen](adr/README.md), [Design und Bausteine](design.md) |

## Funktionen

Die Funktionsseiten für Nutzer:innen stehen auf der Webseite jeder Frieda-Instanz unter `/info/funktionen/`, eine Unterseite je Bereich, auf Deutsch und Englisch, mit Bildern aus den Beispielreisen. Welcher Bereich wo steht und welche Entwicklerdoku dazugehört: [funktionen/README.md](funktionen/README.md).

## Anleitungen

Schritt für Schritt zu einem Ziel.

| Anleitung | Für |
|---|---|
| [Neue Reise anlegen](neue-reise.md) | Organisator:innen, Betreiber |
| [Betrieb einer Instanz](betrieb.md): einrichten, veröffentlichen, sichern, überwachen, wenn etwas klemmt | Betreiber |
| [Werkzeuge für Inhalte](werkzeuge.md): Grundkarte, Punkte und Adressen aus OpenStreetMap, Wasserstellen | Betreiber, Entwickler |
| [Eine Sprache hinzufügen](sprachen.md#eine-sprache-hinzufügen) | Entwickler, Übersetzer |

## Nachschlagen

Vollständige Beschreibungen für den Fall, dass es genau sein muss.

| Thema | Dokument |
|---|---|
| Alle Werkzeuge des Konnektors, Parameter, englische Namen | [Konnektor](konnektor.md) |
| Grundformen, Arten, Merkmale, Dateiformat einer Reise | [Reise-Ontologie](ontologie.md) |
| Wahlstellen, Optionen, Pläne, Merkmale im Vergleich | [Alternativen](alternativen.md) |
| Konten, Anmeldung, Sicherheit, Warteliste | [Konten](konten.md) |
| Wächter, Erinnerer, Stufen und Wege der Meldungen | [Wächter](waechter.md) |
| Seitenordnung, Tagesseite, Bausteine der Oberfläche | [Design](design.md) |
| Sprachdateien, Regeln für Texte | [Sprachen](sprachen.md) |

## Hintergrund

Warum Frieda so ist, wie sie ist.

- [Produktbild](produkt.md): Zweck, Rollen, Status einer Reise, Einstellungen, Ausbaustufen
- [Architektur-Entscheidungen (ADR)](adr/README.md), vor allem [ADR-0001: der Kern](adr/0001-kern.md)
- [Mehrsprachigkeit: Plan und Umsetzung](mehrsprachigkeit.md)

## Arbeitsunterlagen

Diese Ordner gehören zur Entwicklung, nicht zur Nutzung. Sie halten fest, wie einzelne Änderungen geplant, geprüft und abgenommen wurden, und können veraltete Zwischenstände enthalten. Im Zweifel gelten die Seiten oben.

- `specs/`: Spezifikationen einzelner Änderungen
- `context/`, `briefings/`, `artifacts/`, `auftraege/`: Kontext, Zusammenfassungen und Entwürfe zu Änderungen
- [Abgleich vom 29.10.2026](abgleich-2026-10-29.md): Prüfbericht und damaliges Backlog
