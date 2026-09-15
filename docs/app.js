const DATA={ssq:'data/ssq.json',dlt:'data/dlt.json'};
let game='ssq', rows=[], allRows=[];
const $=s=>document.querySelector(s);
function pad(n){return String(n).padStart(2,'0')}
function nums(r){return game==='ssq'?r.red.map(Number):r.front.map(Number)}
function sec(r){return game==='ssq'?r.blue.map(Number):r.back.map(Number)}
function freq(window=100){const c={}; for(const r of rows.slice(0,window)) for(const n of nums(r)) c[n]=(c[n]||0)+1; return c}
function omission(maxn){const o={}; for(let n=1;n<=maxn;n++)o[n]=rows.length; for(let i=0;i<rows.length;i++) for(const n of nums(rows[i])) if(o[n]===rows.length)o[n]=i; return o}
function secFreq(){const c={};for(const r of rows.slice(0,100))for(const n of sec(r))c[n]=(c[n]||0)+1;return c}
function top(obj,desc=true,n=8){return Object.keys(obj).map(Number).sort((a,b)=>desc?(obj[b]-obj[a]||a-b):(obj[a]-obj[b]||a-b)).slice(0,n)}
function mean(arr){return arr.reduce((a,b)=>a+b,0)/(arr.length||1)}
function stats(){
 const maxn=game==='ssq'?33:35,f=freq(100),o=omission(maxn);
 const hot=top(f,true),cold=top(f,false),over=top(o,true);
 const sums=rows.slice(0,100).map(r=>nums(r).reduce((a,b)=>a+b,0));
 const odd=rows.slice(0,100).map(r=>nums(r).filter(x=>x%2).length);
 return {maxn,f,o,hot,cold,over,avgSum:mean(sums),avgOdd:mean(odd)}
}
function comboScore(c,s){
 let v=0; for(const n of c){const z=s.f[n]||0;v+=1-Math.min(Math.abs(z-(100*(game==='ssq'?6:5)/s.maxn))/8,1);v+=Math.min((s.o[n]||0)/30,1)*.2}
 const k=c.length,odd=c.filter(x=>x%2).length,small=c.filter(x=>x<=s.maxn/2).length;
 v+=(1-Math.min(Math.abs(odd-k/2)/k,1));v+=(1-Math.min(Math.abs(small-k/2)/k,1));
 const sorted=[...c].sort((a,b)=>a-b);let run=0;for(let i=1;i<sorted.length;i++)if(sorted[i]===sorted[i-1]+1)run++;v-=Math.max(0,run-2)*.35;
 return v
}
function randomCombo(max,k){const a=[];while(a.length<k){const n=1+Math.floor(Math.random()*max);if(!a.includes(n))a.push(n)}return a.sort((a,b)=>a-b)}
function candidates(n=8){
 const s=stats(), max=s.maxn,k=game==='ssq'?6:5,sm=game==='ssq'?16:12,sk=game==='ssq'?1:2, sf=secFreq(), arr=[];
 for(let i=0;i<30000;i++){const c=randomCombo(max,k);let score=comboScore(c,s);const b=randomCombo(sm,sk);score+=b.reduce((x,n)=>x+Math.min(sf[n]||0,8)*.03,0);arr.push({c,b,score})}
 arr.sort((a,b)=>b.score-a.score);const out=[];
 for(const x of arr){if(out.every(y=>x.c.filter(n=>y.c.includes(n)).length<=(game==='ssq'?4:3)))out.push(x);if(out.length>=n)break}
 return out
}
function balls(c,blue=false){return c.map(n=>`<span class="ball ${blue?'blue':''}">${pad(n)}</span>`).join('')}
function pills(a){return a.map(n=>`<span class="pill">${pad(n)}</span>`).join('')}
function render(){
 const s=stats(), pick=candidates(6), latest=rows[0], secn=sec(latest);
 const sum=nums(latest).reduce((a,b)=>a+b,0);
 $('#app').innerHTML=`
 <div class="grid">
 <section class="card">
  <div class="hero"><div><h2>${game==='ssq'?'双色球':'超级大乐透'}</h2><div class="issue">最新：${latest.issue} · ${latest.date||latest.draw_date||''}</div></div><div class="small">样本 ${rows.length} 期</div></div>
  <div class="balls">${balls(nums(latest))}${balls(secn,true)}</div>
  <div class="metric"><span>本期主区和值</span><b>${sum}</b></div>
  <div class="metric"><span>本期奇数个数</span><b>${nums(latest).filter(x=>x%2).length}</b></div>
 </section>
 <section class="card">
  <h2>近100期画像</h2>
  <div class="metric"><span>平均和值</span><b>${s.avgSum.toFixed(1)}</b></div>
  <div class="metric"><span>平均奇数个数</span><b>${s.avgOdd.toFixed(2)}</b></div>
  <div><div class="small">🔥 高频</div>${pills(s.hot)}</div>
  <div><div class="small">❄️ 低频</div>${pills(s.cold)}</div>
  <div><div class="small">⏳ 当前遗漏较高</div>${pills(s.over)}</div>
 </section>
 <section class="card wide">
  <h2>🏆 今日候选 Top 6</h2>
  <div class="small">这是组合排序分，不是中奖概率；每天数据更新后重新计算。</div>
  ${pick.map((x,i)=>`<div class="rank"><div class="ranknum">#${i+1}</div><div style="flex:1"><div class="balls">${balls(x.c)}${balls(x.b,true)}</div></div><div class="small">${x.score.toFixed(2)}</div></div>`).join('')}
 </section>
 <section class="card">
  <h2>🔬 方法</h2>
  <div class="metric"><span>统计窗口</span><b>30 / 50 / 100</b></div>
  <div class="metric"><span>组合搜索</span><b>30,000 次/刷新</b></div>
  <div class="metric"><span>过滤</span><b>奇偶·大小·连号·重叠</b></div>
  <p class="notice">后续版本将加入严格 walk-forward 回测、模型版本锁定、预测审计台账、蒙特卡洛覆盖优化和模型基线比较。</p>
 </section>
 <section class="card">
  <h2>📊 下一步</h2>
  <p class="notice">自动同步开奖数据 → 开奖后自动结算昨日预测 → 更新回测曲线 → 生成今日候选 → 保留每期历史记录。</p>
  <p class="good">目标：让“准不准”可以被长期验证，而不是只展示漂亮号码。</p>
 </section>
 </div>`;
}
async function load(){
 $('#app').innerHTML='<div class="card">正在加载数据…</div>';
 try{const r=await fetch(DATA[game]+'?t='+Date.now());allRows=await r.json();rows=allRows;render()}catch(e){$('#app').innerHTML='<div class="card"><h2>数据加载失败</h2><p class="notice">请先通过 GitHub Actions 更新 docs/data，或检查网络。</p></div>'}
}
document.querySelectorAll('.tab').forEach(b=>b.onclick=()=>{document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));b.classList.add('active');game=b.dataset.game;load()});
$('#refresh').onclick=load; load();
