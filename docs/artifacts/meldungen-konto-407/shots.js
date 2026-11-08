const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const dir = process.argv[2];
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 2300, height: 1400 }, deviceScaleFactor: 2 });
  await p.goto('file://' + path.resolve(dir, 'mockup.html'));
  for (const id of ['ist', 'soll-neu', 'soll-gelesen', 'soll-viele', 'soll-dunkel']) {
    await p.locator('#' + id + ' .rahmen').screenshot({ path: path.join(dir, id + '.png') });
  }
  await b.close();
})();
