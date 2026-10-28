import csv,sqlite3,json,hashlib,tempfile,os
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
P=Path(__file__).resolve().parent; D=P/'data'
def rows(name,n):
 with (D/name).open(encoding='utf-8-sig',newline='') as f:
  for i,r in enumerate(csv.reader(f,delimiter=';'),1):
   if len(r)!=n: raise ValueError((name,i,len(r)))
   yield r
fd,path=tempfile.mkstemp(suffix='.sqlite'); os.close(fd)
try:
 c=sqlite3.connect(path); c.execute('pragma journal_mode=off'); c.execute('create table users(id text primary key, created text, trial text)'); c.execute('create table devices(uid text, ident text)'); c.execute('create table orders(uid text, created text, trial text)')
 c.executemany('insert into users values(?,?,?)',((r[0],r[5],r[9]) for r in rows('users.csv',23))); c.commit()
 c.executemany('insert into devices values(?,?)',((r[1],r[2]) for r in rows('devices.csv',12) if r[1] and r[2])); c.commit()
 c.executemany('insert into orders values(?,?,?)',((r[1],r[5],r[8]) for r in rows('orders.csv',11) if r[4]=='paid')); c.commit()
 c.execute('create index di on devices(ident,uid)'); c.execute('create index ou on orders(uid,created)'); c.commit()
 q=lambda s:c.execute(s).fetchone()[0]
 out={'users':q('select count(*) from users'),'users_trial_timestamp':q("select count(*) from users where trial<>''"),'device_rows_nonempty_identifier':q('select count(*) from devices'),'unique_identifier':q('select count(distinct ident) from devices'),'identifiers_multiple_users':q('select count(*) from (select ident from devices group by ident having count(distinct uid)>1)'), 'users_sharing_identifier':q('select count(distinct uid) from devices where ident in (select ident from devices group by ident having count(distinct uid)>1)'), 'trial_users_sharing_identifier':q("select count(distinct u.id) from users u join devices d on d.uid=u.id where u.trial<>'' and d.ident in (select ident from devices group by ident having count(distinct uid)>1)"), 'multi_user_identifiers_multiple_trial_users':q("select count(*) from (select d.ident from devices d join users u on u.id=d.uid where u.trial<>'' group by d.ident having count(distinct u.id)>1)")}
 out['identifier_max_users']=q('select max(n) from (select count(distinct uid) n from devices group by ident)')
 out['identifiers_2_to_10_users']=q('select count(*) from (select ident from devices group by ident having count(distinct uid) between 2 and 10)')
 out['identifiers_2_to_10_users_multiple_trials']=q("select count(*) from (select d.ident from devices d join users u on u.id=d.uid where d.ident in (select ident from devices group by ident having count(distinct uid) between 2 and 10) and u.trial<>'' group by d.ident having count(distinct u.id)>1)")
 def parse(s):
  d=datetime.fromisoformat(s)
  return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d.astimezone(timezone.utc)
 data=list(c.execute("select u.created,u.trial,min(o.created) from users u join orders o on o.uid=u.id and o.trial='f' group by u.id")); counts=Counter(); days=[]; trial_days=[]
 for created,trial,first in data:
  if trial and parse(trial)<parse(first):
   counts['prior_trial_timestamp']+=1; trial_days.append((parse(first)-parse(trial)).total_seconds()/86400)
  else: counts['no_prior_trial_timestamp']+=1
  try:
   delta=(parse(first)-parse(created)).total_seconds()/86400
   if delta>=0: days.append(delta)
   else: counts['negative_registration_interval']+=1
  except (ValueError,TypeError): counts['invalid_date']+=1
 days.sort(); trial_days.sort()
 out['metric_names']=dict(Counter(r[1] for r in rows('metric_values.csv',9)))
 out.update({'users_with_nontrial_paid_order_and_user_record':len(data),'trial_timestamp_comparison':dict(counts),'registration_to_first_nontrial_paid_days':{'n':len(days),'median':days[len(days)//2] if days else None,'p90':days[int((len(days)-1)*.9)] if days else None},'trial_to_first_nontrial_paid_days':{'n':len(trial_days),'median':trial_days[len(trial_days)//2] if trial_days else None,'p90':trial_days[int((len(trial_days)-1)*.9)] if trial_days else None},'sha256':{n:hashlib.file_digest((D/n).open('rb'),'sha256').hexdigest() for n in ['users.csv','devices.csv','device_code.csv','product.csv','product_trial.csv','metric_values.csv']}})
 (P/'results'/'extended.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n');print(json.dumps(out,indent=2,ensure_ascii=False))
finally:
 c.close();os.unlink(path)
