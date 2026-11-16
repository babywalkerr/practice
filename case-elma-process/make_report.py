#!/usr/bin/env python3
"""Сборка PDF-отчёта: reportlab, Python 3; данные считываются из CSV кейса."""
from pathlib import Path
import csv
from collections import Counter, defaultdict
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Flowable, KeepTogether
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

P=Path(__file__).resolve().parent
FONT='/System/Library/Fonts/Supplemental/'
pdfmetrics.registerFont(TTFont('Arial',FONT+'Arial.ttf'))
pdfmetrics.registerFont(TTFont('ArialB',FONT+'Arial Bold.ttf'))
pdfmetrics.registerFontFamily('Arial',normal='Arial',bold='ArialB',italic='Arial',boldItalic='ArialB')
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='TitleRu',fontName='ArialB',fontSize=17,leading=22,spaceAfter=12,textColor=colors.HexColor('#17324a')))
styles.add(ParagraphStyle(name='HeadRu',fontName='ArialB',fontSize=12,leading=15,spaceBefore=9,spaceAfter=6,textColor=colors.HexColor('#17324a')))
styles.add(ParagraphStyle(name='BodyRu',fontName='Arial',fontSize=10.2,leading=14,spaceAfter=7))
styles.add(ParagraphStyle(name='SmallRu',fontName='Arial',fontSize=8.6,leading=11.4,spaceAfter=3))
styles.add(ParagraphStyle(name='CellRu',fontName='Arial',fontSize=9,leading=11.5))
styles.add(ParagraphStyle(name='CellBold',fontName='ArialB',fontSize=9,leading=11.5,textColor=colors.white))
styles.add(ParagraphStyle(name='NoteRu',fontName='Arial',fontSize=8.5,leading=11,textColor=colors.HexColor('#4b5a64'),spaceAfter=6))
def para(t,sty='BodyRu'): return Paragraph(t,styles[sty])
def table(data,widths):
    t=Table([[para(str(c),'CellBold' if i==0 else 'CellRu') for c in row] for i,row in enumerate(data)],colWidths=widths,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#304d62')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f0f4f6')]),('GRID',(0,0),(-1,-1),0.35,colors.HexColor('#cbd5dc')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)])); return t
with (P/'students.csv').open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
cases=defaultdict(list)
for r in rows: cases[r['ProcessInstanceId']].append(r)
for c in cases.values(): c.sort(key=lambda x:int(x['EventIndex']))
with (P/'variants.csv').open(encoding='utf-8-sig',newline='') as f: variants=list(csv.DictReader(f))
class Diagram(Flowable):
    def __init__(self): super().__init__(); self.width=480; self.height=330
    def draw(self):
        c=self.canv; c.setFont('Arial',8.5)
        def box(x,y,w,h,lines,end=False):
            c.setStrokeColor(colors.HexColor('#304d62')); c.setFillColor(colors.HexColor('#edf3f6') if not end else colors.HexColor('#e3eee8')); c.roundRect(x,y,w,h,5,fill=1,stroke=1)
            if end: c.roundRect(x+3,y+3,w-6,h-6,3,fill=0,stroke=1)
            c.setFillColor(colors.HexColor('#172c3a'))
            for i,line in enumerate(lines): c.drawCentredString(x+w/2,y+h/2+(len(lines)-1)*5-i*10-3,line)
        def line(points,label,lx,ly):
            c.setStrokeColor(colors.HexColor('#526879')); c.setLineWidth(1)
            p=c.beginPath(); p.moveTo(*points[0])
            for x,y in points[1:]: p.lineTo(x,y)
            c.drawPath(p)
            import math
            (x0,y0),(x,y)=points[-2:]; ang=math.atan2(y-y0,x-x0); s=6
            path=c.beginPath(); path.moveTo(x,y); path.lineTo(x-s*math.cos(ang-.45),y-s*math.sin(ang-.45)); path.moveTo(x,y); path.lineTo(x-s*math.cos(ang+.45),y-s*math.sin(ang+.45)); c.drawPath(path)
            c.setFillColor(colors.HexColor('#344b5a')); c.setFont('Arial',8); c.drawString(lx,ly,label)
        box(150,292,155,31,['Регистрация заявки']); box(150,242,155,31,['Первичная проверка']); box(150,192,155,31,['Согласование','руководителем']); box(150,142,155,31,['Проверка бюджета']); box(150,48,155,31,['Исполнение закупки']); box(150,0,155,31,['Заявка выполнена'],True)
        box(335,232,135,31,['Заявка отклонена'],True); box(335,181,135,31,['Заявка отменена'],True); box(0,192,115,31,['Доработка заявки']); box(315,95,155,31,['Дополнительное','согласование'])
        line([(227,292),(227,273)],'1000',234,279); line([(227,242),(227,223)],'1129',234,229); line([(305,257),(335,248)],'45',308,261); line([(305,207),(320,207),(320,247),(335,247)],'18',310,212); line([(305,199),(335,196)],'26',309,188)
        line([(150,207),(115,207)],'174',125,212); line([(57,223),(57,258),(150,258)],'174',65,263)
        line([(227,192),(227,173)],'911',234,179); line([(210,142),(210,79)],'702',182,108); line([(305,157),(390,157),(390,126)],'209',325,162); line([(390,95),(390,63),(305,63)],'209',346,69); line([(227,48),(227,31)],'911',234,35)

def footer(c,doc):
    c.setFont('Arial',8); c.setFillColor(colors.HexColor('#657681')); c.drawString(20*mm,14*mm,'Производственная практика • Кейс 2'); c.drawRightString(190*mm,14*mm,str(doc.page))

story=[]
story += [para('Восстановление процесса закупки по журналу событий','TitleRu'),para('<b>Студент:</b> Епифанов Максим Дмитриевич<br/><b>Группа:</b> 23-05-06-00'),para('1. Данные и способ анализа','HeadRu'),para('Исходный синтетический журнал содержит 6508 событий для 1000 завершённых заявок. Все записи относятся к версии процесса 1. Строки сгруппированы по ProcessInstanceId и упорядочены внутри заявки по числовому EventIndex. Каждая строка человеческого задания фиксирует его завершение; повторы сохранены.'),para('Полный вариант - последовательность названий действий одной заявки, включая начало и окончание. Переходом считается пара соседних событий. Для подсчётов использован Python 3. Проверены уникальность EventId, непрерывность индексов, типы границ и промежуточных событий. Сумма частот вариантов равна 1000, переходов - 5508, то есть 6508 минус 1000.'),para('2. Активности и окончания','HeadRu')]
names=['Регистрация заявки','Первичная проверка','Согласование руководителем','Проверка бюджета','Дополнительное согласование','Доработка заявки','Исполнение закупки','Заявка выполнена','Заявка отклонена','Заявка отменена']
counts=Counter(r['ActivityName'] for r in rows)
data=[['Активность','Событий','Заявок']]+[[n,counts[n],sum(any(r['ActivityName']==n for r in c) for c in cases.values())] for n in names]
story += [table(data,[300,75,75]),Spacer(1,5),para('Число событий может превышать число заявок: проверка, согласование и доработка повторяются при возврате.','NoteRu'),PageBreak(),para('3. Схема наблюдаемых переходов','HeadRu'),para('На стрелках указано число переходов между соседними событиями. Двойная рамка обозначает окончание заявки.','NoteRu'),Diagram(),Spacer(1,9),para('После первичной проверки 45 раз следовало отклонение. Согласование руководителем завершалось переходом к проверке бюджета, доработке, отклонению или отмене. После проверки бюджета 702 раза следовало исполнение, ещё 209 раз - дополнительное согласование, затем исполнение.'),para('Стрелки объединяют разные истории. Их наличие не доказывает устройство внутренних шлюзов и не означает, что любая комбинация стрелок встречалась в журнале. Например, граф допускает три возврата подряд, хотя в данных их было не более двух.'),PageBreak(),para('4. Полные варианты','HeadRu'),para('Доля рассчитана от 1000 заявок. В таблице сохранены повторные действия и все окончания; сумма долей равна 100%.','NoteRu')]
# Compact codes retain exact full sequence via legend.
short={'Регистрация заявки':'Р','Первичная проверка':'П','Согласование руководителем':'С','Проверка бюджета':'Б','Дополнительное согласование':'Дс','Доработка заявки':'Др','Исполнение закупки':'И','Заявка выполнена':'В','Заявка отклонена':'О','Заявка отменена':'От'}
data=[['Вариант','Последовательность','Заявок','Доля']]
for v in variants:
    route=' → '.join(short[a] for a in v['Route'].split(' > '))
    data.append([v['Variant'],route,v['NumberOfCases'],f"{float(v['Share'])*100:.1f}%".replace('.',',')])
story += [table(data,[55,275,60,60]),Spacer(1,9),para('<b>Обозначения:</b> Р - регистрация заявки; П - первичная проверка; С - согласование руководителем; Б - проверка бюджета; Дс - дополнительное согласование; Др - доработка заявки; И - исполнение закупки; В - заявка выполнена; О - заявка отклонена; От - заявка отменена. Полные названия и последовательности приведены также в variants.csv.','SmallRu'),para('Основной вариант V1 без доработки и дополнительного согласования встречается в 567 заявках (56,7%). Дополнительное согласование без доработки, V2, встречается в 188 заявках (18,8%). Наиболее редкие варианты V7 и V8 содержат по 18 заявок (1,8%). Редкость маршрута не означает, что он ошибочен.'),para('Примеры: V1 - 2fcc6cf4-603b-5153-b1f6-80db32e6b362; V2 - 78f343a1-28d8-5473-b013-17207d09ffa8; V7 - 0add1ba6-ce33-56cc-95d6-639aceb7dae3; V8 - 690b19ea-251a-52a5-9f51-25147a4c63ae.','SmallRu'),PageBreak(),para('5. Выводы','HeadRu'),para('Все 1000 заявок начинались с регистрации и проходили первичную проверку. Согласование руководителем встречалось в 955 заявках. Завершились выполнением 911 заявок (91,1%), отклонением - 63 (6,3%), отменой - 26 (2,6%).'),para('В каждой из 911 выполненных заявок были проверка бюджета и исполнение закупки. Дополнительное согласование встречалось в 209 выполненных заявках: это 22,9% выполненных и 20,9% всех заявок. Для всей выборки эти этапы не являются обязательными.'),para('Доработка встречалась в 156 заявках: в 138 - один раз, в 18 - дважды. Всего зафиксировано 174 возврата по цепочке «согласование руководителем → доработка → первичная проверка». Все заявки с доработкой в этой выборке завершились выполнением. Ограничение на число возвратов из этих данных не следует.'),para('Результаты действий согласуются с наблюдаемыми ветвями: после reject первичной проверки идёт отклонение; после return, reject и cancel руководителя - соответственно доработка, отклонение и отмена. Эти связи описывают журнал и не устанавливают все возможные правила системы.'),para('6. Ограничения и воспроизводимость','HeadRu'),para('Журнал синтетический, а исходное определение процесса недоступно. Последовательность завершений не позволяет надёжно восстановить внутренние шлюзы, причины выбора ветвей или параллельность. Интервалы между событиями включают ожидание и нерабочее время, поэтому не использовались как время труда.'),para('Выводы проверены по исходным строкам; частоты вариантов и переходов дополнительно сверены отдельным расчётом. Код анализа, исходный CSV, таблица вариантов и список переходов приложены к работе. Запуск и требования указаны в README.md.'),para('Источник: предоставленные students.csv и dataset_description.md, кейс 2 «ЭЛМА».','NoteRu')]
doc=SimpleDocTemplate(str(P/'Отчёт_Епифанов_кейс_2.pdf'),pagesize=(210*mm,297*mm),leftMargin=20*mm,rightMargin=20*mm,topMargin=17*mm,bottomMargin=20*mm,title='Восстановление процесса закупки',author='Епифанов Максим Дмитриевич')
doc.build(story,onFirstPage=footer,onLaterPages=footer)
