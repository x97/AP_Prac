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
  await page.goto('http://127.0.0.1:3000/login?next=/dashboard', { waitUntil: 'networkidle', timeout: 120000 }).catch(e => console.log('goto', e.message));
  await page.waitForTimeout(2000);
  const input = page.locator('input[inputmode="tel"]');
  console.log('input count', await input.count());
  console.log('disabled before', await input.isDisabled());
  await input.click();
  await input.fill('13900000002');
  await page.waitForTimeout(500);
  console.log('value', await input.inputValue());
  const btn = page.getByRole('button', { name: /获取验证码/ });
  console.log('btn count', await btn.count());
  console.log('btn disabled after fill', await btn.isDisabled());
  console.log('btn html', await btn.evaluate(el => el.outerHTML).catch(e => e.message));
  await page.screenshot({ path: '/Users/aa/Documents/AP_psych/marketing/_raw/debug-login.png' });
  // try typing
  await input.fill('');
  await input.pressSequentially('13900000002', { delay: 50 });
  await page.waitForTimeout(500);
  console.log('value2', await input.inputValue());
  console.log('btn disabled after type', await btn.isDisabled());
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
