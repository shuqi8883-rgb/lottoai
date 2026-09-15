// LottoAI sports display fix: show today's games, next 48h and recent results.
(function(){
  function renderSportsWindow(){
    if(typeof sportData==='undefined' || !sportData || typeof sport==='undefined') return;
    const app=document.querySelector('#app');
    if(!app) return;
    const all=(sportData.games||[]).filter(g=>g.sport===sport && (league==='all'||g.league===league)).sort((a,b)=>new Date(a.date)-new Date(b.date));
    const now=new Date(), start=now.getTime()-24*3600e3, end=now.getTime()+48*3600e3;
    const focus=all.filter(g=>{const t=new Date(g.date).getTime();return t>=start&&t<=end;});
    const leagues=(sportData.leagues||[]).filter(x=>x.sport===sport);
    const live=focus.filter(g=>g.status==='live').length;
    const upcoming=focus.filter(g=>g.status==='scheduled').length;
    const finished=focus.filter(g=>g.status==='finished').length;
    const title=sport==='football'?'⚽ 足球每日预测':'🏀 篮球每日预测';
    const leagueButtons=`<div class="sub-nav"><button class="sub-btn ${league==='all'?'active':''}" data-league="all">全部赛事</button>${leagues.map(l=>`<button class="sub-btn ${league===l.id?'active':''}" data-league="${esc(l.id)}">${esc(l.name)}</button>`).join('')}</div>`;
    const list=focus.length?`<section class="card"><div class="sports-toolbar"><span class="status">最近24h / 未来48h</span><span class="status">状态/比分</span><span class="status">赛前预测</span></div>${focus.map(matchHTML).join('')}</section>`:`<section class="card empty">当前窗口没有${sport==='football'?'足球':'篮球'}赛事。<div class="footer-note">系统每30分钟自动同步，出现新赛事后会自动显示。</div></section>`;
    app.dataset.sportsWindow='1';
    app.innerHTML=`<section class="hero"><div class="eyebrow">DAILY SPORTS · 自动同步</div><h1>${title}</h1><p class="muted">进行中 ${live} 场 · 未来48小时 ${upcoming} 场 · 最近24小时已结束 ${finished} 场</p><div class="grid"><div>${metric('数据更新时间',(sportData.updatedAt||'').replace('T',' ').slice(0,16))}</div><div>${metric('同步频率','每30分钟')}</div></div></section>${leagueButtons}${list}<section class="card notice"><b>同步说明</b><p>赛事按北京时间显示。赛前显示统计模型预测；比赛进行中/结束后显示最新/最终比分。预测仅供研究参考，不保证结果。</p></section>`;
    $$('.sub-btn').forEach(b=>b.onclick=()=>{league=b.dataset.league;app.dataset.sportsWindow='0';if(typeof renderSports==='function')renderSports();});
  }
  const obs=new MutationObserver(()=>{
    const app=document.querySelector('#app');
    if(!app||app.dataset.sportsWindow==='1') return;
    if(typeof sportData!=='undefined' && sportData && typeof sport!=='undefined' && sport!==''){
      setTimeout(()=>{const a=document.querySelector('#app');if(a&&a.dataset.sportsWindow!=='1')renderSportsWindow();},30);
    }
  });
  obs.observe(document.documentElement,{subtree:true,childList:true});
  window.addEventListener('load',()=>setTimeout(renderSportsWindow,300));
})();
