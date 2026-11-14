#!/usr/bin/env python3
"""Briar Glen TV v2: persistent town, polished procedural retro graphics, natural TTS.

One run advances one day. No AI-generated video: all imagery is code-rendered.
Piper voices are free/offline; eSpeak remains a tested fallback.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import math
import random
import shutil
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from town_engine import initial_state, upgrade_state, advance, write_scripts
from voiceover import synthesize, active_voice_engine

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output'
TEMP=OUT/'_render'
STATE_FILE=ROOT/'town_state.json'
W,H,FPS=960,540,8
BG=(11,22,33);WHITE=(232,232,221);MUTED=(150,172,175);CYAN=(122,208,200)
BRASS=(217,178,110);NAVY=(18,37,54);TEAL=(31,79,81)
FONT_OPTIONS={
 'regular':['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf'],
 'bold':['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf','/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf'],
 'mono':['/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf','/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf'],
}
def font(sz,kind='regular'):
    chosen=next((p for p in FONT_OPTIONS[kind] if Path(p).exists()),None)
    return ImageFont.truetype(chosen,sz) if chosen else ImageFont.load_default()
SIZES=(13,14,15,16,17,18,19,20,22,23,24,28,30,32,36,38,40,42,46,54,64)
F={('reg',s):font(s) for s in SIZES}
F.update({('bold',s):font(s,'bold') for s in SIZES})
F.update({('mono',s):font(s,'mono') for s in SIZES})

def run(*cmd):
    p=subprocess.run([str(x) for x in cmd],text=True,capture_output=True)
    if p.returncode: raise RuntimeError(f'Command failed: {" ".join(map(str,cmd[:6]))}\n{p.stderr[-1500:]}')


def txt(d,xy,text,size=20,fill=WHITE,kind='regular'):
    d.text(tuple(map(int,xy)),str(text),fill=fill,font=F[('reg' if kind=='regular' else kind,size)])


def wrapped(d,xy,s,max_width,size=20,fill=WHITE,leading=8,max_lines=5,kind='regular'):
    x,y=xy; fo=F[('reg' if kind=='regular' else kind,size)]
    words=str(s).split();lines=[];line=''
    for word in words:
        trial=(line+' '+word).strip()
        if line and d.textbbox((0,0),trial,font=fo)[2] > max_width:
            lines.append(line);line=word
        else:line=trial
    if line:lines.append(line)
    for line in lines[:max_lines]:
        d.text((int(x),int(y)),line,fill=fill,font=fo)
        y += size+leading
    return y


def line(d,points,fill,width=2):d.line(points,fill=fill,width=width)


def panel(d,box,fill=NAVY,border=(60,104,116),width=1):
    d.rectangle(box,fill=fill,outline=border,width=width)


def base(d,station,day,name,sec,air_date,events):
    d.rectangle((0,0,W,H),fill=BG)
    # horizontal top band and station ID
    d.rectangle((0,0,W,74),fill=(24,56,70))
    d.rectangle((0,72,W,76),fill=BRASS)
    d.ellipse((22,11,76,65),fill=(10,31,40),outline=CYAN,width=2)
    txt(d,(39,22),'8',32,WHITE,'bold')
    txt(d,(93,11),'WMRW',28,WHITE,'bold')
    txt(d,(94,44),'MORROW COUNTY TELEVISION',14,CYAN,'mono')
    txt(d,(W-256,12),air_date.replace('-',' / '),17,MUTED,'mono')
    txt(d,(W-256,44),f'LOCAL  /  08  /  {day:03d}',14,WHITE,'mono')
    # subtle lines on film, low intensity, no flicker/strobes
    for y in range(82,H-62,7):
        line(d,[(0,y),(W,y)],(16,28,40),1)
    # lower third, patterned station system
    d.rectangle((0,H-61,W,H),fill=(16,43,57))
    d.rectangle((0,H-61,W,H-58),fill=(61,108,111))
    txt(d,(25,H-49),'WMRW 08',20,CYAN,'bold')
    txt(d,(163,H-46),name.upper()+'   /   BRIAR GLEN',15,WHITE,'mono')
    txt(d,(W-116,H-47),f'{int(sec//60):02d}:{int(sec%60):02d}',20,BRASS,'mono')
    # A rare, completely understated unexplained broadcast-system status.
    if day % 13 == 0 and 10 <= sec < 15:
        d.rectangle((W-345,84,W-22,110),fill=(24,53,62))
        txt(d,(W-330,89),'SIGNAL SOURCE: UNLISTED',13,MUTED,'mono')
    ticker='   •   '.join(e['headline'].upper() for e in events[:3])
    tw=max(1,d.textbbox((0,0),ticker,font=F[('mono',13)])[2])
    tick_x=W-int((sec*45) % (tw+W))
    d.text((tick_x,H-20),ticker,fill=(153,180,176),font=F[('mono',13)])
    return d


def news(d,sec,program,daily):
    txt(d,(34,100),'EVENING REPORT',40,WHITE,'bold')
    txt(d,(36,152),'LIVE FROM THE COUNTY NEWSROOM',14,MUTED,'mono')
    # polished 1990s pseudo-digital anchor: no photo, video, or AI images
    panel(d,(32,198,350,460),fill=(23,55,69),border=(77,134,139))
    d.rectangle((46,212,336,414),fill=(34,70,78))
    for y in range(230,400,22):line(d,[(50,y),(332,y)],(43,83,90),1)
    d.ellipse((115,338,274,433),fill=(53,71,79))
    d.polygon([(145,413),(170,385),(221,388),(247,413)],fill=(188,197,181))
    d.rectangle((165,379,210,419),fill=(175,165,149))
    d.ellipse((146,245,229,391),fill=(185,169,153),outline=(103,115,107),width=2)
    d.polygon([(140,286),(150,251),(181,227),(222,247),(231,287),(214,269),(164,274)],fill=(56,61,60))
    # eyes: rare blink, not strobing
    blink=(int(sec*2.4)%47==0)
    for x in (169,204):line(d,[(x-6,317),(x+4,317)],(69,68,61),2 if blink else 3)
    mouth_open=(int(sec*3)%6 in (0,1,2))
    d.rectangle((178,364,202,370 if mouth_open else 366),fill=(80,64,62))
    d.rectangle((46,414,336,446),fill=(14,39,52))
    txt(d,(59,420),'NEWS DESK  /  UNIT 01',15,CYAN,'mono')
    first=program['display'] if sec < 13 else program['second']
    second=program['second'] if sec < 13 else program['display']
    panel(d,(369,199,926,461),(23,47,62),(64,105,124))
    d.rectangle((369,199,926,239),fill=(47,98,110))
    txt(d,(391,208),'TOP STORY',20,WHITE,'bold')
    txt(d,(763,209),'LOCAL / DESK',15,WHITE,'mono')
    wrapped(d,(390,269),first,505,28,WHITE,12,4,'bold')
    line(d,[(388,390),(902,390)],(69,103,112))
    wrapped(d,(391,405),second,510,16,MUTED,5,2)


def weather(d,sec,program,daily):
    wx=daily['weather']
    txt(d,(34,98),'COUNTY WEATHER SERVICE',36,WHITE,'bold')
    txt(d,(36,149),'SYNTHETIC RADAR OBSERVATION  /  SECTOR 04',14,CYAN,'mono')
    panel(d,(32,194,603,459),(13,49,57),(71,134,134))
    L,T,R,B=44,207,591,447
    for x in range(L,R,40):line(d,[(x,T),(x,B)],(37,83,87),1)
    for y in range(T,B,40):line(d,[(L,y),(R,y)],(37,83,87),1)
    # stylized waterways and county routes
    line(d,[(52,340),(104,313),(139,343),(197,297),(243,312),(302,261),(357,278),(422,236),(480,253),(567,213)],(100,148,141),3)
    line(d,[(61,247),(130,275),(189,257),(268,306),(369,292),(440,352),(578,379)],(82,118,131),2)
    # natural-looking weather patches
    phase=sec*.21
    if wx['condition']!='clear':
        for index,(cx,cy,rx,ry) in enumerate([(268,318,76,40),(366,277,87,45),(460,340,54,37)]):
            cx+=int(11*math.sin(phase+index*2));cy+=int(7*math.cos(phase+.7*index))
            for scale,shade in [(1.8,(34,79,75)),(1.35,(49,99,78)),(1,(65,125,89)),(.6,(98,149,102))]:
                d.ellipse((cx-rx*scale,cy-ry*scale,cx+rx*scale,cy+ry*scale),outline=shade,width=2)
    # radar sweep, passive and non-flashing
    cx,cy=309,331
    for r in (35,72,109):d.ellipse((cx-r,cy-r,cx+r,cy+r),outline=(57,102,96),width=1)
    ang=sec*.22
    line(d,[(cx,cy),(cx+int(108*math.cos(ang)),cy+int(108*math.sin(ang)))],BRASS,2)
    for x,y,name in [(96,242,'BRIAR GLEN'),(424,235,'NORTH RIDGE'),(406,405,'RESERVOIR')]:
        d.ellipse((x-2,y-2,x+2,y+2),fill=WHITE)
        txt(d,(x+8,y-17),name,13,WHITE,'mono')
    panel(d,(619,193,929,459),(20,46,62),(68,106,122))
    txt(d,(641,211),'CURRENT',16,CYAN,'mono')
    txt(d,(639,240),str(wx['temp_f'])+'°',64,WHITE,'bold')
    txt(d,(760,268),'FAHRENHEIT',13,MUTED,'mono')
    d.rectangle((638,338,909,342),fill=(70,102,105))
    wrapped(d,(639,358),wx['label'].upper(),265,19,BRASS,6,2,'bold')
    wrapped(d,(639,411),wx.get('footnote') or 'OUTLOOK: LOCAL CONDITIONS NORMAL',265,14,MUTED,5,2)


def swap(d,sec,program,daily):
    txt(d,(37,102),'COUNTY SWAP SHOP',42,WHITE,'bold')
    txt(d,(39,157),'BUY • SELL • TRADE  /  COMMUNITY CLASSIFIEDS',16,CYAN,'mono')
    panel(d,(34,209,312,455),(29,65,74),(84,135,136))
    # procedural rotary-dial telephone icon, more convincing than crude generic shape
    d.ellipse((94,236,251,393),fill=(12,42,54),outline=(183,199,188),width=5)
    d.ellipse((127,268,219,360),fill=(33,73,79),outline=(77,126,123),width=3)
    for i in range(10):
        angle=i*2*math.pi/10 - math.pi/2
        x=173+int(57*math.cos(angle));y=315+int(57*math.sin(angle))
        d.ellipse((x-7,y-7,x+7,y+7),fill=(174,185,172))
    txt(d,(83,417),'CALL 555-0108',17,WHITE,'mono')
    panel(d,(331,208,930,455),(25,49,62),(71,106,122))
    d.rectangle((332,209,929,254),fill=(59,104,112))
    txt(d,(357,220),'TODAY’S CLASSIFIEDS',22,WHITE,'bold')
    wrapped(d,(358,290),daily['swap'],529,24,WHITE,12,5)
    txt(d,(356,426),'REFER TO STATION FOR DETAILS',15,BRASS,'mono')


def nightline(d,sec,program,daily):
    txt(d,(36,103),'THE NIGHT LINE',42,WHITE,'bold')
    txt(d,(38,157),'CALLS FROM AROUND MORROW COUNTY',16,CYAN,'mono')
    panel(d,(35,209,926,458),(13,37,50),(78,114,126))
    caller=daily['call']['caller']
    d.rectangle((54,231,904,278),fill=(35,76,86))
    txt(d,(68,241),'ON THE LINE    '+caller.upper(),20,WHITE,'bold')
    pts=[]
    for x in range(64,901,4):
        a=(math.sin((x/29)+sec*3)+.4*math.sin((x/9)+sec*2.0))
        envelope=(.35+.6*math.sin(x/84+sec*.35)**2)
        pts.append((x,int(349+a*19*envelope)))
    line(d,pts,CYAN,2)
    line(d,[(64,392),(900,392)],(65,99,108),1)
    txt(d,(66,416),'CALL-IN PROGRAM   •   LINES REMAIN OPEN',15,MUTED,'mono')


def render_program(program,daily,state,voice_choice):
    name=program['name'];stem=name.lower().replace(' ','_');day=daily['day']
    work=TEMP/stem;work.mkdir(parents=True,exist_ok=True)
    segments=program.get('segments') or [('host',program['narration'])]
    voice=work/'voice.wav';voice_len,engine=synthesize(segments,voice,voice_choice)
    duration=max(13,math.ceil(voice_len+1.75))
    fn={'News':news,'Weather':weather,'Swap Shop':swap,'Night Line':nightline}[name]
    for i in range(duration*FPS):
        sec=i/FPS
        im=Image.new('RGB',(W,H),BG);d=ImageDraw.Draw(im)
        base(d,state['station'],day,name,sec,daily['air_date'],daily['events'])
        fn(d,sec,program,daily)
        im.save(work/f'f_{i:05d}.jpg',quality=88,subsampling=0)
    output=OUT/f'day_{day:03d}_{stem}.mp4'
    music=next((p for p in [ROOT/'music'/'theme.mp3',ROOT/'music'/'theme.wav',ROOT/'music'/'theme.ogg'] if p.exists()),None)
    args=['ffmpeg','-y','-hide_banner','-loglevel','error','-framerate',str(FPS),
          '-i',str(work/'f_%05d.jpg'),'-i',str(voice)]
    if music:
        args+=['-stream_loop','-1','-i',str(music),'-filter_complex',
               '[1:a]volume=1[v];[2:a]volume=0.12[m];[v][m]amix=inputs=2:duration=first:dropout_transition=0[a]',
               '-map','0:v','-map','[a]']
    else:args+=['-map','0:v','-map','1:a']
    args+=['-t',str(duration),'-c:v','libx264','-preset','veryfast','-crf','25',
           '-pix_fmt','yuv420p','-r',str(FPS),'-c:a','aac','-b:a','128k',
           '-movflags','+faststart',str(output)]
    run(*args)
    return {'title':f'{name} — Day {day}','filename':output.name,'duration_seconds':duration,
            'voice_engine':engine, 'description':f'{state["town"]} {name.lower()} / {daily["air_date"]}'}


def main():
    ap=argparse.ArgumentParser(description='Advance and broadcast a persistent fictional town.')
    ap.add_argument('--no-video',action='store_true')
    ap.add_argument('--days',type=int,default=1)
    ap.add_argument('--voice',choices=['auto','piper','espeak'],default='auto')
    ap.add_argument('--state',type=Path,default=STATE_FILE)
    args=ap.parse_args()
    if not 1<=args.days<=30:ap.error('--days must be 1–30')
    if not args.no_video:
        if not shutil.which('ffmpeg'):raise SystemExit('FFmpeg not installed')
        print('Voice engine:',active_voice_engine(args.voice))
    state=upgrade_state(json.loads(args.state.read_text('utf8'))) if args.state.exists() else initial_state()
    OUT.mkdir(exist_ok=True)
    for _ in range(args.days):
        daily=advance(state)
        print(f'Day {daily["day"]:03d}: {daily["air_date"]}')
        for e in daily['events']:print('  '+('* ' if e['surreal'] else '- ')+e['headline'])
    programs=write_scripts(state,daily)
    report={'station':state['station'],'town':state['town'],'day':daily['day'],
            'air_date':daily['air_date'],'events':daily['events'],
            'weather':daily['weather'],'threads_active':daily['threads_active'],
            'threads_completed':daily['threads_completed'],'businesses_closed':daily['businesses_closed'],
            'programs':[],'scripts':{p['name']:p['narration'] for p in programs}}
    (OUT/'town_report.json').write_text(json.dumps(daily,indent=2)+'\n')
    (OUT/'todays_scripts.txt').write_text('\n\n'.join(f'[{p["name"]}]\n{p["narration"]}' for p in programs)+'\n')
    if not args.no_video:
        TEMP.mkdir(exist_ok=True)
        try:
            for p in programs:
                clip=render_program(p,daily,state,args.voice)
                report['programs'].append(clip)
                print('Rendered',clip['filename'],clip['duration_seconds'],'sec')
        finally:shutil.rmtree(TEMP,ignore_errors=True)
    (OUT/'broadcast_manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    state['last_generation']=dt.datetime.now(dt.timezone.utc).isoformat()
    args.state.write_text(json.dumps(state,indent=2)+'\n')
    print(f'Persisted {len(state["history"])} town events in {args.state}.')

if __name__=='__main__':main()
