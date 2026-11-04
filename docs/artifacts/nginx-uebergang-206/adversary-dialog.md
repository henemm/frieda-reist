# Adversary Dialog — nginx-uebergang-206
Spec: docs/specs/fast/nginx-uebergang-206.md
Datum: 2026-11-04

## Checkliste
- [x] AC-1: Die erzeugte Orte-Datei enthält keinen Ort für `/<token>` und keinen für `/<instanz>-mcp/`.
- [x] AC-2: Die Orte-Datei besteht weiter `nginx -t` mit echtem nginx (bestehender Test), `/` und `/konto` gehen weiter an den Dienst.
- [x] AC-3: Die Tests laufen grün.

## Dialog

### Runde 1
**Adversary:** Unabhängige Gegenprüfung (implementation-validator, 4.11.2026): VERDICT VERIFIED. Die erzeugte Orte-Datei hat keinen Token-Ort und keinen `<instanz>-mcp`-Ort mehr, nichts verwaist (`__KN_PORT__`, Zone `_konto` werden weiter genutzt, Skripte erwarten den alten Pfad nicht), die Negativprüfungen im Test sind scharf. F001 LOW: Kommentar in `nginx-zone.conf` nennt noch „Übergangs-Links“. F002 LOW: Kopf-Docstring von `engine/konnektor.py` führt `POST /<token>` als hinter nginx erreichbar.
**Implementierer:** F001 und F002 behoben (Kommentare); der Handler im Dienst bleibt bewusst. Die ganze Suite lief grün (1255 Tests, siehe suite.txt).
Code reference: betrieb/vorlagen/nginx-konnektor-orte.inc:68
Code reference: engine/konnektor.py:42

### Runde 2
**Adversary:** Zweite unabhängige Prüfung der Korrekturen: VERDICT AMBIGUOUS. Beide Kommentar-Korrekturen richtig, kein Code verändert, `ast.parse` fehlerfrei. Aber `docs/konnektor.md` (Zeilen 9, 10, 133, 205) beschreibt die Links je Reise und Person noch als lesbar beziehungsweise als Einrichtung; weitere Treffer in `docs/produkt.md`, `docs/neue-reise.md` (Erwähnungen des Übergangs, teils „werden nicht mehr ausgestellt“), ein ADR und ein alter Auftrag (Geschichte).
**Implementierer:** `docs/konnektor.md` an den vier Stellen auf „seit 1.11.2026 abgeschaltet (nginx antwortet 404)“ umgestellt. Die übrigen Erwähnungen nennen den Übergang nur geschichtlich oder sagen schon „nicht mehr ausgestellt“; ADR und alter Auftrag bleiben als Geschichte stehen.
Code reference: betrieb/vorlagen/nginx-zone.conf:23

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict: VERIFIED

## Geprüfte Dateien

- sha256:74e7e4d45a546009d75446a4de52d939dfe5a0fabdd464b5251f48be9f81f2f4  betrieb/vorlagen/nginx-konnektor-orte.inc
- sha256:3b517c4d0283063a40af29a41a51a574e624d6315224e71e4ebbb7575987b3e6  betrieb/vorlagen/nginx-zone.conf
- sha256:f1ae53e7a89bc8c73f8ccb0c66e3366b2e588591c9ad13aa749331ee3a17a48a  engine/konnektor.py

## Prüfbasis

- base: f811ca96e06e92fe9c71ada5de5709bb10739f59
- blob:2540c8a1b3e257aeebc5d40a14ccac2141da1016  betrieb/vorlagen/nginx-konnektor-orte.inc
- blob:cfbd63074ac455b067e1c08f66ea295a39516d8b  betrieb/vorlagen/nginx-zone.conf
- blob:147b72e1278fa9649a7e839831d40b24c8626822  engine/konnektor.py
