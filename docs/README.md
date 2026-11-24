# Dokumentation von Frieda Reist

Frieda hält eine Reise als geprüfte Wahrheit, die Reisenden planen sie im Gespräch mit Claude, und eine Reiseseite zeigt sie unterwegs, auch ohne Netz. Diese Seite ist der Einstieg in die Dokumentation. Sie ist nach Zweck gegliedert: erst verstehen und ausprobieren, dann Funktionen, Anleitungen, Nachschlagen und die Entscheidungen dahinter.

*English: a short summary is in [README.en.md](../README.en.md); the detailed documentation is in German.*

## Einstieg

| Wenn du … | dann lies |
|---|---|
| wissen willst, was Frieda ist | [README](../README.md) und [Der Kern (ADR-0001)](adr/0001-kern.md) |
| sehen willst, was Frieda kann | [Funktionen](funktionen/README.md) |
| die Beispielreise auf dem eigenen Rechner bauen willst | [README, „Ausprobieren“](../README.md#ausprobieren) und [Beispielreisen](../beispiel/README.md) |
| Frieda in der Claude-App nutzen willst | [Planen im Gespräch](funktionen/gespraech.md) und [Konto](funktionen/konto.md) |
| Frieda auf einem eigenen Server betreiben willst | [Selbst betreiben](funktionen/selbst-betreiben.md), dann [Betrieb einer Instanz](betrieb.md) |
| an der Software mitarbeiten willst | [Arbeitsregeln](../CLAUDE.md), [Architektur-Entscheidungen](adr/README.md), [Design und Bausteine](design.md) |

## Funktionen

Eine Seite je Bereich, jeweils mit Beispielen, Rechten, Regeln und Grenzen. Übersicht: [funktionen/README.md](funktionen/README.md).

- [Die Reise als geprüfte Wahrheit](funktionen/reisemodell.md)
- [Planen im Gespräch](funktionen/gespraech.md)
- [Reiseseite](funktionen/reiseseite.md)
- [Alternativen und Entscheidungen](funktionen/alternativen.md)
- [Buchungen und Belege](funktionen/buchungen.md)
- [Karte](funktionen/karte.md)
- [Zusammenarbeit](funktionen/zusammenarbeit.md)
- [Packliste](funktionen/packliste.md)
- [Bilder](funktionen/bilder.md)
- [Erinnerungen und Meldungen](funktionen/erinnerungen.md)
- [Von der Idee bis zum Archiv](funktionen/lebenszyklus.md)
- [Konto und Datenschutz](funktionen/konto.md)
- [Sprachen](funktionen/sprachen.md)
- [Selbst betreiben](funktionen/selbst-betreiben.md)

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
