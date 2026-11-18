// Renders every watch face in a page, saves a 2x screenshot of each, and prints the alignment audit.
const { chromium } = require("playwright");
const path = require("path");
const [, , file, prefix] = process.argv;
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1000, height: 900 }, deviceScaleFactor: 2 });
  p.on("pageerror", e => console.log("PAGE ERROR", e.message));
  await p.goto("file://" + path.resolve(file));
  await p.waitForFunction(() => window.AUDIT, null, { timeout: 15000 });
  await p.waitForTimeout(500);
  const audit = await p.evaluate(() => window.AUDIT);
  for (const [face, r] of Object.entries(audit)) {
    console.log(`== ${face}: ${r.issues.length ? r.issues.length + " issue(s)" : "no issues"}`);
    for (const i of r.issues) console.log("  - " + i);
    if (process.env.BOXES) console.log(JSON.stringify(r.boxes));
  }
  const w = await p.locator(".watch").all();
  for (let i = 0; i < w.length; i++) await w[i].screenshot({ path: `${prefix}${i + 1}.png` });
  await b.close();
})();
