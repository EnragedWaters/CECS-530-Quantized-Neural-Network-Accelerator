"""Rebuild editable slide visuals from checked results and the speaking-note source.

Requires python-pptx. Run from any directory; the current deck supplies its native
Ocean Waves theme. --slides 1-7 updates a section; the default rebuilds all slides.
Photos, dataset images and actual demo captures are embedded, never linked.
"""
from pathlib import Path
import argparse
import json
from pptx import Presentation
from pptx.chart.data import CategoryChartData, XyChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_MARKER_STYLE
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN, MSO_AUTO_SIZE
from pptx.oxml.xmlchemy import OxmlElement
from pptx.util import Inches, Pt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
A = json.loads((ROOT/'results/accelerator-results.json').read_text())
M = json.loads((ROOT/'results/mnist-results.json').read_text())
NOTES = json.loads((HERE/'slide-notes.json').read_text())
P = Presentation(HERE/'project-presentation.pptx')
W,H=13.333333,7.5
BG='EFF8FB';NAVY='12394E';INK='18394C';MUTED='4C6D7B';TEAL='187A75'
BLUE='2B7296';ORANGE='AB5A35';BLUE_LIGHT='CEE4EE';ORANGE_LIGHT='F0D8C5'
LINE='B9D6DF';WHITE='FFFFFF';PALE='DCEEF3'
FONT='Arial'
TITLES=[
 'Quantized Neural Network Accelerator','Smaller numbers. Three questions.',
 'One image becomes ten scores','Learn → calibrate → freeze → test',
 'Add the bias. Then rescale.','Our matrix engine, one stage at a time',
 'A hand-checkable six-cycle schedule','Correct arithmetic can still guess wrong',
 'Accuracy stayed almost unchanged','Less data, fewer matrix-stage cycles',
 'Feed the lanes before adding more','Faster loading leaves compute unchanged',
 'The timing boundary matters','Precision and data supply belong together',
 'Backup · operand supply limits','Backup · integer bias and rescaling',
 'Backup · actual demo views','Backup · sources and photo credits']
LAYOUT=[]

def color(c):return RGBColor.from_string(c)
def flat(shape):
    shape._element.spPr.append(OxmlElement('a:effectLst'))
    for r in shape._element.xpath('./p:style/a:effectRef'):r.set('idx','0')
    return shape

def box(s,x,y,w,h,fill=WHITE,stroke=None,radius=True):
    sh=s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE,Inches(x),Inches(y),Inches(w),Inches(h))
    sh.fill.solid();sh.fill.fore_color.rgb=color(fill)
    if radius:sh.adjustments[0]=.08
    if stroke:sh.line.color.rgb=color(stroke);sh.line.width=Pt(1)
    else:sh.line.fill.background()
    return flat(sh)

def text(s,value,x,y,w,h,size=24,c=INK,bold=False,align=PP_ALIGN.LEFT,name=None):
    sh=s.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h));sh.name=name or ('text.'+str(len(s.shapes)))
    tf=sh.text_frame;tf.clear();tf.word_wrap=True;tf.auto_size=MSO_AUTO_SIZE.NONE
    tf.margin_left=tf.margin_right=tf.margin_top=tf.margin_bottom=0
    for i,line in enumerate(str(value).split('\n')):
        p=tf.paragraphs[0] if i==0 else tf.add_paragraph();p.text=line
        p.font.name=FONT;p.font.size=Pt(size);p.font.bold=bold;p.font.color.rgb=color(c)
        p.alignment=align;p.line_spacing=1.05;p.space_after=Pt(2)
    LAYOUT.append({'slide':list(P.slides).index(s)+1,'text':str(value),'x':x,'y':y,'w':w,'h':h,'size':size})
    return sh

def line(s,x1,y1,x2,y2,c=LINE,width=2):
    sh=s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,Inches(x1),Inches(y1),Inches(x2),Inches(y2));sh.line.color.rgb=color(c);sh.line.width=Pt(width);return sh

def arrow(s,x,y,w=.42,h=.28,c=TEAL):
    sh=s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW,Inches(x),Inches(y),Inches(w),Inches(h));sh.fill.solid();sh.fill.fore_color.rgb=color(c);sh.line.fill.background();return flat(sh)

def circle(s,x,y,d,fill=WHITE,stroke=LINE):
    sh=s.shapes.add_shape(MSO_SHAPE.OVAL,Inches(x),Inches(y),Inches(d),Inches(d));sh.fill.solid();sh.fill.fore_color.rgb=color(fill);sh.line.color.rgb=color(stroke);return flat(sh)

def picture(s,name,x,y,w,h,cover=False):
    path=HERE/'assets'/name
    if cover:
        image=s.shapes.add_picture(str(path),Inches(x),Inches(y),width=Inches(w),height=Inches(h));image.crop_left=image.crop_right=image.crop_top=image.crop_bottom=0
        iw,ih=image.image.size;ratio=iw/ih;target=w/h
        if ratio>target:image.crop_left=image.crop_right=(1-target/ratio)/2
        else:image.crop_top=image.crop_bottom=(1-ratio/target)/2
    else:
        from PIL import Image
        with Image.open(path) as im:iw,ih=im.size
        scale=min(w/iw,h/ih);ww,hh=iw*scale,ih*scale
        image=s.shapes.add_picture(str(path),Inches(x+(w-ww)/2),Inches(y+(h-hh)/2),width=Inches(ww),height=Inches(hh))
    image.name='image.'+name
    return image

def icon(s,kind,x,y,c=TEAL):
    if kind=='clock':
        circle(s,x,y,.72,WHITE,c);line(s,x+.36,y+.36,x+.36,y+.13,c,3);line(s,x+.36,y+.36,x+.55,y+.44,c,3)
    elif kind=='memory':
        box(s,x,y+.12,.9,.5,WHITE,c,False)
        for k in range(4):box(s,x+.09+k*.19,y+.23,.12,.22,c,radius=False)
        for k in range(5):box(s,x+.08+k*.15,y+.62,.04,.12,c,radius=False)
    else:
        circle(s,x,y,.75,WHITE,c);circle(s,x+.16,y+.16,.43,WHITE,c);circle(s,x+.29,y+.29,.17,c,c)

def fresh(index,section='PROJECT',dark=False):
    s=P.slides[index-1];rids=set()
    for sh in list(s.shapes):
        rids.update(sh._element.xpath('.//@r:embed|.//@r:link|.//@r:id'))
        s.shapes._spTree.remove(sh._element)
    for rid in rids:
        if rid in s.part.rels:s.part.drop_rel(rid)
    s.background.fill.solid();s.background.fill.fore_color.rgb=color(NAVY if dark else BG)
    if index>=15:s._element.set('show','0')
    else:s._element.set('show','1')
    wave=s.shapes.add_shape(MSO_SHAPE.WAVE,0,Inches(7.13),P.slide_width,Inches(.37));wave.fill.solid();wave.fill.fore_color.rgb=color('175675' if dark else 'D2E9EE');wave.line.fill.background();flat(wave)
    text(s,'CECS 530  /  '+section,.60,.20,11,.25,12,TEAL if not dark else 'ACE6D8',True)
    text(s,f'{index:02d} / 14' if index<=14 else f'BACKUP {index-14} / 4',11.6,7.13,1.1,.25,12,MUTED if not dark else 'C0DDE7',align=PP_ALIGN.RIGHT)
    if index>1:text(s,TITLES[index-1],.60,.66,12.1,.62,32,NAVY if not dark else WHITE,True,name='slide-title')
    record=NOTES[index-1];meta='Backup; outside the main timing.' if index>14 else f"Suggested presenter: {record['presenter']}. Planned time: {record['seconds']} seconds."
    s.notes_slide.notes_text_frame.text=meta+'\n\n'+record['notes']+'\n\nReference details:\n'+record['reference']
    return s

def add_reference(s,value):s.notes_slide.notes_text_frame.text+='\n'+value

def s1():
    s=fresh(1,'FALL 2026 · TOPIC 15',True)
    text(s,'Quantized Neural\nNetwork Accelerator',.75,1.6,7.3,1.7,44,WHITE,True,name='slide-title')
    text(s,'Smaller numbers.\nA balanced data path.',.80,3.65,7,1.05,29,'C0DDE7')
    text(s,'Troy Waters · Tuong Tran',.80,5.35,7,.45,24,WHITE)
    text(s,'High-level software architecture model',.80,6.15,8,.4,18,'ACE6D8')
    # Actual dataset images introduce the workload rather than a decorative stock photo.
    for j,image in enumerate([0,1,3,4]):
        x=8.65+(j%2)*1.70;y=1.60+(j//2)*1.85
        box(s,x-.10,y-.10,1.55,1.55,WHITE,radius=True);picture(s,f'digit-{image}.png',x,y,1.35,1.35)
    text(s,'Real MNIST test images',8.45,5.75,4,.4,18,'C0DDE7',align=PP_ALIGN.CENTER)

def s2():
    s=fresh(2,'THE QUESTION')
    picture(s,'fpga-board.jpg',.65,1.65,4.65,3.55,True)
    text(s,'FPGA prototype board · hardware context',.65,5.38,4.65,.6,16,MUTED)
    for j,(kind,label,question,c) in enumerate([('target','Accuracy','Same predictions?',BLUE),('memory','Memory','Fewer bytes?',TEAL),('clock','Execution','Fewer cycles?',ORANGE)]):
        x=5.65+j*2.35;icon(s,kind,x+.6,1.95,c);text(s,label,x,3.05,2.3,.45,25,c,True,PP_ALIGN.CENTER);text(s,question,x,3.65,2.3,.7,20,INK,False,PP_ALIGN.CENTER)
    box(s,5.65,5.05,6.95,1.15,WHITE,LINE)
    text(s,'Our contribution',5.90,5.20,6.3,.3,18,TEAL,True)
    text(s,'Arithmetic → cycle model → checked results',5.90,5.64,6.35,.42,21)
    add_reference(s,'Real photo: WillWare, Fpgaboard.jpg (2010), public domain. Source and original: presentation/visual-sources.md. It depicts an FPGA prototyping board, not hardware built or measured in this project.')

def s3():
    s=fresh(3,'THE WORKLOAD')
    for j,image in enumerate([0,1,2,3,4,5]):
        picture(s,f'digit-{image}.png',.70+j*1.0,1.65,.78,.78)
    text(s,'MNIST: labeled 28 × 28 grayscale digits',.70,2.60,9,.45,23)
    for x,value,label,c in [(0.8,'784','pixel inputs',BLUE),(4.9,'64','hidden values',TEAL),(9.0,'10','digit scores',ORANGE)]:
        box(s,x,3.50,3.45,1.70,WHITE,LINE);text(s,value,x+.15,3.70,3.15,.70,46,c,True,PP_ALIGN.CENTER);text(s,label,x+.15,4.55,3.15,.40,23,INK,False,PP_ALIGN.CENTER)
    arrow(s,4.32,4.06);arrow(s,8.42,4.06)
    text(s,'ReLU',8.42,4.70,.55,.3,14,MUTED,align=PP_ALIGN.CENTER)
    text(s,'50,816 multiply-adds per image',.8,6.08,11.65,.45,26,TEAL,True,PP_ALIGN.CENTER)

def s4():
    s=fresh(4,'CONFIGURE BEFORE TESTING')
    stages=[('LEARN','54,000','training',BLUE),('CALIBRATE','1,000','choose scale',TEAL),('FREEZE','Locked','weights + scale',NAVY),('TEST','10,000','separate images',ORANGE)]
    for j,(label,value,sub,c) in enumerate(stages):
        x=.68+j*3.17;box(s,x,2.20,2.65,2.55,WHITE,LINE);text(s,label,x+.15,2.44,2.35,.32,18,c,True,PP_ALIGN.CENTER);text(s,value,x+.15,3.08,2.35,.68,35,c,True,PP_ALIGN.CENTER);text(s,sub,x+.15,4.05,2.35,.40,21,INK,False,PP_ALIGN.CENTER)
        if j<3:arrow(s,x+2.75,3.35,.30,.25)
    text(s,'+ 5,000 validation images monitor training',.72,5.34,11.8,.45,22,MUTED,align=PP_ALIGN.CENTER)
    box(s,2.3,6.08,8.7,.55,PALE)
    text(s,'Test images never choose the calibration scale.',2.45,6.17,8.4,.33,21,TEAL,True,PP_ALIGN.CENTER)

def s5():
    s=fresh(5,'INTEGER UNITS')
    text(s,'Illustrative values',.8,1.48,11.7,.35,18,MUTED,align=PP_ALIGN.CENTER)
    stages=[('MATRIX TOTAL','20','× 0.01 = 0.20',BLUE),('ADD BIAS +4','24','× 0.01 = 0.24',TEAL),('RESCALE ÷4','6','× 0.04 = 0.24',ORANGE)]
    for j,(label,value,represented,c) in enumerate(stages):
        x=.8+j*4.18;box(s,x,2.05,3.50,2.8,WHITE,LINE);text(s,label,x+.20,2.32,3.1,.40,19,c,True,PP_ALIGN.CENTER);text(s,value,x+.20,3.0,3.1,.90,55,c,True,PP_ALIGN.CENTER);text(s,represented,x+.20,4.20,3.1,.4,22,INK,False,PP_ALIGN.CENTER)
        if j<2:arrow(s,x+3.65,3.35,.33,.25)
    text(s,'Rescaling preserves the represented value: 0.24',.8,5.40,11.7,.42,25,TEAL,True,PP_ALIGN.CENTER)
    text(s,'INT8 operands → INT32 total + bias → INT64 rescale → INT8 hidden',.8,6.24,11.7,.42,20,MUTED,align=PP_ALIGN.CENTER)

def s6():
    s=fresh(6,'PROPOSED ARCHITECTURE')
    for x,w,label,detail in [(.7,2.45,'External memory','inputs + weights'),(4.05,3.15,'Local buffer','256 KiB resident stage'),(8.1,4.5,'Processing lanes','independent output totals')]:
        box(s,x,2.10,w,2.5,WHITE,LINE);text(s,'External\nmemory' if x<1 else label,x+.15,2.30 if x<1 else 2.42,w-.30,.95 if x<1 else .46,24 if x<1 else 25,NAVY,True,PP_ALIGN.CENTER);text(s,detail,x+.15,3.55 if x<1 else 3.15,w-.30,.75,20,MUTED,align=PP_ALIGN.CENTER)
    arrow(s,3.28,3.12,.55,.40);arrow(s,7.34,3.12,.55,.40)
    for j in range(8):box(s,8.45+j*.48,4.00,.35,.30,TEAL,radius=False)
    text(s,'32 B/cycle\nload + store',2.80,4.95,2.25,.8,19,TEAL,True,PP_ALIGN.CENTER)
    text(s,'32 B/cycle\noperand reads',6.55,4.95,2.25,.8,19,TEAL,True,PP_ALIGN.CENTER)
    text(s,'8 lanes · one MAC per lane/cycle · assumed 100 MHz',.8,6.25,11.7,.45,23,NAVY,True,PP_ALIGN.CENTER)

def s7():
    s=fresh(7,'ONE KNOWN ANSWER')
    text(s,'2 × 4 + 3 × 5 + 1 × 6 = 29',.75,1.55,11.85,.65,34,TEAL,True,PP_ALIGN.CENTER)
    labels=[('Load','inputs',BLUE),('Load','weights',BLUE),('MAC 1','8',TEAL),('MAC 2','23',TEAL),('MAC 3','29',TEAL),('Store','29',ORANGE)]
    for j,(label,value,c) in enumerate(labels):
        x=.75+j*2.13;circle(s,x+.53,2.62,.60,c,c);text(s,str(j+1),x+.53,2.70,.60,.32,21,WHITE,True,PP_ALIGN.CENTER)
        box(s,x,3.48,1.80,1.50,WHITE,LINE);text(s,label,x+.10,3.70,1.6,.35,20,c,True,PP_ALIGN.CENTER);text(s,value,x+.10,4.20,1.6,.45,26,c,True,PP_ALIGN.CENTER)
        if j<5:arrow(s,x+1.88,4.03,.20,.2)
    text(s,'Six sequential cycles = 60 ns at the assumed 100 MHz',.75,5.75,11.85,.55,26,NAVY,True,PP_ALIGN.CENTER)
    text(s,'One INT8 lane · load, compute and store do not overlap',.75,6.43,11.85,.35,18,MUTED,align=PP_ALIGN.CENTER)

GENERATORS={1:s1,2:s2,3:s3,4:s4,5:s5,6:s6,7:s7}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--slides',default='1-7');args=parser.parse_args()
    selected=[]
    for part in args.slides.split(','):
        if '-' in part:a,b=map(int,part.split('-'));selected.extend(range(a,b+1))
        else:selected.append(int(part))
    for index in selected:GENERATORS[index]()
    P.save(HERE/'project-presentation.pptx')
    audit=ROOT/'_local/visual-presentation';audit.mkdir(parents=True,exist_ok=True)
    (audit/'layout.json').write_text(json.dumps(LAYOUT,indent=2))
    print('Built editable slides:',selected)

if __name__=='__main__':main()
