import json, urllib.request, re
from pathlib import Path
from datetime import datetime, timezone
DATA=Path('docs/jobs/data'); companies=json.loads((DATA/'companies.json').read_text(encoding='utf-8'))
ENTRY=['intern','internship','graduate','new grad','entry level','campus','university','校招','应届','实习','毕业生','junior']
CHINA=['china','中国','beijing','北京','shanghai','上海','shenzhen','深圳','guangzhou','广州','hangzhou','杭州','chengdu','成都','nanjing','南京','wuhan','武汉','remote','远程','asia']
MAJ={'计算机':['software','engineer','developer','data','ai','machine learning','devops','security'],'管理学':['operations','business','marketing','sales','hr','project'],'经济学':['finance','economics','analyst','accounting'],'文学':['content','editor','communications','writer'],'外语':['language','translator','localization'],'教育学':['education','training','learning','teacher'],'设计':['design','ux','ui','visual'],'艺术学':['creative','media','music','art']}
def get(u):
 r=urllib.request.Request(u,headers={'User-Agent':'GraduateJobRadar/2.0'})
 with urllib.request.urlopen(r,timeout=25) as x:return json.loads(x.read().decode())
def clean(s):return re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',s or '')).strip()
def add(out,c,t,l,d,u,upd,src,i):
 text=clean(f'{t} {l} {d}'); low=text.lower()
 if not any(k in low for k in CHINA):return
 lev='应届/校招' if any(k in low for k in ENTRY) else '社招/初级'; major=' '.join(m for m,ks in MAJ.items() if any(k in low for k in ks)) or '综合专业'
 out.append({'id':i,'company':c['name'],'title':t,'location':l or 'China/Remote','level':lev,'major':major,'source':src,'updated_at':upd or datetime.now(timezone.utc).isoformat(),'url':u or c['official'],'description':text[:900]})
jobs=[]; status=[]
for c in companies:
 try:
  before=len(jobs)
  if c['ats']=='greenhouse':
   for j in get(f"https://boards-api.greenhouse.io/v1/boards/{c['board']}/jobs?content=true").get('jobs',[]):add(jobs,c,j.get('title',''),(j.get('location') or {}).get('name',''),j.get('content',''),j.get('absolute_url'),j.get('updated_at'),'Greenhouse',f"gh-{c['id']}-{j.get('id')}")
  elif c['ats']=='ashby':
   for j in get(f"https://api.ashbyhq.com/posting-api/job-board/{c['board']}?includeCompensation=true").get('jobs',[]):add(jobs,c,j.get('title',''),j.get('location',''),j.get('descriptionPlain','') or j.get('descriptionHtml',''),j.get('jobUrl') or j.get('applyUrl'),j.get('publishedAt') or j.get('updatedAt'),'Ashby',f"ashby-{c['id']}-{j.get('id') or j.get('jobUrl','')}")
  status.append({'company':c['name'],'ok':True,'jobs':len(jobs)-before})
 except Exception as e:status.append({'company':c['name'],'ok':False,'jobs':0,'error':str(e)[:160]})
seen=set(); jobs=[j for j in sorted(jobs,key=lambda x:x['updated_at'],reverse=True) if not (j['id'] in seen or seen.add(j['id']))]
DATA.mkdir(parents=True,exist_ok=True); (DATA/'jobs.json').write_text(json.dumps(jobs,ensure_ascii=False,indent=2),encoding='utf-8'); (DATA/'update-meta.json').write_text(json.dumps({'updated_at':datetime.now(timezone.utc).isoformat(),'company_count':len(companies),'job_count':len(jobs),'sources':status},ensure_ascii=False,indent=2),encoding='utf-8')
print('updated',len(jobs),'jobs')
