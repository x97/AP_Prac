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
async function newSession(groupId, topicId) {
  return api('/practice-sessions', { method: 'POST', body: JSON.stringify({ source: 'topic', group_id: groupId, topic_id: topicId, restart: true }) });
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
async function hideChrome(page) {
  await page.addStyleTag({ content: 'nextjs-portal{display:none!important}.tabbar{display:none!important}body{overflow-x:hidden!important}' }).catch(() => {});
}
async function hideSources(page) {
  await page.evaluate(() => {
    const bad = /AP Classroom|Barron|College Board|psychology-cb|barrons/i;
    document.querySelectorAll('div, span, a, p').forEach((el) => {
      if (el.children.length === 0 && bad.test(el.textContent || '')) {
        el.style.display = 'none';
      }
    });
    document.querySelectorAll('button').forEach((btn) => {
      if ((btn.textContent || '').includes('标记为已掌握') || (btn.textContent || '').includes('标记为未掌握')) {
        btn.parentElement.style.display = 'none';
      }
    });
  });
}
async function save(page, selector, name) {
  const el = page.locator(selector).first();
  await el.scrollIntoViewIfNeeded();
  await page.waitForTimeout(250);
  const file = path.join(RAW, name);
  await el.screenshot({ path: file });
  console.log('shot', file);
}
async function pageShot(page, name, viewport) {
  if (viewport) await page.setViewportSize(viewport);
  await page.waitForTimeout(600);
  const file = path.join(RAW, name);
  await page.screenshot({ path: file });
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
  await context.addCookies([{ name: 'ap_session', value: sessionCookie(), domain: 'localhost', path: '/', httpOnly: true }]);
  const page = await context.newPage();

  // Wrong book clean card + modal
  await page.goto(`${BASE}/wrong`, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.locator('h1').filter({ hasText: '错题本' }).first().waitFor({ state: 'visible', timeout: 60000 });
  await page.getByText('全部进行中').first().waitFor({ state: 'visible', timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(1200);
  await hideChrome(page);
  await hideSources(page);
  await save(page, '.wrong-card', 'wrong-card-clean.png');
  await pageShot(page, 'wrong-clean-768.png', { width: 768, height: 1024 });
  const openBtn = page.getByRole('button', { name: /查看题目、答案与解析/ }).first();
  if (await openBtn.count()) {
    await openBtn.click();
    await page.waitForTimeout(900);
    await hideSources(page);
    await pageShot(page, 'wrong-modal-768.png', { width: 768, height: 1024 });
    await save(page, '.modal-panel', 'wrong-modal-panel.png');
    await page.keyboard.press('Escape').catch(() => {});
    await page.waitForTimeout(300);
  }

  // Knowledge graph
  await page.goto(`${BASE}/knowledge`, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.locator('svg[role="img"]').first().waitFor({ state: 'visible', timeout: 60000 });
  await page.waitForTimeout(1500);
  await hideChrome(page);
  await pageShot(page, 'graph-unit-structure-768.png', { width: 768, height: 1024 });
  await pageShot(page, 'graph-unit-structure-1280.png', { width: 1280, height: 900 });
  await page.setViewportSize({ width: 1280, height: 900 });
  const topicBtn = page.locator('button').filter({ hasText: 'Interaction of Heredity' }).first();
  if (await topicBtn.count()) {
    await topicBtn.click();
    await page.waitForTimeout(1500);
    await pageShot(page, 'graph-mindmap-1280.png', { width: 1280, height: 900 });
    await pageShot(page, 'graph-mindmap-768.png', { width: 768, height: 1024 });
  } else {
    console.log('topic button not found');
  }

  // Flashcards
  await page.goto(`${BASE}/cards`, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.getByRole('button', { name: 'Already Know' }).first().waitFor({ timeout: 60000 });
  await page.selectOption('select[aria-label="按单元筛选"]', '1').catch(() => {});
  await page.waitForTimeout(1200);
  await page.setViewportSize({ width: 390, height: 844 });
  await hideChrome(page);
  await save(page, '.flashcard-wrap', 'cards-front.png');
  await page.locator('.flashcard').first().click();
  await page.waitForTimeout(500);
  await save(page, '.flashcard-wrap', 'cards-back.png');
  for (let i = 0; i < 10; i += 1) {
    const name = i < 7 ? 'Already Know' : 'Review Later';
    await page.getByRole('button', { name }).first().click();
    await page.waitForTimeout(700);
  }
  await page.waitForTimeout(800);
  await pageShot(page, 'cards-after-10-390.png', { width: 390, height: 844 });
  await pageShot(page, 'cards-after-10-768.png', { width: 768, height: 1024 });

  // Unit 1.2: 10 questions
  const s12 = await newSession('psychology-unit1-practice', 'psychology-unit1-practice:1.2');
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
      await save(page, '.practice-layout > div > .card.card-pad', 'u12-q1.png');
      await save(page, '.rail-card.card', 'u12-q1-rail.png');
    }
    if (i === 4) await save(page, '.practice-layout > div > .card.card-pad', 'u12-q4.png');
    if (i < plan12.length - 1) await nextQuestion(page, i + 2);
  }
  await pageShot(page, 'u12-inprogress-390.png', { width: 390, height: 844 });
  await page.goto(`${BASE}/practice/psychology-unit1-practice`, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.locator('.topic-row').first().waitFor({ timeout: 60000 });
  await pageShot(page, 'u12-topics-inprogress-768.png', { width: 768, height: 1024 });

  // Dashboard with data
  await page.goto(`${BASE}/dashboard`, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.waitForTimeout(1500);
  await hideChrome(page);
  await pageShot(page, 'dashboard-768.png', { width: 768, height: 1024 });

  await browser.close();
  console.log('done');
})().catch((err) => { console.error(err); process.exit(1); });
