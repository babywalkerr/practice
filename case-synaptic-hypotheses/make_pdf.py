from pathlib import Path
import re,html
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, HRFlowable, KeepTogether
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
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
 'body':ParagraphStyle('body',fontName='Arial',fontSize=10.2,leading=14,alignment=TA_LEFT,spaceAfter=7,textColor=ink,allowWidows=0,allowOrphans=0),
 'head':ParagraphStyle('head',fontName='Arial-Bold',fontSize=12,leading=15,spaceBefore=9,spaceAfter=6,textColor=blue,keepWithNext=True),
 'title':ParagraphStyle('title',fontName='Arial-Bold',fontSize=17,leading=22,spaceAfter=12,textColor=blue),
 'meta':ParagraphStyle('meta',fontName='Arial',fontSize=10.2,leading=14,spaceAfter=8,textColor=ink),
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
 w,h=A4;c.setStrokeColor(colors.HexColor('#d8e1e7'));c.line(21*mm,19*mm,w-21*mm,19*mm)
 c.setFont('Arial',8);c.setFillColor(muted);c.drawString(21*mm,13*mm,'Производственная практика · Синаптик');c.drawRightString(w-21*mm,13*mm,str(doc.page))

doc=SimpleDocTemplate(str(P/'Отчёт_Синаптик.pdf'),pagesize=A4,leftMargin=20*mm,rightMargin=20*mm,topMargin=17*mm,bottomMargin=20*mm,title='Продуктовые гипотезы: кейс Синаптик',author='Епифанов Максим Дмитриевич')
story=[Paragraph('Продуктовые гипотезы по кейсу «Синаптик»',styles['title']),Paragraph('<b>Студент:</b> Епифанов Максим Дмитриевич<br/><b>Группа:</b> 23-05-06-00',styles['meta'])]
text=(P/'README.md').read_text(encoding='utf8')
for block in text.split('\n\n'):
 block=block.strip()
 if not block or block.startswith('# ') or block.startswith('Епифанов Максим'):continue
 if block.startswith('## '):story.append(Paragraph(markup(block[3:]),styles['head']))
 else:
  para=Paragraph(markup(block.replace('\n',' ')),styles['body'])
  story.append(KeepTogether([para]) if block.startswith('**Предложение:**') else para)
doc.build(story,onFirstPage=footer,onLaterPages=footer)
