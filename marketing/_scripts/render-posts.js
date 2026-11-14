const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const RAW = '/Users/aa/Documents/AP_psych/marketing/_raw';
const ROOT = '/Users/aa/Documents/AP_psych/marketing/xiaohongshu';
const LOGO = 'data:image/png;base64,' + fs.readFileSync('/Users/aa/Documents/AP_psych/apps/web/public/brand/five-score-logo-sm.png').toString('base64');

const cache = new Map();
function uri(name) {
  if (!cache.has(name)) {
    cache.set(name, 'data:image/png;base64,' + fs.readFileSync(path.join(RAW, name)).toString('base64'));
  }
  return cache.get(name);
}

const CSS = `
:root{
  --paper:#f6f4ef; --ink:#1c1f24; --blue:#2f5be8; --red:#b42318;
  --amber:#b45309; --hl:#f3d36b; --muted:#6b7280; --line:#ddd6c7;
  --hand:"Xingkai SC","Kaiti SC","STKaiti",cursive;
  --body:"Kaiti SC","STKaiti","Songti SC",serif;
  --latin:"Bradley Hand","Noteworthy",cursive;
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:var(--paper)}
body{font-family:var(--body);color:var(--ink)}
.slide{width:1080px;height:1440px;position:relative;overflow:hidden;
  background:
   radial-gradient(circle at 16% 10%, rgba(255,255,255,.9), transparent 40%),
   radial-gradient(circle at 86% 90%, rgba(243,211,107,.16), transparent 46%),
   var(--paper);
  background-image:radial-gradient(rgba(28,31,36,.10) .8px, transparent .8px);
  background-size:26px 26px;
}
.slide:before{content:"";position:absolute;inset:0;pointer-events:none;opacity:.45;
  background:repeating-linear-gradient(0deg, rgba(28,31,36,.022) 0 1px, transparent 1px 4px)}
.kicker{position:absolute;left:72px;top:58px;font-family:var(--latin);font-size:21px;letter-spacing:.22em;color:var(--muted);text-transform:uppercase}
.date{position:absolute;right:72px;top:58px;font-family:var(--hand);font-size:29px;color:var(--muted);transform:rotate(1deg)}
.footer{position:absolute;left:72px;bottom:44px;display:flex;align-items:center;gap:12px;font-family:var(--latin);font-size:18px;letter-spacing:.1em;color:var(--muted)}
.footer img{width:42px;height:42px;border-radius:8px;display:block}
.footer b{font-family:var(--hand);font-size:25px;letter-spacing:0;color:var(--ink);font-weight:400}
.num{position:absolute;right:72px;bottom:44px;font-family:var(--latin);font-size:20px;color:var(--muted)}
.hl{background:linear-gradient(180deg,transparent 56%,rgba(243,211,107,.84) 56%,rgba(243,211,107,.84) 92%,transparent 92%);padding:0 6px}
.tape{position:absolute;width:170px;height:38px;background:rgba(226,215,186,.78);box-shadow:0 2px 6px rgba(16,24,40,.05);z-index:4}
.tape:after{content:"";position:absolute;inset:0;background:linear-gradient(90deg,transparent,rgba(255,255,255,.35),transparent);opacity:.5}

/* cover */
.cover h1{position:absolute;left:64px;top:146px;width:800px;font-family:var(--hand);font-weight:400;font-size:104px;line-height:1.03}
.cover .sub{position:absolute;left:72px;top:432px;font-size:33px;color:#3f4652;letter-spacing:.03em}
.cover .sub b{font-family:var(--hand);font-size:43px;color:var(--blue);font-weight:400}
.cover .frame{position:absolute;right:52px;bottom:92px;width:570px;height:760px;background:#fffdf8;border:15px solid #fffdf8;box-shadow:0 24px 60px rgba(16,24,40,.18);transform:rotate(2deg);overflow:hidden;z-index:2}
.cover .frame img{width:100%;height:100%;object-fit:cover;object-position:top center;display:block}
.cover .frame .tape{left:50%;top:-16px;transform:translateX(-50%) rotate(2deg);width:170px}
.cover .sticky{position:absolute;right:74px;top:116px;width:190px;height:190px;background:#f8e59a;box-shadow:0 10px 22px rgba(16,24,40,.12);transform:rotate(4deg);padding:20px 14px;font-family:var(--hand);font-size:72px;line-height:1;text-align:center;color:#4a3a12;z-index:3}
.cover .sticky small{display:block;font-size:29px;margin-top:8px;letter-spacing:.08em}
.cover .sticky .tape{left:50%;top:-15px;transform:translateX(-50%) rotate(-3deg);width:120px;height:30px}
.cover .note{position:absolute;left:70px;bottom:186px;font-family:var(--hand);font-size:39px;color:var(--blue);transform:rotate(-2deg)}
.cover .note:after{content:"↘";display:inline-block;margin-left:10px;font-size:52px;color:var(--red);transform:rotate(8deg)}

/* shot */
.shot-slide .title{position:absolute;left:66px;top:146px;width:960px;font-family:var(--hand);font-weight:400;font-size:62px;line-height:1.12}
.shot-slide .title .hl{padding:0 5px}
.shot-slide .frame{position:absolute;background:#fffdf8;border:14px solid #fffdf8;box-shadow:0 22px 54px rgba(16,24,40,.17);overflow:hidden;z-index:2}
.shot-slide .frame img{width:100%;height:100%;display:block}
.shot-slide .frame .tape{left:50%;top:-15px;transform:translateX(-50%) rotate(-2deg);width:150px;height:34px}
.shot-slide .anno{position:absolute;background:#fff3bf;box-shadow:0 8px 18px rgba(16,24,40,.10);padding:15px 17px;font-family:var(--hand);font-size:29px;line-height:1.35;color:#4a3a12;transform:rotate(-2deg);z-index:5;max-width:300px}
.shot-slide .anno:before{content:"";position:absolute;left:50%;top:-12px;transform:translateX(-50%) rotate(2deg);width:90px;height:24px;background:rgba(226,215,186,.7)}
.shot-slide .caption{position:absolute;left:72px;right:72px;bottom:104px;font-size:29px;color:#4a4f59;line-height:1.55;border-top:1px solid var(--line);padding-top:18px}
.shot-slide .caption b{color:var(--blue);font-weight:600}

/* two-up */
.two-slide .title{position:absolute;left:66px;top:146px;width:960px;font-family:var(--hand);font-weight:400;font-size:62px;line-height:1.12}
.two-slide .frame{position:absolute;top:396px;width:440px;height:600px;background:#fffdf8;border:14px solid #fffdf8;box-shadow:0 20px 46px rgba(16,24,40,.16);overflow:hidden;z-index:2}
.two-slide .frame img{width:100%;height:100%;object-fit:contain;object-position:center;display:block}
.two-slide .frame .tape{left:50%;top:-15px;transform:translateX(-50%) rotate(-2deg);width:130px;height:32px}
.two-slide .label{position:absolute;top:346px;font-family:var(--hand);font-size:30px;color:var(--muted)}
.two-slide .caption{position:absolute;left:72px;right:72px;bottom:104px;font-size:29px;color:#4a4f59;line-height:1.55;border-top:1px solid var(--line);padding-top:18px}

/* quote */
.quote-slide .quote{position:absolute;left:78px;top:210px;width:820px;font-family:var(--hand);font-size:94px;line-height:1.15;font-weight:400}
.quote-slide .quote .hl{padding:0 8px}
.quote-slide .frame{position:absolute;right:70px;bottom:240px;width:460px;height:600px;background:#fffdf8;border:14px solid #fffdf8;box-shadow:0 20px 46px rgba(16,24,40,.16);transform:rotate(2deg);overflow:hidden;z-index:2}
.quote-slide .frame img{width:100%;height:100%;object-fit:cover;object-position:top center;display:block}
.quote-slide .frame .tape{left:50%;top:-15px;transform:translateX(-50%) rotate(2deg);width:130px;height:32px}
.quote-slide .sticky{position:absolute;left:95px;bottom:240px;width:210px;height:210px;background:#f8e59a;box-shadow:0 10px 22px rgba(16,24,40,.12);transform:rotate(-4deg);padding:22px 16px;font-family:var(--hand);font-size:56px;line-height:1;text-align:center;color:#4a3a12;z-index:3}
.quote-slide .sticky small{display:block;font-size:26px;margin-top:8px}
.quote-slide .caption{position:absolute;left:360px;right:90px;bottom:110px;font-size:27px;color:#4a4f59;line-height:1.55}

/* cta */
.cta-slide .big{position:absolute;left:78px;top:220px;font-family:var(--hand);font-size:132px;line-height:1.02;font-weight:400}
.cta-slide .big .hl{padding:0 8px}
.cta-slide .sub{position:absolute;left:82px;top:560px;width:520px;font-size:36px;color:#3f4652;line-height:1.5}
.cta-slide .note{position:absolute;left:82px;top:700px;font-family:var(--hand);font-size:40px;color:var(--blue);transform:rotate(-2deg)}
.cta-slide .frame{position:absolute;right:60px;bottom:150px;background:#fffdf8;border:14px solid #fffdf8;box-shadow:0 22px 54px rgba(16,24,40,.17);transform:rotate(2deg);overflow:hidden;z-index:2}
.cta-slide .frame img{width:100%;height:100%;display:block}
.cta-slide .frame .tape{left:50%;top:-15px;transform:translateX(-50%) rotate(-2deg);width:150px;height:34px}
.cta-slide .disclaimer{position:absolute;left:72px;right:72px;bottom:86px;font-size:17px;color:#8a8f99;line-height:1.5;border-top:1px solid var(--line);padding-top:12px}
`;

function header(post) {
  return `<div class="kicker">AP Psychology · 2027</div><div class="date">${post.date} · ${post.days} 天</div>`;
}
function footer(post, page) {
  return `<div class="footer"><img src="${LOGO}" alt=""><span><b>Five Score</b> · AP PSYCHOLOGY</span></div><div class="num">${String(page).padStart(2, '0')}</div>`;
}
function cover(post, s) {
  const f = s.frame;
  const frameStyle = f ? `width:${f.w}px;height:${f.h}px;right:${f.right}px;bottom:${f.bottom}px;` : '';
  const imgStyle = f ? `object-fit:${f.fit || 'cover'};object-position:${f.pos || 'top center'};` : '';
  const noteStyle = s.noteTop ? `top:${s.noteTop}px;bottom:auto;` : '';
  return `<div class="slide cover">${header(post)}
    <h1>${s.title}</h1>
    <div class="sub">${s.sub}</div>
    <div class="sticky">${s.sticky}<div class="tape"></div></div>
    <div class="frame" style="${frameStyle}"><img src="${uri(s.image)}" style="${imgStyle}"><div class="tape"></div></div>
    <div class="note" style="${noteStyle}">${s.note}</div>
    ${footer(post, 1)}
  </div>`;
}
function shot(post, s) {
  const f = s.frame;
  return `<div class="slide shot-slide">${header(post)}
    <div class="title">${s.title}</div>
    <div class="frame" style="left:${f.x}px;top:${f.y}px;width:${f.w}px;height:${f.h}px;transform:rotate(${f.rot ?? -1.2}deg)">
      <img src="${uri(s.image)}" style="object-fit:${f.fit || 'cover'};object-position:${f.pos || 'top center'}">
      <div class="tape"></div>
    </div>
    ${s.anno ? `<div class="anno" style="left:${s.anno.x}px;top:${s.anno.y}px">${s.anno.text}</div>` : ''}
    <div class="caption">${s.caption}</div>
    ${footer(post, s.page)}
  </div>`;
}
function two(post, s) {
  return `<div class="slide two-slide">${header(post)}
    <div class="title">${s.title}</div>
    <div class="label" style="left:130px">${s.leftLabel}</div>
    <div class="frame" style="left:100px;transform:rotate(-1.5deg)"><img src="${uri(s.left)}"><div class="tape"></div></div>
    <div class="label" style="left:608px">${s.rightLabel}</div>
    <div class="frame" style="left:580px;transform:rotate(1.5deg)"><img src="${uri(s.right)}"><div class="tape"></div></div>
    <div class="caption">${s.caption}</div>
    ${footer(post, s.page)}
  </div>`;
}
function quote(post, s) {
  return `<div class="slide quote-slide">${header(post)}
    <div class="quote">${s.quote}</div>
    <div class="sticky">${s.sticky}<div class="tape" style="left:50%;top:-13px;transform:translateX(-50%) rotate(-3deg);width:100px;height:28px"></div></div>
    <div class="frame"><img src="${uri(s.image)}" style="object-position:${s.pos || 'top center'}"><div class="tape"></div></div>
    <div class="caption">${s.caption}</div>
    ${footer(post, s.page)}
  </div>`;
}
function cta(post, s) {
  const f = s.frame || { w: 500, h: 600, bottom: 150, right: 60 };
  return `<div class="slide cta-slide">${header(post)}
    <div class="big">${s.big}</div>
    <div class="sub">${s.sub}</div>
    <div class="note">${s.note}</div>
    <div class="frame" style="width:${f.w}px;height:${f.h}px;bottom:${f.bottom}px;right:${f.right}px">
      <img src="${uri(s.image)}" style="object-fit:${s.fit || 'cover'};object-position:${s.pos || 'top center'}">
      <div class="tape"></div>
    </div>
    <div class="disclaimer">AP® 是 College Board 的注册商标；本站与 College Board 无隶属关系。内容为学习记录，不构成分数承诺。</div>
    ${footer(post, 5)}
  </div>`;
}

const POSTS = [
  {
    slug: '2026-11-20_175days-unit1',
    date: '11.20',
    days: 175,
    slides: [
      { type: 'cover', title: '0 元先刷<br><span class="hl">Unit 1</span>', sub: '14 题 · 正确率 <b>71%</b> · 4 道错题', image: 'u11-q0-correct-clean.png', sticky: '175<small>天</small>', note: '做完立刻看解析' },
      { type: 'shot', title: '1.1 做完<br><span class="hl">14 题对 10 题</span>', image: 'topics-after-both-768.png', frame: { x: 130, y: 340, w: 820, h: 860, fit: 'cover', pos: 'top center' }, anno: { text: '1.1 已完成<br>14/14', x: 50, y: 900 }, caption: '进度条终于不是 0 了。先把一个 Topic 完整走一遍，比收藏 10 篇攻略有用。', page: 2 },
      { type: 'shot', title: '做完立刻看解析', image: 'u11-q0-correct-clean.png', frame: { x: 60, y: 340, w: 540, h: 880, fit: 'cover', pos: 'center 15%' }, anno: { text: '解析 + 概念<br>一起看', x: 630, y: 400 }, caption: '这题考的是 <b>inborn distaste</b>，不是条件反射。错选 D 的人，大概率是把“天生”读成了“学过”。', page: 3 },
      { type: 'shot', title: '错了 4 道，<br><span class="hl">自动进错题本</span>', image: 'wrong-modal-panel.png', frame: { x: 80, y: 340, w: 740, h: 860, fit: 'contain', pos: 'center' }, anno: { text: '错 1 次<br>= 未掌握', x: 730, y: 390 }, caption: '错题不是收藏，是回炉。先知道为什么错，再决定要不要重做。', page: 4 },
      { type: 'cta', big: 'Unit 1<br><span class="hl">免费</span>', sub: '先刷一遍，再决定要不要继续。', note: '评论区说一声', image: 'u11-complete-card.png', fit: 'contain', pos: 'center', frame: { w: 540, h: 340, bottom: 240, right: 60 } },
    ],
    copy: `# 11.20 · 距离 AP 心理 175 天

## 标题（3 选 1）
1. 距离 AP 心理 175 天，我 0 元先把 Unit 1 刷了
2. AP 心理 Unit 1.1 免费刷完：14 题对 10 题
3. 0 元刷 AP 心理：我的 Unit 1 错题有 4 道

## 正文
2027 AP Psych 是机考，5/14 下午考。今天距离考试 175 天。

我先没买课，用 Five Score 把 Unit 1 的 1.1 免费刷了一遍：
14 题，对 10 题，正确率 71%，错了 4 题。

做完立刻看解析，右边会同步显示这道题考的概念；错题自动进错题本。
最惨的是 nature vs nurture，选项看着都像对的。

先把免费 Unit 1 的 1.1 刷完，再决定要不要继续。
Unit 1 是免费的，想试的评论区说一声。

## 标签
#AP心理学 #APPsych #AP备考 #国际学校 #2027AP #心理学 #留学申请 #学习记录

## 配图顺序
1. 封面：175 天 / 0 元先刷 Unit 1
2. Unit 1 章节进度：1.1 完成 14/14
3. 做题 + 即时解析
4. 错题本：4 道错题
5. CTA：Unit 1 免费

## 发布备注
- 建议时间：11/20 20:00-22:00
- 账号简介建议：2027 AP Psych 备考记录 · 用 Five Score 刷题
- 不在图片/正文放微信二维码；评论区引导为主
- 数据口径：14 题、10 对、71%、4 道错题（真实练习记录）
`,
  },
  {
    slug: '2026-11-23_172days-unit12',
    date: '11.23',
    days: 172,
    slides: [
      { type: 'cover', title: '今天只做<br><span class="hl">10 题</span>', sub: 'Unit 1.2 · 正确率 <b>70%</b>', image: 'u12-q1-390.png', sticky: '172<small>天</small>', note: '进度自动保存' },
      { type: 'shot', title: '1.2 进度<br><span class="hl">10 / 29</span>', image: 'topics-after-both-768.png', frame: { x: 130, y: 340, w: 820, h: 860, fit: 'cover', pos: 'top center' }, anno: { text: '明天从<br>第 11 题继续', x: 50, y: 900 }, caption: '每天只做 10 题，听起来很少，但一周就是 70 题。比周末突击 100 题好坚持。', page: 2 },
      { type: 'shot', title: 'reflex arc<br>的顺序', image: 'u12-q1-390.png', frame: { x: 60, y: 340, w: 540, h: 880, fit: 'cover', pos: 'center 25%' }, anno: { text: 'receptors →<br>sensory →<br>interneurons →<br>motor', x: 630, y: 400 }, caption: '这题我第一遍也犹豫了。把顺序写成一条线，比背四个名词有用。', page: 3 },
      { type: 'shot', title: '右边是这道题的<br><span class="hl">相关概念</span>', image: 'u12-q1-rail-390.png', frame: { x: 70, y: 340, w: 680, h: 860, fit: 'cover', pos: 'top center' }, anno: { text: '不熟的<br>直接抄笔记', x: 760, y: 390 }, caption: '概念不是孤立的，是挂在题上的。做完题再看概念，记得住。', page: 4 },
      { type: 'cta', big: '每天<br><span class="hl">10 题</span>', sub: '进度自动保存，明天接着做。', note: '先刷 Unit 1', image: 'u12-q4-390.png', pos: 'top center' },
    ],
    copy: `# 11.23 · 距离 AP 心理 172 天

## 标题（3 选 1）
1. AP 心理 Unit 1.2：今天只做 10 题，正确率 70%
2. 神经系统这章，我用 10 道题把概念串起来了
3. 每天 10 题，AP 心理 Unit 1.2 进度 10/29

## 正文
今天没给自己定 30 题的目标，只做了 Unit 1.2 的 10 道题，对了 7 道。

这章最绕的是 reflex arc 的顺序：receptors → sensory neurons → interneurons → motor neurons。

做完题右边会列出这道题的相关概念，我直接把不熟的抄进笔记。
最舒服的是进度自动保存，明天从第 11 题继续，不用重新找。

每天 10 题，比周末突击 100 题好坚持。

## 标签
#AP心理学 #APPsych #AP备考 #国际学校 #2027AP #神经科学 #学习记录

## 配图顺序
1. 封面：今天只做 10 题
2. 章节进度：10/29，明天第 11 题
3. reflex arc 题目 + 解析
4. 右侧相关概念
5. CTA：每天 10 题

## 发布备注
- 建议时间：11/23 20:00-22:00
- 数据口径：10 题、7 对、70%（真实练习记录，未交卷）
- 正文强调“进度自动保存”，这是产品差异点
`,
  },
  {
    slug: '2026-11-26_169days-knowledge-graph',
    date: '11.26',
    days: 169,
    slides: [
      { type: 'cover', title: '197 个概念<br><span class="hl">先看结构</span>', sub: 'Unit 1 · 8 个 Topic', image: 'graph-unit-structure-768.png', sticky: '169<small>天</small>', note: '先看全局' },
      { type: 'shot', title: 'Unit 1 的<br><span class="hl">结构图</span>', image: 'graph-unit-structure-768.png', frame: { x: 110, y: 340, w: 860, h: 860, fit: 'cover', pos: 'top center' }, anno: { text: '8 个 Topic<br>每个只露 3 个<br>核心概念', x: 50, y: 900 }, caption: '先知道这章有什么，再背细节。197 个概念不是让你一次背完的。', page: 2 },
      { type: 'shot', title: '点进 1.1', image: 'graph-mindmap-768.png', frame: { x: 110, y: 340, w: 860, h: 860, fit: 'cover', pos: 'top center' }, anno: { text: 'XMind 风格<br>章节图', x: 50, y: 900 }, caption: 'Behavioral Genetics / Nature & Nurture / Twin & Family Studies… 一张图看完一章。', page: 3 },
      { type: 'quote', quote: '先看全局，<br><span class="hl">再点细节。</span>', sticky: '197<small>概念</small>', image: 'graph-mindmap-768.png', caption: '一页页翻书，不如先走一遍图。点概念还能看定义、教材关系和真题易混。', page: 4 },
      { type: 'cta', big: 'Unit 1<br><span class="hl">图谱免费</span>', sub: '先看结构，再决定怎么背。', note: '评论区说一声', image: 'graph-unit-structure-768.png', fit: 'cover', pos: 'top center', frame: { w: 540, h: 520, bottom: 180, right: 50 } },
    ],
    copy: `# 11.26 · 距离 AP 心理 169 天

## 标题（3 选 1）
1. AP 心理 Unit 1 知识图谱：197 个概念，先看结构再背
2. 别再按字母表背 AP 心理概念了
3. Unit 1 有 197 个概念，我先画了一张图

## 正文
Unit 1 有 197 个概念，直接背会疯。

我先看 Unit 结构：8 个 Topic，每个 Topic 只露 3 个核心概念。
点进 1.1，是一张 XMind 风格的章节图：Behavioral Genetics / Nature & Nurture / Twin & Family Studies…

点概念能看到定义、教材关系和真题易混。
先看全局，再点细节，比一页页翻书快。

Unit 1 的图谱是免费的，先看结构再决定要不要背。

## 标签
#AP心理学 #APPsych #AP备考 #知识图谱 #思维导图 #国际学校 #2027AP #学习记录

## 配图顺序
1. 封面：197 个概念 / 先看结构
2. Unit 1 结构图
3. 1.1 章节思维导图
4. 金句页：先看全局，再点细节
5. CTA：Unit 1 图谱免费

## 发布备注
- 建议时间：11/26 20:00-22:00
- 正文避免“保分/提分”承诺
- 截图使用 Unit 1 结构/1.1 导图，未露出教材来源行
`,
  },
  {
    slug: '2026-11-30_165days-flashcards',
    date: '11.30',
    days: 165,
    slides: [
      { type: 'cover', title: '通勤 15 分钟<br><span class="hl">10 张卡</span>', sub: '7 张认识 · 3 张还不熟', image: 'cards-front.png', sticky: '165<small>天</small>', note: '地铁上就能刷' },
      { type: 'two', title: '正面术语，<br><span class="hl">背面释义</span>', left: 'cards-front.png', right: 'cards-back.png', leftLabel: '正面', rightLabel: '背面', caption: '术语 + IPA + 英文释义，点朗读还能听发音。等车的时候翻两张，比刷短视频踏实。', page: 2 },
      { type: 'shot', title: '10 张卡的<br><span class="hl">真实数据</span>', image: 'cards-after-10-768.png', frame: { x: 110, y: 340, w: 860, h: 860, fit: 'cover', pos: 'top center' }, anno: { text: '今日新卡<br>10 / 60', x: 50, y: 900 }, caption: '不熟的 10 分钟后再出现；认识的按 1/2/4/7/15 天间隔复习。不是背单词，是安排下一次见面。', page: 3 },
      { type: 'quote', quote: '不是背单词，<br>是安排<br><span class="hl">下一次见面。</span>', sticky: '10<small>张</small>', image: 'cards-front.png', caption: '间隔重复的关键不是一次背多久，而是下次什么时候再见。', page: 4 },
      { type: 'cta', big: '每天<br><span class="hl">10 张</span>', sub: '先刷 Unit 1 的卡。', note: '评论区说一声', image: 'cards-front.png', fit: 'contain', pos: 'center', frame: { w: 500, h: 600, bottom: 150, right: 60 } },
    ],
    copy: `# 11.30 · 距离 AP 心理 165 天

## 标题（3 选 1）
1. 通勤 15 分钟，刷了 10 张 AP 心理记忆卡
2. AP 心理术语背不下来？我把卡片塞进通勤
3. 10 张卡，7 张认识，3 张还不熟

## 正文
今天只干了三件事：地铁上翻 10 张卡，7 张点了 Already Know，3 张 Review Later。

卡片正面是术语 + IPA，背面是英文释义；点朗读还能听发音。
不熟的卡 10 分钟后会再出现，认识的卡按 1/2/4/7/15 天间隔复习。

比抱着单词书从 A 背到 Z 有用。
今天新卡 10/60，明天继续。

## 标签
#AP心理学 #APPsych #AP备考 #记忆卡片 #间隔重复 #国际学校 #2027AP #学习记录

## 配图顺序
1. 封面：通勤 10 张卡
2. 正面/背面两图
3. 10 张卡的真实数据
4. 金句页：安排下一次见面
5. CTA：每天 10 张

## 发布备注
- 建议时间：11/30 20:00-22:00
- 数据口径：10 张、7 认识、3 不熟（真实复习记录）
- 正文强调“通勤/碎片时间”，适合学生号人设
`,
  },
  {
    slug: '2026-12-03_162days-wrong-book',
    date: '12.03',
    days: 162,
    slides: [
      { type: 'cover', title: '错了 4 道<br><span class="hl">开始回炉</span>', sub: 'Unit 1.1 · 错题本', image: 'wrong-card-clean.png', sticky: '162<small>天</small>', note: '错题不是收藏', noteTop: 636, frame: { w: 760, h: 440, right: 40, bottom: 150, fit: 'cover', pos: 'center' } },
      { type: 'shot', title: '错 1 次<br><span class="hl">= 未掌握</span>', image: 'wrong-card-clean.png', frame: { x: 130, y: 400, w: 820, h: 480, fit: 'cover', pos: 'center' }, anno: { text: '再答对一次<br>→ 复习中', x: 50, y: 920 }, caption: '连续答对两次，才算真正掌握。错题本会按未掌握 / 复习中 / 已掌握分组。', page: 2 },
      { type: 'shot', title: '点开看<br><span class="hl">原题 + 解析</span>', image: 'wrong-modal-panel.png', frame: { x: 80, y: 340, w: 740, h: 860, fit: 'contain', pos: 'center' }, anno: { text: '正确答案<br>+ 解析', x: 730, y: 390 }, caption: '知道自己为什么错，比再做 10 道新题有用。', page: 3 },
      { type: 'shot', title: '1.1 完成，<br><span class="hl">1.2 继续</span>', image: 'topics-after-both-768.png', frame: { x: 130, y: 340, w: 820, h: 860, fit: 'cover', pos: 'top center' }, anno: { text: '1.1 完成<br>14/14', x: 50, y: 900 }, caption: '错题回炉完，再往下走。Unit 1 的进度是看得见的。', page: 4 },
      { type: 'cta', big: '错题<br><span class="hl">自动回炉</span>', sub: 'Unit 1 免费，先刷一遍。', note: '评论区说一声', image: 'u11-complete-card.png', fit: 'contain', pos: 'center', frame: { w: 540, h: 340, bottom: 240, right: 60 } },
    ],
    copy: `# 12.03 · 距离 AP 心理 162 天

## 标题（3 选 1）
1. AP 心理错题本：错 1 次不算掌握，连续答对 2 次才算
2. 我的 AP 心理错题本，终于不是收藏夹了
3. Unit 1 错了 4 道，我开始回炉了

## 正文
Unit 1.1 做完，错了 4 道。

错题本会自动记录，按未掌握 / 复习中 / 已掌握分组。
点开能看到原题、正确答案和解析；再答对一次进入复习中，连续答对两次才算掌握。

我现在每周只做错题卷，不再从头刷。
今天先把 nature vs nurture 这道翻出来看了解析。

错题不是收藏，是回炉。

## 标签
#AP心理学 #APPsych #AP备考 #错题本 #学习方法 #国际学校 #2027AP #学习记录

## 配图顺序
1. 封面：4 道错题 / 开始回炉
2. 错题卡：错 1 次 = 未掌握
3. 错题详情：原题 + 正确答案 + 解析
4. 章节进度：1.1 完成，1.2 继续
5. CTA：错题自动回炉

## 发布备注
- 建议时间：12/03 20:00-22:00
- 数据口径：Unit 1.1 错 4 道（真实练习记录）
- 截图已隐藏教材来源行/题号，避免露出第三方内容品牌
`,
  },
];

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1440 }, deviceScaleFactor: 1 });
  for (const post of POSTS) {
    const dir = path.join(ROOT, post.slug);
    fs.mkdirSync(dir, { recursive: true });
    for (let i = 0; i < post.slides.length; i += 1) {
      const s = post.slides[i];
      let body = '';
      if (s.type === 'cover') body = cover(post, s);
      else if (s.type === 'shot') body = shot(post, { ...s, page: s.page ?? i + 1 });
      else if (s.type === 'two') body = two(post, { ...s, page: s.page ?? i + 1 });
      else if (s.type === 'quote') body = quote(post, { ...s, page: s.page ?? i + 1 });
      else if (s.type === 'cta') body = cta(post, s);
      const html = `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><style>${CSS}</style></head><body>${body}</body></html>`;
      await page.setContent(html, { waitUntil: 'load' });
      await page.evaluate(() => document.fonts.ready);
      await page.waitForTimeout(120);
      const name = `${String(i + 1).padStart(2, '0')}-${s.type === 'cover' ? 'cover' : s.type === 'cta' ? 'cta' : s.type === 'quote' ? 'quote' : s.type === 'two' ? 'two' : 'shot'}.png`;
      await page.locator('.slide').screenshot({ path: path.join(dir, name) });
      console.log(path.join(dir, name));
    }
    fs.writeFileSync(path.join(dir, 'copy.md'), post.copy, 'utf8');
    fs.writeFileSync(path.join(dir, 'meta.json'), JSON.stringify({ slug: post.slug, date: post.date, days: post.days, slides: post.slides.length }, null, 2), 'utf8');
  }
  await browser.close();
  console.log('done');
})().catch((e) => { console.error(e); process.exit(1); });
