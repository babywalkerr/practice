import csv, json, hashlib
from pathlib import Path
from collections import Counter
from datetime import datetime, timedelta
P=Path(__file__).resolve().parent

def read(name, columns):
    with (P/'data'/name).open(encoding='utf-8-sig', newline='') as f:
        for n,row in enumerate(csv.reader(f,delimiter=';'),1):
            if len(row)!=len(columns): raise ValueError(f'{name}:{n}: {len(row)} columns')
            yield dict(zip(columns,row))
orders=list(read('orders.csv','id user_id product_id amount status created_at updated_at pre_payment trial period_id provider_id'.split()))
subs=list(read('subscribe.csv','id user_id product_id expired_time created_at order_id disabled_at next_product_id pre_payment pre_payment_notification next_period_id'.split()))
assert len({x['id'] for x in orders})==len(orders)
byid={x['id']:x for x in orders}
matched=[s for s in subs if s['order_id'] in byid]
status=Counter(x['status'] for x in orders)
trial=Counter((x['trial'],x['status']) for x in orders)
# Per-user completed orders, ordered by creation time. A previous paid trial order is only a proxy for trial use.
users={}
for x in orders:
    if x['status']=='paid': users.setdefault(x['user_id'],[]).append(x)
first_nontrial=[]
for uid,items in users.items():
    items.sort(key=lambda x:(x['created_at'],x['id']))
    candidates=[x for x in items if x['trial']=='f']
    if candidates:
        first=candidates[0]; prior=any(x['trial']=='t' and x['created_at']<first['created_at'] for x in items)
        first_nontrial.append(prior)
# Recoveries: failed order followed by paid order for same user within seven days, irrespective of product.
allusers={}
for x in orders: allusers.setdefault(x['user_id'],[]).append(x)
failed=0; recovered=0
cutoff=max(datetime.fromisoformat(x['created_at']) for x in orders)-timedelta(days=7)
for items in allusers.values():
    paid=sorted(datetime.fromisoformat(x['created_at']) for x in items if x['status']=='paid')
    from bisect import bisect_right
    for x in items:
        if x['status']=='failed' and datetime.fromisoformat(x['created_at'])<=cutoff:
            failed+=1; t=datetime.fromisoformat(x['created_at']); i=bisect_right(paid,t)
            recovered+= i<len(paid) and paid[i]<=t+timedelta(days=7)
result={'inputs_sha256':{n:hashlib.sha256((P/'data'/n).read_bytes()).hexdigest() for n in ['orders.csv','orders_schema.csv','subscribe.csv','subscribe_schema.csv']},'orders':len(orders),'distinct_order_users':len(allusers),'created_min':min(x['created_at'] for x in orders),'created_max':max(x['created_at'] for x in orders),'status':dict(status),'trial_status':{f'{a}_{b}':v for (a,b),v in trial.items()},'subscriptions':len(subs),'subscriptions_matching_order':len(matched),'matched_order_status':dict(Counter(byid[s['order_id']]['status'] for s in matched)),'matched_user_equal':sum(s['user_id']==byid[s['order_id']]['user_id'] for s in matched),'users_first_paid_nontrial':len(first_nontrial),'users_prior_paid_trial':sum(first_nontrial),'users_no_prior_paid_trial':len(first_nontrial)-sum(first_nontrial),'failed_orders':failed,'failed_followed_by_paid_7d':recovered}
(P/'results').mkdir(exist_ok=True)
(P/'results'/'metrics.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
