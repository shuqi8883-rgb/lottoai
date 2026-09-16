import json, urllib.request, re
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

DATA=Path('docs/jobs/data')
SEED_FILE=DATA/'companies.json'
DISCOVERY_SOURCES={
    'greenhouse':'https://raw.githubusercontent.com/Feashliaa/job-board-aggregator/main/data/greenhouse_companies.json',
    'ashby':'https://raw.githubusercontent.com/Feashliaa/job-board-aggregator/main/data/ashby_companies.json',
    'lever':'https://raw.githubusercontent.com/Feashliaa/job-board-aggregator/main/data/lever_companies.json',
}
ENTRY=['intern','internship','graduate','new grad','entry level','campus','university','校招','应届','实习','毕业生','junior']
CHINA=['china','中国','beijing','北京','shanghai','上海','shenzhen','深圳','guangzhou','广州','hangzhou','杭州','chengdu','成都','nanjing','南京','wuhan','武汉','xiamen','厦门','suzhou','苏州','tianjin','天津','chongqing','重庆','remote','远程','asia','hong kong','hongkong','singapore','japan','tokyo']
MAJ={'计算机':['software','engineer','developer','data','ai','machine learning','devops','security','it','technology'],'管理学':['operations','business','marketing','sales','hr','project','customer','finance'],'经济学':['finance','economics','analyst','accounting','investment'],'文学':['content','editor','communications','writer','copywriter'],'外语':['language','translator','localization','bilingual'],'教育学':['education','training','learning','teacher','teaching','academic'],'设计':['design','ux','ui','visual','product designer'],'艺术学':['creative','media','music','art','video','production']}

def get(u):
    r=urllib.request.Request(u,headers={'User-Agent':'GraduateJobRadar/3.0'})
    with urllib.request.urlopen(r,timeout=20) as x:return json.loads(x.read().decode())

def clean(s):return re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',s or '')).strip()

def add(out,c,t,l,d,u,upd,src,i,require_china=True):
    text=clean(f'{t} {l} {d}'); low=text.lower()
    if require_china and not any(k in low for k in CHINA): return
    lev='应届/校招' if any(k in low for k in ENTRY) else '社招/初级'
    major=' '.join(m for m,ks in MAJ.items() if any(k in low for k in ks)) or '综合专业'
    out.append({'id':i,'company':c['name'],'title':t,'location':l or '未注明','level':lev,'major':major,'source':src,'updated_at':upd or datetime.now(timezone.utc).isoformat(),'url':u or c['official'],'description':text[:900]})

def discover():
    seed=json.loads(SEED_FILE.read_text(encoding='utf-8'))
    by_key={(c.get('ats'),c.get('board')):c for c in seed if c.get('ats') and c.get('board')}
    for ats,url in DISCOVERY_SOURCES.items():
        try:
            slugs=get(url)
            for slug in slugs:
                key=(ats,slug)
                if key not in by_key:
                    by_key[key]={'id':f'{ats}-{slug}','name':slug.replace('-',' ').title(),'category':'公开招聘企业','regions':'全球/中国待识别','official':({'greenhouse':f'https://boards.greenhouse.io/{slug}','ashby':f'https://jobs.ashbyhq.com/{slug}','lever':f'https://jobs.lever.co/{slug}'}[ats]),'ats':ats,'board':slug,'discovered':True}
        except Exception as e:
            print('discovery failed',ats,e)
    return list(by_key.values())

def fetch_company(c):
    out=[]; status={'company':c['name'],'ats':c['ats'],'board':c['board'],'ok':False,'jobs':0}
    try:
        if c['ats']=='greenhouse':
            data=get(f"https://boards-api.greenhouse.io/v1/boards/{c['board']}/jobs?content=true")
            # Replace slug-derived names with the actual public board name when available.
            if data.get('jobs') and c.get('discovered'):
                c['name']=clean(data['jobs'][0].get('company_name') or c['name'])
            for j in data.get('jobs',[]): add(out,c,j.get('title',''),(j.get('location') or {}).get('name',''),j.get('content',''),j.get('absolute_url'),j.get('updated_at'),'Greenhouse',f"gh-{c['board']}-{j.get('id')}")
        elif c['ats']=='ashby':
            data=get(f"https://api.ashbyhq.com/posting-api/job-board/{c['board']}?includeCompensation=true")
            for j in data.get('jobs',[]): add(out,c,j.get('title',''),j.get('location',''),j.get('descriptionPlain','') or j.get('descriptionHtml',''),j.get('jobUrl') or j.get('applyUrl'),j.get('publishedAt') or j.get('updatedAt'),'Ashby',f"ashby-{c['board']}-{j.get('jobUrl','')}")
        elif c['ats']=='lever':
            data=get(f"https://api.lever.co/v0/postings/{c['board']}?mode=json")
            for j in data if isinstance(data,list) else []:
                loc=(j.get('categories') or {}).get('location','')
                cats=j.get('categories') or {}
                text=' '.join([j.get('text',''),j.get('descriptionPlain',''),j.get('description',''),cats.get('team',''),cats.get('commitment','')])
                add(out,c,j.get('text',''),loc,text,j.get('hostedUrl') or j.get('applyUrl'),j.get('createdAt') and datetime.fromtimestamp(j['createdAt']/1000,tz=timezone.utc).isoformat(),'Lever',f"lever-{c['board']}-{j.get('id')}")
        status.update(ok=True,jobs=len(out))
    except Exception as e: status['error']=str(e)[:180]
    return c,out,status

companies=discover()
jobs=[]; statuses=[]
# Public ATS discovery can contain thousands of boards, so fetch concurrently and keep only currently published jobs.
with ThreadPoolExecutor(max_workers=20) as pool:
    futures=[pool.submit(fetch_company,c) for c in companies]
    for f in as_completed(futures):
        c,rows,st=f.result(); jobs.extend(rows); statuses.append(st)

seen=set(); jobs=[j for j in sorted(jobs,key=lambda x:x['updated_at'],reverse=True) if not (j['id'] in seen or seen.add(j['id']))]
# Keep only companies that actually returned at least one public China/Asia/remote listing, plus the manually curated official companies.
active_ids={j['company'] for j in jobs}
active=[]
for c in companies:
    if c['name'] in active_ids or not c.get('discovered'): active.append(c)
companies=active
DATA.mkdir(parents=True,exist_ok=True)
(SEED_FILE).write_text(json.dumps(companies,ensure_ascii=False,indent=2),encoding='utf-8')
(DATA/'jobs.json').write_text(json.dumps(jobs,ensure_ascii=False,indent=2),encoding='utf-8')
(DATA/'update-meta.json').write_text(json.dumps({'updated_at':datetime.now(timezone.utc).isoformat(),'company_count':len(companies),'discovered_company_count':sum(1 for c in companies if c.get('discovered')),'job_count':len(jobs),'sources':statuses},ensure_ascii=False,indent=2),encoding='utf-8')
print('updated',len(companies),'companies and',len(jobs),'jobs')
