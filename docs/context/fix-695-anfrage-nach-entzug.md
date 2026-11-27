# Kontext: fix-695-anfrage-nach-entzug (#695)

## Request Summary

`reisen_anlegen_anfragen` (Konnektor, englisch `trip_create_request`) bricht mit `KeyError: 'freigeschaltet'` ab, wenn
ein Konto früher freigeschaltet wurde und das Recht `reise_anlegen` danach wieder entzogen ist. Die Kontoseite zeigt in
diesem Fall den Knopf „Freischaltung anfragen“, der Klick legt aber keine neue Bitte an. Erwartet: verständliche Antwort;
fachlich zu klären, ob eine neue Bitte möglich ist.

## Ursache (belegt)

- `engine/konten.py:977–989` `reisen_anlegen_anfragen`: Hat das Konto das Recht nicht, aber eine Zeile in `anfragen`,
  wird deren Status unverändert zurückgegeben (`:985–987`). Nach `freischalten(ja=True)` steht dort `freigeschaltet`
  (`:1003–1005`); `recht_setzen(kid, "reise_anlegen", False)` (`:965`) ändert die Zeile nicht.
- `engine/konnektor.py:2653–2658`: Wörterbuch kennt nur `offen`, `schon_erlaubt`, `abgelehnt` → `KeyError`.
- `engine/anmeldung.py:1141–1144`: Kontoseite zeigt bei Status `freigeschaltet` ohne Recht den Knopf (Rückfall von
  `.get`); `anmeldung.py:1864–1866` ruft `reisen_anlegen_anfragen`, bekommt `freigeschaltet`, meldet nichts, lädt neu →
  Knopf steht wieder da, nichts passiert.

## Related Files

- `engine/konten.py` (Bitte, Freischalten, Rechte; Tabelle `anfragen` mit `konto` als Primärschlüssel, `:145`)
- `engine/konnektor.py` (Werkzeug `reisen_anlegen_anfragen`)
- `engine/anmeldung.py` (Kontoseite, Aktion `anfragen`, `betreiber_melden`)
- Tests: `engine/tests/test_konten.py:58–77` (Bitte, Freischalten, Ablehnung bleibt), `test_oauth.py:310–350`,
  `test_anmeldung.py:595–610` (#687: Meldung nur bei Status `offen`).

## Existing Patterns

- Eine Ablehnung bleibt (`test_abgelehnte_bitte_bleibt_abgelehnt`, Docstring „eine Ablehnung bleibt“).
- Die Meldung an den Betreiber geht nur, wenn die Funktion `offen` liefert (#687) – eine wieder geöffnete Bitte löst
  also automatisch die Meldung aus.
- Entziehen des Rechts hat keinen eigenen Weg in der Software (kein CLI-Befehl, keine Seite); nur `recht_setzen(..., False)`
  direkt. Testzugang setzt das Recht ohne Zeile in `anfragen` (`betrieb/testzugang.py:203`).

## Dependencies / Dependents

- `reisen_anlegen_anfragen` wird nur von Konnektor und Kontoseite aufgerufen.
- Kein Datenformat der Reisen betroffen (nur Kontendatenbank, Inhalt einer Zeile), keine Umstellung nötig.

## Existing Specs

Keine eigene Spec zu Konten-Bitten in `docs/specs/`.

## Risks

- Fachlich: Ob eine neue Bitte nach Entzug erlaubt ist. Empfehlung: ja – ein Entzug ist keine Ablehnung, und die
  Kontoseite bietet den Knopf bereits an. Eine ausdrückliche Ablehnung bleibt unverändert endgültig.
- Wiederöffnen muss `erstellt` neu setzen und `entschieden` leeren, damit die Betreiberliste die Bitte als neu zeigt.

## Analysis

**Type:** Bugfix (Ursache belegt, siehe oben; Analyse-Agenten entfallen, Score 1, Ursache mit `file:line`).

**Affected Files (Change Type):**
- `engine/konten.py` MODIFY: `reisen_anlegen_anfragen` öffnet eine Zeile mit Status `freigeschaltet`, deren Konto das
  Recht nicht mehr hat, wieder (`status='offen'`, `erstellt` = heute, `entschieden` = NULL) und liefert `offen`.
  Damit liefert die Funktion nur noch die drei bekannten Werte; Konnektor und Kontoseite bleiben unverändert und
  melden die neue Bitte dem Betreiber über den bestehenden Weg (#687: Meldung nur bei `offen`).
- `engine/tests/test_konten.py` MODIFY: Test „nach Entzug neu bitten“ (Funktion liefert `offen`, Bitte in `anfragen()`).
- `engine/tests/test_oauth.py` MODIFY: Test über den Konnektor (Antwort „liegt beim Betreiber“, kein Abbruch).
- `docs/konten.md` MODIFY: Satz zur Bitte um „nach Entzug des Rechts ist eine neue Bitte möglich“ ergänzen.

**Scope/Risk:** ~5 LoC Code, ~25 LoC Tests, 1 Zeile Doku. Risiko niedrig: nur der Fall „Zeile freigeschaltet, Recht
fehlt“ ändert sich; `offen`, `abgelehnt`, `schon_erlaubt` verhalten sich wie bisher (bestehende Tests decken das ab).

**Technical Approach:** Wiederöffnen in derselben Transaktion wie das Lesen (`with closing(db()) as v, v:`), per
`UPDATE anfragen … WHERE konto = ?`. Kein neuer Text, keine Formatänderung der Reisedaten, keine Umstellung.

**Varianten:**

| Variante | Code | Verhalten | Bewertung |
|---|---|---|---|
| A Wiederöffnen in `konten` | ~5 LoC | neue Bitte, Betreiber wird gemeldet, Kontoseite-Knopf wirkt | empfohlen |
| B Konnektor fängt `freigeschaltet` mit eigenem Text ab | ~3 LoC + Text in allen Sprachen | keine neue Bitte möglich, Knopf auf der Seite bleibt wirkungslos | lässt den Seitenfehler stehen |

**Dependencies:** keine neuen. Instanzen: keine Schnittstelle, kein Meldungstext geändert.

**Open Questions:** Fachlich, ob eine neue Bitte nach Entzug möglich sein soll. Empfehlung A (Entzug ≠ Ablehnung, die
Seite bietet den Knopf bereits an); geht als Ampel-Punkt ins PO-Briefing.
