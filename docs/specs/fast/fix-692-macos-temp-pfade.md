# Mini-Spec: Protokollprüfung erkennt Temp-Pfade von macOS (#692)

## Was ändert sich
- `engine/tests/test_protokolle_ohne_pfade.py`: Das Muster `ABSOLUT` erkennt zusätzlich die Temp-Ordner von macOS, also Pfade, die mit `/private/var/…`, `/private/tmp/…` oder `/var/folders/…` beginnen und danach einen Namen tragen.
- Neuer Testfall im selben Modul: vollständige Temp-Pfade unter `/private/var/folders/…`, `/private/tmp/…` und `/var/folders/…` (Beispiele stehen im Test selbst, nicht in den Docs, damit die Prüfung sie hier nicht findet) werden erkannt; Platzhalter wie `$TMPDIR/pytest-of-<benutzer>/x` und gekürzte Formen mit `…` nicht.
- `docs/artifacts/fix-694-konto-loeschen-ablage-neu/test-run-output.txt`: Die 198 Zeilen, die heute den macOS-Temp-Ordner eines Rechners nennen, werden mechanisch bereinigt: `/private/var/folders/<a>/<b>/T/` wird zu `$TMPDIR/`. Ebenso die Stellen, an denen pytest den Pfad in der Mitte gekürzt hat (`...<rest>/<kennung des Temp-Ordners>/T/` wird zu `...$TMPDIR/`), damit die rechnerspezifische Kennung des Temp-Ordners nirgends mehr steht. Sonst nichts an der Datei.
- Abweichung vom Wortlaut im Issue: `/private/var/folders` wird nur gemeldet, wenn nach `folders` ein echter Name folgt, damit die gekürzte Schreibweise mit `…` erlaubt bleibt.

## Was darf sich nicht ändern
- Alle bisher erkannten Muster (`/home`, `/Users`, `/srv`, `/mnt`, `/root`, `/var/www`, `pytest-of-<name>`) und die erlaubten Platzhalter bleiben gleich.
- Ein schlichtes `/tmp/…` (ohne `/private`) bleibt erlaubt; es verrät keinen Rechner, und bestehende Platzhalter wie `/tmp/pytest-of-<benutzer>` nutzen es.
- Keine Änderung an Engine, Betrieb oder anderen Protokollen.

## Akzeptanzkriterien
- AC-1: Der neue Testfall ist vor der Änderung rot und danach grün.
- AC-2: `test_protokolle_ohne_absolute_pfade` ist nach der Bereinigung grün (vor der Bereinigung meldet er mit dem neuen Muster das #694-Protokoll).
- AC-3: Die übrigen Tests des Moduls bleiben grün.

## Manuelle Test-Schritte
Keine; alles automatisiert über die Tests des Moduls.

## Inline-Test (wird während Implementierung geschrieben)
- [ ] `test_muster_erkennt_macos_temp` für die macOS-Temp-Pfade samt Platzhaltern
