from pathlib import Path
import re,html
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, HRFlowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4

P=Path(__file__).resolve().parent
pdfmetrics.registerFont(TTFont('Arial','/System/Library/Fonts/Supplemental/Arial.ttf'))
pdfmetrics.registerFont(TTFont('Arial-Bold','/System/Library/Fonts/Supplemental/Arial Bold.ttf'))
pdfmetrics.registerFontFamily('Arial',normal='Arial',bold='Arial-Bold',italic='Arial',boldItalic='Arial-Bold')
ink=colors.HexColor('#172235'); muted=colors.HexColor('#536477'); blue=colors.HexColor('#164f70')
styles={
 'body':ParagraphStyle('body',fontName='Arial',fontSize=10.5,leading=14.4,alignment=TA_JUSTIFY,spaceAfter=6,textColor=ink,allowWidows=0,allowOrphans=0),
 'head':ParagraphStyle('head',fontName='Arial-Bold',fontSize=13,leading=16,spaceBefore=9,spaceAfter=6,textColor=blue,keepWithNext=True),
 'cover_top':ParagraphStyle('cover_top',fontName='Arial',fontSize=11,leading=16,alignment=TA_CENTER,textColor=muted),
 'cover_title':ParagraphStyle('cover_title',fontName='Arial-Bold',fontSize=24,leading=31,alignment=TA_CENTER,textColor=ink),
 'cover_sub':ParagraphStyle('cover_sub',fontName='Arial',fontSize=13,leading=19,alignment=TA_CENTER,textColor=muted),
 'cover_by':ParagraphStyle('cover_by',fontName='Arial',fontSize=11.5,leading=19,alignment=TA_RIGHT,textColor=ink),
}
def markup(s):
 s=html.escape(s)
 s=re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)',r'<link href="\2" color="#164f70">\1</link>',s)
 s=re.sub(r'\*\*(.*?)\*\*',r'<b>\1</b>',s)
 s=re.sub(r'`([^`]+)`',r'<font color="#164f70">\1</font>',s)
 return s.replace('\u2011','-')
def footer(c,doc):
 if doc.page==1:return
 w,h=A4;c.setStrokeColor(colors.HexColor('#d8e1e7'));c.line(21*mm,19*mm,w-21*mm,19*mm)
 c.setFont('Arial',8);c.setFillColor(muted);c.drawString(21*mm,13*mm,'Производственная практика · Синаптик');c.drawRightString(w-21*mm,13*mm,str(doc.page))

doc=SimpleDocTemplate(str(P/'Отчёт_Синаптик.pdf'),pagesize=A4,leftMargin=23*mm,rightMargin=23*mm,topMargin=21*mm,bottomMargin=25*mm,title='Продуктовые гипотезы: кейс Синаптик',author='Епифанов Максим Дмитриевич')
story=[Spacer(1,25*mm),Paragraph('ПРОИЗВОДСТВЕННАЯ ПРАКТИКА',styles['cover_top']),Spacer(1,42*mm),Paragraph('Продуктовые гипотезы',styles['cover_title']),Spacer(1,5*mm),Paragraph('Анализ данных интернет-сервиса<br/>Кейс «Синаптик»',styles['cover_sub']),Spacer(1,50*mm),Paragraph('Выполнил: Епифанов Максим Дмитриевич<br/>Группа: 23-05-06-00',styles['cover_by']),Spacer(1,30*mm),Paragraph('2026',styles['cover_top']),PageBreak()]
text=(P/'README.md').read_text(encoding='utf8')
for block in text.split('\n\n'):
 block=block.strip()
 if not block or block.startswith('# ') or block.startswith('Епифанов Максим'):continue
 if block.startswith('## '):story.append(Paragraph(markup(block[3:]),styles['head']))
 else:story.append(Paragraph(markup(block.replace('\n',' ')),styles['body']))
doc.build(story,onFirstPage=footer,onLaterPages=footer)
