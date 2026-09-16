import json, urllib.request, re
from pathlib import Path

BOARDS = [
    ("greenhouse", "stripe", "Stripe"), ("greenhouse", "datadog", "Datadog"),
    ("greenhouse", "gitlab", "GitLab"), ("greenhouse", "coinbase", "Coinbase"),
    ("greenhouse", "anthropic", "Anthropic"),
    ("lever", "palantir", "Palantir"), ("lever", "spotify", "Spotify"),
    ("ashby", "openai", "OpenAI"), ("ashby", "notion", "Notion"),
    ("ashby", "cohere", "Cohere"), ("ashby", "mistral", "Mistral AI"),
]
CHINA = ["china","中国","beijing","北京","shanghai","上海","shenzhen","深圳","guangzhou","广州","hangzhou","杭州","chengdu","成都","nanjing","南京","wuhan","武汉","remote","远程","asia"]
ENTRY = ["intern","internship","graduate","new grad","entry level","campus","university","校招","应届","实习","毕业生","junior","early career"]
MAJORS = {"计算机":["software","engineer","developer","data","ai","machine learning","devops","security"],"管理学":["operations","business","marketing","sales","hr","human resources","project"],"经济学":["finance","economics","analyst","accounting"],"文学":["content","editor","communications","writer","copywriter"],"外语":["language","translator","localization","customer success"],"教育学":["education","training","learning","instructional"],"设计":["design","ux","ui","visual","product designer"],"艺术学":["creative","design","content","media"]}

def get(url):
    req=urllib.request.Request(url,headers={"User-Agent":"GraduateJobRadar/1.0"})
    with urllib.request.urlopen(req,timeout=30) as r:return json.loads(r.read().decode())

def clean_html(s): return re.sub(r"<[^>]+>"," ",s or "")
def classify(text):
    t=text.lower(); return " ".join(m for m,ks in MAJORS.items() if any(k in t for k in ks)) or "综合专业"
def add(jobs,company,title,loc,desc,url,updated,source,ident):
    text=(title+" "+loc+" "+desc).lower()
    if not any(k in text for k in CHINA): return
    level="应届/校招" if any(k in text for k in ENTRY) else "社招/初级"
    jobs.append({"id":ident,"company":company,"title":title,"location":loc or "China/Remote","level":level,"major":classify(text),"source":source,"updated_at":updated,"url":url,"description":clean_html(desc)[:1000]})

def main():
    jobs=[]
    for ats,slug,company in BOARDS:
        try:
            if ats=="greenhouse":
                data=get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true")
                for j in data.get("jobs",[]): add(jobs,company,j.get("title",""),(j.get("location") or {}).get("name",""),j.get("content",""),j.get("absolute_url"),j.get("updated_at"),"Greenhouse",f"gh-{slug}-{j.get('id')}")
            elif ats=="lever":
                data=get(f"https://api.lever.co/v0/postings/{slug}?mode=json")
                for j in data if isinstance(data,list) else []:
                    c=j.get("categories") or {}; loc=c.get("location") or ", ".join(c.get("allLocations") or [])
                    add(jobs,company,j.get("text", ""),loc,j.get("descriptionPlain","") or j.get("description", ""),j.get("hostedUrl"),j.get("createdAt"),"Lever",f"lv-{slug}-{j.get('id')}")
            elif ats=="ashby":
                data=get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true")
                for j in data.get("jobs",[]): add(jobs,company,j.get("title",""),j.get("location",""),j.get("descriptionPlain","") or j.get("descriptionHtml",""),j.get("jobUrl"),j.get("publishedAt") or j.get("updatedAt"),"Ashby",f"ashby-{slug}-{j.get('id')}")
        except Exception as e: print("skip",company,ats,e)
    seen=set(); clean=[]
    for j in sorted(jobs,key=lambda x:("应届" not in x["level"],x.get("updated_at") or "")):
        if j["id"] not in seen and j.get("url"): seen.add(j["id"]); clean.append(j)
    Path("docs/jobs/data").mkdir(parents=True,exist_ok=True)
    Path("docs/jobs/data/jobs.json").write_text(json.dumps(clean,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"wrote {len(clean)} China/Asia/remote jobs")
if __name__=="__main__": main()
