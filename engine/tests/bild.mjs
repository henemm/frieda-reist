// Vollseitenbild mit Wiederholung (#537): `Page.captureScreenshot` scheitert im CI-Runner gelegentlich bei sehr hohen Seiten.
// bild(page, optionen) ruft page.screenshot(optionen) bis zu dreimal auf, mit kurzer Pause zwischen den Versuchen.
// Ergebnis: true beim ersten Erfolg, false nach dem dritten Fehlversuch; wirft nie, damit das Messskript weiterläuft.
export async function bild(page, optionen, {versuche = 3, pause = 500} = {}) {
  for (let i = 1; i <= versuche; i++) {
    try {
      await page.screenshot(optionen);
      return true;
    } catch (e) {
      if (i < versuche) await new Promise(r => setTimeout(r, pause));
    }
  }
  return false;
}
