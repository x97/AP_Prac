const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 2,
    isMobile: true,
    hasTouch: true,
    locale: 'zh-CN',
    timezoneId: 'Asia/Shanghai',
    colorScheme: 'light',
  });
  const page = await context.newPage();
  page.on('pageerror', e => console.log('PAGEERROR:', e.message));
  page.on('console', m => console.log('CONSOLE', m.type(), m.text().slice(0, 300)));
  await page.goto('http://localhost:3000/login?next=/dashboard', { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForTimeout(10000);
  console.log('next data?', await page.evaluate(() => !!window.__NEXT_DATA__));
  console.log('react root?', await page.evaluate(() => !!document.querySelector('#__next')));
  console.log('scripts', await page.evaluate(() => Array.from(document.scripts).map(s => s.src).filter(Boolean).slice(0, 5)));
  const input = page.locator('input[inputmode="tel"]');
  console.log('input disabled', await input.isDisabled());
  await input.fill('13900000002');
  await page.waitForTimeout(1000);
  const btn = page.getByRole('button', { name: /获取验证码/ });
  console.log('btn disabled', await btn.isDisabled());
  // Force a native input event after setting value via the native setter
  await input.evaluate((el) => {
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    setter.call(el, '13900000002');
    el.dispatchEvent(new Event('input', { bubbles: true }));
  });
  await page.waitForTimeout(1000);
  console.log('btn disabled after native event', await btn.isDisabled());
  await page.screenshot({ path: '/Users/aa/Documents/AP_psych/marketing/_raw/debug-login2.png' });
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
