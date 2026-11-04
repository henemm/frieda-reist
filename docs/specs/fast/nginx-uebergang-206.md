# Mini-Spec: nginx-uebergang-206

Issue #206 und #260. Product Owner, 4.11.2026: „freigegeben“ (Streichen der Übergangs-Links empfohlen und freigegeben). Die Vorlage soll den Stand des
Servers abbilden. Auf dem Server liefern die alten Links aus der Zeit vor den Konten (`/<token>` und `/<instanz>-mcp/<token>`) 404; die Vorlage
würde sie wieder zum Dienst durchlassen.

## Was ändert sich

- `betrieb/vorlagen/nginx-konnektor-orte.inc`: die beiden Orte für die Übergangs-Links entfallen.
- `docs/betrieb.md`: Hinweis auf den Übergang und die Beschreibung der Zone `<instanz>_konto` ohne Übergangs-Links.
- `engine/tests/test_betrieb.py`: Test, der den Ort `/probe-mcp/` voraussetzt, prüft stattdessen, dass keine Übergangs-Orte erzeugt werden.

## Was darf sich nicht ändern

- Alle anderen Orte, Zonen und Drosseln der Vorlage. Nichts am Server.

## Acceptance Criteria

- AC-1: Die erzeugte Orte-Datei enthält keinen Ort für `/<token>` und keinen für `/<instanz>-mcp/`.
- AC-2: Die Orte-Datei besteht weiter `nginx -t` mit echtem nginx (bestehender Test), `/` und `/konto` gehen weiter an den Dienst.
- AC-3: Die Tests laufen grün.

## Manuelle Test-Schritte

1. Keine; die Umstellung des Servers ist ein eigener Schritt.

## Inline-Test

- [ ] `test_betrieb.py`: AC-1 und AC-2.
