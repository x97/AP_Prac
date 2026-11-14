const { chromium } = require('playwright');
const path = require('path');

const BASE = 'http://localhost:3000';
const OUT = path.resolve(__dirname, '..', '_raw');

async function shot(page, name, opts = {}) {
  const file = path.join(OUT, name);
  await page.screenshot({ path: file, ...opts });
  console.log('shot', file);
}

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
  page.on('console', (msg) => {
    if (msg.type() === 'error') console.log('console-error:', msg.text());
  });

  await page.goto(`${BASE}/login?next=/dashboard`, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.locator('input[inputmode="tel"]').waitFor({ timeout: 60000 });
  await page.waitForFunction(() => {
    const el = document.querySelector('input[inputmode="tel"]');
    return el && Object.keys(el).some((k) => k.startsWith('__reactProps'));
  }, { timeout: 60000 });
  await page.locator('input[inputmode="tel"]').fill('13900000002');
  await page.waitForFunction(() => {
    const btn = [...document.querySelectorAll('button')].find((b) => b.textContent.includes('获取验证码'));
    return btn && !btn.disabled;
  }, { timeout: 30000 });
  await page.getByRole('button', { name: /获取验证码/ }).click();
  await page.locator('input[inputmode="numeric"]').waitFor({ timeout: 30000 });
  await page.locator('input[inputmode="numeric"]').fill('246810');
  await page.getByRole('button', { name: /^登录$/ }).click();
  await page.waitForURL('**/dashboard', { timeout: 60000 });
  await page.waitForLoadState('networkidle').catch(() => {});
  await shot(page, 'pilot-01-dashboard.png');

  await page.goto(`${BASE}/practice`, { waitUntil: 'domcontentloaded' });
  await page.locator('.unit-card').first().waitFor({ timeout: 60000 });
  await page.waitForLoadState('networkidle').catch(() => {});
  await shot(page, 'pilot-02-units.png');

  await page.locator('.unit-card').first().click();
  await page.waitForURL('**/practice/psychology-unit1-practice', { timeout: 60000 });
  await page.locator('.topic-row').first().waitFor({ timeout: 60000 });
  await page.waitForLoadState('networkidle').catch(() => {});
  await shot(page, 'pilot-03-topics.png');

  const row = page.locator('.topic-row').filter({ hasText: '1.1' }).first();
  await row.click();
  await page.waitForURL('**/practice/session/**', { timeout: 60000 });
  await page.locator('.option').first().waitFor({ timeout: 60000 });
  await page.waitForLoadState('networkidle').catch(() => {});
  await shot(page, 'pilot-04-question.png');

  // full page too, to inspect layout
  await shot(page, 'pilot-04-question-full.png', { fullPage: true });

  await browser.close();
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
