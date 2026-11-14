const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

function sessionCookie() {
  const text = fs.readFileSync('/tmp/ap_cookies.txt', 'utf8');
  const line = text.split('\n').find((l) => l.includes('\tap_session\t'));
  if (!line) throw new Error('no ap_session cookie');
  const parts = line.split('\t');
  return parts[parts.length - 1];
}

async function snap(width, height, label) {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width, height },
    deviceScaleFactor: 2,
    isMobile: true,
    hasTouch: true,
    locale: 'zh-CN',
    timezoneId: 'Asia/Shanghai',
    colorScheme: 'light',
  });
  await context.addCookies([
    { name: 'ap_session', value: sessionCookie(), domain: 'localhost', path: '/', httpOnly: true },
  ]);
  const page = await context.newPage();
  await page.addStyleTag({ content: 'nextjs-portal{display:none!important} body{padding-bottom:96px!important}' }).catch(() => {});
  for (const [url, name] of [
    ['/practice/psychology-unit1-practice', 'topics'],
    ['/dashboard', 'dashboard'],
    ['/practice', 'units'],
  ]) {
    await page.goto(`http://localhost:3000${url}`, { waitUntil: 'domcontentloaded', timeout: 120000 });
    await page.waitForTimeout(2500);
    await page.addStyleTag({ content: 'nextjs-portal{display:none!important} body{padding-bottom:96px!important}' }).catch(() => {});
    const file = path.join('/Users/aa/Documents/AP_psych/marketing/_raw', `layout-${label}-${name}.png`);
    await page.screenshot({ path: file });
    console.log(file);
  }
  await browser.close();
}

(async () => {
  await snap(430, 932, '430');
  await snap(480, 1040, '480');
  await snap(768, 1024, '768');
})().catch((e) => { console.error(e); process.exit(1); });
