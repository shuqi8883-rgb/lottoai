import json, urllib.request, re
from datetime import datetime, timezone
from pathlib import Path

BOARDS = [
    ("greenhouse", "stripe", "Stripe"),
    ("greenhouse", "datadog", "Datadog"),
    ("greenhouse", "gitlab", "GitLab"),
    ("greenhouse", "coinbase", "Coinbase"),
]

CHINA = ["china","中国","beijing","北京","shanghai","上海","shenzhen","深圳","guangzhou","广州","hangzhou","杭州","chengdu","成都","nanjing","南京","wuhan","武汉","remote","远程"]
ENTRY = ["intern","internship","graduate","new grad","entry level","campus","university","校招","应届","实习","毕业生","junior"]
MAJORS = {
    "计算机": ["software","engineer","developer","data","ai","machine learning","devops","security"],
    "管理学": ["operations","business","marketing","sales","hr","human resources","project"],
    "经济学": ["finance","economics","analyst","accounting"],
    "文学": ["content","editor","communications","writer","copywriter"],
    "外语": ["language","translator","localization","customer success"],
    "教育学": ["education","training","learning","instructional"],
    "设计": ["design","ux","ui","visual","product designer"],
    "艺术学": ["creative","design","content","media"],
}

def get(url):
    req=urllib.request.Request(url,headers={"User-Agent":"GraduateJobRadar/1.0 (public job aggregation)"})
    with urllib.request.urlopen(req,timeout=25) as r:
        return json.loads(r.read().decode("utf-8"))

def classify(text):
    t=text.lower()
    majors=[m for m,ks in MAJORS.items() if any(k in t for k in ks)]
    return " ".join(majors) or "综合专业"

def main():
    jobs=[]
    for ats,slug,company in BOARDS:
        try:
            if ats=="greenhouse":
                data=get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true")
                for j in data.get("jobs",[]):
                    loc=(j.get("location") or {}).get("name","")
                    title=j.get("title","")
                    content=re.sub(r"<[^>]+>"," ",j.get("content","") or "")
                    text=(title+" "+loc+" "+content).lower()
                    if not any(k in text for k in CHINA):
                        continue
                    level="应届/校招" if any(k in text for k in ENTRY) else "社招/初级"
                    jobs.append({"id":f"gh-{slug}-{j.get('id')}","company":company,"title":title,"location":loc or "China/Remote","level":level,"major":classify(text),"source":"Greenhouse","updated_at":j.get("updated_at"),"url":j.get("absolute_url"),"description":content[:900]})
        except Exception as e:
            print("skip",company,e)
    # Deduplicate and prioritize entry-level roles.
    seen=set(); clean=[]
    for j in sorted(jobs,key=lambda x:("应届" not in x["level"], x.get("updated_at") or ""),reverse=False):
        if j["id"] not in seen and j.get("url"):
            seen.add(j["id"]); clean.append(j)
    out=Path("docs/jobs/data/jobs.json")
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(clean,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"wrote {len(clean)} China/remote jobs")

if __name__=="__main__": main()
