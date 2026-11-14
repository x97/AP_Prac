const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const RAW = '/Users/aa/Documents/AP_psych/marketing/_raw';
const OUT = '/Users/aa/Documents/AP_psych/marketing/_samples';

function dataUri(file) {
  const ext = path.extname(file).slice(1) || 'png';
  return `data:image/${ext};base64,${fs.readFileSync(file).toString('base64')}`;
}

const img = dataUri(path.join(RAW, 'u11-q0-correct-clean.png'));

const html = `<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<style>
  :root{
    --paper:#f6f4ef; --ink:#1c1f24; --blue:#2f5be8; --red:#b42318;
    --amber:#b45309; --hl:#f3d36b; --muted:#6b7280;
    --hand:"Xingkai SC","Kaiti SC","STKaiti",cursive;
    --body:"Kaiti SC","STKaiti","Songti SC",serif;
    --latin:"Bradley Hand","Noteworthy",cursive;
  }
  *{box-sizing:border-box;margin:0;padding:0}
  html,body{background:var(--paper);}
  body{font-family:var(--body);color:var(--ink);}
  .slide{width:1080px;height:1440px;position:relative;overflow:hidden;background:
    radial-gradient(circle at 18% 12%, rgba(255,255,255,.85), transparent 42%),
    radial-gradient(circle at 82% 88%, rgba(243,211,107,.18), transparent 46%),
    var(--paper);
    background-image:radial-gradient(rgba(28,31,36,.10) .8px, transparent .8px);
    background-size:26px 26px;
  }
  .slide:before{content:"";position:absolute;inset:0;background:
    repeating-linear-gradient(0deg, rgba(28,31,36,.025) 0 1px, transparent 1px 4px);
    pointer-events:none;opacity:.5}
  .kicker{position:absolute;left:72px;top:64px;font-family:var(--latin);font-size:22px;letter-spacing:.22em;color:var(--muted);text-transform:uppercase}
  .date{position:absolute;right:72px;top:64px;font-family:var(--hand);font-size:30px;color:var(--muted);transform:rotate(1deg)}
  h1{position:absolute;left:66px;top:150px;width:760px;font-family:var(--hand);font-weight:400;font-size:104px;line-height:1.02;letter-spacing:.01em}
  .hl{background:linear-gradient(180deg,transparent 56%,rgba(243,211,107,.82) 56%,rgba(243,211,107,.82) 92%,transparent 92%);padding:0 6px}
  .sub{position:absolute;left:74px;top:430px;font-family:var(--body);font-size:34px;color:#3f4652;letter-spacing:.04em}
  .sub b{font-family:var(--hand);font-size:44px;color:var(--blue);font-weight:400}
  .sticky{position:absolute;right:74px;top:120px;width:190px;height:190px;background:#f8e59a;box-shadow:0 10px 22px rgba(16,24,40,.12);transform:rotate(4deg);padding:22px 18px;font-family:var(--hand);font-size:74px;line-height:1;text-align:center;color:#4a3a12}
  .sticky small{display:block;font-size:30px;margin-top:8px;letter-spacing:.08em}
  .sticky:before{content:"";position:absolute;left:50%;top:-16px;transform:translateX(-50%) rotate(-3deg);width:120px;height:32px;background:rgba(225,214,185,.8)}
  .shot{position:absolute;right:54px;bottom:96px;width:570px;height:760px;background:#fffdf8;border:16px solid #fffdf8;box-shadow:0 24px 60px rgba(16,24,40,.18);transform:rotate(2deg);overflow:hidden}
  .shot img{width:100%;height:100%;object-fit:cover;object-position:top center;display:block}
  .shot:after{content:"";position:absolute;left:50%;top:-18px;transform:translateX(-50%) rotate(2deg);width:170px;height:40px;background:rgba(225,214,185,.78)}
  .note{position:absolute;left:70px;bottom:190px;font-family:var(--hand);font-size:40px;color:var(--blue);transform:rotate(-2deg)}
  .note:after{content:"↘";display:inline-block;margin-left:10px;font-size:54px;color:var(--red);transform:rotate(8deg)}
  .footer{position:absolute;left:72px;bottom:54px;font-family:var(--latin);font-size:20px;letter-spacing:.12em;color:var(--muted)}
  .footer b{font-family:var(--hand);font-size:26px;letter-spacing:0;color:var(--ink);font-weight:400}
  .num{position:absolute;right:72px;bottom:52px;font-family:var(--latin);font-size:22px;color:var(--muted)}
</style></head>
<body>
  <div class="slide">
    <div class="kicker">AP Psychology · 2027</div>
    <div class="date">11.20 · 175 天</div>
    <h1>0 元先刷<br><span class="hl">Unit 1</span></h1>
    <div class="sub">14 题 · 正确率 <b>71%</b> · 4 道错题</div>
    <div class="sticky">175<small>天</small></div>
    <div class="shot"><img src="${img}"></div>
    <div class="note">做完立刻看解析</div>
    <div class="footer"><b>Five Score</b> · AP PSYCHOLOGY</div>
    <div class="num">01</div>
  </div>
</body></html>`;

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1440 }, deviceScaleFactor: 1 });
  await page.setContent(html, { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(300);
  await page.locator('.slide').screenshot({ path: path.join(OUT, 'sample-cover.png') });
  await browser.close();
  console.log('saved');
})().catch((e) => { console.error(e); process.exit(1); });
