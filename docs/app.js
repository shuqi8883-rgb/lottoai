const DATA = { ssq: 'data/ssq.json', dlt: 'data/dlt.json' };
let game = 'ssq';
let rows = [];
let seedBase = 0;

const $ = (s) => document.querySelector(s);
const pad = (n) => String(n).padStart(2, '0');
const isDLT = () => game === 'dlt';
const mainMax = () => isDLT() ? 35 : 33;
const mainPick = () => isDLT() ? 5 : 6;
const backMax = () => isDLT() ? 12 : 16;
const backPick = () => isDLT() ? 2 : 1;
const mainNums = (r) => (isDLT() ? r.front : r.red).map(Number);
const backNums = (r) => (isDLT() ? r.back : r.blue).map(Number);

function esc(v) {
  return String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[c]));
}
function sum(a) { return a.reduce((x, y) => x + y, 0); }
function avg(a) { return a.length ? sum(a) / a.length : 0; }
function balls(nums, type = '') { return nums.map(n => `<span class="ball ${type}">${pad(n)}</span>`).join(''); }
function chips(nums) { return nums.map(n => `<span class="chip">${pad(n)}</span>`).join(''); }
function sorted(a) { return [...a].sort((x,y) => x-y); }

function freq(list, limit = 100) {
  const f = {};
  for (const r of list.slice(0, limit)) for (const n of mainNums(r)) f[n] = (f[n] || 0) + 1;
  return f;
}
function backFreq(list, limit = 100) {
  const f = {};
  for (const r of list.slice(0, limit)) for (const n of backNums(r)) f[n] = (f[n] || 0) + 1;
  return f;
}
function omission(list) {
  const o = {};
  for (let n=1; n<=mainMax(); n++) o[n] = list.length;
  for (let i=0; i<list.length; i++) for (const n of mainNums(list[i])) if (o[n] === list.length) o[n] = i;
  return o;
}
function topKeys(obj, count, high = true) {
  return Object.keys(obj).map(Number).sort((a,b) => high ? (obj[b]-obj[a] || a-b) : (obj[a]-obj[b] || a-b)).slice(0,count);
}
function recentSums(limit=100) { return rows.slice(0,limit).map(r => sum(mainNums(r))); }
function recentOdd(limit=100) { return rows.slice(0,limit).map(r => mainNums(r).filter(n => n%2).length); }
function zoneCount(c) {
  const max = mainMax();
  const third = max / 3;
  return [c.filter(n => n <= third).length, c.filter(n => n > third && n <= third*2).length, c.filter(n => n > third*2).length];
}

function stats() {
  const f = freq(rows, 100), bf = backFreq(rows, 100), om = omission(rows);
  const sums = recentSums(100), odds = recentOdd(100);
  const avgSum = avg(sums), avgOdd = avg(odds);
  const hot = topKeys(f, 8, true), cold = topKeys(f, 8, false), miss = topKeys(om, 8, true);
  return { f, bf, om, sums, odds, avgSum, avgOdd, hot, cold, miss };
}

function makeRng(seed) {
  let x = (seed >>> 0) || 1;
  return () => {
    x ^= x << 13; x ^= x >>> 17; x ^= x << 5;
    return (x >>> 0) / 4294967296;
  };
}
function randomCombo(max, k, rng) {
  const out = [];
  while (out.length < k) {
    const n = 1 + Math.floor(rng() * max);
    if (!out.includes(n)) out.push(n);
  }
  return sorted(out);
}
function comboScore(c, s) {
  const k = c.length;
  const targetFreq = 100 * k / mainMax();
  let score = 0;
  for (const n of c) {
    const f = s.f[n] || 0;
    const o = s.om[n] || 0;
    score += 1.6 - Math.min(Math.abs(f - targetFreq) / 9, 1.6);
    score += Math.min(o / 18, 1.2) * 0.20;
  }
  const odd = c.filter(n => n%2).length;
  score += Math.max(0, 1.15 - Math.abs(odd - s.avgOdd) * 0.65);
  score += Math.max(0, 1.1 - Math.abs(sum(c) - s.avgSum) / 75);
  const z = zoneCount(c);
  if (Math.min(...z) >= 1) score += 0.55;
  let consecutive = 0;
  for (let i=1;i<c.length;i++) if (c[i] === c[i-1]+1) consecutive++;
  score -= Math.max(0, consecutive-2) * 0.45;
  const span = c[c.length-1] - c[0];
  if (span < mainMax()*0.45) score -= 0.55;
  return score;
}
function generateCandidates(count=6) {
  const s = stats();
  const rng = makeRng(seedBase + (isDLT() ? 7919 : 3571));
  const total = 6500;
  const best = [];
  for (let i=0;i<total;i++) {
    const c = randomCombo(mainMax(), mainPick(), rng);
    let score = comboScore(c, s);
    const b = randomCombo(backMax(), backPick(), rng);
    score += b.reduce((v,n) => v + Math.min((s.bf[n]||0)/8, 1) * 0.18, 0);
    best.push({ c, b, score });
  }
  best.sort((a,b)=>b.score-a.score);
  const out=[];
  for (const x of best) {
    if (out.every(y => x.c.filter(n=>y.c.includes(n)).length <= (isDLT()?3:4))) out.push(x);
    if (out.length >= count) break;
  }
  return out;
}

function metric(label, value, sub='') {
  return `<div class="metric"><span>${label}</span><strong>${value}</strong>${sub ? `<small>${sub}</small>` : ''}</div>`;
}
function statCard(title, body, cls='') { return `<section class="card ${cls}"><h2>${title}</h2>${body}</section>`; }

function baseRender() {
  if (!rows.length) {
    $('#app').innerHTML = `<section class="card error"><h2>暂时没有开奖数据</h2><p>请点击“刷新数据”重试。</p></section>`;
    return;
  }
  const s = stats();
  const latest = rows[0];
  const main = mainNums(latest), back = backNums(latest);
  const sumNow = sum(main);
  const zone = zoneCount(main);
  const name = isDLT() ? '超级大乐透' : '双色球';
  $('#app').innerHTML = `
    <section class="hero-card">
      <div class="hero-top">
        <div><div class="eyebrow">${isDLT()?'大乐透':'双色球'} · LIVE DATA</div><h1>${name}</h1><p>第 ${esc(latest.issue)} 期 · ${esc(latest.date)}</p></div>
        <div class="status"><i></i> 数据正常</div>
      </div>
      <div class="draw-label">最新开奖号码</div>
      <div class="balls big">${balls(main)}<span class="divider">+</span>${balls(back,'blue')}</div>
      <div class="hero-metrics">
        <div><span>主区和值</span><b>${sumNow}</b></div>
        <div><span>奇偶</span><b>${main.filter(n=>n%2).length}:${main.filter(n=>n%2===0).length}</b></div>
        <div><span>三区</span><b>${zone.join(' · ')}</b></div>
        <div><span>样本</span><b>${Math.min(rows.length,100)}期</b></div>
      </div>
    </section>
    <div class="section-title"><div><b>数据画像</b><span>近100期统计</span></div></div>
    <div class="grid two">
      ${statCard('🔥 热号', `<div class="chips">${chips(s.hot)}</div><p class="hint">出现次数较高，不代表下一期更容易开出。</p>`)}
      ${statCard('❄️ 冷号', `<div class="chips">${chips(s.cold)}</div><p class="hint">历史频率较低，仅作为组合分的一项参考。</p>`)}
      ${statCard('⏳ 高遗漏', `<div class="chips">${chips(s.miss)}</div><p class="hint">按当前遗漏期数排序，避免把“久未开”理解成必开。</p>`)}
      ${statCard('📐 区间画像', `${metric('平均和值', s.avgSum.toFixed(1))}${metric('平均奇数', s.avgOdd.toFixed(2))}${metric('最近和值', sumNow)}`)}
    </div>
    <section class="card recommendation">
      <div class="section-head"><div><h2>🎯 今日候选组合</h2><p>统计评分 + 组合约束 · 同一期刷新保持稳定</p></div><button id="reroll">换一组</button></div>
      <div id="candidateBox"><div class="loading">正在计算候选组合…</div></div>
    </section>
    <div class="grid two">
      ${statCard('📋 最近10期', `<div class="recent">${rows.slice(0,10).map((r,i)=>`<div class="recent-row"><span>#${esc(r.issue)}</span><div>${balls(mainNums(r),'mini')}${balls(backNums(r),'blue mini')}</div><em>${esc(r.date)}</em></div>`).join('')}</div>`, 'wide')}
      ${statCard('🧠 评分逻辑', `<div class="logic">${metric('频率偏离', '30%', '避免只追极热号码')}${metric('和值 / 奇偶', '30%', '贴近历史分布中心')}${metric('遗漏', '10%', '仅作弱权重')}${metric('三区 / 连号', '20%', '控制结构')}${metric('组合去重', '10%', '减少相似组合')}</div>`)}
      ${statCard('🔬 研究状态', `<div class="research"><span class="ok">● 数据同步</span><span class="ok">● 近100期统计</span><span class="ok">● 候选组合</span><span class="wait">● Walk-forward 回测</span></div><p class="hint">下一阶段可以加入逐期预测台账、命中统计和滚动回测曲线。</p>`)}
    </div>
    <section class="card notice"><b>重要说明</b><p>彩票开奖结果具有独立随机性。本站的评分、热冷号、遗漏和候选组合仅用于数据研究与娱乐，不是中奖概率，也不能保证预测下一期。正式开奖信息请以官方渠道为准。</p></section>`;
  renderCandidates();
}

function renderCandidates() {
  const box = $('#candidateBox');
  if (!box) return;
  const picks = generateCandidates(6);
  box.innerHTML = picks.map((x,i)=>`<div class="candidate ${i===0?'featured':''}">
    <div class="rank">${i+1}</div>
    <div class="candidate-main"><div class="balls">${balls(x.c)}<span class="divider">+</span>${balls(x.b,'blue')}</div><div class="score">组合评分 <b>${x.score.toFixed(2)}</b></div></div>
    ${i===0?'<span class="tag">综合优先</span>':''}
  </div>`).join('');
  $('#reroll')?.addEventListener('click', () => { seedBase += 97; renderCandidates(); });
}

async function load() {
  $('#app').innerHTML = `<section class="card loading"><div class="spinner"></div><h2>正在同步 ${isDLT()?'大乐透':'双色球'} 数据</h2><p>正在读取最近开奖记录，请稍候…</p></section>`;
  try {
    const res = await fetch(`${DATA[game]}?v=${Date.now()}`, { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (!Array.isArray(data) || !data.length) throw new Error('数据格式为空');
    rows = data.filter(r => Array.isArray(isDLT()?r.front:r.red) && Array.isArray(isDLT()?r.back:r.blue));
    if (!rows.length) throw new Error('没有有效开奖记录');
    seedBase = Number(String(rows[0].issue).replace(/\D/g,'')) || 1;
    baseRender();
  } catch (e) {
    console.error(e);
    $('#app').innerHTML = `<section class="card error"><div class="error-icon">!</div><h2>数据加载失败</h2><p>请检查网络后点击右上角“刷新数据”。</p><small>${esc(e.message)}</small></section>`;
  }
}

document.querySelectorAll('.tab').forEach(btn => btn.addEventListener('click', () => {
  document.querySelectorAll('.tab').forEach(x => x.classList.remove('active'));
  btn.classList.add('active');
  game = btn.dataset.game;
  load();
}));
$('#refresh').addEventListener('click', load);
load();
