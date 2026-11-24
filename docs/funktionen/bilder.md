# Bilder und App-Symbol

Bilder machen eine Reiseseite lebendig: ein Titelbild für die Reise, ein Foto der Burg, die man am zweiten Tag besichtigt, die eigenen Fotos vom Weg. Frieda holt freie Bilder aus Wikimedia Commons, nimmt eigene Fotos an und hält bei jedem Bild fest, woher es stammt. Dazu bekommt jede Reise ein eigenes App-Symbol.

**Auf einen Blick:** Wo: Gespräch · Reiseseite · Mein Konto (Kachel) · Wer: Mitwirkende und Organisator:innen fügen hinzu, Titelbild und Symbol setzen Organisator:innen · Baustein: immer da

## Was du damit tun kannst

- Ein freies Bild aus Wikimedia Commons zur Reise oder zu einer Stelle hinzufügen lassen, etwa zu einem Ort, einer Etappe oder einer Unterkunft.
- Ein Bild als Titelbild der Reise wählen.
- Bildunterschrift und Alternativtext ändern, ein Bild einer anderen Stelle zuordnen.
- Ein Bild zurückziehen und später wiederherstellen.
- Eigene Fotos auf der Reiseseite hochladen oder über einen Link aus dem Gespräch, auch direkt vom Handy.
- Ein eigenes Foto endgültig entfernen.
- Ein App-Symbol für die Reise entwerfen lassen, das auf der Seite, auf dem Home-Bildschirm und in „Meine Reisen“ erscheint.

## So geht's

### Im Gespräch

> „Such ein schönes freies Bild von der Burg Hohnstein und häng es an den Aufenthalt am zweiten Tag.“

Claude sucht in Wikimedia Commons und gibt Frieda den Dateinamen (oder ein Wikidata-Objekt, dessen Bild dann genommen wird). Frieda holt das Bild selbst, legt es an und zeigt eine kleine Vorschau. Die Antwort nennt Urheber, Lizenz und mögliche Einschränkungen; Claude gibt das an dich weiter.

> „Nimm den Blick von der Brandaussicht als Titelbild statt der Schrammsteine.“

Das geht nur als Organisator:in; das neue Titelbild löst das bisherige ab.

> „Ich will meine Fotos vom Amselsee hochladen.“

Claude gibt dir einen Link. Er öffnet eine Seite, auf der du nur Fotos auswählst und hochlädst.

> „Entwirf ein Symbol für die Reise: ein Sandsteinfelsen in Grün.“

Claude entwirft das Symbol als Grafik und gibt es an Frieda. Ohne Angaben liefert `icon_set` das aktuelle Symbol samt Vorschau, damit Claude es weiterentwickeln kann.

| Werkzeug | wofür |
|---|---|
| `image_add` | Bild aus Wikimedia Commons hinzufügen: zu einer Stelle oder zur Reise, mit Bildunterschrift, Alternativtext, als Titelbild |
| `image_update` | Bildunterschrift, Alternativtext, Zuordnung, Titelbild ändern; zurückziehen oder wiederherstellen |
| `image_upload_link` | Link zum Hochladen eigener Fotos, für eine Stelle oder die ganze Reise |
| `icon_set` | App-Symbol der Reise lesen, setzen, ersetzen oder entfernen (Organisator:innen) |

### Auf der Reiseseite

- **Wo Bilder stehen:** Das Titelbild steht ganz oben im Reiseüberblick. Das erste Bild einer Stelle steht als Kopfbild an ihrer Heimat: am Ort über dem Namen, an der Etappe über den Kennzahlen, am Tag über der Tageszahl, an der Unterkunft oben in der Karte ihrer ersten Nacht. Weitere Bilder folgen als Bildreihe. Claude kann Bilder auch in Texte setzen.
- **Großansicht:** Ein Tipp auf ein Bild öffnet es groß; blättern mit Wischen, Pfeilen oder Pfeiltasten.
- **Nennung:** Unter jedem Bild stehen Urheber und Lizenz mit Link, bei eigenen Fotos „Foto: <Name>“.
- **Eigene Fotos:** Unter den Bildern einer Stelle steht „+ Foto hinzufügen“, auch wenn es noch keine Bilder gibt. Nach der Auswahl zeigt ein Blatt, wie viele Fotos zu welcher Stelle gehen, und einen Hinweis zu den Menschen auf den Fotos. Nicht angemeldet steht dort „Anmelden, um Fotos hinzuzufügen.“
- **Foto entfernen:** In der Großansicht eines eigenen Fotos, für die Person, die es hochgeladen hat, und für Organisator:innen. Vorher sagt Frieda genau, was wo entfernt wird und was bleibt.
- **Offline:** Die Seite speichert die kleinen Fassungen aller Bilder und die großen von Titel-, Kopf- und Textbildern; die übrigen großen lädt sie beim Ansehen.

### Auf Mein Konto

Jede Reise steht in „Meine Reisen“ als Kachel mit ihrem Titelbild. Ohne Titelbild zeigt die Kachel das App-Symbol der Reise auf einer ruhigen Fläche.

## Wer darf was

| Rolle | darf |
|---|---|
| Gast | Bilder sehen |
| Mitwirkende:r | Bilder hinzufügen, ändern, zurückziehen und wiederherstellen; eigene Fotos hochladen und wieder entfernen |
| Organisator:in | dazu Titelbild wählen, jedes eigene Foto entfernen, App-Symbol setzen |

## Regeln und Grenzen

- **Herkunft statt Prüfung:** Frieda prüft die Nutzungsrechte eines Commons-Bildes nicht und lehnt wegen der Lizenz nie ab. Sie nennt Urheber, Lizenz und Einschränkungen (etwa „nicht kommerziell“ oder keine Bearbeitung). Verantwortlich ist, wer das Bild hinzufügt. Bei eigenen Fotos gilt dasselbe.
- **Zurückziehen statt Löschen:** Ein Bild aus Commons erscheint nach dem Zurückziehen nirgends mehr, bleibt aber erhalten und lässt sich wiederherstellen. Jedes Bild hat eine feste Kennung, die nie neu vergeben wird.
- **Eigene Fotos sind wirklich löschbar:** „Foto entfernen“ nimmt das Foto sofort aus Seite, Verlauf, Export und Speicher. Im Verlauf bleibt nur „Foto entfernt am <Datum> von <Name>“. In Sicherungen bleibt es noch höchstens 30 Tage. Kopien, die andere schon geladen oder offline gespeichert haben, kann Frieda nicht zurückholen.
- **Datenschutz beim Hochladen:** Frieda speichert nie das Original, sondern zwei verkleinerte Fassungen ohne Standort und Kameradaten. Die Reiseseite kann jede Person lesen, die ihren Link kennt; lade nur Fotos hoch, mit denen die Abgebildeten einverstanden sind.
- **Formate und Grenzen:** JPEG, PNG, WebP und HEIC, höchstens 12 MB je Foto. Je Reise höchstens 60 Bilder und 150 MB; die Reise kann das ändern.
- **Link aus dem Gespräch:** gilt 30 Minuten und für höchstens 10 Fotos, nur für dich und diese Reise. Die Seite dahinter kann nur hochladen, nichts zeigen oder löschen. Abgelaufen: Claude um einen neuen bitten.
- **Titelbild:** Es gibt höchstens eines je Reise; ein neues löst das bisherige ab.
- **App-Symbol:** quadratisch, als SVG oder als PNG mit mindestens 512 Pixeln, höchstens 40 KB. Frieda prüft eine SVG-Grafik vor dem Speichern und lehnt Skripte, Links und Verweise nach außen ab. Das alte Symbol bleibt im Verlauf. Ohne eigenes Symbol entsteht eines aus dem Kurznamen der Reise. Ob die Claude-App das Symbol beim Konnektor anzeigt, entscheidet die App.
- **Status:** Bilder hinzufügen und ändern geht auch im Status „danach“, im Archiv nicht mehr.

## Siehe auch

- [Reiseseite](reiseseite.md), [Planen im Gespräch](gespraech.md), [Konto](konto.md), [Reisemodell](reisemodell.md)
- Referenz: [Bilder im Modell](../ontologie.md#bilder-eine-eigenschaft-der-grundformen-455-stufe-1), [Konnektor: Symbol](../konnektor.md#symbol), [Eigene Fotos im Betrieb](../betrieb.md#eigene-fotos-582), [Datenschutz je Instanz](../betrieb.md#datenschutz-je-instanz-15), [ADR-0001: Der Kern](../adr/0001-kern.md)
