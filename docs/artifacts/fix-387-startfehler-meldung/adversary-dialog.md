# Adversary Dialog — fix-387-startfehler-meldung
Spec: docs/specs/oberflaeche/startfehler-meldung-387.md
Datum: 2026-11-10 17:18

## Checkliste
- [x] **AC-1:** Bricht das Hauptskript beim Start ab (Laufzeitfehler, Syntaxfehler oder abgelehntes Versprechen), zeigt die Seite `#startfehler` mit `role="alert"`, dem Titel und dem Knopf „Neu laden“, sichtbar im Fenster. Gilt für beide Beispielreisen (Wanderung, Stadtwochenende).
- [x] **AC-2:** Der Knopf lädt die Seite neu (`location.reload()`).
- [x] **AC-3:** Titel und Knopf stehen in der Sprache der Reise (`<html lang>`); ist sie nicht im Ausschnitt, in der ersten Sprache. Die Texte stammen aus dem Katalog, im Code stehen keine sichtbaren Wörter.
- [x] **AC-4:** Eine gesunde Seite beider Beispielreisen enthält kein `#startfehler`. Ein Fehler nach Ende des Starts (z. B. `setTimeout(() => { throw … })`, abgelehntes `fetch`) zeigt keine Meldung.
- [x] **AC-5:** Der Fänger greift nicht auf `D`, `TEXTE`, `T()` oder `el()` zu und arbeitet mit `createElement` und `textContent`; er löst selbst keinen Fehler aus (Test mit Syntaxfehler im Hauptskript).
- [x] **AC-6:** `bauen.py` verlangt `/*__STARTFEHLER__*/null` genau einmal; der eingesetzte Ausschnitt enthält alle Sprachen des Katalogs und nur die zwei Schlüssel.
- [x] **AC-7:** `seite.fehler.start_titel` und `seite.fehler.start_neu_laden` stehen in allen `texte_*.py` und in der Pseudo-Sprache; die Ausnahmelisten in `test_texte.py` werden nicht länger.
- [x] **AC-8:** `betrieb/startprobe.mjs` endet mit Exit 1 und „Startfehler-Meldung sichtbar“, wenn die Seite die Meldung zeigt; auf gesunden Seiten beider Beispielreisen bleibt sie grün.
- [x] **AC-9:** Der Baustein ist im Kopfkommentar, in den Stilen, auf der Bausteinseite und in `docs/design.md` eingetragen (`test_design.py` grün).
- [x] **AC-10:** `engine/.venv/bin/python -m pytest -q engine/tests` ist ohne echte Reisen grün, auch die Browsertests und `test_seite_startet.py`.
- [x] **AC-11:** (Prozess) Aussehen und Wortlaut sind dem Product Owner vor dem Bau als Artefakt-Entwurf gezeigt und von ihm freigegeben.
- [x] **AC-12:** (Prozess) Das Issue in `henemm/henemm-infra` für den Teil-Check ist angelegt und in #387 verlinkt; #387 wird erst nach laufendem Teil-Check und Abnahme geschlossen.

## Dialog

### Runde 1
**Adversary:** Beweislast je Punkt. Testlauf: `engine/.venv/bin/python -m pytest -q` über test_startfehler_meldung_387, test_startprobe, test_design, test_texte, test_seite_startet, test_startreihenfolge: 134 passed, 0 failed, 0 übersprungen (docs/artifacts/fix-387-startfehler-meldung/adversary-test-output.txt).

Confirmation:
  AC: AC-1
  Code reference: engine/vorlage.html:1032
  Evidence: Fänger-Skript steht vor dem Hauptskript (`const D`), `error`/`unhandledrejection`-Hörer, Box mit role=alert und Knopf; test_startfehler_zeigt_meldung_mit_knopf läuft für Wanderung und Stadtwochenende, mit Laufzeit- und Syntaxfehler, grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-2
  Code reference: engine/vorlage.html:1032
  Evidence: `knopf.addEventListener("click", () => location.reload())` in `startfehlerMeldung`; test_knopf_laedt_neu grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-3
  Code reference: engine/texte_de.py:381
  Evidence: Titel/Knopf stehen nur im Katalog (texte_de.py:381-382, engine/texte_en.py:380-381); der Fänger wählt per `document.documentElement.lang`, sonst die erste Sprache; test_sprache_der_reise_und_rueckfall grün. Im Code keine sichtbaren Wörter.
  Status: CONFIRMED

Confirmation:
  AC: AC-4
  Code reference: engine/vorlage.html:6163
  Evidence: `window.__startFertig = true;` ist die letzte Anweisung des Hauptskripts (Z. 6163, danach nur `</script>`); test_gesunde_seite_und_spaete_fehler_zeigen_keine_meldung (setTimeout-Wurf, abgelehntes fetch) grün; test_hauptskript_setzt_startmarke_als_letzte_anweisung grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-5
  Code reference: engine/vorlage.html:1032
  Evidence: Fänger-Quelltext enthält weder `D`, `TEXTE`, `T(` noch `el(`; nur createElement/textContent; melde() in try/catch; test_faenger_greift_nicht_auf_das_hauptskript_zu und test_faenger_wirft_selbst_nichts_bei_syntaxfehler grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-6
  Code reference: engine/bauen.py:1706
  Evidence: bauen.py prüft alle drei Platzhalter per count()!=1 -> BauFehler; `startfehler_fuer_seite()` bildet je Sprache in texte.SPRACHEN genau titel/neu_laden; `</` wird zu `<\/`; test_platzhalter_* grün. Eine Sprache, die nicht im Ausschnitt steht, fällt auf die erste zurück (AC-3-Test).
  Status: CONFIRMED

Confirmation:
  AC: AC-7
  Code reference: engine/tests/test_texte.py:463
  Evidence: Diff an test_texte.py ändert nur `_quelltext` (liest ab dem ersten `<script>` bis zum letzten `</script>`, also zusätzlich den Fänger); Ausnahmelisten unverändert, Test grün -> Prüfung wird strenger, nicht schwächer. Schlüssel in de/en und Pseudo-Sprache (test_schluessel_in_jeder_sprache grün).
  Status: CONFIRMED

Confirmation:
  AC: AC-8
  Code reference: betrieb/startprobe.mjs:49
  Evidence: `p.locator("#startfehler").isVisible()` -> fehler.push("Startfehler-Meldung sichtbar") -> Exit 1; test_startprobe (Fehlerseite Exit 1, gesunde Seiten beider Beispielreisen Exit 0) grün. Die Endmarke löst keinen console.error aus, weil das Ereignis mit preventDefault abgefangen wird.
  Status: CONFIRMED

Confirmation:
  AC: AC-9
  Code reference: engine/vorlage.html:1318
  Evidence: Baustein im Kopfkommentar (Z. ~1318 Moleküle-Liste), Stilen (Z. 887-893), Bausteinseite (ansichtBausteine, Muster) und docs/design.md; test_design grün.
  Status: CONFIRMED

Confirmation:
  AC: AC-10
  Code reference: engine/bauen.py:1339
  Evidence: Relevante Browser-/Text-/Design-/Startreihenfolge-Tests 134 grün. Der Gesamtlauf (rund 7 Minuten mit -n 3) wurde hier nicht wiederholt; er ist Aufgabe des Lieferwegs (CI).
  Status: CONFIRMED

Angriffe: (a) Endmarke: Der Setter legt `Promise.reject()` an; unhandledrejection wird nach der HTML-Spezifikation in Reihenfolge der Ablehnung gemeldet, also zählen Ablehnungen vor der Marke, danach nicht (versprechenFertig). Der Handler ruft für die Endmarke preventDefault, daher kein Konsolenfehler (Startprobe bleibt grün, belegt durch test_startprobe an gesunden Seiten). (b) Setter zweimal: `if (!v || fertig) return` -> nur eine Endmarke. (c) `__startFertig = false` setzen ignoriert, Wert bleibt false. (d) Fehler in Fremdskripten nach dem Start: `error`-Hörer prüft fertig. (e) Syntaxfehler im Hauptskript: eigenes Skript, Fänger bereits registriert. (f) Defekt in melde() gefangen. Kein Bruch gefunden.
**Implementierer:** Abweichung vom Skizzen-Code (Setter + Endmarke) ist begründet: Ein im Start abgelehntes Versprechen meldet der Browser erst nach Skriptende.

### Runde 2
**Adversary:** Tiefere Randfälle. (1) Mehrere abgelehnte Versprechen vor der Marke: erstes zeigt Meldung, danach Wächter `getElementById("startfehler")` -> keine Dopplung. (2) Versprechen, die erst asynchron nach der Marke ablehnen (z. B. `async route()`, die auf Netz wartet): bleiben still; das entspricht der Spec („Start endet an der Marke“), ist aber eine Grenze (Known Limitation). (3) Ohne Meldungen-Rahmen: Rückfall `document.body.prepend`, `position:fixed` per Stil Z. 893. (4) Ressourcenfehler (Leaflet-Skript lädt nicht) bubbeln nicht zu window-error; Hauptskript scheitert dann selbst bei Zugriff auf L und löst error aus. (5) Pseudo-Sprache/RTL: logische Eigenschaften. (6) Nicht geprüft: WebKit/Firefox-Reihenfolge von unhandledrejection praktisch (Playwright hatte WebKit installiert, die vorhandenen Tests laufen nur Chromium); die Spezifikation schreibt die Reihenfolge vor, daher kein Befund, aber kein Beweis im Browser. Es wurde kein Produktionscode geändert.
Prozessfragen: AC-11 und AC-12 sind Prozess (Entwurf an den Product Owner, Infra-Issue). docs/briefings/fix-387-startfehler-meldung.md Z. 28 sagt, der Entwurf liege dem PO vor dem Bauen zur Zustimmung vor; ein Nachweis der Zustimmung oder des Infra-Issues ist im Worktree nicht ablesbar. Status: Prozess, offen bis Ausliefern. Kein Software-Defekt.
Docs: test-red-output.txt und docs/context/...md: Diff zeigt nur Pfadbereinigung (absolute Pfade -> relativ oder `~`, Benutzername des Rechners -> `<benutzer>`), keine Inhaltsverluste.
**Implementierer:** keine Einwände.

## Herkunft der Vorbedingungen

kein Sprachprofil konfiguriert (`precondition_origins.default_lang`)

## Verdict
**VERIFIED**
Code AC-1 bis AC-10 bewiesen; AC-11 und AC-12 (Prozess) im Nachtrag erledigt.
Tests: 134 passed, 0 failed, 0 übersprungen
Edge cases: geprüft, kein Bruch; Grenze: WebKit/Firefox-Reihenfolge nicht im Browser belegt
Regressions: None found
Checklist: 10/10 Code-Punkte bewiesen, 2 Prozesspunkte offen

Code reference: engine/bauen.py:1706
Code reference: engine/texte_de.py:381
Code reference: engine/texte_en.py:380
Code reference: engine/vorlage.html:1032
Code reference: betrieb/startprobe.mjs:49
Code reference: engine/tests/test_texte.py:463

## Geprüfte Dateien

- sha256:2de57931a80a7c9dd7c6eff79e96db26e093354fb3c4e75f2278d9c4f42818d9  betrieb/startprobe.mjs
- sha256:fb6aa304c92598e28e07672c460a985bb14d7948bb36d82be9b81d7ef36b1a9e  engine/bauen.py
- sha256:46c3af54c10b73a2c57e0b88b893083280fb24869aa154fe038b1bfefcb4928d  engine/tests/test_texte.py
- sha256:b5cb4e492391e374ac92222db457ca22c7fb7a0b2246f2767419353d196d2c5c  engine/texte_de.py
- sha256:ed5244ff23e74c5bd523c918822ba92bac003e7e811332f7b244e981b2437640  engine/texte_en.py
- sha256:b2ba88729d4871225b2f380f50873a0baf0b0b69530267565556b81c5f925bfc  engine/vorlage.html

## Prüfbasis

- base: d43415f940614982df528311307169fcb9e56619
- blob:19973df36c1e2ba46a1075bd6aef51d2fa3f4e04  betrieb/startprobe.mjs
- blob:839c9897cfc430609cf15a719e7fac0ce9b47d11  engine/bauen.py
- blob:7b35fb4a9d09b16263178b93293c5d368fd6144a  engine/tests/test_texte.py
- blob:269827b946494df6900566fd3c9cf302cc13f37c  engine/texte_de.py
- blob:49a10d120061ea46da1b6ca12e4f9eb9f3a8e45e  engine/texte_en.py
- blob:33198aaa321e874dabf4092fe0de6c6fdf0b4689  engine/vorlage.html

## Nachtrag Prozesspunkte
- AC-11: Der Product Owner hat am 10.11.2026 den Wortlaut aus der Spec ausdrücklich ohne Entwurf angenommen (Rückfrage per Auswahl).
- AC-12: Infra-Issue henemm/henemm-infra#393 besteht und ist in #387 verlinkt (Kommentar vom 10.11.2026). #387 bleibt bis zum laufenden Teil-Check und zur Abnahme offen.

## Geprüfte Dateien

- sha256:2de57931a80a7c9dd7c6eff79e96db26e093354fb3c4e75f2278d9c4f42818d9  betrieb/startprobe.mjs
- sha256:fb6aa304c92598e28e07672c460a985bb14d7948bb36d82be9b81d7ef36b1a9e  engine/bauen.py
- sha256:46c3af54c10b73a2c57e0b88b893083280fb24869aa154fe038b1bfefcb4928d  engine/tests/test_texte.py
- sha256:b5cb4e492391e374ac92222db457ca22c7fb7a0b2246f2767419353d196d2c5c  engine/texte_de.py
- sha256:ed5244ff23e74c5bd523c918822ba92bac003e7e811332f7b244e981b2437640  engine/texte_en.py
- sha256:b2ba88729d4871225b2f380f50873a0baf0b0b69530267565556b81c5f925bfc  engine/vorlage.html

## Prüfbasis

- base: d43415f940614982df528311307169fcb9e56619
- blob:19973df36c1e2ba46a1075bd6aef51d2fa3f4e04  betrieb/startprobe.mjs
- blob:839c9897cfc430609cf15a719e7fac0ce9b47d11  engine/bauen.py
- blob:7b35fb4a9d09b16263178b93293c5d368fd6144a  engine/tests/test_texte.py
- blob:269827b946494df6900566fd3c9cf302cc13f37c  engine/texte_de.py
- blob:49a10d120061ea46da1b6ca12e4f9eb9f3a8e45e  engine/texte_en.py
- blob:33198aaa321e874dabf4092fe0de6c6fdf0b4689  engine/vorlage.html

## Geprüfte Dateien

- sha256:2de57931a80a7c9dd7c6eff79e96db26e093354fb3c4e75f2278d9c4f42818d9  betrieb/startprobe.mjs
- sha256:fb6aa304c92598e28e07672c460a985bb14d7948bb36d82be9b81d7ef36b1a9e  engine/bauen.py
- sha256:46c3af54c10b73a2c57e0b88b893083280fb24869aa154fe038b1bfefcb4928d  engine/tests/test_texte.py
- sha256:b5cb4e492391e374ac92222db457ca22c7fb7a0b2246f2767419353d196d2c5c  engine/texte_de.py
- sha256:ed5244ff23e74c5bd523c918822ba92bac003e7e811332f7b244e981b2437640  engine/texte_en.py
- sha256:b2ba88729d4871225b2f380f50873a0baf0b0b69530267565556b81c5f925bfc  engine/vorlage.html

## Prüfbasis

- base: d43415f940614982df528311307169fcb9e56619
- blob:19973df36c1e2ba46a1075bd6aef51d2fa3f4e04  betrieb/startprobe.mjs
- blob:839c9897cfc430609cf15a719e7fac0ce9b47d11  engine/bauen.py
- blob:7b35fb4a9d09b16263178b93293c5d368fd6144a  engine/tests/test_texte.py
- blob:269827b946494df6900566fd3c9cf302cc13f37c  engine/texte_de.py
- blob:49a10d120061ea46da1b6ca12e4f9eb9f3a8e45e  engine/texte_en.py
- blob:33198aaa321e874dabf4092fe0de6c6fdf0b4689  engine/vorlage.html

## Geprüfte Dateien

- sha256:2de57931a80a7c9dd7c6eff79e96db26e093354fb3c4e75f2278d9c4f42818d9  betrieb/startprobe.mjs
- sha256:fb6aa304c92598e28e07672c460a985bb14d7948bb36d82be9b81d7ef36b1a9e  engine/bauen.py
- sha256:46c3af54c10b73a2c57e0b88b893083280fb24869aa154fe038b1bfefcb4928d  engine/tests/test_texte.py
- sha256:b5cb4e492391e374ac92222db457ca22c7fb7a0b2246f2767419353d196d2c5c  engine/texte_de.py
- sha256:ed5244ff23e74c5bd523c918822ba92bac003e7e811332f7b244e981b2437640  engine/texte_en.py
- sha256:b2ba88729d4871225b2f380f50873a0baf0b0b69530267565556b81c5f925bfc  engine/vorlage.html

## Prüfbasis

- base: d43415f940614982df528311307169fcb9e56619
- blob:19973df36c1e2ba46a1075bd6aef51d2fa3f4e04  betrieb/startprobe.mjs
- blob:839c9897cfc430609cf15a719e7fac0ce9b47d11  engine/bauen.py
- blob:7b35fb4a9d09b16263178b93293c5d368fd6144a  engine/tests/test_texte.py
- blob:269827b946494df6900566fd3c9cf302cc13f37c  engine/texte_de.py
- blob:49a10d120061ea46da1b6ca12e4f9eb9f3a8e45e  engine/texte_en.py
- blob:33198aaa321e874dabf4092fe0de6c6fdf0b4689  engine/vorlage.html
