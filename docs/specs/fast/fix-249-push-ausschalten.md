# Mini-Spec: fix-249-push-ausschalten

Issue #249: Nach „Auf diesem Gerät einschalten“ lädt Mein Konto neu, und „Auf diesem Gerät ausschalten“ steht genau
dort, wo eben der Knopf zum Einschalten war. Ein zweites Tippen schaltet sofort wieder aus.

Gewählt ist der erste Vorschlag aus dem Issue: Eingeschaltet zeigt der `pushSchalter` an seiner Stelle nur den Zustand;
das Ausschalten dieses Geräts wandert in die Einstellungen hinter „Konfigurieren“, neben „Auf allen Geräten
ausschalten“. Keine Sperrzeit und keine Rückfrage: Beides wäre mehr Bedienung, und die Stelle des Knopfs bliebe dieselbe.

## Was ändert sich

- `engine/anmeldung.py` (`push_karte`): In den aufgeklappten Einstellungen („Konfigurieren“) steht vor „Auf allen
  Geräten ausschalten“ ein leerer Platz `<div id="push-geraet-aus" hidden></div>`. Ohne Skript bleibt er leer und
  verborgen.
- `engine/app/konto.js` (`darstellen`): Eingeschaltet zeigt `#push-geraet` nur „Auf diesem Gerät eingeschaltet.“ (grün)
  und den Hinweis „Ausschalten unter ‚Konfigurieren‘.“ (klein); der neutrale Knopf „Auf diesem Gerät ausschalten“ kommt
  in `#push-geraet-aus`. Ausgeschaltet, gesperrt oder ohne Push bleibt `#push-geraet-aus` leer und verborgen.
- `engine/texte_de.py` (und die übrigen Sprachen im Katalog, falls der Texttest es verlangt): neuer Text
  `konto.push.geraet.aus_wo` „Ausschalten unter ‚Konfigurieren‘.“; `PUSH_GERAET_TEXTE` nimmt ihn auf.
- `docs/design.md`, Baustein `pushSchalter`: an: „Auf diesem Gerät eingeschaltet.“ in Grün mit dem Hinweis, wo man
  ausschaltet; der Knopf „Auf diesem Gerät ausschalten“ steht in den Einstellungen hinter „Konfigurieren“ vor „Auf allen
  Geräten ausschalten“ — nie an der Stelle des Einschaltknopfs (#249). Kopfkommentar in `engine/app/konto.js` und
  Docstring von `push_karte` gleichziehen.

## Was darf sich nicht ändern

- Einschalten, das stille Auffrischen beim Öffnen, `push_ab` und „Auf allen Geräten ausschalten“ wirken wie bisher.
- Nach dem Umschalten lädt die Seite neu und nennt das Ergebnis im grauen Kasten (`?push=an|aus#push`).
- Gesperrt, kein Browser-Push und die drei Schritte für iPhone/iPad bleiben unverändert.
- Ohne Skript bleibt die Seite bedienbar; kein Inline-Skript (CSP).

## Manuelle Test-Schritte

1. Auf dem Handy Mein Konto öffnen, „Auf diesem Gerät einschalten“ tippen, Erlaubnis geben.
2. Nach dem Neuladen an derselben Stelle noch einmal tippen: Es passiert nichts, dort steht nur „Auf diesem Gerät
   eingeschaltet.“ und der Hinweis.
3. „Konfigurieren“ aufklappen: „Auf diesem Gerät ausschalten“ steht vor „Auf allen Geräten ausschalten“; Tippen schaltet
   aus, die Seite meldet „Benachrichtigungen auf diesem Gerät ausgeschaltet.“ und zeigt wieder den Einschaltknopf.

## Inline-Test (wird während Implementierung geschrieben)

- [ ] `test_push.py`: Die Kontoseite hat den Platz `push-geraet-aus` in den Einstellungen („Konfigurieren“), vor dem
      Formular `push_aus`, und nicht im Platz `push-geraet`; die Texte für das Skript enthalten `aus_wo`.
- [ ] `test_push.py`: `engine/app/konto.js` hängt den Knopf zum Ausschalten in `push-geraet-aus`, nicht in
      `push-geraet` (Prüfung des Quelltexts, weil Push im Testbrowser nicht abonnierbar ist).
- [ ] Die Texttests (`test_texte.py`) bleiben grün.
