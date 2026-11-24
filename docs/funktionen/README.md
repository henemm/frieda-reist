# Funktionen von Frieda

Diese Übersicht zeigt alles, was Frieda kann, gegliedert nach Aufgaben rund um eine Reise. Jede Zeile führt zu einer eigenen Seite mit Beispielen, Rechten und Grenzen. Die Beispiele stammen aus der erfundenen Beispielreise „Malerweg in vier Tagen“ mit Ida und Karl.

Frieda arbeitet an drei Orten:

- **Im Gespräch:** In der Claude-App (Handy, Desktop, claude.ai) planst du die Reise mit Claude. Frieda ist dort ein Konnektor: Claude liest die Reise und trägt ein, Frieda prüft jede Eintragung nach festen Regeln.
- **Auf der Reiseseite:** Eine Webseite je Reise, die auch ohne Netz funktioniert. Sie ist das Nachschlagewerk unterwegs und die Stelle für Rückmeldungen, Aufgaben, Wünsche und Packliste.
- **Auf Mein Konto:** Anmeldung, Meldungen über alle Reisen, Kalender, Benachrichtigungen, eigene Daten.

## Überblick

| Bereich | Was es kann | Wo | Seite |
|---|---|---|---|
| **Die Reise als geprüfte Wahrheit** | Tage, Orte, Unterkünfte, Aufenthalte, Strecken mit festen Kennungen; Arten und Merkmale je Reise; jede Angabe mit Herkunft und Prüfdatum; nichts wird gelöscht, alles hat einen Verlauf | überall | [Reisemodell](reisemodell.md) |
| **Planen im Gespräch** | die Reise in der Claude-App lesen, recherchieren lassen, eintragen; prüfen, ob eine Änderung schon auf der Seite ist; die Seite als Bild ansehen | Gespräch | [Planen im Gespräch](gespraech.md) |
| **Reiseseite** | Reiseüberblick mit Zeitachse, Tagesseiten, Ortsseiten, Wissen, „Zu tun“, Suche; offline, als App auf dem Home-Bildschirm | Reiseseite | [Reiseseite](reiseseite.md) |
| **Alternativen und Entscheidungen** | Wahlstellen mit Optionen an jeder Stelle, benannte Pläne mit Summen, Vergleich nach Merkmalen, Entscheidungen mit Person, Datum und Grund, Konflikte werden zur offenen Frage | Gespräch, Reiseseite | [Alternativen](alternativen.md) |
| **Buchungen und Belege** | Buchungen mit Nummer, Frist, Stornoregel und Zahlstand; Belege anhängen und freigeben; Check-in-Ansicht; Kosten der Übernachtungen | Gespräch, Reiseseite | [Buchungen](buchungen.md) |
| **Karte** | Karte aus allen Orten mit Koordinaten, GPX-Tracks, Kartenansichten je Tag oder Fahrt, Punkte aus OpenStreetMap, Grundkarte offline | Gespräch, Reiseseite | [Karte](karte.md) |
| **Zusammenarbeit** | Personen mit Rollen einladen; Rückmeldungen an jeder Stelle; offene Fragen; Aufgaben mit Frist und Zuständigkeit; Wunsch-Brett mit Punkten | Gespräch, Reiseseite | [Zusammenarbeit](zusammenarbeit.md) |
| **Packliste** | Gegenstände in Kategorien, Summen wie Gewicht, wer packt was, Abhaken auch ohne Netz, Übernahme aus einer früheren Reise | Gespräch, Reiseseite | [Packliste](packliste.md) |
| **Bilder** | Bilder aus Wikimedia Commons mit Namensnennung, eigene Fotos hochladen, Titelbild, eigenes App-Symbol der Reise | Gespräch, Reiseseite | [Bilder](bilder.md) |
| **Erinnerungen und Meldungen** | Fristen, Stornofristen, offene Zahlungen, fällige Statuswechsel, zu alte Prüfdaten; als Meldung, Push-Nachricht oder Mail; Kalender-Abo | Mein Konto, Reiseseite, Gespräch | [Erinnerungen](erinnerungen.md) |
| **Von der Idee bis zum Archiv** | neue Reise im Gespräch anlegen; Status Idee, Planung, fest, unterwegs, danach, Archiv; Bausteine an- und abschalten; Reise löschen mit Schonfrist | Gespräch, Mein Konto | [Lebenszyklus einer Reise](lebenszyklus.md) |
| **Konto und Datenschutz** | Anmeldung ohne Passwort, Claude verbinden, persönliches Profil, Meine Daten herunterladen, Konto löschen, Warteliste | Mein Konto, Gespräch | [Konto](konto.md) |
| **Sprachen** | Deutsch und Englisch; Sprache der Reise, Sprache des Kontos und Umschalter auf der Seite sind getrennt | überall | [Sprachen](sprachen.md) |
| **Selbst betreiben** | eigene Instanz auf dem eigenen Server: Reisespeicher, Veröffentlichen, Sicherung, Überwachung; keine KI auf dem Server | Server | [Selbst betreiben](selbst-betreiben.md) |

## Wer darf was

Rollen gelten je Reise. Jede Stufe enthält die darunter.

| Rolle | darf |
|---|---|
| Gast | lesen |
| Mitwirkende:r | dazu Rückmeldungen, Antworten, Aufgaben, Wünsche, Packliste; Werte, Dinge, Optionen, Fragen, Wissen und Buchungen eintragen |
| Organisator:in | dazu entscheiden, Arten und Merkmale festlegen, Status und Einstellungen setzen, Personen einladen |

Claude im Gespräch ist kein Mitglied der Reise: Es handelt immer im Namen der angemeldeten Person und mit deren Rolle, schlägt vor und trägt ein, entscheidet aber nie selbst. Einzelheiten: [Zusammenarbeit](zusammenarbeit.md#rollen).

## Was Frieda bewusst nicht tut

- **Keine eigene KI.** Recherchieren, Abwägen und Formulieren geschieht in der Claude-App der Person. Frieda prüft Regeln, hält die Reise und zeigt sie ([ADR-0001](../adr/0001-kern.md)).
- **Kein Katalog.** Welche Arten von Dingen eine Reise kennt (Hütte, Ryokan, Nachtfähre, Museum) und was über sie bekannt sein muss, legt jede Reise selbst fest.
- **Kein stilles Überschreiben.** Nichts wird gelöscht; Verworfenes, Storniertes und Weggelassenes bleibt mit Verlauf erhalten. Ausnahmen gibt es nur für den Datenschutz (Konto, Reise oder eigenes Foto löschen).
- **Keine Buchungsplattform.** Frieda bucht nichts, sie hält fest, was gebucht ist.

## Siehe auch

- [Startseite der Dokumentation](../README.md)
- [Der Kern (ADR-0001)](../adr/0001-kern.md) und [Produktbild](../produkt.md)
- [Konnektor: alle Werkzeuge im Einzelnen](../konnektor.md)
