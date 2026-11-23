# Mini-Spec: fix-638-fusslinie-dunkel

Issue #638. Rein gestalterisch, kein sichtbarer Text ändert sich.

## Was ändert sich
- Die Fußzelle der Anmeldecode-Mail (`engine/mailrahmen.py`, `code_mail`) trägt die Klasse `fr-fuss`.
- Der Dunkelmodus-Block `DUNKEL` enthält `.fr-fuss { border-top-color: #3d3a35 !important; }`, dieselbe Farbe wie der Kartenrand im Dunkelmodus.

## Was darf sich nicht ändern
- Heller Modus: Die Linie bleibt `border-top: 1px solid #e3ddd3` als Inline-Stil (Mailprogramme ohne Stilblock zeigen sie wie bisher).
- Kein Text, kein Schlüssel im Katalog, kein Textteil der Mail ändert sich; weiter keine externen Ressourcen.

## Manuelle Test-Schritte
1. Mail-HTML mit erfundenen Werten erzeugen und im Browser im Dunkelmodus öffnen: Linie über dem Fuß ist dunkel (#3d3a35), nicht hell.
2. Im hellen Modus: Linie unverändert hell (#e3ddd3).

## Inline-Test (wird während Implementierung geschrieben)
- [ ] `engine/tests/test_mailrahmen.py`: Die Zelle mit `border-top` trägt die Klasse `fr-fuss`, und der Dunkelblock enthält die Regel `.fr-fuss` mit `border-top-color: #3d3a35 !important`.

## Entwurf für den PO (#436)
- Vorschau als privates Claude-Artefakt mit erfundenen Daten: Mail im Dunkelmodus vorher/nachher.
