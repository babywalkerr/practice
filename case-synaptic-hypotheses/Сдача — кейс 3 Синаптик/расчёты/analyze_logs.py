"""Aggregate incident archives; no raw lines or identifiers are exported."""
import zipfile,re,json,hashlib,tempfile,shutil,argparse
from pathlib import Path
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
P=Path(__file__).resolve().parent; PATH=P/'data'/'logs.zip'
PATTERNS={k:re.compile(v,re.I) for k,v in {'vpn_start_timeout':r'vpn did not turn on within the allotted time','dns_pending_request':r'cannot find the pending request','connection_refused':r'connection (?:was )?refused','timeout':r'timed?\s*out|timeout','dns':r'\bdns\b|name resolution|no such host','network_unreachable':r'network is unreachable|no route to host','tls_certificate':r'\btls\b|certificate|\bssl\b','socket':r'socketexception|socket error'}.items()}
OUTER=None
def init(path):
 global OUTER
 OUTER=zipfile.ZipFile(path)
def analyze(name):
 summary=Counter(nested_archives=1); cats=Counter(); seen=set(); platforms=Counter(); failure=''
 try:
  with OUTER.open(name) as stream, tempfile.SpooledTemporaryFile(max_size=16*1024*1024) as tmp:
   shutil.copyfileobj(stream,tmp); tmp.seek(0)
   with zipfile.ZipFile(tmp) as inner:
    for f in inner.infolist():
     if f.is_dir():continue
     filename=f.filename.lower(); kind='vpn_error' if 'vpn_error_log' in filename else ('app' if filename.endswith('.log') else 'other')
     if kind=='other':continue
     summary[kind+'_files']+=1
     with inner.open(f) as src:
      for raw in src:
       line=raw.decode('utf-8','replace'); low=line.lower()
       if kind=='app' and 'running on os.' in low:
        m=re.search(r'running on os\.([a-z]+)',low)
        if m:platforms[m.group(1)]+=1
       iserr=(kind=='vpn_error' and ('[error]' in low or '[fatal]' in low)) or (kind=='app' and ('[e]' in low or '[error]' in low))
       if not iserr:continue
       summary[kind+'_error_lines']+=1
       for key,pat in PATTERNS.items():
        if pat.search(line):cats[kind+':'+key]+=1;seen.add(kind+':'+key)
 except (zipfile.BadZipFile,RuntimeError,EOFError,NotImplementedError,OSError) as e:
  summary['failed_archives']+=1;failure=type(e).__name__
 return summary,cats,Counter(seen),platforms,failure

def main():
 parser=argparse.ArgumentParser()
 parser.add_argument('--input',type=Path,default=PATH); parser.add_argument('--names',type=Path); parser.add_argument('--output',type=Path,default=P/'results'/'logs_metrics.json'); parser.add_argument('--skip-hash',action='store_true')
 args=parser.parse_args()
 with zipfile.ZipFile(args.input) as outer:
  names=[x.filename for x in outer.infolist() if not x.is_dir() and x.filename.lower().endswith('.zip')]
 if args.names:
  selected=set(json.loads(args.names.read_text())); names=[n for n in names if n in selected]
 summary=Counter();cats=Counter();archives=Counter();platforms=Counter();failures=Counter(); folders_by_category={}
 with ProcessPoolExecutor(max_workers=3,initializer=init,initargs=(args.input,)) as pool:
  for i,(s,c,a,p,f) in enumerate(pool.map(analyze,names,chunksize=1),1):
   summary.update(s);cats.update(c);archives.update(a);platforms.update(p)
   for category in a: folders_by_category.setdefault(category,set()).add(names[i-1].split('/')[1])
   if f:failures[f]+=1
   if i%100==0:print(f'processed {i}/{len(names)}',flush=True)
 summary['distinct_user_folders']=len({n.split('/')[1] for n in names})
 digest=None
 if not args.skip_hash:
  with args.input.open('rb') as source: digest=hashlib.file_digest(source,'sha256').hexdigest()
 out={'source_sha256':digest,'summary':dict(summary),'error_lines_by_category':dict(cats),'archives_with_category':dict(archives),'folders_with_category':{k:len(v) for k,v in folders_by_category.items()},'app_platform_markers':dict(platforms),'read_failures':dict(failures),'rules':'Categories may overlap. VPN errors: [Error]/[Fatal]; app errors: [E]/[Error]. Counts are lines and archives, not users or incidents.'}
 args.output.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
