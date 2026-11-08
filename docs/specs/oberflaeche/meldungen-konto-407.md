---
entity_id: meldungen-konto-407
type: module
created: 2026-11-08
updated: 2026-11-08
status: approved
version: "0.1"
tags: [konto, meldungen, waechter, push, anmeldung, lesestand]
---

# „Meldungen an dich“ auf Mein Konto: Posteingang mit Ziel (#407)

Workflow: `meldungen-konto-407`. Analyse: `docs/context/meldungen-konto-407.md`.
Mockups: `docs/artifacts/meldungen-konto-407/mockup.html` und die Bildschirmfotos daneben.

## Approval

- [x] Approved (Product Owner, 8.11.2026: freigegeben, Stufen A bis C nacheinander bauen; die vier offenen Fragen sind entschieden, siehe Ende)

## Purpose

Heute ist „Meldungen an dich“ eine Liste festgeschriebener Sätze: Neue Reisen ohne Link, lange Adressen als Rohtext,
alles gleich laut, nichts wird gelesen. Nach dieser Spec gilt in einfachen Worten:

- **Jede Meldung führt irgendwohin.** Antippen öffnet die Stelle, um die es geht: die neue Reise, die Aufgabe mit der
  Frist, die Wahlstelle mit dem Konflikt, die Freischaltungen. Adressen stehen nie mehr als Text da.
- **Neu und gelesen.** Neue Meldungen haben einen Punkt und stehen oben. Antippen oder „Alle gelesen“ legt sie unter
  „Gelesen (n)“ zusammen. Der Lesestand gilt für das Konto, auf jedem Gerät, auch im Hinweis „Für dich“ der Reiseseite.
- **Man sieht, was zu tun ist.** Eine kleine Marke sagt die Art: „Konflikt“, „Frist“, „Status“, „Prüfen“, „Freischalten“,
  „Hinweis“, „Neue Reise“. Was Handeln verlangt, hat eine warme Marke; reine Info eine leise.
- **Keine Flut.** Prüfmeldungen des Wächters einer Reise werden zu einer Zeile („7 Angaben zu prüfen“). Mehr als fünf
  neue Meldungen: die ersten fünf, dann „Alle 12 neuen zeigen“.
- **Text in der Sprache des Kontos.** Neue Meldungen werden beim Zeigen aus dem Katalog formuliert, nicht beim Anlegen.
  Alte Meldungen zeigen ihren gespeicherten Text, ohne Adressen.

Nichts wird gelöscht. Die Regeln, wann eine Meldung nicht mehr gilt (14 Tage, Aufgabe erledigt, Status gewechselt,
Konflikte bleiben), bleiben, wie sie sind (`meldungen_aktuell`).

## Gestalt

Mockup „Soll“ in `docs/artifacts/meldungen-konto-407/`. Der Abschnitt bleibt an seinem Platz (oben, vor „Meine Reisen“)
und im Gesicht B2 der Kontoseiten.

```
Meldungen an dich                         [3 neu]   Alle gelesen
┌───────────────────────────────────────────────────────────────┐
│ ● [Konflikt] Beispielreise – Malerweg · heute 9:14          › │
│   Karl hat „Pension Rathen“ gewählt, du hattest sie verworfen.│
│   Zu klären in der offenen Frage.                             │
├───────────────────────────────────────────────────────────────┤
│ ● [Frist] Beispielreise – Malerweg · gestern                › │
│   Frist morgen: Anzahlung zur Buchung Hotel Bad Schandau.     │
├───────────────────────────────────────────────────────────────┤
│ ● [Neue Reise] Beispielstadt – Wochenende · 3.11.           › │
│   Deine neue Reise ist angelegt (Status Idee).                │
│   2 Einladungen per Mail verschickt.                          │
├───────────────────────────────────────────────────────────────┤
│ ▸ Gelesen (4)                                                 │
└───────────────────────────────────────────────────────────────┘
```

### Zeile (Molekül `meldungZeile`, neu)

| Teil | Inhalt | Regel |
|---|---|---|
| Punkt | Akzentgrün, 0,5 rem, links | nur bei ungelesen; für Screenreader „neu“ (`<span class="neu-punkt" role="img" aria-label="neu">`) |
| Kopfzeile, klein | Marke · Reise · Zeit | Reise als Titel aus `reise_info`, gekürzt mit Ellipse; ohne Reise nur die Zeit |
| Marke | Art der Meldung (Tabelle unten) | `.marke` vorhanden; neu nur die Tönung `.marke.warm` (`--warn` auf `--warnbg`, Kontrast hell und dunkel ≥ 4,5:1) |
| Zeit | „heute 9:14“, „gestern“, sonst `datum_kurz` („3.11.“) | in der Zeitzone des Geräts, sonst UTC; Schlüssel `konto.meldungen.heute`, `konto.meldungen.gestern` |
| Text | ein bis zwei Sätze, ohne Adressen und ohne Werkzeugnamen | höchstens drei Zeilen (`-webkit-line-clamp: 3`), ganz im Ziel |
| Pfeil | „›“ wie jede Zeile | die ganze Zeile ist der Link |

Gelesene Zeilen haben keinen Punkt und normales statt halbfettes Gewicht im Text. Sonst sehen sie gleich aus.

### Arten, Marke, Ziel

Eine Funktion `rueckmeldungen.meldung_ziel(m, reise_info)` bestimmt das Ziel. Push benutzt sie mit, damit Push und
Mein Konto an dieselbe Stelle führen (heute rechnet `push.py` das selbst, Zeile 222).

| `art` | Marke | Ton | Ziel |
|---|---|---|---|
| `konflikt` | Konflikt | warm | Seite der Reise `#<ziel>` (Option bzw. Wahlstelle) |
| `erinnerung` | Frist | warm | Seite der Reise `#<bezug>` (AG-… oder B-…) |
| `status` | Status | warm | Seite der Reise (Überblick) |
| `pruefung` | Prüfen | warm | Seite der Reise `#zu-tun`; gebündelt, siehe unten |
| `technik`, `betrieb` | Hinweis | warm | Seite der Reise |
| `anfrage_reisen`, Warteliste | Freischalten | warm | `/konto#freischalten` (nur Betreiber sehen sie) |
| `neue_reise` | Neue Reise | leise | Seite der Reise aus `ziel` (Ordner), sobald das Konto Mitglied ist |
| unbekannt | – | leise | Seite der Reise, ohne Reise kein Link |

Die Marken sind Texte im Katalog (`konto.meldungen.art.<art>`). Eine neue Art ohne Eintrag bekommt keine Marke statt
eines Fehlers. Arten bleiben Begriffe der Software, sie kommen nicht aus der Reise (ADR-0001, Frage 2).

### Bündeln

Prüfmeldungen (`pruefung`) derselben Reise und desselben Tages werden zu einer Zeile: „7 Angaben zu prüfen“
(`konto.meldungen.pruefungen.one/other`). Ungelesen, solange eine von ihnen ungelesen ist. Antippen markiert alle als
gelesen und öffnet „Zu tun“ der Reise. Andere Arten werden nicht gebündelt, weil jede ein eigenes Ziel hat.

### Ordnung und Menge

1. Ungelesene, neueste zuerst; ungelesene Konflikte immer ganz oben, auch ältere (Entscheidung 4). Sie verlangen
   Handeln von mehreren Personen. Keine Gruppen je Reise (Entscheidung 3).
2. Mehr als fünf ungelesene: die ersten fünf, darunter die Zeile „Alle 12 neuen zeigen“ (`<details>`, ohne Skript).
3. „Gelesen (n)“ als zugeklappte Zeile am Ende der Liste (`<details>`). Darin die gelesenen, die noch gelten.
4. Alles gelesen: Die Liste zeigt nur „Keine neuen Meldungen“ (leise) und „Gelesen (n)“. Gilt keine Meldung mehr, fällt
   der Abschnitt weg wie heute.

### Kopf des Abschnitts

„Meldungen an dich“, daneben die Zahlmarke „3 neu“ (nur mit ungelesenen), rechts der Textknopf „Alle gelesen“
(`button.link`, Formular `aktion=meldungen_gelesen`, ohne Skript). Mit Skript bleibt die Seite stehen (wie
„Speichern mit Zustand“ in `engine/app/konto.js`).

## Lesestand

- **Ort:** Tabelle `meldung_gelesen (konto TEXT, meldung TEXT, wann TEXT, PRIMARY KEY (konto, meldung))` in
  `konten.db`. Sie wird beim Öffnen angelegt (`CREATE TABLE IF NOT EXISTS`), keine Migration von Hand. Löscht jemand
  das Konto, fallen die Zeilen mit.
- **Gelesen wird eine Meldung,** wenn die Person (a) die Zeile auf Mein Konto antippt: `GET /konto/meldung/<id>` merkt
  sie und leitet zum Ziel weiter (303); (b) „Alle gelesen“ drückt; (c) auf der Reiseseite im Hinweis „Für dich“
  „Gelesen“ tippt: `POST api/gelesen` mit den IDs; (d) nur bei `neue_reise`: die Seite dieser Reise angemeldet
  öffnet (`api/ich` der Reise aus `ziel` merkt sie, Entscheidung 2). Push-Tippen öffnet die Stelle ohne Umweg und zählt
  nicht.
- **Reiseseite:** `api/ich` liefert zu jeder Meldung `gelesen: true|false`. `fuerDich` zeigt nur ungelesene. Der Browser
  behält seine Liste weiter als Puffer ohne Netz und schickt sie beim nächsten Kontakt mit.
- **Konnektor:** `meine_reisen` zeigt die ungelesenen zuerst und nennt die Zahl der gelesenen; Lesen im Gespräch
  verändert den Stand nicht (Entscheidung 1).
- **Push** schickt wie bisher jede neue Meldung einmal; der Lesestand ändert daran nichts.

## Texte zur Anzeigezeit

Neue Meldungen speichern neben `text` den Schlüssel und die Werte: `"t": "dienst.zustellen.konto", "werte": {...}`.
Beim Zeigen formuliert `texte.t(<Sprache des Kontos>, t, **werte)` den Satz. `text` bleibt als Rückfall für alte
Zeilen, für Sprachen ohne den Schlüssel und für die Sammelnachricht an den Betreiber.

- Adressen kommen nie in `werte`. Das Ziel ergibt sich aus `ziel`/`bezug` und der aktuellen Adresse der Reise
  (`reise_info`). So stimmen alte Meldungen auch nach einem Umzug der Instanz.
- Neue Schlüssel ohne Adresse und ohne Werkzeugnamen für die Seite, z. B.
  `konto.meldungen.text.neue_reise`: „Deine neue Reise ist angelegt (Status Idee).“
  Der Konnektor behält seinen Wortlaut mit `meine_reisen`.
- Alte Zeilen ohne `t`: Beim Zeigen auf Mein Konto werden Adressen der eigenen Instanz (`FR_BASIS`) und das Stück
  „ und steht in meine_reisen“ (Katalogtext, alle Sprachen) aus dem Text genommen. Das ist eine Darstellungsregel mit
  Test, keine Änderung der Datei.
- Der Link für die Claude-App (Zustellen ohne Konto, `dienst.zustellen.app`) ist geheim. Auf Mein Konto steht er nicht als
  Text, sondern hinter dem Knopf „Link für die Claude-App kopieren“ im Ziel. Bis das gebaut ist, bleibt er in der
  Zeile verborgen und die Zeile führt zur Reise.

`meldungen.jsonl` bekommt zwei zusätzliche, freiwillige Felder. Alte Zeilen bleiben gültig; `neu.py nachziehen` muss
nichts umstellen (CLAUDE.md, #250). Ein Test belegt, dass eine Zeile von heute unverändert gezeigt wird.

## Heimat (ADR-0003)

Die Heimat der Meldungen ist Mein Konto (`#meldungen`). Der Hinweis „Für dich“ der Reiseseite bleibt eine Zeile mit
Link dorthin, ohne eigene Liste. Neu ist nur, dass er denselben Lesestand nutzt.

## Source

- **Files:** `engine/anmeldung.py` (`meldungen_abschnitt`, Route `/konto/meldung/<id>`, Aktion `meldungen_gelesen`,
  Stile `.neu-punkt`, `.marke.warm`, `.meldung-kopf`), `engine/rueckmeldungen.py` (`meldung_ziel`, `meldungen_des_kontos`
  gibt `ziel`, `bezug`, `gelesen`, `t`, `werte` weiter, Bündeln), `engine/konten.py` (Tabelle und Funktionen
  `gelesen_merken`, `gelesen`), `engine/push.py` (nutzt `meldung_ziel`), `engine/vorlage.html` (`fuerDich`),
  `betrieb/zustellen.py`, `engine/waechter.py`, `engine/konnektor.py` (`t`/`werte` beim Anlegen),
  `engine/texte_*.py` (neue Schlüssel in allen Sprachen), `docs/design.md`, `docs/konten.md`.
- **Neuer Baustein** `meldungZeile` an den vier Stellen aus ADR-0002 (die Kontoseiten haben keine Bausteinseite;
  `docs/design.md` Abschnitt „Anmelde- und Kontoseiten“ nennt ihn).

## Stufen

Jede Stufe ist ein eigener PR mit grünen Tests und für sich nützlich.

| Stufe | Inhalt | Format |
|---|---|---|
| A | Ziel je Meldung (`meldung_ziel`, auch für Push), Link bei neuen Reisen, Adressen und Werkzeugnamen aus dem Text, Marke je Art, Zeit „heute/gestern“, Prüfungen bündeln, höchstens fünf | keine Änderung |
| B | Lesestand in `konten.db`, Punkt, „Alle gelesen“, „Gelesen (n)“, Weiterleitung `/konto/meldung/<id>`, Reiseseite über `api/ich` und `api/gelesen` | neue Tabelle, angelegt beim Öffnen |
| C | `t`/`werte` beim Anlegen, Formulieren beim Zeigen in der Sprache des Kontos | zwei freiwillige Felder |

## Tests (je Stufe, gegen beide Beispielreisen)

- A: Meldung `neue_reise` mit `ziel` = Ordner der Beispielreise → Zeile ist ein Link auf deren Seite; Text enthält keine
  `https://` und kein `meine_reisen`. Meldung `erinnerung` mit `bezug` AG-… → Link endet auf `#AG-…`, Push bekommt
  dasselbe Ziel. Acht Prüfmeldungen des Stadtwochenendes → eine Zeile mit Zahl. Sieben ungelesene → fünf plus
  „Alle 7 neuen zeigen“. Marke fehlt für unbekannte Art, Seite baut. Pseudo-Sprache der Tests zeigt alle neuen Texte
  (`test_texte.py`).
- B: `/konto/meldung/<id>` merkt und leitet weiter, fremde ID → 404 ohne Merken, ohne Anmeldung → Anmeldung. „Alle
  gelesen“ → nur „Gelesen (n)“. Ein Gerät liest, das andere sieht es (zwei Sitzungen). `api/ich` meldet `gelesen`.
  Konto löschen löscht den Lesestand. Seite der neuen Reise angemeldet öffnen → ihre Meldung `neue_reise` ist gelesen,
  andere Meldungen dieser Reise nicht. Ein älterer ungelesener Konflikt steht vor einer neueren Frist. Playwright: Punkt und Zahlmarke verschwinden nach dem Antippen, hell und dunkel.
- C: Meldung mit `t` in Deutsch angelegt, Konto auf Englisch → englischer Text. Meldung ohne `t` → gespeicherter Text.
  `werte` mit Adresse → Test schlägt fehl (Prüfung beim Anlegen).

## Prüfstelle (ADR-0001)

| Nr. | Frage | Antwort |
|---|---|---|
| 1 | Reisespezifisches in der Reise; mit zwei Reisetypen durchgespielt? | ja: Wanderung (Konflikt, Frist) und Stadtwochenende (neue Reise, Prüfungen) im Mockup und in den Tests |
| 2 | Keine Art und kein Merkmal eingeführt? | ja: Meldungsarten sind Begriffe der Software, keine Arten der Reise |
| 3 | Kein KI-Lauf; Regeln im Code und getestet? | ja: Ziel, Bündeln, Lesestand sind Regeln |
| 4 | Über den Konnektor lesbar? | ja: `meine_reisen` mit Lesestand |
| 5 | Herkunft neuer Aussagen? | nicht berührt: Meldungen sind keine Aussagen über die Reise |
| 6 | Keine Entscheidung ohne Organisator:in? | ja: Meldungen entscheiden nichts |
| 7 | Keine ID neu vergeben oder gelöscht? | ja: Gelesen blendet aus, löscht nicht |
| 8 | PWA offline? | ja: „Für dich“ behält den letzten Stand und puffert „Gelesen“ |
| 9 | Reiseinhalte nicht in Claude Code? | ja |
| 10 | Dokumentiert in | diese Spec; nach Freigabe `docs/design.md`, `docs/konten.md`, `docs/waechter.md` |

## Entscheidungen des Product Owners (8.11.2026)

1. **Lesen im Gespräch zählt nicht.** Eine Meldung gilt nicht als gelesen, weil Frieda sie in der Claude-App vorgelesen
   hat. Ob die Person zugehört hat, weiß Frieda nicht.
2. **Neue Reise gilt beim Öffnen als gelesen.** Eine Meldung `neue_reise` gilt als gelesen, sobald die Person die Seite
   dieser Reise einmal angemeldet geöffnet hat (Stufe B).
3. **Flache Liste nach Zeit.** Keine Gruppen je Reise; die Reise steht klein in jeder Zeile.
4. **Ungelesene Konflikte stehen immer oben**, auch wenn sie älter sind.
