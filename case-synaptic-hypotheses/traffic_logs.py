"""Describe traffic-counter snapshots from incident logs; do not export identifiers."""
import re,zipfile,tempfile,shutil,json,hashlib
from collections import Counter
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
P=Path(__file__).resolve().parent; PATH=P/'data'/'logs.zip'; Z=None
RE=re.compile(r'(\d{4}-\d{2}-\d{2})T.*?Traffic info changed:\s*(null|\d+) bytes limit,\s*(\d+) bytes used')
def init():
 global Z
 Z=zipfile.ZipFile(PATH)
def read(name):
 counts=Counter(); days={}; folder=name.split('/')[1]
 try:
  with Z.open(name) as src,tempfile.SpooledTemporaryFile(max_size=16*1024*1024) as tmp:
   shutil.copyfileobj(src,tmp);tmp.seek(0)
   with zipfile.ZipFile(tmp) as z:
    for f in z.infolist():
     if f.is_dir() or not f.filename.lower().endswith('.log'):continue
     with z.open(f) as source:
      for raw in source:
       if b'Traffic info changed:' not in raw:continue
       m=RE.search(raw.decode('utf8','replace'))
       if not m:counts['unparsed']+=1;continue
       day,limit,used=m.groups();counts['parsed']+=1;counts['limit_base' if limit=='524288000' else 'limit_null' if limit=='null' else 'limit_other']+=1
       if limit=='524288000':
        key=(folder,day);days[key]=max(days.get(key,0),int(used))
 except (zipfile.BadZipFile,RuntimeError,EOFError,NotImplementedError,OSError): counts['failed_archives']+=1
 return counts,days

def main():
 with zipfile.ZipFile(PATH) as z:names=[x.filename for x in z.infolist() if not x.is_dir() and x.filename.lower().endswith('.zip')]
 counts=Counter();days={}
 with ProcessPoolExecutor(max_workers=3,initializer=init) as pool:
  for i,(c,d) in enumerate(pool.map(read,names,chunksize=1),1):
   counts.update(c)
   for k,v in d.items():days[k]=max(days.get(k,0),v)
   if i%100==0:print(f'processed {i}/{len(names)}',flush=True)
 values=sorted(days.values()); n=len(values);limit=524288000
 with PATH.open('rb') as f:h=hashlib.file_digest(f,'sha256').hexdigest()
 out={'source_sha256':h,'archives':len(names),'counts':dict(counts),'base_limit_observed_folder_days':n,'base_limit_distinct_folders':len({x[0] for x in days}),'base_limit_at_least_90_percent_folder_days':sum(v>=.9*limit for v in values),'base_limit_at_least_100_percent_folder_days':sum(v>=limit for v in values),'base_limit_max_observed_bytes_per_folder_day_median':values[n//2] if n else None,'definition':'Maximum observed counter in application log lines per folder and calendar date when recorded limit equals 524288000 bytes. Incident-selected logs; not complete daily traffic or a representative sample.'}
 (P/'results'/'traffic_logs.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
