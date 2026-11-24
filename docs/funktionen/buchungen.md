# Buchungen und Belege

Eine Buchung ist in Frieda ein eigenes Ding: die Tatsache, dass eine Unterkunft, ein Aufenthalt oder eine Strecke angefragt, gebucht oder storniert ist, mit Nummer, Anbieter, Preis, Zahlstand, Fristen und Stornoregel. Die Bestätigung hängt als Beleg daran. So steht unterwegs alles, was man an der Rezeption oder im Zug braucht, an einer Stelle, auch ohne Netz.

**Auf einen Blick:** Wo: Gespräch · Reiseseite · Wer: alle lesen; Mitwirkende tragen ihre Buchungen ein; Organisator:innen ändern alle · Baustein: immer da (Erinnerungen an Fristen mit dem Baustein `waechter`)

## Was du damit tun kannst

- Eine Buchung festhalten, sobald sie angefragt oder bestätigt ist, für ein Ding oder mehrere (Hin- und Rückfahrt in einer Buchung).
- Nummer, Anbieter, Preis und Zahlstand eintragen: offen, angezahlt, bezahlt, vor Ort, inklusive oder erstattet.
- Zeitraum, Check-in ab und Check-out bis angeben und was vor Ort noch zu zahlen ist, etwa die Kurtaxe.
- Fristen festhalten (bis wann etwas zu tun ist, etwa „Ticket in die App laden“), ab wann etwas geht (etwa der Online-Check-in) und bis wann man kostenlos stornieren kann.
- Je Reisender:m Angaben wie Sitzplatz, Gepäck oder Vielfliegernummer eintragen.
- Die Buchungsbestätigung als Beleg anhängen, als Datei oder als Abschrift aus der Mail.
- Unterwegs die Check-in-Ansicht nutzen und die Buchungsnummer mit einem Tipp kopieren.
- Rechtzeitig an Fristen, Stornofristen und offene Zahlungen erinnert werden.

## So geht's

### Angebot und Buchung

Frieda trennt, was für jeden Kandidaten gilt, von dem, was erst durch das Buchen entsteht. Zum **Angebot** gehören die Merkmale der Art, etwa „Preis pro Nacht laut Website“ oder „Frühstück“. Zur **Buchung** gehören der tatsächlich bezahlte Preis, der Zahlstand, die Nummer, die Stornoregel und die Reisenden. Was eine Buchung darüber hinaus tragen soll, legt die Reise je Art fest: In der Beispielreise hat jede Bahnbuchung eine „Ticketart“ (Sparpreis, Flexpreis, Verbundticket).

Ob ein Ding überhaupt gebucht wird, sagt seine Art: Unterkünfte und Aufenthalte sind von sich aus buchbar, Strecken nur, wenn die Reise ihre Art so festlegt (im Malerweg etwa die Bahn).

### Beispiele aus den Beispielreisen

- **Hotel am Elbufer** (Malerweg): gebucht direkt beim Hotel, Nummer HE-2027-0415, angezahlt, Check-in ab 15:00, Check-out bis 11:00, vor Ort noch 90 € Rest und 3 € Kurtaxe, kostenlos stornieren bis zum 11.5.2027.
- **S-Bahn Dresden → Stadt Wehlen** (Malerweg): von Karl gebucht, Sparpreis, bezahlt, Frist „Ticket in die App laden“ am Reisetag.
- Eine ältere Buchung desselben Hotels ist **storniert**, mit dem Grund „Zimmer doppelt gebucht“ und erstatteter Anzahlung. Sie bleibt erhalten, zählt aber nicht.
- **Hin- und Rückfahrt** (Stadtwochenende): eine Buchung für beide Fahrten, mit Angaben je Fahrt; an jeder Fahrt steht nur ihr eigener Komfort-Check-in.

### Im Gespräch

> „Ich habe das Hotel am Elbufer gebucht, hier ist die Bestätigung.“

Frieda liest Nummer, Preis, Zeitraum, Stornoregel und Zahlstand aus der Bestätigung, lässt kurz bestätigen und legt die Buchung mit dem Beleg in einem Schritt an. Die Herkunft („Buchungsbestätigung per Mail vom …“) ist Pflicht.

> „Was ist bei unseren Buchungen als Nächstes fällig?“

Frieda nennt die nächsten Fristen aus dem Überblick.

> „Die Buchung in Hohnstein hat sich erledigt.“

Frieda storniert die Buchung mit Grund und sagt danach, dass nichts gelöscht ist und wie man sie zurückholt.

| Werkzeug | wofür |
|---|---|
| `booking_create` | Buchung anlegen, auf Wunsch gleich mit Beleg |
| `booking_update` | Buchung ändern, stornieren oder zurückholen, mit Verlaufseintrag |
| `receipt_add` | Beleg nachträglich anhängen (Datei oder Abschrift) |
| `show` | eine Buchung mit allen Angaben und Belegen |
| `overview` | Zahl der Buchungen und die nächsten Fristen |
| `attribute_define` | Merkmale festlegen, die Buchungen einer Art tragen |

### Auf der Reiseseite

Eine Buchung steht vollständig an ihrem ersten Ding: auf der Tagesseite bei der Unterkunft, beim Aufenthalt oder bei der Strecke. An jedem weiteren Ding steht nur eine kleine Marke mit Link dorthin.

Jedes buchbare Ding durchläuft dieselben Stufen, und die Seite folgt ihnen:

| Stand | Was die Seite zeigt |
|---|---|
| offen (noch zur Wahl) | den Vergleich der Möglichkeiten |
| entschieden, nicht gebucht | das Ding mit allem, was man zum Buchen braucht, unter „Einzelheiten“ |
| angefragt | dazu die Buchung mit Preis und Zahlung |
| gebucht | kompakt die **Check-in-Ansicht**: Nummer mit Kopier-Knopf, Check-in, Check-out, vor Ort zu zahlen, eine laufende Frist; Preis, Zahlung, Belege, Stornoregel und Verlauf in den „Einzelheiten zur Buchung“ |

**Ab wann etwas geht** (etwa der Online- oder Komfort-Check-in) steht bei einer Fahrt nicht im Buchungsblock, sondern in ihrem **Ablauf**, der Zeitleiste der Fahrt, mit dem Zusatz „aus der Buchung“ und der Marke „erinnert“ (#665, siehe [Reiseseite](reiseseite.md)). Der Buchungsblock einer Fahrt zeigt nur das Geschäftliche: Nummer, Stand, Preis, Zahlung, Reisende, Tarif, Beleg. Bei Unterkünften und Aufenthalten bleibt die Zeile, wie sie ist.

Nach der Buchung gilt die Buchung: Die Angaben aus der Planung (Preis laut Website, Zimmer) rücken zugeklappt unter „Aus der Planung“. Merkmale, die die Reise als „nach der Buchung sichtbar“ markiert, bleiben oben, etwa der Charakter des Hotels. Stornierte Buchungen stehen zusammen im zugeklappten Block „Storniert“.

Unter **„Zu tun · Zu buchen“** steht jedes buchbare Ding mit Datum und Stand, etwa „gebucht · Frist 13.5.“. Der Stand der Vorbereitung im Überblick zählt „Gebucht x von y“, und die Zeitachse zeigt an jeder Nacht „gebucht“ oder „nicht gebucht“. In der Kennzahl **Übernachtungen** zählt bei gebuchten Unterkünften der Preis der Buchung statt des Angebots.

**Belege:** Angemeldet hängst du mit „+ Beleg anhängen“ eine Datei an (PDF, JPEG, PNG, WebP oder HEIC, höchstens 10 MB). Je Beleg steht eine Zeile mit Name, Größe, wer ihn wann angehängt hat und wer ihn sehen darf. Die Liste bleibt auch ohne Netz sichtbar; die Datei selbst zu öffnen braucht Netz.

### Erinnerungen und Kalender

Ist der Baustein `waechter` an und die Reise im Status „fest“ oder „unterwegs“, erinnert Frieda die Person, die gebucht hat (sonst die Organisator:innen):

- an eine Frist, einige Tage vorher (Vorgabe 3 Tage), und bei Überfälligkeit alle 7 Tage wieder;
- an die Stornofrist, solange kostenloses Stornieren noch geht;
- an den Tag, ab dem etwas geht, etwa den Online-Check-in;
- an offene oder angezahlte Zahlungen, wenn die Reise das ausdrücklich einschaltet.

Fristen von Buchungen stehen außerdem im persönlichen Kalender ([Erinnerungen](erinnerungen.md)).

## Wer darf was

| Rolle | darf |
|---|---|
| Gast | Buchungen lesen, freigegebene Belege sehen (angemeldet) |
| Mitwirkende:r | Buchungen anlegen, eigene Buchungen ändern und stornieren, Belege anhängen, eigene Belege zurückziehen |
| Organisator:in | alle Buchungen ändern, Belege für alle freigeben, jeden Beleg zurückziehen |

Ein Beleg ist zunächst nur für die Person, die ihn angehängt hat, und für Organisator:innen sichtbar. Erst wenn eine Organisator:in ihn freigibt, sehen ihn alle angemeldeten Personen der Reise.

## Regeln und Grenzen

- Jede Buchung braucht eine Herkunft; Stornieren braucht einen Grund. Gelöscht wird nie: Eine stornierte Buchung holt man mit dem Status „gebucht“ zurück, ein zurückgezogener Beleg bleibt als Datei erhalten.
- Hat ein Ding mehrere Buchungen, gilt gebucht vor angefragt, dann die jüngste; stornierte gelten nie. Hat eine Unterkunft getrennte Aufenthalte, trägt jede Buchung ihren eigenen Zeitraum, und jede Nacht zeigt nur ihre Buchung.
- Kurzfelder wie Preis, Zahlungsweg oder Fristtext sind höchstens 60 Zeichen lang; Einzelheiten gehören in die Notiz. Eine Uhrzeit gehört ins Feld der Frist, nicht in ihren Text.
- Belege liegen in einer eigenen Ablage der Instanz, nicht in der Reise. Je Reise sind es höchstens 200 Dateien und 100 MB.
- Buchungen und Belege anlegen und ändern geht in den Status Idee bis Unterwegs; in der Nachlese und im Archiv nicht mehr.
- Frieda bucht nicht selbst und prüft nicht beim Anbieter nach. Sie hält fest, was die Reisenden gebucht haben, und erinnert an Fristen.

## Siehe auch

- [Alternativen und Entscheidungen](alternativen.md), [Reisemodell](reisemodell.md), [Erinnerungen](erinnerungen.md), [Reiseseite](reiseseite.md)
- [Reise-Ontologie](../ontologie.md) (Felder der Buchung, Angebot und Buchung), [Design](../design.md) (Stand-Leiter, Belege)
- [Wächter und Erinnerer](../waechter.md), [Konnektor](../konnektor.md) (`booking_create`, `receipt_add`)
