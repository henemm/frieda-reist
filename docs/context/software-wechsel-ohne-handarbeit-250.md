# Context: Software-Wechsel ohne Handarbeit (#250)

## Request Summary
Henning (PO, 2.11.2026) nach der Prüfung „müssen die Reisen nach #214/#217 nachgearbeitet werden?“: „Denke Frieda als
Produkt. Was davon muss im Sinne des Produktes in der Software geändert werden? Ich möchte keine Software, die
Handarbeit braucht.“ Seine Entscheidungen 1–3 aus dem Prüfbericht hat er mit „ja, mach das“ angenommen (Bericht:
https://claude.ai/artifact/MxL94dweEfVXX5CQAJDmyo). Spec-Entwurf: `docs/specs/betrieb/software-wechsel-ohne-handarbeit-250.md`.

## Befund der Prüfung (2.11.2026, Kopien aller sechs Reisen der Instanz)
- Alle Reisen bauen mit 7430aec (online) und 74a2d29 (main) ohne Fehler, ohne neue Warnungen.
- #214: `tagesseiten` (GR 221) und `plan_reiter` (Japan) werden ohne Wirkung gelesen, nichts nötig.
- #217: Oldenburg, Skiurlaub, test-135, test-14 tragen Eckdaten der früheren Vorlage als Text. `neu.py nachziehen`
  stellt sie korrekt um. Mit der ALTEN Software baut eine umgestellte Reise nicht („unknown key ziel“) → Reihenfolge
  zwingend; Lösung: Umstellen im selben Commit wie der Software-Wechsel.
- Skiurlaub: handgeschriebene Zeile „Status: Planung (seit 28.10.2026). Nightjet … gebucht; Buchungsdaten in
  `inhalt/wissen.md`.“ in W-01 → nach Umstellung doppelter Status. PO hat zugestimmt: Wort „Status:“ streichen, Rest
  bleibt. Das ist Inhalt → über den Konnektor (Frieda, Wissen ändern auf W-01), NICHT in Claude Code.
- `reise.json` wird von `nachziehen` auf `indent=2` gebracht: das ist die kanonische Form der Software (schreiben.py
  schreibt genauso). KEIN Fehler (im Bericht fälschlich als Kleinkram genannt → im Abschlussbericht berichtigen).
- „Status: planung“ in den Eckdaten: Datenwert statt Wort → Teil dieses Vorhabens (AC-7).
- CLAUDE.md-Reste: oldenburg, test-135, test-14 = ausgefüllte Kopien der früheren Vorlage (entfernbar);
  skiurlaub (33 Zeilen), gr221 und japan-2027 (je 60 Zeilen) haben EIGENEN Inhalt (Vorlieben, Entscheidungen,
  Buchungsnotizen), den weder Seite noch Konnektor sehen. Nicht automatisch anfassen (Sichtbarkeit auf der Seite ist
  eine PO-Entscheidung) → im Abschlussbericht als Entscheidung vorlegen.
- `kontext/herkunft.md` der vier Reisen: je eine Zeile „angelegt von … (Auftrag …)“ = ausgefüllte Vorlage.
- GitHub-Zeitplan „7,37 * * * *“ lief real nur alle 3–8 h (Läufe 1.11. 05:50, 13:10, 18:31, 22:19; 2.11. 01:45, 09:19).
- Dienste: `deploy.sh` startet Schreibweg/Push (und Konnektor) neu, wenn sich ihr Code ändert → Fenster alter Code /
  neue Daten nur bis zum nächsten Veröffentlichen-Lauf (wenige Minuten).
- `gh` auf dem Server hat Scope `workflow` (nötig, um `.github/workflows/` in Reisen-Repo der Instanz zu ändern).

## Related Files
| Datei | Rolle |
|---|---|
| `betrieb/software-nachziehen.yml` | Vorlage des Workflows; wird dünn, ruft nur noch das neue Skript |
| `betrieb/software-nachziehen.sh` (neu) | Umstellen, Tor, Commit/Push mit Neu-Umstellen bei Konflikt, Issue |
| `betrieb/veroeffentlichen.sh` | `anstoss_weitergeben()` (Zeile ~219) startet schon `gh workflow run`; neu: Anstoß bei neuem Software-Stand, einmal je SHA, Merkdatei in `FR_DIENST` |
| `betrieb/gemeinsam.sh` | Vorgaben wie `FR_NACHZIEHEN_WORKFLOW`; neu `FR_NACHZIEHEN_WIEDERHOLEN_STUNDEN` |
| `engine/neu.py` | `nachziehen()` (~425), `eckdaten_nachziehen()` (~509, enthält bisher die OFFEN-Meldung zu Resten) |
| `engine/reise.py` | `eckdaten_text()` (~206), `STATUS` |
| `engine/texte_de.py`, `texte_en.py` | `inhalt.eckdaten.*`, `pruefung.neu.nachziehen.*` |
| `engine/altformen/vorlage-vor-217/{de,en}/` (neu, schon angelegt) | frühere Vorlage `CLAUDE.md`, `kontext/herkunft.md` aus `55446c7^` als Muster |
| `engine/tests/test_umstellung_250.py` (neu, schon geschrieben, rot) | neue Reise nichts nachzuziehen, Reste, Kopfkommentar, Status in Worten |
| `engine/tests/test_neu.py:387` | erwartet heute „OFFEN CLAUDE.md“ → anpassen |
| `engine/tests/test_software_nachziehen.py` | prüft Text der yml → auf Skript umziehen |
| `engine/tests/test_betrieb.py` | Betriebsskripte, Anstoß (VF_NACHZIEHEN) |
| `docs/betrieb.md` | Zeile ~219 „Änderungen an der Vorlage werden von Hand übernommen“ → raus; Abschnitt Anstoß/Überwachung |
| `CLAUDE.md` (Repo) | neue Regel: Formatänderung bringt Umstellung in `neu.py nachziehen` mit |
| `betrieb/deploy.sh` | Modulliste (falls neues Python-Modul) |

## Existing Patterns
- Workflow-Tor #168: `engine/tests` + Bau sperren, `tests/` warnt; Issue mit Label `software-nachziehen`.
- `veroeffentlichen.sh`: Testbarkeit über `VF_*`-Überschreibungen (z. B. `VF_NACHZIEHEN`, `VF_JETZT`).
- `neu.py nachziehen`: idempotent, „nur Schlüssel, nie Inhalt“, Meldungen in der Sprache der Reise.
- Texte nur über `texte.t()`; Tests prüfen Meldungen über Schlüssel (`conftest.meldet`).

## Dependencies
- Upstream: git, gh (Server), GitHub Actions Runner (python 3.12), `neu.py`, `bauen.py`.
- Downstream: Reisen-Repos jeder Instanz (Reisen-Repo der Instanz: `.github/workflows/software-nachziehen.yml` muss ein letztes
  Mal kopiert werden, per PR dort; Instanz-Tests in `Reisen-Repo der Instanz/tests/` auf Bezüge zur yml prüfen).

## Begleitaufgaben außerhalb des Codes (Stand 2.11.2026 ~16:45 UTC)
1. Lauf „Software nachziehen“ 41482067829 (von Hand gestartet 16:30 UTC, Freigabe Henning) prüfen; danach ob der
   Bauordner der Instanz veröffentlicht hat (Protokoll des Veröffentlichens, „Published“).
2. Sichtprüfung nach dem Nachziehen: Japan (tiefe, plan_reiter) und eine Reise ohne Pläne (Oldenburg).
3. Nach Merge: yml in Reisen-Repo der Instanz per PR (Arbeitsordner, nie Bauordner), Workflow starten → Umstellung der vier
   Reisen prüfen.
4. Skiurlaub-Zeile über Konnektor ändern (nach Umstellung).
5. Abschlussbericht ans Artefakt: reise.json-Punkt streichen, CLAUDE.md-Inhalte bei gr221/japan/skiurlaub als
   Entscheidung.
6. Eigenes Issue für weitere Handschritte in `docs/betrieb.md` (Push-Dienst: pip install, einrichten.sh, sudo-Regel).
7. Andere Sitzung frieda-reist-14 arbeitet an #249 (anmeldung.py, konto.js) — keine Überschneidung.

## Risks & Considerations
- Erster Lauf: Alte yml der Instanz zieht die Software ohne Umstellung nach → deshalb Umstellen in jedem Lauf (auch
  ohne neuen Stand), sonst blieben die vier Reisen liegen.
- Rotes Tor + zuverlässiger Anstoß → Mail-Flut; deshalb einmal je SHA, Wiederholung erst nach Stunden.
- Push-Konflikt mit dem Schreibweg: nicht rebasen, sondern zurücksetzen und neu umstellen.
- Löschen von Dateien nur bei exakter Übereinstimmung mit der Vorlage (Platzhalter als `.*`).
- Instanzneutral bleiben (kein Pfad, keine Domain in Vorlage/Skript; Test `test_nichts_einer_instanz`).

## Analysis

### Type
Feature (Betrieb: Software-Wechsel ohne Handschritte), PO-Auftrag 2.11.2026.

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| `engine/neu.py` | MODIFY | `nachziehen()`: Vorlagen-Reste (`CLAUDE.md`, `kontext/herkunft.md`) zeilenweise gegen `engine/altformen/vorlage-vor-217/<sprache>/` prüfen und nur bei exakter Übereinstimmung entfernen (Platzhalter `$wort` → `.*`, `fullmatch`, gleiche Zeilenzahl, CRLF/Leerzeilen am Ende normalisiert, leere Datei passt nie); leeren Ordner `kontext/` mit entfernen; OFFEN-Meldung zu Resten entfällt; Kopfkommentar der `reise.yaml` mit wörtlichem `\n` reparieren. Meldungen über `texte.t` (`pruefung.neu.nachziehen.*`) |
| `engine/reise.py` | MODIFY | `eckdaten_text()`: Status über `inhalt.eckdaten.status.<wert>` in Worten |
| `engine/texte_de.py`, `engine/texte_en.py` | MODIFY | neue Schlüssel: Status-Wörter, Meldungen „Rest entfernt“, „Kopfkommentar berichtigt“ |
| `engine/altformen/vorlage-vor-217/{de,en}/` | CREATE (liegt schon) | Muster der früheren Vorlage |
| `engine/tests/test_umstellung_250.py` | CREATE (liegt schon, rot) | AC-6/AC-7 |
| `engine/tests/test_neu.py` (~387) | MODIFY | erwartet heute „OFFEN CLAUDE.md“ |
| `betrieb/software-nachziehen.sh` | CREATE | Bash mit `main()`-Wrapper: Umstellen, Tor, Commit, Push mit Zurücksetzen und Neu-Umstellen (3 Versuche), Issue bei Rot |
| `betrieb/software-nachziehen.yml` | MODIFY | behält „Neuer Stand?“ (unshallow, merge-base) und „Submodul setzen“, richtet Python in jedem Lauf ein, ruft dann `frieda/betrieb/software-nachziehen.sh` mit `ALT`, `NEU`, `NEU_DA`; fehlt das Skript (Submodul zu alt): klarer Fehlertext |
| `betrieb/veroeffentlichen.sh` | MODIFY | Anstoß je neuem Software-Stand direkt nach `anstoss_weitergeben` (vor dem fetch, läuft immer): URL aus `git config -f .gitmodules submodule.frieda.url`, eingebunden = `git rev-parse HEAD:frieda`, Merkdatei `<FR_DIENST>/nachziehen-angestossen` („SHA Epoche“) erst nach erfolgreichem `gh`; Testhaken `VF_LSREMOTE`, `VF_JETZT`, `VF_NACHZIEHEN` |
| `betrieb/gemeinsam.sh` | MODIFY | `FR_NACHZIEHEN_WIEDERHOLEN_STUNDEN` (Vorgabe 6) |
| `engine/tests/test_software_nachziehen.py` | MODIFY | Prüfungen der yml auf das Skript umziehen; Skript-Test nach Muster `test_betrieb.py:1112` (Reisen-Repo mit Submodul) plus Bare-Remote als origin, Attrappen für gh/pytest/bauen im PATH, Wettlauf durch Commit auf origin zwischen Umstellen und Push |
| `engine/tests/test_betrieb.py` | MODIFY | Anstoß: einmal je SHA, Wiederholung nach Wartezeit, Fehler hält Veröffentlichen nicht auf (Muster ~773 mit lokaler `.gitmodules`-URL) |
| `docs/betrieb.md` | MODIFY | „Vorlage von Hand übernehmen“ raus; Ablauf, Anstoß, Wartezeit, Fehlermails |
| `CLAUDE.md` | MODIFY | Regel: Formatänderung bringt Umstellung in `neu.py nachziehen` mit Test mit |
| `betrieb/deploy.sh` | — | keine Änderung: kein neues Python-Modul für Konnektor/Dienst |

### Scope Assessment
- Files: ~14 (davon 2 schon angelegt)
- Estimated LoC: +450 bis +550 / −100
- Risk Level: MEDIUM — betrifft den Weg, auf dem jede Instanz neue Software bekommt, und schreibt automatisch in echte Reisen; abgesichert durch Tor (Bau jeder Reise), Idempotenz und „im Zweifel nichts löschen“.

### Technical Approach
Empfehlung (Plan-Bewertung, übernommen):
1. Fachlogik in `neu.py` (pytest-testbar), Betrieb in Bash. Der Schritt „Neuer Stand?“ und das Setzen des Submoduls bleiben in der
   yml (Henne-Ei: erst danach existiert das Skript des neuen Stands); alles Weitere im Skript aus dem Submodul.
2. Umstellen in jedem Lauf; Pflicht-Test „zweiter Lauf ändert nichts“, sonst Commit je Lauf.
3. Push-Wettlauf: `git reset --hard origin/main`, Submodul erneut auf NEU, neu umstellen, neu bauen, neu committen; max. 3
   Versuche, nie `--force`.
4. Anstoß vom Server einmal je SHA; Merkdatei erst nach erfolgreichem `gh`.
5. Reihenfolge: neu.py+Texte → Eckdaten → Skript+yml+Tests → Anstoß+Tests → Docs/CLAUDE.md → Einführung (yml-PR in Reisen-Repo der Instanz
   erst nach Merge der Software).

### Dependencies
- Upstream: git, gh (Server, Scope `workflow`), GitHub Runner (python 3.12, libcairo2), `neu.py`, `bauen.py`.
- Downstream: Reisen-Repos jeder Instanz (yml ein letztes Mal kopieren). `deploy.sh` startet Dienste bei neuem engine-Code neu.

### Befunde gegen den Plan
- Keiner kippt ihn. Bootstrapping: Die alte yml zieht beim ersten Mal ohne Umstellung nach; die neue Software baut unumgestellte
  Reisen weiter → nur Verzögerung bis zum yml-PR. Anstoß startet bis dahin den alten Lauf (ohne Schaden; nach Einführung prüfen).
- Setup in jedem Lauf kostet einige Minuten je Lauf; vertretbar (Pip-Cache bleibt).

### Open Questions (technisch, in der Spec zu entscheiden, keine PO-Frage)
- [ ] Rotes Tor + Zeitplan alle 30 Min: GitHub mailt jeden roten Lauf. Vorschlag für die Spec: Liegt für denselben SHA schon ein
      offenes Issue `software-nachziehen` vor, endet der Lauf mit Warnung statt rot (eine Mail je Stand, wie beim Anstoß).
- [ ] Meldungen der Umstellung in neuen Zweigen ausschließlich über `texte.t`; Ausnahmelisten in `test_texte.py` nur kürzer.

## Festlegungen aus der RED-Phase (2.11.2026, Commit 43f7906, Branch software-wechsel-250)
- Dieses Dokument bleibt lokal (nennt Personen und Reisen der Instanz), nicht committen.
- Python-Umgebung: Im Worktree fehlt engine/.venv; Tests mit dem venv des Submoduls im Reisen-Repo der Instanz ausführen (`<reisen-repo>/frieda/engine/.venv/bin/python -m pytest -q engine/tests`). Gesamtsuite dauert ca. 16 Minuten → im Hintergrund starten.
- Testhaken veroeffentlichen.sh: `VF_LSREMOTE` ersetzt `git ls-remote`, wird mit der URL (aus .gitmodules) aufgerufen und gibt `SHA<TAB>refs/heads/main` aus; Exit ≠ 0 = Warnung. `VF_NACHZIEHEN` ersetzt `gh workflow run` (wie beim Anstoß der Seite). `VF_JETZT` = Uhr. Merkdatei `<FR_DIENST>/nachziehen-angestossen` = „SHA Epoche“ in einer Zeile. Vorgabe `FR_NACHZIEHEN_WIEDERHOLEN_STUNDEN=6` in gemeinsam.sh, auch in einstellungen.beispiel erklären (Test test_beispiel_einstellungen_sind_vollstaendig).
- Testhaken software-nachziehen.sh: `SN_PAUSE` (Sekunden zwischen Push-Versuchen, Test setzt 0). Skript ruft `python` (PATH-Attrappe fängt `-m pytest … engine/tests`, `-m pytest` (tests/) und `bauen.py … <reise>` als letztes Argument ab), `gh issue list/view/create/comment`, `gh label create`. Ausgabe der Warnungen mit `::warning::`. Reisen werden umgestellt mit `python frieda/engine/neu.py nachziehen reisen/<r>`.
- Der Aufruf-Schritt der yml: Werte nur über env (ALT, NEU, NEU_DA, GH_TOKEN), kein `if`, kein `${{` im run; fehlt das Skript → Exit ≠ 0 und Hinweis mit „software-nachziehen.sh“. In der yml darf kein `gh issue create`, `git push`, `bauen.py` mehr stehen. setup-python und „Python-Pakete“ ohne `if`.
