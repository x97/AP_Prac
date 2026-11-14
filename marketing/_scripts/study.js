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
  const line = text.split('\n').find((l) => l.includes('\tap_session\t'));
  if (!line) throw new Error('no ap_session cookie');
  return line.split('\t').pop();
}

async function api(pathname, options = {}) {
  const res = await fetch(`${API}${pathname}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      Cookie: `ap_session=${sessionCookie()}`,
      ...(options.headers || {}),
    },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${options.method || 'GET'} ${pathname} -> ${res.status}: ${text}`);
  }
  return res.json();
}

function correctLabel(questionId) {
  const out = execFileSync(
    'sqlite3',
    [DB, `select label from options where question_id='${questionId}' and is_correct=1 limit 1;`],
    { encoding: 'utf8' },
  ).trim();
  if (!out) throw new Error(`no correct label for ${questionId}`);
  return out;
}

async function newSession(groupId, topicId) {
  return api('/practice-sessions', {
    method: 'POST',
    body: JSON.stringify({ source: 'topic', group_id: groupId, topic_id: topicId, restart: true }),
  });
}

async function answer(page, label) {
  const option = page
    .locator('.option')
    .filter({ has: page.locator('.option-letter', { hasText: new RegExp(`^${label}$`) }) })
    .first();
  await option.click();
  await page.locator('.feedback').first().waitFor({ state: 'visible', timeout: 20000 });
}

async function nextQuestion(page, expected) {
  const next = page.getByRole('button', { name: /^Next/ }).first();
  if (await next.count()) {
    await next.click();
  }
  await page.waitForFunction(
    (n) => {
      const pills = [...document.querySelectorAll('.pill.pill-primary.font-mono')];
      return pills.some((el) => el.textContent.trim() === `Question ${n}`);
    },
    expected,
    { timeout: 20000 },
  );
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

async function hideDev(page) {
  await page.addStyleTag({ content: 'nextjs-portal{display:none!important}' }).catch(() => {});
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
  await context.addCookies([
    { name: 'ap_session', value: sessionCookie(), domain: 'localhost', path: '/', httpOnly: true },
  ]);
  const page = await context.newPage();

  // ---------- Unit 1.1: complete 14 questions ----------
  const session = await newSession('psychology-unit1-practice', 'psychology-unit1-practice:1.1');
  console.log('session', session.session.id, 'questions', session.questions.length);
  const labels = session.questions.map((q) => correctLabel(q.question_id));
  const wrongIdx = new Set([2, 4, 6, 10]);
  const plan = session.questions.map((q, i) => {
    const correct = labels[i];
    if (!wrongIdx.has(i)) return correct;
    return ['A', 'B', 'C', 'D'].find((l) => l !== correct);
  });

  await page.goto(`${BASE}/practice/session/${session.session.id}`, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.locator('.option').first().waitFor({ timeout: 60000 });
  await hideDev(page);

  for (let i = 0; i < plan.length; i += 1) {
    const label = plan[i];
    if (i === 0) {
      await save(page, '.practice-layout > div > .card.card-pad', 'u11-q0-before.png');
    }
    await answer(page, label);
    if (i === 0) {
      await save(page, '.practice-layout > div > .card.card-pad', 'u11-q0-correct.png');
      await save(page, '.rail-card.card', 'u11-q0-rail.png');
    }
    if (i === 2) {
      await save(page, '.practice-layout > div > .card.card-pad', 'u11-q2-wrong.png');
    }
    if (i === 4) {
      await save(page, '.practice-layout > div > .card.card-pad', 'u11-q4-correct.png');
    }
    if (i < plan.length - 1) {
      await nextQuestion(page, i + 2);
    } else {
      await page.getByText('Chapter Complete', { exact: false }).first().waitFor({ timeout: 30000 });
    }
  }

  await pageShot(page, 'u11-complete.png', { width: 390, height: 844 });
  await save(page, '.card.card-pad.mb-4', 'u11-complete-card.png');

  // ---------- Unit 1.1 topics after completion ----------
  await page.goto(`${BASE}/practice/psychology-unit1-practice`, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.locator('.topic-row').first().waitFor({ timeout: 60000 });
  await pageShot(page, 'u11-topics-after-768.png', { width: 768, height: 1024 });

  // ---------- Wrong book ----------
  await page.goto(`${BASE}/wrong`, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.getByText('错题本', { exact: false }).first().waitFor({ timeout: 60000 });
  await page.waitForTimeout(1200);
  await pageShot(page, 'wrong-list-768.png', { width: 768, height: 1024 });
  await pageShot(page, 'wrong-list-390.png', { width: 390, height: 844 });

  // ---------- Knowledge graph ----------
  await page.goto(`${BASE}/knowledge`, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.locator('svg').first().waitFor({ timeout: 60000 });
  await page.waitForTimeout(1200);
  await pageShot(page, 'graph-unit-structure-768.png', { width: 768, height: 1024 });

  const topicBtn = page.locator('button').filter({ hasText: 'Interaction of Heredity' }).first();
  if (await topicBtn.count()) {
    await topicBtn.click();
    await page.waitForTimeout(1200);
    await pageShot(page, 'graph-mindmap-768.png', { width: 768, height: 1024 });
    await pageShot(page, 'graph-mindmap-390.png', { width: 390, height: 844 });
  } else {
    console.log('topic button not found');
  }

  // ---------- Flashcards ----------
  await page.goto(`${BASE}/cards`, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.getByRole('button', { name: 'Already Know' }).first().waitFor({ timeout: 60000 });
  await page.selectOption('select[aria-label="按单元筛选"]', '1').catch(() => {});
  await page.waitForTimeout(1200);
  await page.setViewportSize({ width: 390, height: 844 });
  await save(page, '.flashcard-wrap', 'cards-front.png');
  await page.locator('.flashcard').first().click();
  await page.waitForTimeout(500);
  await save(page, '.flashcard-wrap', 'cards-back.png');

  for (let i = 0; i < 10; i += 1) {
    const name = i < 7 ? 'Already Know' : 'Review Later';
    const btn = page.getByRole('button', { name }).first();
    await btn.click();
    await page.waitForTimeout(700);
  }
  await page.waitForTimeout(800);
  await pageShot(page, 'cards-after-10-390.png', { width: 390, height: 844 });

  // ---------- Unit 1.2: 10 questions, leave in progress ----------
  const s12 = await newSession('psychology-unit1-practice', 'psychology-unit1-practice:1.2');
  const labels12 = s12.questions.map((q) => correctLabel(q.question_id));
  const wrong12 = new Set([3, 6, 8]);
  const plan12 = s12.questions.slice(0, 10).map((q, i) => {
    const correct = labels12[i];
    if (!wrong12.has(i)) return correct;
    return ['A', 'B', 'C', 'D'].find((l) => l !== correct);
  });

  await page.goto(`${BASE}/practice/session/${s12.session.id}`, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.locator('.option').first().waitFor({ timeout: 60000 });
  await hideDev(page);
  for (let i = 0; i < plan12.length; i += 1) {
    await answer(page, plan12[i]);
    if (i === 1) {
      await save(page, '.practice-layout > div > .card.card-pad', 'u12-q1.png');
      await save(page, '.rail-card.card', 'u12-q1-rail.png');
    }
    if (i === 4) {
      await save(page, '.practice-layout > div > .card.card-pad', 'u12-q4.png');
    }
    if (i < plan12.length - 1) {
      await nextQuestion(page, i + 2);
    }
  }
  await pageShot(page, 'u12-inprogress-390.png', { width: 390, height: 844 });

  // topics page shows In Progress 10/29
  await page.goto(`${BASE}/practice/psychology-unit1-practice`, { waitUntil: 'domcontentloaded', timeout: 120000 });
  await page.locator('.topic-row').first().waitFor({ timeout: 60000 });
  await pageShot(page, 'u12-topics-inprogress-768.png', { width: 768, height: 1024 });

  await browser.close();
  console.log('done');
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
