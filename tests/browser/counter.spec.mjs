import { chromium } from 'playwright';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const dist = fileURLToPath(new URL(process.env.DIST_DIR, import.meta.url));
const port = Number(process.env.PORT || '4178');

const browser = await chromium.launch();
const page = await browser.newPage();
const problems = [];
page.on('console', (msg) => {
  if (msg.type() === 'error' || msg.type() === 'warning') problems.push(msg.type() + ': ' + msg.text());
});
page.on('pageerror', (err) => problems.push('pageerror: ' + err.message));

await page.goto(`http://localhost:${port}/index.html`);

const step = process.env.STEP;
const readValue = () => page.locator('button.value').textContent();

if (step === 'mount' || !step) {
  const heading = await page.locator('h2').textContent();
  if (heading !== 'Lemon counter') throw new Error('B01 mount: heading was ' + heading);
  const value = await readValue();
  if (value !== 'Clicked 0 times') throw new Error('B01 mount: initial count ' + value);
}

if (step === 'click-once' || !step) {
  await page.reload();
  await page.click('button.value');
  const value = await readValue();
  if (value !== 'Clicked 1 times') throw new Error('B02 click-once: ' + value);
}

if (step === 'click-many' || !step) {
  await page.reload();
  await page.click('button.value');
  await page.click('button.value');
  await page.click('button.value');
  const value = await readValue();
  if (value !== 'Clicked 3 times') throw new Error('B03 click-many: ' + value);
  const hint = await page.locator('p.hint').textContent();
  if (hint !== 'now positive') throw new Error('B04/B05 nested update: ' + hint);
}

if (step === 'reload' || !step) {
  await page.reload();
  await page.click('button.value');
  await page.reload();
  const value = await readValue();
  if (value !== 'Clicked 0 times') throw new Error('B06 reload: ' + value);
  const heading = await page.locator('h2').textContent();
  if (heading !== 'Lemon counter') throw new Error('B06 reload heading: ' + heading);
}

if (problems.length) {
  throw new Error('B07 console problems:\n' + problems.join('\n'));
}

await browser.close();
console.log('browser checks ok');
