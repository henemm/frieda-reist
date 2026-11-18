# Context: 624-veroeffentlichen-eigener-dienst

## Request Summary
Der Schreibweg startet das Veröffentlichen heute per `Popen(start_new_session=True)` als Kindprozess; der Lauf bleibt in der
cgroup von `<instanz>-schreiben.service` (Speicherspitze 3,4 GiB, erbt `NoNewPrivileges=yes`, stirbt beim Neustart des
Schreibdienstes mit). Ziel (#624): Der Schreibweg legt nur einen Merker, eine eigene systemd-Einheit startet
`<instanz>-veroeffentlichen.service`; danach sinkt die Grenze des Schreibdienstes auf 512M. Latenz (Zeitziel 2 Minuten, #230) darf
nicht leiden.

## Related Files
| Datei | Bedeutung |
|------|-----------|
| engine/schreiben.py:5658 `veroeffentlichen_anstossen` | Popen mit nice/ionice, Protokoll `<FR_DIENST>/veroeffentlichen-anstoss.log`; Aufrufer 5638 (Speicherweg) und engine/schreiben_git.py:79 (Git-Weg) |
| engine/schreiben.py:5465, 5484–5489 | Skriptpfad: Argument > `SB_VEROEFFENTLICHEN` > `veroeffentlichen_skript(wurzel)`; leer = aus |
| betrieb/veroeffentlichen.sh:1115–1127 | Sperre `<FR_DIENST>/veroeffentlichen.lock` (flock -n); belegt → `touch <FR_DIENST>/veroeffentlichen-nochmal`, sonst `rm -f` des Merkers; `nachlauf()` ab ~1378 startet bei Merker neu (exec $0); 1296 setzt Merker bei Software-Wechsel |
| betrieb/veroeffentlichen.sh:96–141 | `root_geht()` (sudo -n), freischalten über sudo, `ausstehende_neustarts` – scheitern heute im angestoßenen Lauf wegen NoNewPrivileges (#465, #494) |
| betrieb/vorlagen/veroeffentlichen.service / .timer | oneshot, Nice=10, TimeoutStartSec=45min, kein NoNewPrivileges; Timer alle 5 min |
| betrieb/vorlagen/schreiben.service | MemoryHigh=4G, MemoryMax=5G, MemorySwapMax=1G, Kommentar „bis #624“; ReadWritePaths enthält __DIENST__ (Merker beschreibbar) |
| betrieb/einrichten.sh:137–139, 213, 236–238 | erzeugt nur `vorlagen/*.service` und `*.timer`; aktiviert fest benannte Einheiten |
| betrieb/units.py:30–39 | `ERLAUBT` (Erlaubnisliste), `EINHEITEN` = nur .service/.timer, `DAUERDIENSTE` |
| betrieb/vorlagen/units-installieren.py:30, 36–43, 146 | Root-Hilfsprogramm: nur sechs `.service`-Einheiten (`ARTEN`), gleiche ERLAUBT-Liste; neue Einheiten lehnt es ab |
| docs/betrieb.md:89, 262–266, 410–470 | Anstoß, Zeitziel, Einheiten abgleichen, Speichergrenzen (#538) mit „bis #624“ |
| docs/specs/betrieb/speichergrenzen-538.md | Vorgänger-Spec, nennt #624 als Folge |

## Existing Patterns
- Merker-Dateien in `<FR_DIENST>` als Signal zwischen Prozessen (`veroeffentlichen-nochmal`, `neustart-ausstehend`, `freischalten-ausstehend`).
- Seite → Rückmeldedienst legt `<FR_ABLAGE>/_anstoss.json`; der nächste Timer-Lauf holt ihn ab (gleiches Muster: Merker statt Prozessstart).
- Einheiten aus Vorlagen; Abweichungen werden über `units.py pruefen` gemeldet; nur erlaubte Zeilen installiert das Root-Hilfsprogramm automatisch, alles andere ist „gesperrt“ (einmaliger bewusster Schritt, Sicherheitsentscheidung des PO).

## Dependencies
- Upstream: systemd (path unit `PathExists=`/`PathChanged=`, Retrigger nach Ende des Dienstes), flock, nice/ionice.
- Downstream: alle Tests mit `SB_VEROEFFENTLICHEN`-Stummel (test_schreiben.py, test_schreiben_speicher.py, test_software_weg_454.py, test_speicher_stufe5.py), test_anstoss_pfad_570.py (7 Tests), test_stand.py:254, test_units.py, test_units_helfer.py (`test_ac1_alle_sechs_einheiten_sind_erlaubt`), test_betrieb.py:2565–2592 (Speichergrenzen, Doku-Prüfung auf #624), betrieb/messlauf-schreibweg.py:64.

## Existing Specs
- docs/specs/betrieb/speichergrenzen-538.md

## Risks & Considerations
- **Handarbeit:** Eine neue `.path`-Einheit ist heute für Abgleich und Root-Hilfsprogramm „gesperrt“ (einmal Root je Instanz). Projektregel „keine Handarbeit im Betrieb“ verlangt einen automatischen Übergang. Optionen: Rückfall auf Popen, solange die neue Einheit nicht aktiv ist; oder das Hilfsprogramm darf genau diese eine neue Einheit mit festem Inhalt anlegen (Erweiterung der Erlaubnis = Sicherheitsentscheidung des PO).
- **Reihenfolge der Grenze:** MemoryMax=512M für `schreiben` geht über den Abgleich automatisch auf die Instanz. Läuft dort noch der Popen-Rückfall, würde der Schreibdienst beim nächsten Veröffentlichen beendet → Grenze erst senken, wenn kein Rückfall mehr möglich ist (oder Rückfall entfällt).
- **Latenz:** Path-Unit reagiert per inotify sofort; ist der Dienst schon aktiv, startet systemd ihn nicht zweimal. Mit `PathExists=` prüft systemd nach Ende des Dienstes erneut → Retrigger, wenn der Merker noch/wieder da ist. Das Skript muss den Merker nach Übernahme der Sperre löschen (tut es für `veroeffentlichen-nochmal` schon).
- **Endlosschleife:** Bleibt der Merker liegen (Skript scheitert vor `rm`), startet die Path-Unit den Dienst immer wieder (systemd-Trigger-Limit). Merker früh löschen.
- **Rechte:** Der vom Dienst gestartete Lauf hat kein NoNewPrivileges → `sudo -n` für Freischalten und Neustarts geht direkt (behebt #465/#494-Nebenwirkung, „freischalten-ausstehend“ wird seltener).
- **Neustart des Schreibdienstes** (deploy.sh, Abgleich) tötet das Veröffentlichen nicht mehr.
- Messlauf `messlauf-schreibweg.py` (Sandbox-Schreibziele) und `ReadWritePaths`: Merker liegt in `__DIENST__`, schon beschreibbar.
- Mehrere Instanzen auf einem Server: Einheiten- und Merkername tragen die Instanz bzw. liegen im Dienstordner der Instanz.

## Analysis

### Type
Feature (Betriebsumbau, Folge aus #538)

### Vorgehen der Analyse
Der Kontext aus Phase 1 war schon vollständig (Aufrufer, Sperre, Vorlagen, Abgleich, Tests). Statt drei Such-Agenten hat der Tech
Lead die offenen Punkte gezielt selbst nachgelesen: Root-Hilfsprogramm (`ARTEN`, `ERLAUBT`), `units.py` (`EINHEITEN`), Vorlagen
`veroeffentlichen.service/.timer`, `veroeffentlichen_anstossen`, Sperrblock in `veroeffentlichen.sh`, `einrichten.sh`, `docs/betrieb.md`
(Einmalschritt #454, Zeile ~578).

### Entscheidende Befunde
1. **Präzedenzfall für den Root-Schritt:** Beim Umzug #454 stellt der Tech Lead die Units „einmalig bei der Auslieferung bewusst“
   mit `einrichten.sh --installieren` um (das Skript holt sich Root per `sudo`). Das ist Teil der Auslieferung durch Claude, kein
   Handschritt beim PO oder Betreiber. Dasselbe Muster trägt die neue `.path`-Einheit; Erlaubnisliste und Root-Hilfsprogramm
   bleiben unverändert (keine neue Sicherheitsentscheidung nötig).
2. **Popen-Rückfall ist gefährlich, nicht hilfreich:** `units.py installieren` installiert je Einheit automatisch, sobald nur
   erlaubte Zeilen abweichen. `MemoryMax=512M` für `schreiben` ist erlaubt und käme ohne Root sofort auf die Instanz, die neue
   `.path`-Einheit dagegen nicht (gesperrt). Ein Popen-Rückfall liefe dann in 512M → OOM, systemd beendet den Schreibdienst.
   **Folge:** Popen fällt ganz weg. Übergang ohne aktive `.path`-Einheit: Der Merker bleibt liegen, der vorhandene Timer (alle
   5 min) veröffentlicht; nur die Latenz ist in diesem Fenster bis zu 5 min statt sofort, nichts geht verloren, nichts stürzt.
3. **Endlosschleife vermeiden:** Mit `PathExists=` startet systemd den Dienst erneut, solange der Merker existiert. Das Skript muss
   den Anstoß-Merker **vor** `flock` löschen; bei belegter Sperre greift das vorhandene `veroeffentlichen-nochmal` (nachlauf). So
   bleibt der Merker nie liegen, auch nicht, wenn ein Lauf außerhalb der Einheit (vergleichslauf, Handlauf) die Sperre hält, und
   das Trigger-Limit der Path-Unit wird nie erreicht. Auch der Timer-Lauf löscht ihn (gleiches Skript).
4. **Eigener Merkername** `<FR_DIENST>/veroeffentlichen-anstoss` (nicht `-nochmal` wiederverwenden: dessen Bedeutung „nach dem
   laufenden Lauf“ gehört dem Skript). `ReadWritePaths` von `schreiben` enthält `__DIENST__` schon.
5. **Latenz (#230):** Path-Unit reagiert per inotify sofort; Nice/IOScheduling stehen schon in `veroeffentlichen.service`. Läuft
   der Dienst schon, startet systemd ihn nicht doppelt; nach dem Ende prüft `PathExists=` erneut → Nachlauf ohne Wartezeit.
6. **Nebennutzen:** Der Lauf hat kein `NoNewPrivileges` mehr → `sudo -n` für Freischalten und Neustarts gelingt direkt (#465/#494
   seltener); ein Neustart von `schreiben` tötet das Veröffentlichen nicht mehr.

### Affected Files (with changes)
| File | Change Type | Description |
|------|-------------|-------------|
| engine/schreiben.py (`veroeffentlichen_anstossen`) | MODIFY | Statt Popen nur Merker `<FR_DIENST>/veroeffentlichen-anstoss` anlegen (wirft nie); „leer = aus“ von `SB_VEROEFFENTLICHEN` bleibt; Anstoß-Protokoll entfällt |
| engine/schreiben_git.py:79 | MODIFY (ggf. nur Test) | Git-Weg nutzt denselben Anstoß |
| betrieb/vorlagen/veroeffentlichen.path | CREATE | `PathExists=__DIENST__/veroeffentlichen-anstoss`, `Unit=__INSTANZ__-veroeffentlichen.service`, `WantedBy=paths.target` |
| betrieb/veroeffentlichen.sh (~1115) | MODIFY | Anstoß-Merker vor `flock` löschen |
| betrieb/vorlagen/schreiben.service | MODIFY | MemoryHigh/MemoryMax auf 384M/512M, Kommentar „bis #624“ weg |
| betrieb/einrichten.sh | MODIFY | `.path`-Vorlagen erzeugen und installieren, `enable --now <instanz>-veroeffentlichen.path` |
| betrieb/units.py | MODIFY | `EINHEITEN` kennt `.path` (fehlende Einheit = gesperrte Abweichung, gemeldet) |
| betrieb/vorlagen/units-installieren.py | unverändert | `.path` bleibt bewusst nicht automatisch installierbar |
| betrieb/messlauf-schreibweg.py:64 | MODIFY | Anstoß in der Sandbox prüft Merker statt Skriptstart |
| docs/betrieb.md (89, 262–266, 410–470) | MODIFY | Anstoß über Merker + Path-Unit, Grenze 512M, Einmalschritt bei Auslieferung |
| docs/specs/betrieb/speichergrenzen-538.md | MODIFY (Verweis) | Folge #624 erledigt |
| engine/tests/test_anstoss_pfad_570.py, test_schreiben*.py, test_software_weg_454.py, test_speicher_stufe5.py, test_stand.py, test_units.py, test_betrieb.py | MODIFY | Stummel prüfen Merker statt Skriptlauf; neue Tests für Path-Vorlage, Merker vor Sperre, 512M, Doku |

### Scope Assessment
- Files: ~14 (davon ~8 Tests)
- Estimated LoC: +250/-120
- Risk Level: MEDIUM — zentraler Weg „Speichern → Seite aktuell“; abgesichert durch den Timer als Rückfall, keine Datenänderung

### Technical Approach
Merker + systemd-Path-Unit, Popen ersatzlos weg, Grenze 512M in derselben Lieferung. Auslieferung: nach `main` installiert der
Tech Lead auf der Instanz einmalig `einrichten.sh --installieren` (Muster #454), prüft `systemctl is-active <instanz>-veroeffentlichen.path`,
einen Anstoß aus der Testreise (Latenz < 2 min) und `units.py pruefen` = 0. Bis dahin veröffentlicht der Timer.

### Dependencies
systemd Path-Units (`PathExists=`), flock; keine neue Bibliothek. Reisen-Repo der Instanz: dessen Tests mit dem Branch laufen lassen
(Anstoß-Protokolldatei entfällt, Verhalten des Anstoßes ändert sich).

### Open Questions
- keine Produktfrage; alle Punkte technisch entschieden (Befunde 1–4)

## Hinweise aus der RED-Phase (18.11.2026)

- Die Prüfung „Skript fehlt“ (#570, eine Zeile auf stderr, kein Anstoß) bleibt erhalten: Bei gesetztem, aber fehlendem Skriptpfad entsteht kein Merker (`test_fehlendes_skript_schreibt_eine_zeile`). „Leer = aus“ gilt wie bisher.
- Entfallen sind die Tests, die nur den Kindprozess prüften (Priorität mit `nice`/`ionice`, Ausgabe in `veroeffentlichen-anstoss.log`, langes Veröffentlichen hält die Antwort nicht auf); an ihre Stelle treten die Merker-Tests.
- Ein Fehler beim Anlegen des Merkers steht als Zeile auf stderr und nennt `veroeffentlichen-anstoss` (`test_anstoss_wirft_nie`).
- Der Quelltext von `veroeffentlichen_anstossen` darf die Wörter `Popen`, `subprocess`, `ionice`, `os.system`, `os.spawn` nicht enthalten, auch nicht im Docstring (`test_anstoss_startet_keinen_prozess`).
- Der Messlauf darf den Pfad `ohne-veroeffentlichen` nicht mehr nennen und muss `veroeffentlichen-anstoss` prüfen.
