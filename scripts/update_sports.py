import json
import math
import os
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

OUT = 'docs/data/sports.json'
TZ = ZoneInfo('Asia/Shanghai')
NOW = datetime.now(TZ)
TODAY = NOW.date()
START = TODAY - timedelta(days=45)
END = TODAY + timedelta(days=3)

SOCCER = {
    'eng.1': '英超',
    'esp.1': '西甲',
    'ita.1': '意甲',
    'ger.1': '德甲',
    'fra.1': '法甲',
    'uefa.champions': '欧冠',
}
BASKETBALL = {
    'nba': 'NBA',
    'wnba': 'WNBA',
    'mens-college-basketball': 'NCAA篮球',
}


def get_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'LottoAI/1.0'})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)


def scoreboard(sport, league):
    dates = f'{START:%Y%m%d}-{END:%Y%m%d}'
    url = f'https://site.api.espn.com/apis/site/v2/sports/{sport}/{urllib.parse.quote(league, safe=".")}/scoreboard?dates={dates}&limit=1000'
    try:
        return get_json(url).get('events', [])
    except Exception as e:
        print('WARN', league, e)
        return []


def event_to_game(event, sport, league, league_name):
    comp = (event.get('competitions') or [{}])[0]
    teams = comp.get('competitors') or []
    if len(teams) < 2:
        return None
    home = next((x for x in teams if x.get('homeAway') == 'home'), teams[0])
    away = next((x for x in teams if x.get('homeAway') == 'away'), teams[1])
    status = (event.get('status') or {}).get('type') or {}
    state = status.get('state', 'pre')
    completed = bool(status.get('completed')) or state == 'post'
    def score(x):
        try:
            return float(x.get('score'))
        except Exception:
            return None
    hs, aws = score(home), score(away)
    dt = event.get('date')
    try:
        local_dt = datetime.fromisoformat(dt.replace('Z', '+00:00')).astimezone(TZ)
    except Exception:
        local_dt = NOW
    return {
        'id': str(event.get('id')),
        'sport': sport,
        'league': league,
        'leagueName': league_name,
        'date': local_dt.isoformat(),
        'dateLocal': local_dt.strftime('%Y-%m-%d %H:%M'),
        'status': 'finished' if completed else ('live' if state == 'in' else 'scheduled'),
        'home': home.get('team', {}).get('displayName') or home.get('athlete', {}).get('displayName') or home.get('displayName'),
        'away': away.get('team', {}).get('displayName') or away.get('athlete', {}).get('displayName') or away.get('displayName'),
        'homeAbbr': home.get('team', {}).get('abbreviation', ''),
        'awayAbbr': away.get('team', {}).get('abbreviation', ''),
        'homeScore': int(hs) if hs is not None and hs.is_integer() else hs,
        'awayScore': int(aws) if aws is not None and aws.is_integer() else aws,
    }


def poisson_pmf(k, lam):
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def team_stats(games, sport):
    hist = defaultdict(list)
    for g in games:
        if g['status'] != 'finished' or g['homeScore'] is None or g['awayScore'] is None:
            continue
        h, a = g['home'], g['away']
        if sport == 'soccer':
            hist[h].append((g['homeScore'], g['awayScore']))
            hist[a].append((g['awayScore'], g['homeScore']))
        else:
            hist[h].append((g['homeScore'], g['awayScore']))
            hist[a].append((g['awayScore'], g['homeScore']))
    out = {}
    for team, vals in hist.items():
        vals = vals[-10:]
        gf = sum(x for x, _ in vals) / len(vals)
        ga = sum(y for _, y in vals) / len(vals)
        wins = sum(x > y for x, y in vals)
        losses = sum(x < y for x, y in vals)
        out[team] = {'gf': gf, 'ga': ga, 'winRate': wins / len(vals), 'n': len(vals)}
    return out


def league_average(games):
    vals = [(g['homeScore'], g['awayScore']) for g in games if g['status'] == 'finished' and g['homeScore'] is not None and g['awayScore'] is not None]
    if not vals:
        return 1.35, 1.15
    return sum(x for x, _ in vals) / len(vals), sum(y for _, y in vals) / len(vals)


def predict_soccer(g, stats, avg_home, avg_away):
    h = stats.get(g['home'], {'gf': avg_home, 'ga': avg_away, 'winRate': .33, 'n': 0})
    a = stats.get(g['away'], {'gf': avg_away, 'ga': avg_home, 'winRate': .33, 'n': 0})
    lh = max(.15, .55*h['gf'] + .45*a['ga'] + .12)
    la = max(.10, .55*a['gf'] + .45*h['ga'] - .05)
    matrix = []
    for i in range(6):
        for j in range(6):
            p = poisson_pmf(i, lh) * poisson_pmf(j, la)
            matrix.append((p, i, j))
    matrix.sort(reverse=True)
    best = matrix[0]
    home_p = sum(p for p, i, j in matrix if i > j)
    draw_p = sum(p for p, i, j in matrix if i == j)
    away_p = sum(p for p, i, j in matrix if i < j)
    total = lh + la
    return {
        'type': 'football', 'homeWin': round(home_p, 3), 'draw': round(draw_p, 3), 'awayWin': round(away_p, 3),
        'score': f'{best[1]}-{best[2]}', 'total': round(total, 2),
        'totalBand': '0-1' if total < 1.75 else ('2-3' if total < 3.25 else '4+'),
        'over25': round(1 - sum(poisson_pmf(k, total) for k in range(3)), 3),
        'confidence': round(min(0.88, .48 + abs(home_p-away_p)*.45 + abs(total-2.5)*.04), 2),
        'model': '近10场攻防 + 主场修正 + 泊松比分'
    }


def predict_basketball(g, stats, avg_home, avg_away):
    h = stats.get(g['home'], {'gf': avg_home, 'ga': avg_away, 'winRate': .5, 'n': 0})
    a = stats.get(g['away'], {'gf': avg_away, 'ga': avg_home, 'winRate': .5, 'n': 0})
    hp = .55*h['gf'] + .45*a['ga'] + 2.2
    ap = .55*a['gf'] + .45*h['ga']
    diff = hp - ap
    win = 1 / (1 + math.exp(-diff / 7.5))
    total = hp + ap
    return {
        'type': 'basketball', 'homeWin': round(win, 3), 'draw': 0, 'awayWin': round(1-win, 3),
        'score': f'{round(hp)}-{round(ap)}', 'total': round(total, 1),
        'totalBand': '低于210' if total < 210 else ('210-229' if total < 230 else ('230-249' if total < 250 else '250+')),
        'confidence': round(min(.9, .50 + abs(win-.5)*.72), 2),
        'model': '近10场得失分 + 主场修正 + Logistic胜率'
    }


def main():
    all_games = []
    leagues = []
    for league, name in SOCCER.items():
        games = [event_to_game(e, 'soccer', league, name) for e in scoreboard('soccer', league)]
        games = [g for g in games if g]
        stats = team_stats(games, 'soccer')
        avgh, avga = league_average(games)
        for g in games:
            if g['status'] == 'scheduled':
                g['prediction'] = predict_soccer(g, stats, avgh, avga)
        all_games.extend(games)
        leagues.append({'sport': 'soccer', 'id': league, 'name': name})
    for league, name in BASKETBALL.items():
        games = [event_to_game(e, 'basketball', league, name) for e in scoreboard('basketball', league)]
        games = [g for g in games if g]
        stats = team_stats(games, 'basketball')
        avgh, avga = league_average(games)
        for g in games:
            if g['status'] == 'scheduled':
                g['prediction'] = predict_basketball(g, stats, avgh, avga)
        all_games.extend(games)
        leagues.append({'sport': 'basketball', 'id': league, 'name': name})

    all_games.sort(key=lambda x: x['date'])
    payload = {
        'updatedAt': NOW.isoformat(),
        'timezone': 'Asia/Shanghai',
        'leagues': leagues,
        'games': all_games,
        'notice': '预测为统计模型输出，不代表实际概率或保证结果；比赛结果具有随机性。'
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, separators=(',', ':'))
    upcoming = [g for g in all_games if g['status'] == 'scheduled' and g['date'].startswith(str(TODAY))]
    print('sports games:', len(all_games), 'today upcoming:', len(upcoming))

if __name__ == '__main__':
    main()
