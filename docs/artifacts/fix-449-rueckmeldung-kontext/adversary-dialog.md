# Adversary Dialog — fix-449-rueckmeldung-kontext
Spec: docs/specs/oberflaeche/rueckmeldung-kontext-449.md
Datum: 2026-11-10 21:54

## Checkliste
- [x] **Input:** Tippen auf eine Sprechblase (`[data-rm]`), Text eingeben, Senden; auch ohne Netz.
- [x] **Output:** Eintrag mit `kontext` (nur gültige Teile); `feedback_list` zeigt den Ort lesbar in der Sprache des Aufrufers.
- [x] **Side effects:** keine; kein neuer Dienst, keine KI, keine Umstellung bestehender Reisen.
- [x] **AC-1:** Given die gebaute Seite der Beispielreise (Wanderung) / When eine Sprechblase auf einer Tagesseite im Abschnitt „Weg“ angetippt wird / Then bildet `rmKontext` `{ansicht: <Hash der Tagesseite>, abschnitt: "weg", stand: <Nummer>}`; derselbe Knopf in der Ansicht „Varianten“ liefert die dortige Ansicht und keinen Abschnitt einer Tagesseite.
- [x] **AC-2:** Given das Städtewochenende (ohne Varianten, ohne Wanderung) / When eine Sprechblase einer Tagesseite oder die „Allgemeine Rückmeldung“ angetippt wird / Then ist der Kontext gültig und enthält nur Teile, die es dort gibt (bei „allgemein“ im Reiter Rückmeldungen: `ansicht`, `stand`, kein `abschnitt`); kein Fehler, wenn die Reise keine Varianten hat.
- [x] **AC-3:** Given eine Seite ohne Reise-Stand (`RS` ist `null`) / When gesendet wird / Then fehlt `stand` im Kontext, ohne Fehler; sind alle Teile leer, geht der Body ohne `kontext`-Feld.
- [x] **AC-4:** Given der Dienst / When `POST` einen gültigen Kontext enthält (`ansicht`, `abschnitt`, `stand`) / Then wird die Rückmeldung angenommen und der Eintrag in `eingang.jsonl` trägt genau diesen Kontext.
- [x] **AC-5:** Given der Dienst / When der Kontext ungültig ist (kein Objekt, fremder Schlüssel, Muster verletzt, zu lang, `stand` keine Zahl oder ≤ 0 oder zu groß, verschachtelte Werte) / Then wird die Rückmeldung trotzdem mit derselben Antwort wie ohne Kontext angenommen, aber ohne die ungültigen Teile (gültige Restteile bleiben, fremde Schlüssel nie); kein Fehlertext wegen des Kontexts.
- [x] **AC-6:** Given zwei Rückmeldungen mit gleichem `INHALT` und verschiedenem Kontext innerhalb von `DOPPELT_SEKUNDEN` / When beide gesendet werden / Then bleibt es ein Doppelt-Treffer (ein Eintrag); `rm.INHALT` ist unverändert (`name, art, ziel, text, quelle`).
- [x] **AC-7:** Given alte Einträge ohne `kontext` in `eingang.jsonl` / When `rm.eintraege`, `feedback_list`, die Befehlszeilenausgabe, Wächter, Erinnerer und Export sie lesen / Then funktioniert alles wie bisher; `feedback_list` und die Befehlszeilenausgabe zeigen für sie keine „Ort“-Zeile, die Ausgabe ist Zeichen für Zeichen gleich der Ausgabe vor der Änderung (Vergleichstest mit festem Soll-Text).
- [x] **AC-8:** Given Offline (`senden` schlägt mit Netzfehler fehl) / When die Rückmeldung später aus `AUSGANG` nachgereicht wird / Then trägt sie den Kontext vom Klick, auch wenn dann eine andere Ansicht offen ist; `senden` schickt `kontext` aus dem Eintrag mit.
- [x] **AC-9:** Given ein Eintrag mit Kontext / When `feedback_list` aufgerufen wird / Then steht unter dem Eintrag eine Zeile „Ort“ mit Ansicht, Abschnitt und Stand; für `de`, `en` und die Pseudo-Sprache der Tests mit den Beschriftungen aus dem Katalog, die Werte unübersetzt; fehlende Teile entfallen samt Beschriftung. Die Befehlszeilenausgabe zeigt denselben Ort.
- [x] **AC-10:** Given `feedback_give` / When es aufgerufen wird / Then ist Verhalten und Parametersatz unverändert (kein Kontext-Parameter, kein neuer Alias); der Eintrag hat keinen `kontext`.
- [x] **AC-11:** Given der Textkatalog / When `engine/tests/test_texte.py` läuft / Then sind die neuen Schlüssel in allen Sprachen vorhanden, die Ausnahmelisten nicht länger geworden; im Code steht kein neuer sichtbarer Text.
- [x] **AC-12:** Given der Gesamtlauf / When `engine/.venv/bin/python -m pytest -q engine/tests` (mit `-n 3`) läuft / Then ist er grün, ohne echte Reisen; der Bau beider Beispielreisen bleibt deterministisch (zweimal bauen, gleiche Ausgabe).

## Dialog

### Runde 1
**Adversary:** Alle ACs am Code geprüft (Randfälle in `kontext_pruefen`, Doppelt-Erkennung, Neuzeichnen des Dialogs, Offline-Ausgang, alte Einträge). Ein Fund:

Finding:
  id: F001
  severity: MEDIUM
  category: edge_case
  description: `kontext_pruefen` prüfte mit `ZIEL_MUSTER.match`; das Muster endet auf `$`, das in Python einen einzelnen Zeilenumbruch am Ende zulässt. `{"ansicht": "heute" mit Zeilenumbruch am Ende}` wurde abgelegt und erzeugte in der Zeile „Ort“ einen eingeschmuggelten Zeilenumbruch.
  evidence: Code reference: engine/rueckmeldungen.py:442 (kontext_pruefen), Muster in engine/rueckmeldungen.py:98. Aufruf `kontext_pruefen({"ansicht": "heute" mit Zeilenumbruch am Ende})` lieferte `{"ansicht": "heute" mit Zeilenumbruch am Ende}`.
  remediation: `fullmatch` statt `match`, Test mit Umbruch am Ende ergänzen.

Bestätigt (ohne Fund): Anzeige in Code reference: engine/konnektor.py:2363 (kontext_text), Beschriftungen in Code reference: engine/texte_de.py:2149 und Code reference: engine/texte_en.py:2148; Erfassung und Offline-Weg in Code reference: engine/vorlage.html:4886 (rmKontext), Dialog behält den Kontext beim Neuzeichnen (engine/vorlage.html:4931, 4963, 4983); `stand` als `True`, `5.0`, `10**30` wird verworfen; `INHALT` unverändert.
**Implementierer:** F001 anerkannt, wird behoben.

### Runde 2
**Adversary:** Nachprüfung der Behebung: `kontext_pruefen` nutzt `ZIEL_MUSTER.fullmatch` (Code reference: engine/rueckmeldungen.py:442). Proben `{"ansicht": "heute" mit Zeilenumbruch am Ende}`, `{"abschnitt": "weg" mit Zeilenumbruch am Ende}`, `{"ansicht": "a
"}` ergeben `None`; ein gültiger Kontext bleibt erhalten. Im neuen Code gibt es kein weiteres `$`-Muster (die Regex in `rmKontext` hat kein Multiline-Flag). Beweis: `test_rueckmeldung_kontext_449.py`, `test_rueckmeldungen.py` und `test_texte.py` zusammen 177 passed; Gesamtlauf 2252 passed. Alle ACs belegt, keine offenen Findings.
**Implementierer:** Behebung und Test „zeilenumbruch_am_ende“ sind eingecheckt.

Geprüfte Stellen (Bestätigungen):
Code reference: engine/rueckmeldungen.py:442
Code reference: engine/konnektor.py:2363
Code reference: engine/texte_de.py:2149
Code reference: engine/texte_en.py:2148
Code reference: engine/vorlage.html:4886

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict

VERDICT: VERIFIED

## Geprüfte Dateien

- sha256:906cc7d116e12020838733a5ab26164f7dd51205532ac515e8036409f90f3ec7  engine/konnektor.py
- sha256:125ec0cc5e653d6c0498290903ab3700c73b76aa269be05f0d045873bdc96533  engine/rueckmeldungen.py
- sha256:fb3a94f810dc12bc91b38460ec85f31fb7cb950e2cecfa9fcc79f8dfc9b5be1b  engine/texte_de.py
- sha256:c3acbb985592b224c55289c0b0675a5705cafa64a75204d7d33d7d66f1acd54d  engine/texte_en.py
- sha256:f10f97f2c4253c9dac08bd5ab165073233cd17f8a8a6fd067a4284bf9986fcec  engine/vorlage.html

## Prüfbasis

- base: fd8b7080c4ceeee9ab86a063e433fa2b165cd817
- blob:38397c2edfe6a370e8b2c2129747a6282848525b  engine/konnektor.py
- blob:348e6d4d2bf739363c2fac7f51e9129386570edf  engine/rueckmeldungen.py
- blob:364b4a9e97d1e572ffdce3e2ce5a31e5c074c8c7  engine/texte_de.py
- blob:df2ee8c11e261909b8038fa13c31e1b9284cc347  engine/texte_en.py
- blob:54662ff24b5fd3ed6e86217d523ff111ebc61093  engine/vorlage.html
