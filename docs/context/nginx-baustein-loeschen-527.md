# Context: nginx-baustein-loeschen-527

## Request Summary
Nach dem endgültigen Entfernen einer Reise (#381) bleibt ihr nginx-Baustein `<FR_NGINX_SNIPPETS>/<instanz>-<reise>.conf` stehen und liefert 404. Er soll automatisch über den Betriebsweg mit Root-Rechten entfernt werden (geprüft mit `nginx -t`, neu geladen), ohne Handschritt (#250). Quelle: Adversary-Finding F006 aus `docs/artifacts/alpha-381-loeschen/adversary-dialog.md`.

## Related Files
| File | Relevance |
|------|-----------|
| `betrieb/vorlagen/nginx-reise-installieren.py` | Root-Hilfsprogramm (#552); kann den Baustein schon entfernen: `--entfernen`, Reisename auf stdin, Sperre, Sicherung, `nginx -t`, Rückweg, Reload. Ausgang 0 entfernt, 2 nichts da, 3 abgelehnt, 4/5/6 nginx-Fehler. Bislang ruft niemand `--entfernen` auf. |
| `betrieb/veroeffentlichen.sh` | `vorgemerkte_entfernen` (Z. ~256) löscht Webordner vorgemerkter Reisen, `root_geht` (Z. 101) prüft sudo per `sudo -l`, `ausstehende_freischalten` / `ausstehende_neustarts` zeigen das Muster „ohne Root vormerken, im nächsten Lauf mit Root nachholen“. Dienst läuft ohne NoNewPrivileges (Unit-Kommentar). Natürlicher Ort für den Aufruf. |
| `betrieb/freischalten.sh` | Ruft den Helfer zum Anlegen auf; Fallunterscheidung der Ausgänge 0–6 als Vorlage für Meldungstexte. |
| `engine/waechter.py` | `loeschungen_ausfuehren` / `_seitenlink_entfernen` (Z. 428–480): entfernt Ordner, Stempel, `seiten.json`-Eintrag; Docstring sagt „Baustein bleibt (Root-Rechte)“ — muss angepasst werden. Wächter-Dienst (`vorlagen/waechter.service`) soll keine Root-Rechte bekommen. |
| `engine/konten.py` | `vorgemerkt` (CLI) = Schonfrist ∪ Löschprotokoll; `loeschprotokoll()` = endgültig entfernte Reisen (Tabelle `loeschprotokoll`). Für die Baustein-Entfernung zählt nur das Löschprotokoll: in der Schonfrist kann die Reise zurückgeholt werden und soll ihren Link behalten. Ggf. neuer CLI-Befehl für die Liste des Löschprotokolls. |
| `betrieb/einrichten.sh` | erzeugt Helfer und sudoers-Regel (Z. 161–219); sudoers erlaubt den Helfer schon (beliebige Argumente) — keine Änderung an Root-Teilen nötig. |
| `betrieb/nginx.py` | liest Bausteine ohne sudo (0640 root:<Gruppe>); Existenzprüfung eines Bausteins ohne sudo ist damit möglich. |
| `docs/betrieb.md` (Abschnitt Wächter, Veröffentlichen), `docs/waechter.md` | Doku nachziehen. |
| Tests: `engine/tests/test_loeschen_reise.py`, `test_nginx_reise_helfer.py`, `test_betrieb.py` (ALARMSTELLEN), `test_waechter.py` | Bestehende Tests zu #381 und Helfer; neue Tests für den Aufruf aus dem Veröffentlichen. |

## Existing Patterns
- Root-Aktionen nur über eingebackene Hilfsprogramme in `/usr/local/sbin` mit `sudo -n` (#552); Aufrufer übergibt nur den Reisenamen auf stdin.
- Ohne Root-Rechte (Lauf aus dem Schreibweg mit NoNewPrivileges): vormerken und im nächsten Lauf mit Root nachholen (#465, #494).
- `vorgemerkte_entfernen` läuft vor jedem Bau und ist fail-closed bei unlesbarer Liste.
- Testbare Überschreibungen über Umgebung: `FR_SUDO`/`FS_SUDO`, `FR_NGINX_REISE_HELFER`, `FR_NGINX_SNIPPETS`.

## Dependencies
- Upstream: Löschprotokoll in `konten.db`, Helfer `--entfernen`, sudoers-Regel der Instanz.
- Downstream: nginx-Konfiguration der Instanz (Reload), `nginx.py pruefen` (betrachtet Reise-Bausteine nicht), Wächter-Docstring/Doku.

## Existing Specs
- `docs/specs/` zu #381 (Löschen einer Reise) und #552 (Helfer) — in der Spec-Phase referenzieren.

## Risks & Considerations
- Kritischer Pfad: nginx-Reload für alle Reisen der Instanz; ein Fehler darf nie einen kaputten Stand laden (Helfer sichert und rollt zurück).
- Nur Reisen im Löschprotokoll, nie in der Schonfrist (Zurückholen behält den Link).
- Löschprotokoll wächst dauerhaft: nicht bei jedem Lauf sudo je Reise; vorher ohne sudo prüfen, ob der Baustein-Datei existiert.
- Fehler des Helfers: kein `high`-Alarm (kein Ausfall, Seite liefert 404 ohnehin) → Warnzeile, nächster Lauf versucht erneut; neue `high`-Stelle bräuchte Begründung in `ALARMSTELLEN`.
- Reisename vor dem Aufruf gegen das Muster prüfen (Helfer prüft ebenfalls).
- Bestehende Instanzen: verwaiste Bausteine bereits gelöschter Reisen werden beim ersten Lauf mit erfasst (Löschprotokoll), kein Handschritt.

## Analysis

### Type
Bug (Lücke aus #381, Adversary-Finding F006): verwaister nginx-Baustein nach endgültigem Entfernen einer Reise; widerspricht #250 (kein Handschritt nach Software-Wechsel/Betrieb).

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| `engine/konten.py` | MODIFY | Neuer CLI-Befehl `entfernt` (nur Löschprotokoll, je Zeile eine Reise), Docstring-Liste der Befehle ergänzen. `vorgemerkt` bleibt unverändert (Schonfrist ∪ Löschprotokoll). |
| `betrieb/veroeffentlichen.sh` | MODIFY | Neue Funktion `entfernte_bausteine` direkt nach `vorgemerkte_entfernen` (beide Aufrufstellen, Z. ~874 und ~1153): liest `konten.py entfernt`, prüft Muster, prüft ohne sudo `[ -e <SNIPPETS>/<instanz>-<reise>.conf ]`, nur dann `root_geht` und `printf '%s\n' "$r" \| $FR_SUDO $HELFER --entfernen`; Ausgänge 0 → Zeile „Block removed“, 2 → still, 3–6 → Warnzeile, nächster Lauf versucht erneut. Ohne Root: Hinweiszeile, nächster Timer-Lauf erledigt es (Datei bleibt ja liegen, keine eigene Vormerkdatei nötig). Liste nicht lesbar: Warnzeile, kein Abbruch des Baus (der Bau hängt nicht davon ab, fail-closed übernimmt schon `vorgemerkte_entfernen`). |
| `engine/waechter.py` | MODIFY | Docstring `loeschungen_ausfuehren` (Z. ~430): Baustein entfernt der nächste Lauf von Veröffentlichen. |
| `docs/betrieb.md`, `docs/waechter.md` | MODIFY | Ablauf beim endgültigen Entfernen nachziehen. |
| `engine/tests/test_veroeffentlichen*.py` bzw. `test_loeschen_reise.py` | MODIFY/CREATE | Tests mit Attrappe des Helfers (`FR_NGINX_REISE_HELFER`, `FR_SUDO=""`, `FR_NGINX_SNIPPETS` auf tmp): entfernt nur Reisen im Löschprotokoll, nie in der Schonfrist; kein Aufruf, wenn Datei fehlt; ohne Root kein Aufruf und Hinweis; Fehlerausgang → Warnung, Bau läuft weiter, kein `high`-Alarm; ungültiger Name wird übersprungen. |
| `engine/tests/test_konten*.py` | MODIFY | Test für `konten.py entfernt`. |

Nicht betroffen: Helfer (`--entfernen` existiert, getestet in `test_nginx_reise_helfer.py`), sudoers/`einrichten.sh` (Regel erlaubt den Helfer mit beliebigen Argumenten), Wächter-Dienst (bekommt keine Root-Rechte), `deploy.sh` (kein neues Modul), `ALARMSTELLEN` (keine neue `high`-Stelle).

### Scope Assessment
- Files: ~6–8 (davon 2–3 Code, Rest Doku/Tests)
- Estimated LoC: +120/-5 (Code ~40, Tests ~70, Doku ~10)
- Risk Level: MEDIUM — nginx-Reload betrifft alle Reisen der Instanz; der Helfer sichert, prüft mit `nginx -t` und rollt zurück, das Risiko liegt also nur im richtigen Aufruf (richtige Reise, nur Löschprotokoll).

### Technical Approach
Aufruf aus `veroeffentlichen.sh`, weil dort Root-Rechte (Timer-Lauf ohne NoNewPrivileges) und das Muster „ohne Root später nachholen“ bereits bestehen (#465, #494). Quelle ist allein das Löschprotokoll (neuer Befehl `konten.py entfernt`), damit Reisen in der Schonfrist beim Zurückholen ihren Link behalten. Vor sudo eine Existenzprüfung ohne Root (Snippet-Ordner `${FR_NGINX_SNIPPETS:-/etc/nginx/snippets}`, wie `einrichten.sh`; Bausteine 0640 root:<Gruppe>, Ordner lesbar): Das Löschprotokoll wächst dauerhaft, sudo wird so nur bei echter Arbeit aufgerufen und protokolliert. Der Zustand „Datei existiert noch“ ist selbst die Vormerkung — keine zusätzliche Ausstehend-Datei. Bestehende Instanzen: verwaiste Bausteine früher gelöschter Reisen werden im ersten Lauf erfasst, ohne Handschritt.

Verworfen: Wächter mit Root-Rechten (widerspricht Rechtetrennung); Aufruf direkt in `loeschungen_ausfuehren` per sudo (Wächter-Dienst darf kein sudo); Aufruf über `vorgemerkt` (würde Schonfrist-Reisen ihren Link nehmen).

### Dependencies
- Upstream: Tabelle `loeschprotokoll` in `konten.db` (`konten.loeschprotokoll()` existiert), Helfer `<instanz>-nginx-reise-installieren --entfernen` (#552), sudoers-Regel der Instanz, `root_geht`.
- Downstream: nginx der Instanz (Reload durch den Helfer), Doku.
- Instanz-Tests: Meldungstexte in `veroeffentlichen.sh` neu → vor dem Vorspulen Instanz-Tests mit dem Branch laufen lassen (Projektregel).

### Open Questions
- Keine Produktfrage offen: Verhalten ist rein technisch (Link einer endgültig entfernten Reise war schon 404, jetzt verschwindet auch die nginx-Regel).
