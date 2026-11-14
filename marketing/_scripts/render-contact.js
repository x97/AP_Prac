const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const ROOT = '/Users/aa/Documents/AP_psych/marketing/xiaohongshu';
const files = [];
for (const dir of fs.readdirSync(ROOT).filter((d) => fs.statSync(path.join(ROOT, d)).isDirectory()).sort()) {
  for (const f of fs.readdirSync(path.join(ROOT, dir)).filter((f) => f.endsWith('.png')).sort()) {
    files.push({ dir, file: f, uri: 'data:image/png;base64,' + fs.readFileSync(path.join(ROOT, dir, f)).toString('base64') });
  }
}
const html = `<!doctype html><html><head><meta charset="utf-8"><style>
body{margin:0;background:#eee;font-family:-apple-system,"PingFang SC",sans-serif}
.grid{display:grid;grid-template-columns:repeat(5,300px);gap:12px;padding:12px;width:1572px}
.cell{background:#fff;padding:6px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.08)}
.cell img{width:100%;display:block;border-radius:4px}
.label{font-size:10px;color:#666;padding:4px 2px 0;line-height:1.3;word-break:break-all}
</style></head><body><div class="grid">${files.map((x) => `<div class="cell"><img src="${x.uri}"><div class="label">${x.dir}/${x.file}</div></div>`).join('')}</div></body></html>`;
(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1572, height: 2400 }, deviceScaleFactor: 1 });
  await page.setContent(html, { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(300);
  await page.screenshot({ path: '/Users/aa/Documents/AP_psych/marketing/_samples/contact-sheet.png', fullPage: true });
  await browser.close();
  console.log('saved');
})();
