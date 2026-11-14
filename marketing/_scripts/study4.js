const { chromium } = require('playwright');
const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const BASE = 'http://localhost:3000';
const API = 'http://localhost:8000/api/v1';
const DB = '/Users/aa/Documents/AP_psych/data/releases/active/exam.db';
const RAW = '/Users/aa/Documents/AP_psych/marketing/_raw';

function sessionCookie() {
  const text = fs.readFileSync('/tmp/ap_cookies.txt', 'utf8');
  return text.split('\n').find((l) => l.includes('\tap_session\t')).split('\t').pop();
}
async function api(pathname, options = {}) {
  const res = await fetch(`${API}${pathname}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', Cookie: `ap_session=${sessionCookie()}`, ...(options.headers || {}) },
  });
  if (!res.ok) throw new Error(`${pathname} -> ${res.status}: ${await res.text()}`);
  return res.json();
}
function correctLabel(qid) {
  return execFileSync('sqlite3', [DB, `select label from options where question_id='${qid}' and is_correct=1 limit 1;`], { encoding: 'utf8' }).trim();
}
async function hideChrome(page) {
  await page.addStyleTag({ content: 'nextjs-portal{display:none!important}.tabbar{display:none!important}body{overflow-x:hidden!important}' }).catch(() => {});
}
async function hideSources(page) {
  await page.evaluate(() => {
    const bad = /AP Classroom|Barron|College Board|psychology-cb|barrons|AP Psychology Premium/i;
    document.querySelectorAll('div, span, a, p').forEach((el) => {
      if (el.children.length === 0 && bad.test(el.textContent || '')) el.style.display = 'none';
    });
    document.querySelectorAll('.font-mono').forEach((el) => {
      if (/psychology-|barrons/i.test(el.textContent || '')) el.style.display = 'none';
    });
  });
}
async function save(page, selector, name) {
  const el = page.locator(selector).first();
  await el.scrollIntoViewIfNeeded();
  await page.waitForTimeout(200);
  const file = path.join(RAW, name);
  await el.screenshot({ path: file });
  console.log('shot', file);
}
async function pageShot(page, name, viewport) {
  if (viewport) await page.setViewportSize(viewport);
  await page.waitForTimeout(500);
  const file = path.join(RAW, name);
  await page.screenshot({ path: file });
  console.log('shot', file);
}
async function answer(page, label) {
  const option = page.locator('.option').filter({ has: page.locator('.option-letter', { hasText: new RegExp(`^${label}$`) }) }).first();
  await option.click();
  await page.locator('.feedback').first().waitFor({ state: 'visible', timeout: 20000 });
}
async function nextQuestion(page, expected) {
  const next = page.getByRole('button', { name: /^Next/ }).first();
  if (await next.count()) await next.click();
  await page.waitForFunction((n) => [...document.querySelectorAll('.pill.pill-primary.font-mono')].some((el) => el.textContent.trim() === `Question ${n}`), expected, { timeout: 20000 });
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
  await context.addCookies([{ name: 'ap_session', value: sessionCookie(), domain: 'localhost', path: '/', httpOnly: true }]);
  const page = await context.newPage();

  // Fresh 1.2 session at mobile width
  const s12 = await api('/practice-sessions', {
    method: 'POST',
    body: JSON.stringify({ source: 'topic', group_id: 'psychology-unit1-practice', topic_id: 'psychology-unit1-practice:1.2', restart: true }),
  });
  const labels12 = s12.questions.map((q) => correctLabel(q.question_id));
  const wrong12 = new Set([3, 6, 8]);
  const plan12 = s12.questions.slice(0, 10).map((q, i) => {
    if (!wrong12.has(i)) return labels12[i];
    return ['A', 'B', 'C', 'D'].find((l) => l !== labels12[i]);
  });
  await page.goto(`${BASE}/practice/session/${s12.session.id}`, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.locator('.option').first().waitFor({ timeout: 60000 });
  await hideChrome(page);
  for (let i = 0; i < plan12.length; i += 1) {
    await answer(page, plan12[i]);
    if (i === 1) {
      await hideSources(page);
      await save(page, '.practice-layout > div > .card.card-pad', 'u12-q1-390.png');
      await save(page, '.rail-card.card', 'u12-q1-rail-390.png');
    }
    if (i === 4) {
      await hideSources(page);
      await save(page, '.practice-layout > div > .card.card-pad', 'u12-q4-390.png');
    }
    if (i < plan12.length - 1) await nextQuestion(page, i + 2);
  }

  // Topics after both sessions
  await page.goto(`${BASE}/practice/psychology-unit1-practice`, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.locator('.topic-row').first().waitFor({ timeout: 60000 });
  await hideChrome(page);
  await pageShot(page, 'topics-after-both-768.png', { width: 768, height: 1024 });
  await hideChrome(page);
  await pageShot(page, 'topics-after-both-390.png', { width: 390, height: 844 });

  // Dashboard
  await page.goto(`${BASE}/dashboard`, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForTimeout(1500);
  await hideChrome(page);
  await pageShot(page, 'dashboard-clean-768.png', { width: 768, height: 1024 });

  await browser.close();
  console.log('done');
})().catch((err) => { console.error(err); process.exit(1); });
