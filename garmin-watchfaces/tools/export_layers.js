// Exports everything the watch build and the alignment checks need from mockups/final-faces.html:
//   <face>/resources/drawables/<face>_base.png   static art, 390×390, drawn first by the watch
//   common/resources/drawables/*.png + sprites.xml  icon sprites with transparency
//   mockups/reference/<face>-<state>.png|.json      reference renders + audited element boxes
//   mockups/reference/text-widths.json              curved-label lengths (checks the glyph atlases)
//   mockups/states.json                             the six reference states (fixtures source)
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const PAGE = "file://" + path.join(ROOT, "mockups", "final-faces.html");
const FACES = ["dayring", "halo"];

async function open(browser, query) {
  const page = await browser.newPage({ viewport: { width: 390, height: 390 }, deviceScaleFactor: 1 });
  page.on("pageerror", e => { throw new Error(`page error (${query}): ${e.message}`); });
  await page.goto(`${PAGE}?${query}`);
  await page.evaluate(() => document.fonts.ready);
  await page.waitForFunction(() => window.AUDIT !== null && window.AUDIT !== undefined, null, { timeout: 30000 });
  return page;
}

(async () => {
  const browser = await chromium.launch();
  const refDir = path.join(ROOT, "mockups", "reference");
  const sprDir = path.join(ROOT, "common", "resources", "drawables");
  fs.mkdirSync(refDir, { recursive: true });
  fs.mkdirSync(sprDir, { recursive: true });

  // states + reference renders
  let states = null, widths = {};
  for (const face of FACES) {
    const first = await open(browser, `face=${face}&state=reference`);
    states = states || await first.evaluate(() => window.STATES);
    await first.close();
    for (const st of states) {
      const page = await open(browser, `face=${face}&state=${st.name}`);
      const audit = await page.evaluate(k => window.AUDIT[k], `${face}-${st.name}`);
      if (st.name === "reference") Object.assign(widths, await page.evaluate(() => window.TEXT_WIDTHS));
      await page.locator("#face").screenshot({ path: path.join(refDir, `${face}-${st.name}.png`) });
      fs.writeFileSync(path.join(refDir, `${face}-${st.name}.json`), JSON.stringify(audit, null, 1));
      await page.close();
    }
    // static base layer
    const base = await open(browser, `face=${face}&state=reference&layer=base`);
    const dir = path.join(ROOT, face, "resources", "drawables");
    fs.mkdirSync(dir, { recursive: true });
    await base.locator("#face").screenshot({ path: path.join(dir, `${face}_base.png`) });
    await base.close();
  }
  fs.writeFileSync(path.join(ROOT, "mockups", "states.json"), JSON.stringify(states, null, 1));
  fs.writeFileSync(path.join(refDir, "text-widths.json"), JSON.stringify(widths, null, 1));

  // sprites
  const sp = await open(browser, "sprites=1");
  const names = await sp.evaluate(() => [...document.querySelectorAll("[data-sprite]")].map(e => e.dataset.sprite));
  for (const n of names) {
    await sp.locator(`[data-sprite="${n}"]`).screenshot({ path: path.join(sprDir, `${n}.png`), omitBackground: true });
  }
  await sp.close();
  const rows = names.map(n => `    <bitmap id="${n}" filename="${n}.png"/>`).join("\n");
  fs.writeFileSync(path.join(sprDir, "sprites.xml"), `<drawables>\n${rows}\n</drawables>\n`);

  await browser.close();
  console.log(`exported ${states.length} states × ${FACES.length} faces, ${names.length} sprites`);
})().catch(e => { console.error(e); process.exit(1); });
