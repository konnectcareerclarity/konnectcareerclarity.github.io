import io, datetime, os
HERE=os.path.dirname(os.path.abspath(__file__))
from xml.sax.saxutils import escape as esc
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
                                PageBreak, Flowable, KeepTogether, Image, NextPageTemplate, CondPageBreak)
import scoring as S, texts as T, colleges as CO
from clusters import CLUSTERS
import content as CT, skills as SKL

def _font_dir():
    for d in (os.path.join(HERE,'fonts'),HERE,'/usr/share/fonts/truetype/google-fonts'):
        if os.path.exists(os.path.join(d,'Poppins-Regular.ttf')): return d+'/'
    raise FileNotFoundError('Poppins fonts not found next to report.py or in a fonts folder')
FD=_font_dir()
for n,f in (('P','Poppins-Regular'),('PM','Poppins-Medium'),('PS','Poppins-Bold'),('PB','Poppins-Bold'),('PI','Poppins-Italic')):
    pdfmetrics.registerFont(TTFont(n,FD+f+'.ttf'))
pdfmetrics.registerFontFamily('P',normal='P',bold='PS',italic='PI',boldItalic='PS')
NAVY=colors.HexColor('#1F3864'); BLUE=colors.HexColor('#2E75B6'); GOLD=colors.HexColor('#F0A500'); TEAL=colors.HexColor('#1D9E75')
INK=colors.HexColor('#26364a'); MUTED=colors.HexColor('#66758a'); LIGHT=colors.HexColor('#F5F8FC'); LINE=colors.HexColor('#dfe7f0'); PALE=colors.HexColor('#E8F1FA'); CREAM=colors.HexColor('#FFF8E6')
LOGO=os.path.join(HERE,'logo_symbol.png')
W,H=A4; LM=RM=18*mm
CW=W-LM-RM

def st(name,**k):
    base=dict(fontName='P',fontSize=10,leading=15,textColor=INK,spaceAfter=6)
    base.update(k); return ParagraphStyle(name,**base)
BODY=st('body'); SMALL=st('small',fontSize=8.5,leading=12,textColor=MUTED)
H1=st('h1',fontName='PB',fontSize=20,leading=25,textColor=NAVY,spaceAfter=4)
H2=st('h2',fontName='PS',fontSize=13,leading=17,textColor=NAVY,spaceBefore=8,spaceAfter=4)
H3=st('h3',fontName='PS',fontSize=11,leading=15,textColor=NAVY,spaceAfter=3)
KICK=st('kick',fontName='PS',fontSize=8.5,leading=11,textColor=BLUE,spaceAfter=2)
BUL=st('bul',leftIndent=12,bulletIndent=2,spaceAfter=3)
CELL=st('cell',fontSize=9,leading=12.5,spaceAfter=0)
CELLB=st('cellb',fontName='PS',fontSize=9,leading=12.5,spaceAfter=0,textColor=NAVY)
CELLW=st('cellw',fontName='PS',fontSize=9,leading=12,spaceAfter=0,textColor=colors.white)
def P(t,s=BODY): return Paragraph(t,s)
def bullets(items,s=BUL): return [Paragraph(esc(i),s,bulletText='•') for i in items]

class Rule(Flowable):
    def __init__(s,w=CW,c=BLUE,t=1.2): super().__init__(); s.w=w;s.c=c;s.t=t
    def wrap(s,aw,ah): return s.w,s.t+4
    def draw(s): s.canv.setStrokeColor(s.c); s.canv.setLineWidth(s.t); s.canv.line(0,2,s.w,2)

class Bars(Flowable):
    """Horizontal bars without numbers. rows=[(label,frac,colour)]"""
    def __init__(s,rows,w=CW,lab=42*mm): super().__init__(); s.rows=rows;s.w=w;s.lab=lab
    def wrap(s,aw,ah): return s.w,len(s.rows)*10*mm+2*mm
    def draw(s):
        c=s.canv; y=len(s.rows)*10*mm
        for lab,fr,col in s.rows:
            y-=10*mm
            c.setFont('PS',9.5); c.setFillColor(NAVY); c.drawString(0,y+2.2*mm,lab)
            x0=s.lab; bw=s.w-s.lab; c.setFillColor(colors.HexColor('#E3EAF3')); c.roundRect(x0,y+1.8*mm,bw,4.6*mm,2.3*mm,0,1)
            c.setFillColor(col); c.roundRect(x0,y+1.8*mm,max(4*mm,bw*fr),4.6*mm,2.3*mm,0,1)

class Meter(Flowable):
    """Three-step band meter."""
    def __init__(s,band,w=60*mm): super().__init__(); s.band=band; s.w=w
    def wrap(s,aw,ah): return s.w,9*mm
    def draw(s):
        c=s.canv; names=["Developing","Solid","Strong"]; seg=s.w/3
        cols=[colors.HexColor('#F4C26B'),colors.HexColor('#6FB8E8'),TEAL]
        for i,n in enumerate(names):
            on = n==s.band
            c.setFillColor(cols[i] if on else colors.HexColor('#E3EAF3'))
            c.roundRect(i*seg+0.6*mm,2.6*mm,seg-1.2*mm,4.2*mm,2*mm,0,1)
            c.setFont('PS' if on else 'P',7.5); c.setFillColor(NAVY if on else MUTED); c.drawCentredString(i*seg+seg/2,0.2*mm,n)

def card(flow,bg=LIGHT,border=LINE,pad=9,w=CW):
    t=Table([[flow]],colWidths=[w]); t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),bg),('BOX',(0,0),(-1,-1),0.8,border),
        ('LEFTPADDING',(0,0),(-1,-1),pad+2),('RIGHTPADDING',(0,0),(-1,-1),pad+2),('TOPPADDING',(0,0),(-1,-1),pad),('BOTTOMPADDING',(0,0),(-1,-1),pad),('ROUNDEDCORNERS',[8,8,8,8])])); return t
def headerbar(text,w=CW,bg=NAVY):
    t=Table([[Paragraph(esc(text),CELLW)]],colWidths=[w]); t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),bg),('LEFTPADDING',(0,0),(-1,-1),10),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),('ROUNDEDCORNERS',[6,6,0,0])])); return t
def two_col(a,b,gap=6*mm):
    w=(CW-gap)/2; t=Table([[a,b]],colWidths=[w,w],hAlign='LEFT'); t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(0,0),0),('RIGHTPADDING',(1,0),(1,0),0),('RIGHTPADDING',(0,0),(0,0),gap/2),('LEFTPADDING',(1,0),(1,0),gap/2),('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0)])); return t
def table_roadmap(rows):
    data=[[Paragraph(h,CELLW) for h in ("Area","School stage","Degree or course","After graduation")]]
    for r in rows: data.append([Paragraph(esc(r[0]),CELLB)]+[Paragraph(esc(x),CELL) for x in r[1:]])
    t=Table(data,colWidths=[CW*.22,CW*.24,CW*.28,CW*.26],repeatRows=1)
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),NAVY),('VALIGN',(0,0),(-1,-1),'TOP'),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,LIGHT]),
        ('LINEBELOW',(0,0),(-1,-1),0.4,LINE),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('BOX',(0,0),(-1,-1),0.6,LINE)])); return t

class Doc(BaseDocTemplate):
    def __init__(s,fn,student,**k):
        super().__init__(fn,pagesize=A4,leftMargin=LM,rightMargin=RM,topMargin=26*mm,bottomMargin=20*mm,title="Career Discovery Report",author="Konnect Career Clarity",**k)
        s.student=student
        s.addPageTemplates([PageTemplate(id='cover',frames=[Frame(0,0,W,H,0,0,0,0)],onPage=s.cover),
                            PageTemplate(id='body',frames=[Frame(LM,20*mm,CW,H-46*mm,0,0,0,0)],onPage=s.page)])
    def cover(s,c,d):
        c.saveState(); c.setFillColor(NAVY); c.rect(0,H*0.38,W,H*0.62,0,1)
        c.setFillColor(colors.HexColor('#2E75B6')); c.circle(W*0.86,H*0.86,46*mm,0,1)
        c.setFillColor(colors.HexColor('#F0A500')); c.circle(W*0.12,H*0.43,22*mm,0,1)
        c.setFillColor(colors.HexColor('#1D9E75')); c.circle(W*0.93,H*0.47,13*mm,0,1)
        c.setFillColor(LIGHT); c.rect(0,0,W,H*0.38,0,1)
        c.setFillColor(NAVY); c.rect(0,H*0.38-1.2*mm,W,1.2*mm,0,1)
        c.saveState(); c.setFillColor(colors.white); c.roundRect(LM-3*mm,H-51*mm,36*mm,36*mm,4*mm,stroke=0,fill=1); c.restoreState()
        c.drawImage(LOGO,LM,H-48*mm,width=30*mm,height=30*mm,mask='auto')
        c.setFillColor(colors.white); c.setFont('PS',11); c.drawString(LM,H-58*mm,"KONNECT CAREER CLARITY")
        c.setFont('PB',34); c.drawString(LM,H*0.66,"Your Career"); c.drawString(LM,H*0.66-14*mm,"Discovery Report")
        c.setFillColor(GOLD); c.rect(LM,H*0.66-22*mm,28*mm,1.6*mm,0,1)
        c.setFillColor(colors.white); c.setFont('P',12.5)
        c.drawString(LM,H*0.66-33*mm,"Your interests, strengths and the paths worth exploring")
        st_=s.student; y=H*0.30
        c.setFillColor(NAVY); c.setFont('PS',9); c.drawString(LM,y+14*mm,"PREPARED FOR")
        c.setFont('PB',22); c.drawString(LM,y+4*mm,st_['name'])
        c.setFont('P',11.5); c.setFillColor(INK)
        c.drawString(LM,y-6*mm,f"Grade {st_['grade']}   |   {st_['city']}, {st_['state']}")
        if st_.get('school'): c.drawString(LM,y-13*mm,st_['school'])
        c.setFont('P',9); c.setFillColor(MUTED); c.drawString(LM,y-26*mm,"Report date: "+datetime.date.today().strftime('%d %B %Y'))
        c.setFont('PS',8.5); c.setFillColor(NAVY); c.drawString(LM,16*mm,"CONFIDENTIAL  |  konnectcareerclarity@gmail.com  |  7657861998")
        c.restoreState()
    def page(s,c,d):
        c.saveState(); c.drawImage(LOGO,LM,H-19*mm,width=11*mm,height=11*mm,mask='auto')
        c.setFont('PS',8.5); c.setFillColor(NAVY); c.drawString(LM+14*mm,H-13.5*mm,"KONNECT CAREER CLARITY")
        c.setFont('P',8.5); c.setFillColor(MUTED); c.drawRightString(W-RM,H-13.5*mm,"Career Discovery Report")
        c.setStrokeColor(BLUE); c.setLineWidth(1); c.line(LM,H-21*mm,W-RM,H-21*mm)
        c.setStrokeColor(LINE); c.setLineWidth(0.6); c.line(LM,15*mm,W-RM,15*mm)
        c.setFont('P',7.5); c.setFillColor(MUTED)
        c.drawString(LM,10.5*mm,f"Confidential. Prepared for {s.student['name']}.   konnectcareerclarity@gmail.com | 7657861998")
        c.drawRightString(W-RM,10.5*mm,f"Page {d.page}"); c.restoreState()

SUBJ_STREAM={"Mathematics":"PCM","Physics":"PCM","Computer Science":"PCM","Chemistry":"PCM","Biology":"PCB","Economics":"COM","Business Studies":"COM","Accountancy":"COM",
 "English":"HUM","Hindi or my regional language":"HUM","Social Science (History, Geography, Civics)":"HUM","Art or Design":"HUM","Music":"HUM","Physical Education":"HUM"}

BOOK_URL='https://calendar.app.google/5yu1fAyP11pyyGM56'
def make_report(profile,resp,outfile):
    g=int(profile['grade']); form_g=9 if g<=9 else 10
    abroad=str(profile.get('plan','')).strip().lower().startswith('abroad')
    R=S.score(resp,form_g)
    doc=Doc(outfile,profile); E=[]
    name=esc(profile['name']); first=esc(profile['name'].split()[0])
    top=R['clusters'][:5]
    # ---- cover then welcome
    E+= [NextPageTemplate('body'),PageBreak()]
    E+= [P("WELCOME",KICK),P(f"Hello {first}, welcome to your report",H1),Rule(),Spacer(1,4)]
    E+= [P("You have just taken the first step in planning your future. This report is built from your own answers. It shows what you enjoy, what you are good at today and how you like to study and work, and then it points to career paths that are worth exploring."),
         P("It is not a test you pass or fail, and it does not decide your future. Think of it as a map with several good roads on it.")]
    E+= [P("What this report looks at",H2)]
    dims=[("1","Interests","What you enjoy doing. Based on Holland's RIASEC model."),("2","Strengths","Where your natural tendencies lie. Based on Gardner's Multiple Intelligences."),
          ("3","Aptitude","How you did on puzzles in four thinking skills."),("4","Work style and values","How you like to work and what matters to you."),("5","Study preferences","The ways of studying that suit you.")]
    rows=[[Paragraph(f"<font color='#ffffff'><b>{a}</b></font>",st('n',alignment=TA_CENTER,fontName='PB',fontSize=13,leading=16,spaceAfter=0)),Paragraph(f"<b>{esc(b)}</b><br/>{esc(c)}",CELL)] for a,b,c in dims]
    t=Table(rows,colWidths=[11*mm,CW-11*mm],rowHeights=[14*mm]*5)
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(0,-1),BLUE),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LINEBELOW',(0,0),(-1,-2),0.5,colors.white),('BOX',(0,0),(-1,-1),0.6,LINE),('BACKGROUND',(1,0),(1,-1),LIGHT),('LEFTPADDING',(1,0),(1,-1),10)]))
    E+= [t,Spacer(1,8)]
    E+= [P("How to read it",H2)]+bullets(["Read the first pages on your own. Then read the career pages with your parents.","Words and levels are used instead of marks on purpose. They describe tendencies, not talent limits.","Every suggestion tells you why it appeared. If something surprises you, talk about it, because that is where good conversations start.","Choose two or three clusters to explore properly. You do not need to decide everything now."])
    E+= [Spacer(1,6),card(P("<b>Research-informed.</b> This assessment is based on Holland's RIASEC interest model, Gardner's Multiple Intelligences and the VARK study-preference model, together with original aptitude puzzles written for this assessment.",SMALL),bg=CREAM,border=colors.HexColor('#F4DE9E')),PageBreak()]
    # ---- parents
    E+= [P("FOR FAMILIES",KICK),P("A note for parents",H1),Rule(),Spacer(1,4)]
    for ti,tx in T.PARENT[1:]:
        E+= [card([P(esc(ti),H3),P(esc(tx))],bg=colors.white),Spacer(1,5)]
    E.insert(len(E)-6,P(esc(T.PARENT[0][1])))  # intro paragraph above cards
    rows=[[P(f"<b>{esc(a)}</b><br/>{esc(b)}",st('c3',textColor=colors.white,fontSize=9.2,leading=13,spaceAfter=0))] for a,b in T.PARENT3C]
    t=Table([[ [P(f"<font color='#F0A500'><b>{i+1}. {esc(a)}</b></font><br/>{esc(b)}",st('c3',textColor=colors.white,fontSize=9.4,leading=13.5,spaceAfter=0))] for i,(a,b) in enumerate(T.PARENT3C)]],colWidths=[CW/3]*3)
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),NAVY),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),10),('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),10),('ROUNDEDCORNERS',[8,8,8,8])]))
    E+= [Spacer(1,4),P("Three things that help",H2),t,Spacer(1,8)]
    E+= [P("A family conversation guide",H2),card(bullets(["Each of you reads the report alone first, then you meet.","Start with what pleased or surprised you, before any worries.","Ask your child which two clusters they find most interesting, and why.","Write down questions about courses, exams and costs, and bring them to a counselling session.","Agree on one small action for this month, such as speaking to someone who works in that field."]),bg=colors.white,pad=9),PageBreak()]
    # ---- profile at a glance
    code=R['code']; ctop=", ".join(TYPE for TYPE in [S.TYPE_NAME[x] for x in code])
    mi_names=[T.MI[k][0] for k in R['mi_top']]; stu_names=[T.STUDY[k][0] for k in R['stu_top']]
    ws=R['workstyle']; wsl=[T.WS_TEXT[v][0] for v in ws.values() if v and v!='balanced']
    vals=[T.VAL[v][0] for v in R['values_top']]
    E+= [P("YOUR PROFILE",KICK),P("Your profile at a glance",H1),Rule(),Spacer(1,4)]
    def row(a,b): return [Paragraph(esc(a),CELLB),Paragraph(esc(b),CELL)]
    prof=[row("Top interests",f"{ctop} ({code})" if not R['broad'] else f"Broad interests (top three: {ctop})"),
          row("Strongest tendencies"," , ".join(mi_names).replace(" , ",", ")),
          row("Aptitude levels","; ".join(f"{S.APT_NAME[a]}: {R['apt_band'][a]}" for a in "VNLS")),
          row("Study preferences",", ".join(stu_names)),
          row("Work style",("; ".join(wsl)) if wsl else "Balanced across the pairs we asked about"),
          row("What matters most",", ".join(vals) if len(vals)<4 else "All four values matter to you")]
    t=Table(prof,colWidths=[38*mm,CW-38*mm]); t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('ROWBACKGROUNDS',(0,0),(-1,-1),[LIGHT,colors.white]),('BOX',(0,0),(-1,-1),0.6,LINE),('LINEBELOW',(0,0),(-1,-2),0.4,LINE),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),('LEFTPADDING',(0,0),(-1,-1),9)]))
    names=[S.TYPE_NAME[x].lower() for x in code]
    strong=[S.APT_NAME[a].lower() for a in "VNLS" if R['apt_band'][a]=="Strong"] or [S.APT_NAME[a].lower() for a in "VNLS" if R['apt_band'][a]=="Solid"]
    apt_line=(f"Your puzzle results are strongest in {' and '.join(strong[:2])}." if strong else "Your puzzle skills are still developing in all four areas, which is worth building with regular practice.")
    interest_line=(f"Your interests are wide, with {names[0]}, {names[1]} and {names[2]} just ahead." if R['broad'] else f"Your interests lean towards {names[0]}, {names[1]} and {names[2]} activities.")
    para=f"{first}, {interest_line[0].lower()+interest_line[1:]} Your strongest tendencies are {', '.join(m.lower() for m in mi_names[:-1]) + (' and ' if len(mi_names)>1 else '') + mi_names[-1].lower() if mi_names else 'still emerging'}. {apt_line} Together, these point first towards {top[0]['name']}, {top[1]['name']} and {top[2]['name']}."
    E+= [t,Spacer(1,8),P("In a few words",H2),card(P(esc(para)),bg=colors.HexColor('#E9F7F1'),border=colors.HexColor('#BFE5D4'),pad=9),Spacer(1,8),P("Your top five career clusters",H2),P("These are the clusters where your interests and aptitude line up best today.",SMALL)]
    rows=[[Paragraph(f"<b>{i+1}</b>",st('r',textColor=colors.white,alignment=TA_CENTER,fontName='PB',fontSize=11,leading=14,spaceAfter=0)),Paragraph(f"<b>{esc(c['name'])}</b><br/><font size='8.5' color='#66758a'>{esc(c['why'])}</font>",CELL)] for i,c in enumerate(top)]
    t=Table(rows,colWidths=[11*mm,CW-11*mm]); t.setStyle(TableStyle([('BACKGROUND',(0,0),(0,-1),TEAL),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LINEBELOW',(0,0),(-1,-1),1,colors.white),('BACKGROUND',(1,0),(1,-1),LIGHT),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),('LEFTPADDING',(1,0),(1,-1),10)]))
    E+= [t,PageBreak()]
    # ---- interests
    E+= [P("DIMENSION 1",KICK),P("Your interests",H1),Rule(),Spacer(1,4)]
    E+= [P("We used Holland's RIASEC model, which groups interests into six types. The longer the bar, the more you enjoyed activities of that type. Your top three types make your interest code.")]
    order=sorted("RIASEC",key=lambda t:-R['riasec_avg'][t]); cols={"R":BLUE,"I":TEAL,"A":colors.HexColor('#8E5CA8'),"S":colors.HexColor('#E07A5F'),"E":GOLD,"C":colors.HexColor('#5B7C99')}
    rows=[(S.TYPE_NAME[t],(R['riasec_avg'][t]-1)/4,cols[t]) for t in order]
    E+= [card(Bars(rows,w=CW-24,lab=36*mm),bg=colors.white),Spacer(1,8)]
    E+= [P(f"Your interest code: <font color='#1D9E75'><b>{code}</b></font>",H2)]
    if R['broad']: E+= [card(P(esc(T.INTEREST_BROAD)),bg=CREAM,border=colors.HexColor('#F4DE9E')),Spacer(1,6)]
    for t in code:
        ti,de,en=T.INTEREST[t]
        E+= [KeepTogether([headerbar(ti,bg=cols[t]),card([P(esc(de)),P(f"<b>You may enjoy:</b> {esc(en)}",CELL)],bg=colors.white,pad=8),Spacer(1,6)])]
    E+= [PageBreak()]
    # ---- strengths
    E+= [P("DIMENSION 2",KICK),P("Your strongest tendencies",H1),Rule(),Spacer(1,4)]
    E+= [P("Based on Gardner's theory of Multiple Intelligences, these are the ways of thinking that came through most strongly in your answers."),P(esc(T.MI_NOTE),SMALL),Spacer(1,4)]
    for k in R['mi_top']:
        ti,de,gr=T.MI[k]
        E+= [KeepTogether([headerbar(ti,bg=TEAL),card([P(esc(de)),P(f"<b>Ways to grow it:</b> {esc(gr)}",CELL)],bg=colors.white,pad=8),Spacer(1,6)])]
    E+= [P("The eight ways of thinking",H2),P("Everyone has some of each. These are the eight areas in the model, so you can see where your top three sit.",SMALL)]
    rows8=[[Paragraph(f"<b>{esc(T.MI[k][0])}</b>",CELLB),Paragraph(esc(T.MI[k][1].split('. ')[0].rstrip('.')+'.'),CELL)] for k in T.MI]
    t8=Table(rows8,colWidths=[40*mm,CW-40*mm]); t8.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('ROWBACKGROUNDS',(0,0),(-1,-1),[LIGHT,colors.white]),('BOX',(0,0),(-1,-1),0.6,LINE),('LINEBELOW',(0,0),(-1,-2),0.4,LINE),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),('LEFTPADDING',(0,0),(-1,-1),8)]))
    E+= [t8,PageBreak()]
    # ---- aptitude
    E+= [P("DIMENSION 3",KICK),P("Your aptitude",H1),Rule(),Spacer(1,4)]
    E+= [P("You answered puzzles in four thinking areas. Your level in each is shown below as Developing, Solid or Strong."),P(esc(T.APT_NOTE)+f" Each area is based on {R['apt_total']['V']} puzzles.",SMALL),Spacer(1,4)]
    for a in "VNLS":
        nm,de,use=T.APT_DESC[a]; b=R['apt_band'][a]
        left=[P(esc(nm),H3),P(esc(de),CELL),P(f"<font color='#66758a'>Useful in: {esc(use)}</font>",SMALL)]
        right=[Meter(b,w=52*mm)]
        extra_in=[P(esc(T.APT_BAND[b]),CELL)]+([P(f"<b>Try this:</b> {esc(T.APT_TIP[a])}",CELL)] if b!="Strong" else [])
        body=[[left,right],[extra_in,""]]
        t=Table(body,colWidths=[CW-70*mm,60*mm]); t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('SPAN',(0,1),(1,1)),('BACKGROUND',(0,0),(-1,-1),LIGHT),('BOX',(0,0),(-1,-1),0.6,LINE),('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),10),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),('ROUNDEDCORNERS',[8,8,8,8])]))
        E+= [KeepTogether([t,Spacer(1,8)])]
    E+= [PageBreak()]
    # ---- work style & values & study
    E+= [P("DIMENSIONS 4 AND 5",KICK),P("How you like to work and study",H1),Rule(),Spacer(1,4)]
    E+= [P("Work style",H2)]
    for k,v in ws.items():
        if not v: continue
        ti,tx=T.WS_TEXT[v]
        E+= [KeepTogether([card([P(f"<font color='#66758a' size='8'>{esc(T.WS_LABEL[k]).upper()}</font>",st('lab',spaceAfter=1)),P(f"<b>{esc(ti)}.</b> {esc(tx)}",CELL)],bg=colors.white,pad=7),Spacer(1,4)])]
    E+= [P("What matters most to you",H2)]
    vt=[f"<b>{esc(T.VAL[v][0])}:</b> {esc(T.VAL[v][1])}" for v in R['values_top']]
    E+= [card([P(x,CELL) for x in vt]+[P(esc(T.VAL_NOTE),SMALL)],bg=LIGHT,pad=8),Spacer(1,6)]
    E+= [P("Your study preferences",H2),P(esc(T.STUDY_NOTE),SMALL)]
    for k in R['stu_top']:
        ti,de,tips=T.STUDY[k]
        E+= [KeepTogether([headerbar(ti,bg=BLUE),card([P(esc(de),CELL)]+bullets(tips,st('b2',fontSize=9.2,leading=13,leftIndent=12,bulletIndent=2,spaceAfter=2)),bg=colors.white,pad=8),Spacer(1,6)])]
    E+= [PageBreak()]
    # ---- cluster overview
    E+= [P("CAREER DIRECTION",KICK),P("Your 21 career clusters",H1),Rule(),Spacer(1,4)]
    E+= [P("We looked at 21 career clusters and compared them with your interests and aptitude. The clusters are shown in three groups. Every cluster is worth knowing about, and the order can change as you grow and learn more.")]
    groups=[("Strong match on your results",R['clusters'][:5],TEAL),("Good match on your results",R['clusters'][5:10],BLUE),("Worth exploring",R['clusters'][10:],colors.HexColor('#8A9BB0'))]
    for gname,items,col in groups:
        rows=[[Paragraph(f"<b>{esc(c['name'])}</b>",CELL)] for c in items]
        t=Table([[headerbar(gname,w=CW,bg=col)]],colWidths=[CW]); 
        tt=Table(rows,colWidths=[CW]); tt.setStyle(TableStyle([('ROWBACKGROUNDS',(0,0),(-1,-1),[colors.white,LIGHT]),('BOX',(0,0),(-1,-1),0.6,LINE),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),('LEFTPADDING',(0,0),(-1,-1),10)]))
        E+= [KeepTogether([headerbar(gname,bg=col),tt,Spacer(1,6)])]
    E+= [PageBreak()]
    # ---- top 5 clusters in depth
    state=profile['state']
    for n,c in enumerate(top,1):
        cl=next(x for x in CLUSTERS if x['id']==c['id']); ct=CT.C[c['id']]
        E+= [P(f"YOUR TOP CLUSTER {n}",KICK),P(esc(cl['name']),H1),Rule(),Spacer(1,3)]
        E+= [card([P(f"<b>Why this appeared:</b> {esc(c['why'])}",CELL)]+([P(f"<b>{esc(c['note'])}</b>",CELL)] if c['note'] else []),bg=colors.HexColor('#E9F7F1'),border=colors.HexColor('#BFE5D4'),pad=7),Spacer(1,6)]
        E+= [P(esc(ct['summary']))]
        subl=[P(f"<b>Areas inside this cluster</b>",H3)]+bullets([s[0] for s in ct['subs']],st('b3',fontSize=9.2,leading=13,leftIndent=12,bulletIndent=2,spaceAfter=2))
        exl=[P(f"<b>Entrance routes{' in India' if abroad else ''} (high level)</b>",H3)]+bullets(cl['exams'],st('b3',fontSize=9.2,leading=13,leftIndent=12,bulletIndent=2,spaceAfter=2))
        E+= [two_col(card(subl,bg=LIGHT,pad=8,w=(CW-6*mm)/2),card(exl,bg=LIGHT,pad=8,w=(CW-6*mm)/2)),Spacer(1,8)]
        E+= [P("Roadmap",H2),table_roadmap(ct['subs']),Spacer(1,3),P(f"Typical Grade 11 and 12 stream: {esc(cl['stream'])}."+(" You do not need to know these routes yet. They are here so you can see where each path can lead." if g<=8 else ""),SMALL)]
        rolesl=[P("<b>Traditional roles</b>",H3)]+bullets(ct['trad'],st('b3',fontSize=9.2,leading=13,leftIndent=12,bulletIndent=2,spaceAfter=2))
        rolesr=[P("<b>New-age roles</b>",H3)]+bullets(ct['new'],st('b3',fontSize=9.2,leading=13,leftIndent=12,bulletIndent=2,spaceAfter=2))
        E+= [CondPageBreak(60*mm),P("Roles to look up",H2),two_col(card(rolesl,bg=colors.white,pad=8,w=(CW-6*mm)/2),card(rolesr,bg=colors.white,pad=8,w=(CW-6*mm)/2)),Spacer(1,8)]
        E+= [Spacer(1,4),card([P("<b>Good to know</b>",H3),P(esc(CT.REALITY[c['id']]),CELL)],bg=CREAM,border=colors.HexColor('#F4DE9E'),pad=8)]
        nat,more=CO.places(c['id'],state)
        pl=[P("<b>Well-known options</b>",H3)]+[Paragraph(f"<b>{esc(a)}</b><br/><font size='8' color='#66758a'>{esc(b)}</font>",st('pl',fontSize=9,leading=12,spaceAfter=3)) for a,b in nat]
        pr=[P("<b>More options to explore</b>",H3)]+([Paragraph(f"<b>{esc(a)}</b><br/><font size='8' color='#66758a'>{esc(b)}</font>",st('pl',fontSize=9,leading=12,spaceAfter=3)) for a,b,_ in more] if more else [P("Ask your counsellor for options that fit your state and course.",CELL)])
        r0=ct['trad'][0]
        E+= [PageBreak(),P(f"{esc(cl['name'])}: going deeper",H2),Rule(c=LINE)]
        sb=ct['subs'][0]
        today=("Grade %d: explore, try things and stay curious"%g) if g==8 else ("Grade %d: build strong basics and explore"%g) if g==9 else ("Grade 10: choose your stream with care" if g==10 else "Grade %d: focus on subjects and exam preparation"%g)
        steps=[("Today",today),("Grades 11 and 12",sb[1]),("Degree or course",sb[2]),("After graduation",sb[3]),("Career",ct['trad'][0])]
        cells=[[Paragraph(f"<font color='#ffffff'><b>{esc(h)}</b></font>",st('jh',fontName='PB',fontSize=8.5,leading=11,spaceAfter=0)) for h,_ in steps],[Paragraph(esc(x),CELL) for _,x in steps]]
        pt=Table(cells,colWidths=[CW/5]*5)
        pt.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),BLUE),('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,1),(-1,1),LIGHT),('BOX',(0,0),(-1,-1),0.6,LINE),('LINEAFTER',(0,0),(-2,-1),1.5,colors.white),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),9),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7)]))
        E+= [P(f"A typical journey: {esc(sb[0])}",H2),pt,Spacer(1,8)]
        sk_apt=[S.APT_NAME[a].lower() for a in "VNLS" if cl['apt'][a]>=3]; sk_int=[S.TYPE_NAME[t_].lower() for t_ in "RIASEC" if cl['ri'][t_]>=3]
        helps=[]
        if sk_int: helps.append("Interests that fit: "+", ".join(sk_int)+".")
        if sk_apt: helps.append("Thinking skills that help: "+", ".join(sk_apt)+".")
        helps.append("Habits that matter: steady daily practice, curiosity and asking questions early.")
        ask=["What part of this cluster excites me most, and why?","Which subject here will I need to work hardest in?","Can I see myself doing this work for many years?"]
        E+= [two_col(card([P("<b>What helps in this cluster</b>",H3)]+bullets(helps,st('b4',fontSize=9.2,leading=13,leftIndent=12,bulletIndent=2,spaceAfter=3)),bg=LIGHT,pad=8,w=(CW-6*mm)/2),
                        card([P("<b>Questions to ask yourself</b>",H3)]+bullets(ask,st('b4',fontSize=9.2,leading=13,leftIndent=12,bulletIndent=2,spaceAfter=3)),bg=LIGHT,pad=8,w=(CW-6*mm)/2)),Spacer(1,8)]
        if abroad:
            E+= [KeepTogether([P("Studying abroad?",H2),card(P("You told us you may study abroad. Courses, entrance tests, costs and admission rules differ from country to country and change every year, so this report does not list institutions. To plan studying abroad, please book a separate 30-minute counselling session, free of cost, by messaging us on WhatsApp at 7657861998.",CELL),bg=LIGHT,pad=8)])]
        else:
            E+= [KeepTogether([P("Other places to explore",H2),two_col(card(pl,bg=LIGHT,pad=8,w=(CW-6*mm)/2),card(pr,bg=LIGHT,pad=8,w=(CW-6*mm)/2)),Spacer(1,3),
            P("Entrance exams, eligibility and programmes change every year. Please confirm details on the official website before you decide. Being listed here is not a promise of admission.",SMALL)])]
        E+= [Spacer(1,6),KeepTogether([P("Try it this month",H2),card(bullets([f"Watch two 'a day in the life of a {r0.lower()}' videos and note what you like and dislike.",f"Talk to one person who works in {cl['name'].lower()}, such as a family friend, a teacher or an alumnus.","Read about one entrance route above, and note the subjects it needs."]),bg=CREAM,border=colors.HexColor('#F4DE9E'),pad=8)]),PageBreak()]
    # ---- skills worth building
    E+= [P("SKILLS FOR YOUR FUTURE",KICK),P("Skills worth building",H1),Rule(),Spacer(1,4)]
    E+= [P("Whatever you choose, some skills help in every career. We did not measure these skills, so this is not a score. These are the skills we suggest you build, based on your top clusters, your puzzle results and the way you like to work."),Spacer(1,2)]
    for k,helps in SKL.pick(R,4):
        nm,why,act_y,act_o=SKL.SK[k]; acts=act_y if g<=9 else act_o
        hl=f"<b>Why it matters for you:</b> it helps in {esc(' and '.join(helps))}." if helps else "<b>Why it matters for you:</b> it supports almost any path you choose."
        E+= [KeepTogether([headerbar(nm,bg=TEAL),card([P(esc(why),CELL),P(hl,CELL),P("<b>Start this month:</b>",CELL)]+bullets(acts,st('b5',fontSize=9.2,leading=13,leftIndent=12,bulletIndent=2,spaceAfter=2)),bg=colors.white,pad=8),Spacer(1,6)])]
    E+= [PageBreak()]
    # ---- stream guide (Grade 10-12) or early preview (Grade 8-9)
    sk=R['stream']; 
    enj=[x for x in (resp.get('CTX-2') or []) if isinstance(resp.get('CTX-2'),list)]; sc=[x for x in (resp.get('CTX-3') or []) if isinstance(resp.get('CTX-3'),list)]
    subj=set(enj)|set(sc)
    planned=resp.get('CTX-1','')
    if g<=9:
        E+= [P("YOUR NEXT STEPS",KICK),P("An early look at streams",H1),Rule(),Spacer(1,4)]
        E+= [P("You will choose a stream after Grade 10, so there is time. This is an early preview, not a decision. Your results so far point towards the following.")]
    else:
        E+= [P("ACADEMIC PATH",KICK),P("Your stream guide for Grades 11 and 12" if g<=11 else "How your stream fits your results",H1),Rule(),Spacer(1,4)]
        E+= [P("A stream decides which subjects you study for two years. Based on your top clusters and your aptitude, these are the two streams that fit your results best." if g<=11 else "Based on your top clusters and your aptitude, these are the two streams that fit your results best. Use this to check your own choice against your results.")]
    labels=["Best fit on your results","Also worth considering"]
    for i,s_ in enumerate(sk):
        ti,sub,opens,suits=T.STREAM[s_]
        line=[P(f"<font color='#1D9E75'><b>{labels[i].upper()}</b></font>",st('l',fontSize=8,spaceAfter=2)),P(f"<b>{esc(ti)}</b>",H2),P(f"<b>Subjects:</b> {esc(sub)}",CELL),P(f"<b>Careers it opens:</b> {esc(opens)}",CELL),P(f"<b>Suits students who:</b> {esc(suits[len('Suits students who '):] if suits.startswith('Suits students who ') else suits)}",CELL)]
        match=[x for x in subj if SUBJ_STREAM.get(x)==s_]
        if match: line.append(P(f"<b>Your subjects:</b> You told us you enjoy or do well in {esc(', '.join(sorted(match)))}, which fits this stream.",CELL))
        E+= [card(line,bg=colors.white if i else colors.HexColor('#E9F7F1'),border=colors.HexColor('#BFE5D4') if i==0 else LINE,pad=9),Spacer(1,7)]
    if R['stream_note']: E+= [card(P(esc(R['stream_note']),CELL),bg=CREAM,border=colors.HexColor('#F4DE9E'),pad=8),Spacer(1,6)]
    pm={"Science with Maths (PCM)":"PCM","Science with Biology (PCB)":"PCB","Science with Maths and Biology (PCMB)":"PCMB","Commerce with Maths":"COM","Commerce without Maths":"COM","Humanities or Arts":"HUM"}
    pk=pm.get(planned)
    if pk and pk not in sk and not (pk=="PCMB" and any(x in sk for x in ("PCM","PCB"))):
        E+= [card(P(f"You mentioned that you are thinking about {esc(planned)}. Your results also point towards {esc(T.STREAM[sk[0]][0])}. This is worth talking through with your family and a counsellor before you decide. Your interest and effort matter as much as these results.",CELL),bg=LIGHT,pad=8),Spacer(1,6)]
    E+= [P(esc(T.STREAM_KEEP)),P("A stream guide is guidance based on assessment patterns. The final decision should include your marks, your school's subject options and a conversation with a counsellor.",SMALL),Spacer(1,8)]
    # ---- action plan
    E+= [CondPageBreak(70*mm),P("NEXT STEPS",KICK),P("Your action plan",H1),Rule(),Spacer(1,4)]
    if g==8:
        ph=[("Phase 1: This month",["Read this report again, and underline three things that surprised you.","Share it with your parents and talk about the clusters you liked.","Try one new activity or hobby linked to your top interest."]),
            ("Phase 2: Next three months",["Start two of the skills suggested in this report.","Join one club, competition or hobby class linked to your top cluster.","Speak to two people who work in a field you liked."]),
            ("Phase 3: Grades 9 and 10",["Notice which subjects you enjoy most, and which you find hard.","Build the area marked 'worth building' with ten minutes of daily practice.","Come back for a counselling session in Grade 9 or early Grade 10, before you choose a stream."])]
    elif g==9:
        ph=[("Phase 1: This month",["Read this report again, and underline three things that surprised you.","Share it with your parents and talk about the clusters you liked.","Try one new activity linked to your top interest."]),
            ("Phase 2: Next three months",["Strengthen the area marked 'worth building' with ten minutes of daily practice.","Join one club, competition or hobby class linked to your top cluster.","Speak to two people who work in a field you liked."]),
            ("Phase 3: Before Grade 10",["Notice which subjects you enjoy most, and which you find hard.","Read about the stream choices and what each opens.","Come back for a counselling session when you are in Grade 9 or early Grade 10."])]
    elif g==10:
        ph=[("Phase 1: This month",["Read this report with your parents and shortlist two clusters.","List the subjects each stream needs, and compare them with the ones you enjoy.","Look up one entrance route for each shortlisted cluster."]),
            ("Phase 2: Before choosing your stream",["Talk to a teacher in each subject you are considering.","Speak to students already in Grade 11 and 12 in those streams.","Book a counselling session to make your final choice with confidence."]),
            ("Phase 3: Grade 11 and 12",["Build the skills marked 'worth building' with a steady routine.","Find out entrance exam dates, syllabus and eligibility early.","Use holidays for projects, internships or short courses in your cluster."])]
    else:
        ph=[("Phase 1: This month",["Read this report with your parents and shortlist two clusters.","Check the subject and exam requirements for each route.","Write down the entrance exams and their dates."]),
            ("Phase 2: Next three months",["Build a study plan around the exams that match your top clusters.","Visit or research three institutions in each shortlisted cluster.","Speak to a professional or a college student in that field."]),
            ("Phase 3: This year",["Prepare applications and documents on time.","Keep a backup option in a related cluster.","Book a counselling session to review your choices before applying."])]
    for ti,its in ph:
        E+= [KeepTogether([headerbar(ti),card(bullets(its),bg=colors.white,pad=8),Spacer(1,8)])]
    logrows=[[Paragraph(h,CELLW) for h in ("Career I explored","What I learned","What surprised me","My next step")]]+[[Paragraph("&nbsp;<br/>&nbsp;<br/>",CELL)]*4 for _ in range(3)]
    lg=Table(logrows,colWidths=[CW/4]*4); lg.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),BLUE),('GRID',(0,0),(-1,-1),0.6,LINE),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
    E+= [KeepTogether([P("My exploration log",H2),P("Use this to note down each career you look into.",SMALL),lg]),CondPageBreak(110*mm)]
    # ---- closing
    E+= [P("CLOSING",KICK),P("Want to talk it through?",H1),Rule(),Spacer(1,4)]
    E+= [P("A report shows patterns. A conversation helps you turn them into a plan. Your one-to-one counselling session with Ritu is included with this assessment. In 30 minutes we go through your results, answer your family's questions and plan the next steps for your stream, course and entrance exams."),
         card([P("<b>Book your included 30-minute session</b>",H3),P(f"Booking link: <link href='{BOOK_URL}' color='#1D6FB8'>{BOOK_URL}</link><br/>Email: konnectcareerclarity@gmail.com<br/>Phone: 7657861998<br/>Website: konnectcareerclarity.com",BODY),P("Please book after you and your parents have read the report.",SMALL)],bg=colors.HexColor('#E9F7F1'),border=colors.HexColor('#BFE5D4'),pad=10),Spacer(1,12)]
    E+= [P("About your counsellor",H2),P("Ritu Singh is a career counsellor with more than 19 years in education, including 10+ years as a Mathematics Coordinator in school education. She is the founder of Konnect Career Clarity and is trained in career and education counselling.",BODY),Spacer(1,10)]
    E+= [KeepTogether([P("Disclaimer",H2),card(P(esc(T.DISCLAIMER),st('disc',fontSize=8.5,leading=12.5,textColor=INK)),bg=LIGHT,pad=9)])]
    doc.build(E)
    return R

if __name__=="__main__":
    import random,sys
    random.seed(3)
    def mk(grade,likes,strong):
        r={}
        for b in S.form_items(grade):
            i=b['id']
            if i.startswith('INT-'): r[i]=5 if i[4] in likes else random.choice([1,2])
            elif i.startswith('APT-'): r[i]=b['answer'] if i[4] in strong else 'D' if b['answer']!='D' else 'A'
            elif b['fmt'].startswith(('Agree','Self')): r[i]=random.choice([2,3,4,5])
        r['CTX-1']='Science with Biology (PCB)'; r['CTX-2']=['Mathematics','Physics','Computer Science']; r['CTX-3']=['Mathematics','English']
        return r
    prof=dict(name="Aarav Sharma",plan="India",grade="10",city="Jalandhar",state="Punjab",school="Sample Public School")
    R=make_report(prof,mk(10,"IR","NL"),os.path.join(HERE,'sample_g10.pdf'))
    prof8=dict(name="Kabir Singh",plan="India",grade="8",city="Amritsar",state="Punjab",school="")
    make_report(prof8,mk(9,"RE","VN"),os.path.join(HERE,'sample_g8.pdf'))
    prof9=dict(name="Meher Kaur",plan="Abroad",grade="9",city="Ludhiana",state="Punjab",school="")
    make_report(prof9,mk(9,"AS","VS"),os.path.join(HERE,'sample_g9.pdf'))
    print(R['code'],[c['name'] for c in R['clusters'][:5]],R['stream'])
