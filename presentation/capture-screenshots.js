const puppeteer = require('/opt/homebrew/Cellar/marp-cli/4.3.1/libexec/lib/node_modules/@marp-team/marp-cli/node_modules/puppeteer-core');
const path = require('path');
const fs = require('fs/promises');

const APP_URL = 'http://localhost:5173/';
const OUT_DIR = path.join(__dirname, 'images');
const CHROME_PATH = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

async function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function saveSectionShot(page, selector, outputName) {
  const el = await page.waitForSelector(selector, { visible: true, timeout: 15000 });
  await el.screenshot({
    path: path.join(OUT_DIR, outputName),
    type: 'png',
  });
}

async function clickTab(page, label) {
  await page.locator(`button::-p-text(${label})`).click();
  await wait(600);
}

async function main() {
  await fs.mkdir(OUT_DIR, { recursive: true });

  const browser = await puppeteer.launch({
    headless: true,
    executablePath: CHROME_PATH,
    args: ['--no-sandbox', '--disable-gpu'],
  });

  const page = await browser.newPage();
  page.on('console', (msg) => console.log('browser:', msg.type(), msg.text()));
  page.on('pageerror', (err) => console.log('pageerror:', err.message));
  await page.setViewport({ width: 1600, height: 1800, deviceScaleFactor: 2 });

  try {
    await page.goto(APP_URL, { waitUntil: 'networkidle2', timeout: 30000 });
    await page.waitForSelector('h1', { timeout: 15000 });

    // Run tab: show batch matrix selection.
    await page.locator('label::-p-text(Batch Mode)').click();
    await wait(500);
    await saveSectionShot(page, '.dash-section', 'run-tab-batch.png');

    // Results tab: select a couple of experiments so the compare bar is visible.
    await clickTab(page, 'Results');
    await page.waitForSelector('table.data-table.sortable tbody tr', { visible: true, timeout: 15000 });
    const resultChecks = await page.$$('table.data-table.sortable tbody input[type="checkbox"]');
    if (resultChecks.length < 2) throw new Error('Need at least two experiment rows for results screenshot.');
    await resultChecks[0].click();
    await resultChecks[1].click();
    await wait(500);
    await saveSectionShot(page, '.dash-section', 'results-tab-compare.png');

    // Compare tab: open compare view from selected rows.
    await page.locator('button::-p-text(Compare Selected)').click();
    await page.waitForSelector('h3', { visible: true, timeout: 15000 });
    await page.waitForFunction(
      () => document.body.innerText.includes('Metrics Comparison'),
      { timeout: 15000 }
    );
    await wait(1200);
    await saveSectionShot(page, '.dash-section', 'compare-tab-metrics.png');
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
