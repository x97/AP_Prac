const { chromium } = require('playwright');

async function test(label, contextOptions) {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext(contextOptions);
  const page = await context.newPage();
  const failures = [];
  const errors = [];
  page.on('requestfailed', r => failures.push(`${r.method()} ${r.url()} ${r.failure()?.errorText}`));
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push('console:' + m.text().slice(0, 200)); });
  await page.goto('http://localhost:3000/login?next=/dashboard', { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForTimeout(6000);
  const input = page.locator('input[inputmode="tel"]');
  await input.fill('13900000002');
  await page.waitForTimeout(1000);
  const btn = page.getByRole('button', { name: /获取验证码/ });
  const disabled = await btn.isDisabled();
  const nextF = await page.evaluate(() => (self.__next_f ? self.__next_f.length : -1));
  console.log(`\n=== ${label} ===`);
  console.log('disabled', disabled, 'nextF', nextF);
  console.log('failures', failures.slice(0, 8));
  console.log('errors', errors.slice(0, 8));
  await page.screenshot({ path: `/Users/aa/Documents/AP_psych/marketing/_raw/debug-${label}.png` });
  await browser.close();
}

(async () => {
  await test('desktop', { viewport: { width: 1280, height: 900 }, locale: 'zh-CN', colorScheme: 'light' });
  await test('mobile', { viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true, locale: 'zh-CN', colorScheme: 'light' });
})().catch(e => { console.error(e); process.exit(1); });
