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
  await page.goto('http://127.0.0.1:3000/login?next=/dashboard', { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForTimeout(8000);
  const info = await page.evaluate(() => {
    const el = document.querySelector('input[inputmode="tel"]');
    const keys = Object.keys(el).filter(k => k.startsWith('__react'));
    const propsKey = keys.find(k => k.startsWith('__reactProps'));
    const props = propsKey ? el[propsKey] : null;
    return {
      keys,
      propKeys: props ? Object.keys(props) : null,
      hasOnChange: props ? typeof props.onChange : null,
      value: el.value,
    };
  });
  console.log(JSON.stringify(info, null, 2));
  // Call React onChange directly with a plausible event
  const result = await page.evaluate(() => {
    const el = document.querySelector('input[inputmode="tel"]');
    const propsKey = Object.keys(el).find(k => k.startsWith('__reactProps'));
    const props = el[propsKey];
    try {
      props.onChange({ target: { value: '13900000002' } });
      return 'called';
    } catch (e) {
      return 'error: ' + e.message;
    }
  });
  console.log('onChange direct:', result);
  await page.waitForTimeout(1000);
  const btn = page.getByRole('button', { name: /获取验证码/ });
  console.log('btn disabled after direct onChange', await btn.isDisabled());
  console.log('input value', await page.locator('input[inputmode="tel"]').inputValue());
  await page.screenshot({ path: '/Users/aa/Documents/AP_psych/marketing/_raw/debug-login3.png' });
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
