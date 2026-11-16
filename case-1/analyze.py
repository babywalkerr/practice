#!/usr/bin/env python3
import csv, json
from collections import Counter
from datetime import datetime, timedelta, time
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
CUT = pd.Timestamp('2026-07-01T00:00:00+03:00')
d = pd.read_csv(HERE/'students.csv', keep_default_na=False, dtype=str)
d['EventIndex'] = pd.to_numeric(d.EventIndex)
d['dt'] = pd.to_datetime(d.Timestamp, utc=True).dt.tz_convert('Etc/GMT-3')
d = d.sort_values(['ProcessInstanceId','EventIndex'])
assert not d.EventId.duplicated().any()
assert not d.duplicated(['ProcessInstanceId','EventIndex']).any()
after_cut = d[d.dt > CUT].copy()
d = d[d.dt <= CUT].copy()
assert (d.groupby('ProcessInstanceId').dt.diff().dropna() >= pd.Timedelta(0)).all()
assert (d.groupby('ProcessInstanceId')[['RequestType','Amount','TemplateVersion']].nunique() == 1).all().all()
assert (d.groupby('ProcessInstanceId').EventIndex.apply(lambda x: list(x)==list(range(1,len(x)+1)))).all()

def working(a,b):
    total=0.0
    day=a.date()
    while day<=b.date():
        if day.weekday()<5:
            start=pd.Timestamp(datetime.combine(day,time(9)),tz=a.tz)
            end=pd.Timestamp(datetime.combine(day,time(18)),tz=a.tz)
            total+=max(0,(min(b,end)-max(a,start)).total_seconds())
        day+=timedelta(days=1)
    return total/3600

created=d[d.EventType.eq('task_created')]; done=d[d.EventType.eq('task_completed')]
assert not created.TaskId.duplicated().any() and not done.TaskId.duplicated().any()
assert set(done.TaskId)<=set(created.TaskId)
t=created.merge(done[['TaskId','dt','Role','UserId','Result','ProcessInstanceId','ActivityName']],on='TaskId',how='left',suffixes=('','_end'))
assert (t.loc[t.dt_end.notna(),'ProcessInstanceId']==t.loc[t.dt_end.notna(),'ProcessInstanceId_end']).all()
assert (t.loc[t.dt_end.notna(),'ActivityName']==t.loc[t.dt_end.notna(),'ActivityName_end']).all()
t['calendar_h']=(t.dt_end.fillna(CUT)-t.dt).dt.total_seconds()/3600
t['work_h']=[working(a,b if pd.notna(b) else CUT) for a,b in zip(t.dt,t.dt_end)]
closed=t[t.dt_end.notna()]
stats=closed.groupby(['RequestType','ActivityName']).work_h.agg(n='count',median='median',q1=lambda x:x.quantile(.25),q3=lambda x:x.quantile(.75),max='max')
stats['limit']=(stats.q3+3*(stats.q3-stats.q1)).clip(lower=18)
rows=[]
def add(pid,kind,explanation): rows.append((pid,kind,explanation))
roles={'Проверка заявки':'specialist','Согласование руководителем':'manager','Доработка заявки':'requester','Согласование бюджета':'finance','Проверка договора':'legal','Исполнение заявки':'procurement','Внеплановая проверка':'auditor'}
route_counts=Counter(); outcomes=Counter(); returns=Counter()
for pid,g in d.groupby('ProcessInstanceId',sort=True):
    typ=g.RequestType.iloc[0]; completions=g[g.EventType.eq('task_completed')]; end=g[g.EventType.eq('process_completed')]; outcome=end.Result.iloc[0] if len(end) else 'open';outcomes[outcome]+=1
    route_counts[(typ,outcome,' → '.join(completions.ActivityName+' ('+completions.Result+')'))]+=1
    rr=(completions.Result=='return').sum();returns[int(rr)]+=1
    for _,e in completions.iterrows():
        if e.ActivityName in roles and e.Role!=roles[e.ActivityName]:
            add(pid,'Несоответствие роли',f'{e.ActivityName}: задание {e.TaskId} закрыто ролью {e.Role}, ожидается {roles[e.ActivityName]}; результат {e.Result}. Проверить полномочия и журнал делегирования.')
    initiator=g.loc[g.EventType.eq('process_started'),'UserId'].iloc[0]
    self_decisions=completions[(completions.ActivityName=='Согласование руководителем') & (completions.UserId==initiator)]
    for _,e in self_decisions.iterrows():
        add(pid,'Решение по собственной заявке',f'Инициатор {initiator} самостоятельно закрыл согласование руководителем, задание {e.TaskId}, результат {e.Result}; проверить разделение полномочий.')
    if rr>=5: add(pid,'Многократный возврат',f'Руководитель вернул заявку {rr} раз; каждый возврат сопровождается доработкой и повторной проверкой. Требуется выяснить причину циклов.')
    audits=completions[completions.ActivityName.eq('Внеплановая проверка')]
    if len(audits): add(pid,'Дополнительные проверки',f'Выполнено внеплановых проверок: {len(audits)}; события № {", ".join(map(str,audits.EventIndex))}. Само участие auditor допустимо; проверить основание и необходимость повторения.')
    # State machine validates sequence of completed stages; a prefix is valid for an open case.
    state='check'; errors=[]
    for _,e in completions.iterrows():
        name=e.ActivityName; result=e.Result
        if name=='Внеплановая проверка': continue
        expected={'check':'Проверка заявки','manager':'Согласование руководителем','revision':'Доработка заявки','budget':'Согласование бюджета','legal':'Проверка договора','execute':'Исполнение заявки','end_rejected':'завершение с отказом','end_fulfilled':'завершение с исполнением'}[state]
        if name!=expected:
            errors.append(f'событие № {e.EventIndex}: «{name}» вместо ожидаемого «{expected}»')
            # Resynchronize after an unexpected step so further steps can still be assessed.
        if name=='Проверка заявки': state='manager'
        elif name=='Согласование руководителем': state={'return':'revision','reject':'end_rejected','accept':'budget'}.get(result,'manager')
        elif name=='Доработка заявки': state='check'
        elif name=='Согласование бюджета': state='legal' if typ=='contract' else 'execute'
        elif name=='Проверка договора': state='execute'
        elif name=='Исполнение заявки': state='end_fulfilled'
    if outcome=='fulfilled' and state!='end_fulfilled': errors.append(f'завершено fulfilled при ожидаемом этапе «{state}»')
    if outcome=='rejected' and state!='end_rejected': errors.append(f'завершено rejected при ожидаемом этапе «{state}»')
    if errors: add(pid,'Отклонение маршрута','; '.join(errors)+'. Проверить порядок и полноту обязательных этапов.')
for _,x in t.iterrows():
    # Audits are evaluated as process context, not against tiny cohorts.
    if x.ActivityName=='Внеплановая проверка': continue
    s=stats.loc[(x.RequestType,x.ActivityName)]
    if x.work_h>s['limit']:
        status='не закрыто к срезу; минимум' if pd.isna(x.dt_end) else 'закрыто;'
        add(x.ProcessInstanceId,'Длительное задание',f'{x.ActivityName}, TaskId {x.TaskId}: {status} {x.work_h:.1f} рабочих ч и {x.calendar_h:.1f} календарных ч; порог для {x.RequestType} и этапа {s["limit"]:.1f} рабочих ч (Q3 + 3 IQR, минимум 18 ч; n={int(s.n)}). Ожидание включено, нужна проверка причин.')
with (HERE/'anomalies.csv').open('w',encoding='utf-8',newline='') as f:
    w=csv.writer(f);w.writerow(['ProcessInstanceId','AnomalyType','Explanation']);w.writerows(sorted(set(rows)))
stats.round(2).to_csv(HERE/'duration_stats.csv',encoding='utf-8')
summary={'events_after_cut':len(after_cut),'processes_after_cut':after_cut.ProcessInstanceId.nunique(),'events':len(d),'processes':d.ProcessInstanceId.nunique(),'types':d.groupby('RequestType').ProcessInstanceId.nunique().to_dict(),'outcomes':dict(outcomes),'returns':dict(sorted(returns.items())),'open_tasks':int(t.dt_end.isna().sum()),'anomaly_rows':len(set(rows)),'candidate_processes':len(set(r[0] for r in rows)),'anomaly_types':dict(Counter(r[1] for r in set(rows))),'top_routes':[(list(k),v) for k,v in route_counts.most_common(12)]}
(HERE/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
