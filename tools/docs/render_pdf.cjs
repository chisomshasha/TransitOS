#!/usr/bin/env node
/**
 * render_pdf.cjs — minimal Playwright HTML→PDF renderer for the TransitOS
 * client handover guide.
 *
 * Why this exists instead of the shared `render_html.cjs`:
 * Playwright's `page.pdf()` defaults `linkAnnotations` to **false**, which
 * silently drops every internal `#anchor` — i.e. the table of contents stops
 * being clickable in the finished PDF. This renderer turns link annotations
 * on and exposes the page geometry the guide needs.
 *
 * Usage:
 *   node render_pdf.cjs --in page.html --out guide.pdf
 *                      [--format A4|Letter]
 *                      [--margin "18mm 14mm 15mm 14mm"]
 *                      [--header header.html]
 *                      [--wait 1200] [--scale 1]
 */

'use strict';

const path = require('path');
const fs = require('fs');
const { execSync } = require('child_process');

function usage(msg) {
  if (msg) console.error(msg);
  console.error(
    'Usage: node render_pdf.cjs --in page.html --out out.pdf\n' +
      '       [--format A4|Letter] [--margin "18mm 14mm 15mm 14mm"]\n' +
      '       [--header header.html] [--wait 1200] [--scale 1]',
  );
  process.exit(1);
}

const args = process.argv.slice(2);
let input = null;
let outFile = null;
let waitMs = 1200;
let format = 'A4';
let margin = '18mm 14mm 15mm 14mm';
let scale = 1;
let headerFile = null;

for (let i = 0; i < args.length; i++) {
  const a = args[i];
  if (a === '--in' || a === '--input') { i++; input = args[i]; }
  else if (a === '--out' || a === '--output') { i++; outFile = args[i]; }
  else if (a === '--wait') { i++; waitMs = parseInt(args[i], 10); }
  else if (a === '--format') { i++; format = args[i]; }
  else if (a === '--margin') { i++; margin = args[i]; }
  else if (a === '--scale') { i++; scale = parseFloat(args[i]); }
  else if (a === '--header') { i++; headerFile = args[i]; }
  else if (a === '-h' || a === '--help') usage();
}

if (!input || !outFile) usage('error: --in and --out are required');

if (!fs.existsSync(input)) {
  console.error(JSON.stringify({ status: 'error', error: `File not found: ${input}` }));
  process.exit(1);
}
const pageUrl = 'file://' + path.resolve(input);

function parseMargin(css) {
  const parts = css.trim().split(/\s+/);
  const [t, r, b, l] = (() => {
    if (parts.length === 1) return [parts[0], parts[0], parts[0], parts[0]];
    if (parts.length === 2) return [parts[0], parts[1], parts[0], parts[1]];
    if (parts.length === 3) return [parts[0], parts[1], parts[2], parts[1]];
    return [parts[0], parts[1], parts[2], parts[3]];
  })();
  return { top: t, right: r, bottom: b, left: l };
}

function loadPlaywright() {
  try {
    return require('playwright');
  } catch (_) {}
  try {
    const root = execSync('npm root -g', { stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim();
    return require(path.join(root, 'playwright'));
  } catch (_) {}
  console.error(
    JSON.stringify({
      status: 'error',
      error: 'playwright not found',
      hint: 'npm install -g playwright && npx playwright install chromium',
    }),
  );
  process.exit(2);
}

(async () => {
  const { chromium } = loadPlaywright();
  let browser;
  try {
    browser = await chromium.launch();
  } catch (_) {
    const { spawnSync } = require('child_process');
    const r = spawnSync('npx', ['playwright', 'install', 'chromium'], { stdio: 'inherit', shell: true });
    if (r.status !== 0) {
      console.error(JSON.stringify({ status: 'error', error: 'Chromium install failed' }));
      process.exit(3);
    }
    browser = await chromium.launch();
  }

  try {
    const page = await browser.newPage();
    page.setDefaultTimeout(60_000);
    page.setDefaultNavigationTimeout(60_000);

    await page.goto(pageUrl, { waitUntil: 'networkidle', timeout: 60_000 });

    try {
      await page.waitForFunction(() => document.fonts && document.fonts.ready, { timeout: 15_000 });
      await page.evaluate(() => document.fonts.ready);
    } catch (_) {
      /* no webfonts in this document — safe to ignore */
    }

    if (waitMs > 0) await page.waitForTimeout(waitMs);

    const pdfOpts = {
      path: outFile,
      format,
      printBackground: true,
      scale,
      margin: parseMargin(margin),
      linkAnnotations: true, // ← the whole reason this renderer exists
      preferCSSPageSize: false,
    };

    if (headerFile) {
      pdfOpts.displayHeaderFooter = true;
      pdfOpts.headerTemplate = fs.readFileSync(headerFile, 'utf8');
    }

    await page.pdf(pdfOpts);
    await browser.close();

    const size = fs.statSync(outFile).size;
    if (size < 5000) {
      console.error(
        JSON.stringify({
          status: 'error',
          error: 'Output PDF is suspiciously small — page may be blank',
          hint: 'Open the source HTML in a browser and check for render errors',
        }),
      );
      process.exit(3);
    }
    console.log(JSON.stringify({ status: 'ok', out: outFile, bytes: size }));
  } catch (err) {
    console.error(JSON.stringify({ status: 'error', error: String(err && err.stack ? err.stack : err) }));
    process.exit(3);
  }
})();
