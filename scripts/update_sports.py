import json
import math
import os
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

OUT = 'docs/data/sports.json'
ARCHIVE = 'docs/data/sports_predictions.json'
TZ = ZoneInfo('Asia/Shanghai')
NOW = datetime.now(TZ)
TODAY = NOW.date()
START = TODAY - timedelta(days=7)
END = TODAY + timedelta(days=7)

SOCCER = {'eng.1':'英超','eng.2':'英冠','esp.1':'西甲','ita.1':'意甲','ger.1':'德甲','fra.1':'法甲','ned.1':'荷甲','por.1':'葡超','sco.1':'苏超','usa.1':'美职联','mex.1':'墨西哥联赛','bra.1':'巴西甲','uefa.champions':'欧冠','uefa.europa':'欧联杯','uefa.europa.conf':'欧协联'}
BASKETBALL = {'nba':'NBA','wnba':'WNBA'}


def get_json(url, retries=3):
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent':'LottoAI/2.0'})
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r)
        except Exception as e:
            last = e
            if attempt + 1 < retries:
                time.sleep(2 * (attempt + 1))
    raise last


def scoreboard(sport, league):
    events = []
    d = START
    while d <= END:
        date = d.strftime('%Y%m%d')
        url = f'https://site.api.espn.com/apis/site/v2/sports/{sport}/{urllib.parse.quote(league, safe=".")}/scoreboard?dates={date}&limit=1000'
        try:
            events.extend(get_json(url).get('events', []))
        except Exception as e:
            print('WARN', league, date, e)
        d += timedelta(days=1)
    seen = {str(e['id']): e for e in events if e.get('id') is not None}
    return list(seen.values())


def event_to_game(event, sport, league, league_name):
    comp = (event.get('competitions') or [{}])[0]
    teams = comp.get('competitors') or []
    if len(teams) < 2: return None
    home = next((x for x in teams if x.get('homeAway') == 'home'), teams[0])
    away = next((x for x in teams if x.get('homeAway') == 'away'), teams[1])
    st = (event.get('status') or {}).get('type') or {}
    state = st.get('state', 'pre')
    completed = bool(st.get('completed')) or state == 'post'
    def score(x):
        try: return float(x.get('score'))
        except Exception: return None
    hs, aws = score(home), score(away)
    try: local_dt = datetime.fromisoformat(event.get('date','').replace('Z','+00:00')).astimezone(TZ)
    except Exception: local_dt = NOW
    return {'id':str(event.get('id')),'sport':sport,'league':league,'leagueName':league_name,
            'date':local_dt.isoformat(),'dateLocal':local_dt.strftime('%Y-%m-%d %H:%M'),
            'status':'finished' if completed else ('live' if state == 'in' else 'scheduled'),
            'home':home.get('team',{}).get('displayName') or home.get('displayName'),
            'away':away.get('team',{}).get('displayName') or away.get('displayName'),
            'homeAbbr':home.get('team',{}).get('abbreviation',''),'awayAbbr':away.get('team',{}).get('abbreviation',''),
            'homeScore':int(hs) if hs is not None and hs.is_integer() else hs,
            'awayScore':int(aws) if aws is not None and aws.is_integer() else aws}


def poisson_pmf(k, lam): return math.exp(-lam) * (lam ** k) / math.factorial(k)


def team_stats(games):
    hist = defaultdict(list)
    for g in games:
        if g['status'] != 'finished' or g['homeScore'] is None or g['awayScore'] is None: continue
        hist[g['home']].append((g['homeScore'],g['awayScore']))
        hist[g['away']].append((g['awayScore'],g['homeScore']))
    return {team:{'gf':sum(x for x,_ in vals[-10:])/len(vals[-10:]),'ga':sum(y for _,y in vals[-10:])/len(vals[-10:]),'winRate':sum(x>y for x,y in vals[-10:])/len(vals[-10:]),'n':len(vals[-10:])} for team,vals in hist.items()}


def league_average(games):
    vals=[(g['homeScore'],g['awayScore']) for g in games if g['status']=='finished' and g['homeScore'] is not None and g['awayScore'] is not None]
    return (1.35,1.15) if not vals else (sum(x for x,_ in vals)/len(vals),sum(y for _,y in vals)/len(vals))


def predict_soccer(g, stats, avg_home, avg_away):
    h=stats.get(g['home'],{'gf':avg_home,'ga':avg_away}); a=stats.get(g['away'],{'gf':avg_away,'ga':avg_home})
    lh=max(.15,.55*h['gf']+.45*a['ga']+.12); la=max(.10,.55*a['gf']+.45*h['ga']-.05)
    matrix=sorted([(poisson_pmf(i,lh)*poisson_pmf(j,la),i,j) for i in range(7) for j in range(7)],reverse=True)
    best=matrix[0]; hp=sum(p for p,i,j in matrix if i>j); dp=sum(p for p,i,j in matrix if i==j); ap=sum(p for p,i,j in matrix if i<j); total=lh+la
    return {'type':'football','homeWin':round(hp,3),'draw':round(dp,3),'awayWin':round(ap,3),'score':f'{best[1]}-{best[2]}','total':round(total,2),'totalBand':'0-1' if total<1.75 else ('2-3' if total<3.25 else '4+'),'over25':round(1-sum(poisson_pmf(k,total) for k in range(3)),3),'confidence':round(min(.88,.48+abs(hp-ap)*.45+abs(total-2.5)*.04),2),'model':'近10场攻防 + 主场修正 + 泊松比分','createdAt':NOW.isoformat()}


def predict_basketball(g, stats, avg_home, avg_away):
    h=stats.get(g['home'],{'gf':avg_home,'ga':avg_away}); a=stats.get(g['away'],{'gf':avg_away,'ga':avg_home})
    hp=.55*h['gf']+.45*a['ga']+2.2; ap=.55*a['gf']+.45*h['ga']; win=1/(1+math.exp(-(hp-ap)/7.5)); total=hp+ap
    return {'type':'basketball','homeWin':round(win,3),'draw':0,'awayWin':round(1-win,3),'score':f'{round(hp)}-{round(ap)}','total':round(total,1),'totalBand':'低于210' if total<210 else ('210-229' if total<230 else ('230-249' if total<250 else '250+')),'confidence':round(min(.9,.50+abs(win-.5)*.72),2),'model':'近10场得失分 + 主场修正 + Logistic胜率','createdAt':NOW.isoformat()}


def load_archive():
    try:
        with open(ARCHIVE,encoding='utf-8') as f: data=json.load(f)
        return data if isinstance(data,dict) else {}
    except Exception: return {}


def result_evaluation(game):
    p=game.get('prediction') or {}; hs=game.get('homeScore'); aws=game.get('awayScore')
    if game.get('status')!='finished' or hs is None or aws is None or not p: return None
    if game['sport']=='soccer':
        actual='home' if hs>aws else ('draw' if hs==aws else 'away'); probs={'home':p.get('homeWin',0),'draw':p.get('draw',0),'away':p.get('awayWin',0)}; predicted=max(probs,key=probs.get)
        ps=str(p.get('score','0-0')).split('-'); score_hit=len(ps)==2 and int(hs)==int(ps[0]) and int(aws)==int(ps[1]); total=hs+aws; band='0-1' if total<=1 else ('2-3' if total<=3 else '4+'); over25_hit=(total>2)==(p.get('over25',.5)>=.5)
    else:
        actual='home' if hs>aws else 'away'; predicted='home' if p.get('homeWin',0)>=p.get('awayWin',0) else 'away'; ps=str(p.get('score','0-0')).split('-'); score_hit=len(ps)==2 and abs(float(hs)-float(ps[0]))<=5 and abs(float(aws)-float(ps[1]))<=5; total=hs+aws; band='低于210' if total<210 else ('210-229' if total<230 else ('230-249' if total<250 else '250+')); over25_hit=None
    return {'outcome':actual,'predictedOutcome':predicted,'outcomeHit':actual==predicted,'scoreHit':score_hit,'totalBandActual':band,'totalBandHit':band==p.get('totalBand'),'over25Hit':over25_hit,'evaluatedAt':NOW.isoformat()}


def build_settlement(games):
    settled=[g for g in games if g.get('evaluation')]
    def stats(items):
        if not items: return {'games':0,'outcomeAccuracy':None,'scoreHitRate':None,'totalBandAccuracy':None}
        return {'games':len(items),'outcomeAccuracy':round(sum(x['evaluation']['outcomeHit'] for x in items)/len(items),3),'scoreHitRate':round(sum(x['evaluation']['scoreHit'] for x in items)/len(items),3),'totalBandAccuracy':round(sum(x['evaluation']['totalBandHit'] for x in items)/len(items),3)}
    return {'overall':stats(settled),'football':stats([g for g in settled if g['sport']=='soccer']),'basketball':stats([g for g in settled if g['sport']=='basketball']),'lastUpdated':NOW.isoformat()}


def main():
    archive=load_archive(); predictions=archive.get('predictions',{}) if isinstance(archive,dict) else {}; all_games=[]; leagues=[]
    for sport_name,mapping in [('soccer',SOCCER),('basketball',BASKETBALL)]:
        for league,name in mapping.items():
            games=[event_to_game(e,sport_name,league,name) for e in scoreboard(sport_name,league)]; games=[g for g in games if g]
            stats=team_stats(games); avgh,avga=league_average(games)
            for g in games:
                key=str(g['id'])
                if g['status']=='scheduled':
                    if key not in predictions: predictions[key]=predict_soccer(g,stats,avgh,avga) if sport_name=='soccer' else predict_basketball(g,stats,avgh,avga)
                    g['prediction']=predictions[key]
                elif key in predictions: g['prediction']=predictions[key]
                if g['status']=='finished':
                    ev=result_evaluation(g)
                    if ev: g['evaluation']=ev
                all_games.append(g)
            leagues.append({'sport':sport_name,'id':league,'name':name})
    cutoff=NOW-timedelta(days=180); predictions={k:v for k,v in predictions.items() if _created_after(v,cutoff)}
    settlement=build_settlement(all_games)
    os.makedirs(os.path.dirname(ARCHIVE),exist_ok=True)
    with open(ARCHIVE,'w',encoding='utf-8') as f: json.dump({'updatedAt':NOW.isoformat(),'predictions':predictions,'settlement':settlement},f,ensure_ascii=False,separators=(',',':'))
    all_games.sort(key=lambda x:x['date'])
    payload={'updatedAt':NOW.isoformat(),'timezone':'Asia/Shanghai','predictionDate':str(TODAY),'range':{'start':str(START),'end':str(END)},'leagues':leagues,'games':all_games,'settlement':settlement,'notice':'赛事数据来自公开体育数据接口；预测为统计模型输出，不代表实际概率或保证结果。'}
    with open(OUT,'w',encoding='utf-8') as f: json.dump(payload,f,ensure_ascii=False,separators=(',',':'))
    print('sports games:',len(all_games),'scheduled:',sum(g['status']=='scheduled' for g in all_games),'live:',sum(g['status']=='live' for g in all_games),'finished:',sum(g['status']=='finished' for g in all_games),'archived predictions:',len(predictions),'settled:',settlement['overall']['games'])


def _created_after(v, cutoff):
    try: return datetime.fromisoformat(v['createdAt']).astimezone(TZ) >= cutoff
    except Exception: return False

if __name__=='__main__': main()
