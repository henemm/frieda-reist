# ADR-0006: Mehrsprachigkeit (Deutsch und Englisch als Vorgabe)

Status: **Entwurf**, wartet auf Entscheidung des Product Owners (offene Fragen unten) · Plan: `docs/mehrsprachigkeit.md`

## Kontext

Alle Texte der Software sind heute Deutsch und fest im Code: rund 700 Textstellen im Skript der Vorlage (`engine/vorlage.html`), rund 300 Beschreibungen und Anleitungen im Konnektor (`engine/konnektor.py`), rund 250 Ablehnungen im Schreibweg (`engine/schreiben.py`), dazu Fehlertexte des Rückmeldedienstes, Kontoseiten, Mails, Kalender und Wächter. Es gibt kein Feld für eine Sprache, weder an der Reise noch am Konto noch an der Instanz. Die Seite erkennt an einigen Stellen deutschen Inhalt per Regex (Fragestatus „geklärt“, Überschriften „Etappe“, „Zusammenfassung“, „Übersicht:“). Datum und Zahl werden von Hand deutsch formatiert.

Die Software soll Deutsch und Englisch sprechen, auf der Seite und am Konnektor; weitere Sprachen sollen ohne Umbau dazukommen können.

## Entscheidung (Vorschlag)

1. **Ein Textkatalog je Sprache, in der Software.** `engine/texte.py` (Zugriff, Plural, Rückfall auf Deutsch) mit `engine/texte_de.py` und `engine/texte_en.py` (flache Schlüssel, Bereiche `seite.`, `konnektor.`, `schreiben.`, `dienst.`, `konto.`, `mail.`, `kalender.`, `waechter.`). Der Katalog enthält nur Wörter der Software (Beschriftungen, Beschreibungen, Fehler, Mails), nie Reiseinhalte. Eine neue Sprache ist eine neue Datei; ein Test prüft, dass alle Sprachen dieselben Schlüssel und Platzhalter haben.
2. **Die Seite spricht die Sprache der Reise.** `reise.yaml` bekommt `sprache: de | en` (Vorgabe `de`). Der Bau schreibt Sprache, Katalog und Locale fest in `index.html`, `manifest.json` und den Service Worker. Kein Umschalter im Browser: Der Inhalt einer Reise (Wissen, Namen und Werte der Arten, Fragen, Gründe) ist einsprachig, eine umgeschaltete Hülle ergäbe eine gemischte Seite. Datum, Zahl und Sortierung kommen aus `Intl` mit der Locale der Reise; die zwei Datumsformen aus ADR-0002 bleiben.
3. **Der Konnektor spricht die Sprache der Person.** Das Konto bekommt `sprache` (Vorgabe aus `FR_SPRACHE` der Instanz, sonst `de`; beim ersten Anmelden aus `Accept-Language` des Browsers vorbelegt). Anleitung (`instructions`), Beschreibungen der Werkzeuge und Parameter, Ergebnisse und Fehler kommen in dieser Sprache. Übergangs-Links ohne Konto nehmen die Sprache der Reise. Die Person ändert die Sprache auf der Kontoseite oder mit dem Werkzeug `sprache_setzen`.
4. **Kennungen bleiben, nur Wörter wechseln.** Werkzeugnamen (`reise_anlegen`), Parameternamen, Enum-Werte (`gewaehlt`, `organisator`, `pflicht`), ID-Präfixe (`T-`, `E-`, `U-` …), Dateinamen (`offene-fragen.md`, `plan/routen.yaml`) und die Pfade des Schreibwegs sind Schnittstelle und Datenschlüssel, nicht Text. Sie bleiben deutsch und stabil (wie bei den Rollen, `docs/produkt.md`). Englische Beschreibungen erklären sie („`art`: Kommentar = comment, Frage = question …“).
5. **Reiseinhalte werden nicht übersetzt.** Was die Reise sagt (Arten, Merkmale, Auswahlwerte, Wissen, Lesetexte, Gründe), gehört der Reise und steht in ihrer Sprache; Frieda enthält keine KI, die übersetzt (ADR-0001, Punkt 5). Was die Software in Dateien der Reise schreibt (Fragestatus, Verlaufsgründe, Kopfkommentare der YAML-Dateien, Meldungen, Commit-Nachrichten), schreibt sie in der Sprache der Reise, nicht in der Sprache der Person. Die Antwort an die Person ist davon getrennt und in ihrer Sprache.
6. **Fehler sind Schlüssel mit Werten, keine fertigen Sätze.** Der Schreibweg (`Ablehnung(schluessel, **werte)`), `reise.erlaubt()` und der Rückmeldedienst (`fehler_code` neben `fehler`) liefern Schlüssel; Konnektor und Seite machen daraus den Satz in der jeweiligen Sprache. Der Konnektor gibt dem Schreibweg die Sprache der Person mit.
7. **Inhaltserkennung wird sprachfest.** Wo die Software heute deutsche Wörter im Inhalt erkennt (Fragestatus, „Etappe“, Ebenen-Titel, „Übersicht:“, „Tag n“), erkennt sie die Wörter aller Sprachen des Katalogs. Die Reisevorlage (`engine/reisevorlage/`) gibt es je Sprache; `neu.py` nimmt die der Reise.
8. **Code und Doku bleiben Deutsch** (`CLAUDE.md`). Der englische Katalog ist Inhalt, kein Kommentar. Das README bekommt eine englische Kurzfassung (`README.en.md`); `docs/` bleibt deutsch.

## Begründung

- Ein Katalog statt zweier Codepfade: Übersetzen heißt eine Datei ergänzen, nicht Code anfassen. Der Paritätstest hält die Sprachen gleich.
- Sprache an der Reise, weil die Seite ein Bau je Reise ist und ihr Inhalt einsprachig ist; Sprache am Konto, weil der Konnektor die Person kennt, bevor er die Reise kennt (`initialize`, `tools/list`), und eine Person auf mehreren Reisen dieselbe Sprache erwartet.
- Kennungen bleiben, weil sie in Reisen-Repos, Tests, Dokumentation und den Konnektor-Einstellungen der Leute stehen; Claude kommt mit deutschen Kennungen zurecht, wenn die Beschreibung englisch ist.
- Keine Übersetzung von Inhalten, weil das ein KI-Lauf in Frieda wäre (ADR-0001, Prüfstelle Frage 3) und zwei Wahrheiten erzeugte.

## Konsequenzen

- Neu: `engine/texte.py`, `engine/texte_de.py`, `engine/texte_en.py` (in `betrieb/deploy.sh` bei KN_, RM_ und SB_MODULE; in `CODE_DATEIEN`), `reise.yaml sprache`, Spalte `konten.sprache`, `FR_SPRACHE`, Werkzeug `sprache_setzen`, `engine/reisevorlage/<sprache>/`, `README.en.md`.
- Geändert: Vorlage (alle Literale über `t()`, `Intl` für Datum, Zahl, Sortierung, Karte), Konnektor (Beschreibungen und Anleitung je Sprache, Ergebnisse, Fehler), Schreibweg (Ablehnung als Schlüssel, Antwort getrennt von gespeichertem Text), Rückmeldedienst (`fehler_code`), Kontoseiten, Mails, Kalender, Wächter.
- Bleibt: alle Schlüssel, IDs, Dateinamen, Werkzeugnamen, die deutschen Texte wörtlich (bestehende Tests bleiben grün, solange Deutsch die Vorgabe ist).
- Prüfstelle ADR-0001: 1 ja (Sprache der Reise steht in der Reise; Grundform-Wörter in der Software), 2 ja (der Katalog enthält keine Art und kein Merkmal), 3 ja (keine Übersetzung zur Laufzeit), 4 ja (`sprache_setzen`, Feld im Konto), 5 bis 7 nicht berührt, 8 ja (Katalog liegt in der Seite, offline), 9 ja, 10 dieses ADR und `docs/mehrsprachigkeit.md`.

## Offene Fragen an den Product Owner

1. Seite: Sprache fest je Reise (Vorschlag) oder zusätzlich ein Umschalter im Browser, der nur die Hülle übersetzt?
2. Werkzeug- und Parameternamen bleiben deutsch (Vorschlag), oder sollen englische Namen (`trip_create`) als zweiter Satz angeboten werden? Zweiter Satz heißt doppelte Werkzeugliste und zwei Namen in jeder Doku.
3. Was die Software in die Reise schreibt (Gründe, Fragestatus, Commits): Sprache der Reise (Vorschlag) oder immer Deutsch?
4. Braucht es eine englische Beispielreise, oder reicht für Tests eine Kopie der Beispielreise mit `sprache: en` (Vorschlag: Kopie)?
5. Vorgabe neuer Konten: `FR_SPRACHE` der Instanz (Vorschlag) oder immer `Accept-Language` des Browsers?

## Verlauf

- 30.10.2026: Entwurf nach Bestandsaufnahme von Vorlage, Generator, Konnektor, Schreibweg, Rückmeldedienst, Konten und Tests (Claude Code, Auftrag des Product Owners: Plan für Mehrsprachigkeit).
