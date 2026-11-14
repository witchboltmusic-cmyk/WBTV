#!/usr/bin/env python3
"""Briar Glen: persistent fictional-town TV generator, no AI video.

One run advances one simulated day, renders 4 MP4 programs, and saves town_state.json.
Use --no-video for a fast simulation-only test. All visuals procedural, TTS = eSpeak.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import math
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from town_engine import initial_state, upgrade_state, advance, write_scripts

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'output'
TEMP = OUT / '_render'
STATE_FILE = ROOT / 'town_state.json'
W, H, FPS = 800, 450, 4
BG=(7,17,20); CREAM=(212,227,208); MUTED=(132,162,148)
HILITE=(126,190,160); GOLD=(200,184,126)
FONT_PATH=next((p for p in ['/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',
                            '/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf',
                            'C:/Windows/Fonts/consola.ttf'] if Path(p).exists()),None)
def font(size): return ImageFont.truetype(FONT_PATH,size) if FONT_PATH else ImageFont.load_default()
F10,F14,F17,F23,F32=(font(n) for n in (10,14,17,23,32))

def run(*cmd):
    completed = subprocess.run([str(x) for x in cmd],capture_output=True,text=True)
    if completed.returncode:
        raise RuntimeError(f"Command failed: {' '.join(map(str,cmd[:6]))}\n{completed.stderr[-1400:]}")

def synthesize(segments, dest):
    """Convert narrator/caller lines to one WAV. Deterministic and fully offline."""
    with tempfile.TemporaryDirectory() as td:
        pieces=[]; audio_params=None
        for i,(voice,message) in enumerate(segments):
            fp=Path(td)/f'{i:02d}.wav'
            tts_voice = 'en-us+f3' if voice == 'caller' else 'en-us'
            pitch='42' if voice == 'caller' else '26'
            run('espeak','-v',tts_voice,'-s','139','-p',pitch,'-a','160','-w',str(fp),message)
            with wave.open(str(fp),'rb') as w:
                params=(w.getnchannels(),w.getsampwidth(),w.getframerate())
                if audio_params is None: audio_params=params
                if params != audio_params: raise ValueError('TTS audio format mismatch')
                pieces.append(w.readframes(w.getnframes()))
        channels,sampwidth,rate=audio_params
        pause=b'\x00'*int(rate*.3)*channels*sampwidth
        with wave.open(str(dest),'wb') as out:
            out.setnchannels(channels);out.setsampwidth(sampwidth);out.setframerate(rate)
            for i,frames in enumerate(pieces):
                if i: out.writeframes(pause)
                out.writeframes(frames)
        return sum(len(x) for x in pieces)/(rate*channels*sampwidth)+max(len(pieces)-1,0)*.3

def txt(draw,xy,value,font_obj=F17,color=CREAM,max_chars=70,gap=4,max_lines=None):
    x,y=xy; words=str(value).split(' ');line='';shown=0
    for word in words+['']:
        candidate=(line+' '+word).strip()
        if (len(candidate)>max_chars and line) or not word:
            draw.text((x,y),line,fill=color,font=font_obj)
            y+=(font_obj.size if hasattr(font_obj,'size') else 14)+gap
            shown+=1;line=word
            if max_lines and shown>=max_lines:break
        else:line=candidate
    return y

def base(draw,station,day,label,sec,air_date):
    draw.rectangle((0,0,W,H),fill=BG)
    draw.rectangle((0,0,W,42),fill=(20,43,42))
    draw.text((20,11),station,fill=CREAM,font=F17)
    draw.text((W-190,13),f'{air_date} / {day:03d}',fill=MUTED,font=F14)
    draw.line((18,H-38,W-18,H-38),fill=(55,87,77),width=2)
    draw.text((22,H-29),f'CHANNEL 08 / {label.upper()}',font=F14,fill=MUTED)
    draw.text((W-152,H-29),f'{int(sec//60):02d}:{int(sec%60):02d}  AIR',font=F14,fill=HILITE)
    # Low-intensity scan lines, not flashing.
    for y in range(48,H-40,5):draw.line((0,y,W,y),fill=(13,24,25),width=1)

def draw_news(draw,sec,day,primary,second):
    draw.rectangle((20,58,W-20,104),fill=(31,68,64),outline=(74,120,99),width=2)
    draw.text((32,67),'MORROW COUNTY EVENING NEWS',font=F23,fill=CREAM)
    # Stylized procedural digital anchor; no footage, AI, or photorealism.
    draw.polygon([(85,370),(100,280),(210,280),(235,370)],fill=(52,74,73))
    draw.rectangle((135,264,180,300),fill=(163,161,141))
    draw.ellipse((110,143,205,275),fill=(185,174,153),outline=(95,108,101),width=3)
    draw.polygon([(108,175),(125,132),(192,137),(211,170)],fill=(63,70,68))
    for x in (139,178):draw.rectangle((x-9,195,x+3,199),fill=(49,55,48))
    mouth_h=3+(8 if int(sec*4.2)%5<3 else 0)
    draw.rectangle((145,239,174,239+mouth_h),fill=(66,45,42))
    draw.rectangle((24,368,255,394),fill=(31,68,64))
    draw.text((33,373),'ANCHOR / UNIT 01',fill=CREAM,font=F14)
    draw.text((293,134),'LOCAL HEADLINES',fill=GOLD,font=F17)
    draw.rectangle((281,176,770,295),fill=(13,32,31),outline=(51,87,75))
    txt(draw,(294,190),primary if sec%22<13 else second,F17,CREAM,39,8,max_lines=4)
    draw.rectangle((280,360,W-26,393),fill=(32,62,60))
    draw.text((292,367),'MUNICIPAL REPORT / NEWS DESK',fill=HILITE,font=F14)

def draw_weather(draw,sec,wx):
    draw.text((28,67),'COUNTY WEATHER SERVICE',fill=CREAM,font=F23)
    draw.text((W-185,70),f'{wx["temp_f"]} F',fill=GOLD,font=F23)
    L,T,R,B=24,110,480,373
    draw.rectangle((L,T,R,B),fill=(19,48,46),outline=(74,120,99),width=2)
    for k in range(1,9):draw.line((L+k*51,T,L+k*51,B),fill=(31,64,58))
    for k in range(1,5):draw.line((L,T+k*52,R,T+k*52),fill=(31,64,58))
    draw.line([(30,280),(125,212),(175,247),(260,164),(350,205),(472,155)],fill=(92,150,128),width=3)
    draw.line([(50,130),(122,176),(220,150),(310,218),(445,307)],fill=(72,115,104),width=2)
    x=265+int(5*math.sin(sec*.5));y=230
    for r in (20,42,68):draw.ellipse((x-r,y-r*.62,x+r,y+r*.62),outline=(80,140,107),width=2)
    a=sec*.45;draw.line((x,y,int(x+68*math.cos(a)),int(y+43*math.sin(a))),fill=GOLD,width=3)
    draw.text((40,124),'BRIAR GLEN',fill=CREAM,font=F14)
    draw.text((300,338),'RESERVOIR',fill=CREAM,font=F14)
    draw.text((510,148),'TONIGHT',fill=GOLD,font=F23)
    txt(draw,(510,203),wx['forecast'],F14,CREAM,29,7,max_lines=6)
    draw.text((29,386),'SIMULATED DOPPLER / COUNTY 08',fill=MUTED,font=F10)

def draw_swap(draw,sec,listing):
    draw.text((24,68),'COUNTY SWAP SHOP',fill=CREAM,font=F32)
    draw.text((26,115),'BUY  /  SELL  /  TRADE',fill=MUTED,font=F17)
    draw.rectangle((29,160,260,375),fill=(22,47,42),outline=(105,146,123),width=2)
    draw.ellipse((105,188,176,218),fill=(90,122,103))
    draw.polygon([(115,207),(166,207),(155,245),(125,245)],fill=(118,148,126))
    draw.rectangle((132,245,145,323),fill=(104,124,112))
    draw.rectangle((97,323,178,334),fill=(104,124,112))
    draw.text((58,348),'LISTING 08-04',fill=MUTED,font=F14)
    draw.text((289,165),'TODAY\'S LISTINGS',fill=GOLD,font=F23)
    txt(draw,(290,226),listing,F17,CREAM,43,7,max_lines=6)
    draw.text((291,365),'CALL STATION FOR DETAILS',fill=HILITE,font=F14)

def draw_nightline(draw,sec,caller,message):
    draw.text((30,65),'THE NIGHT LINE',fill=CREAM,font=F32)
    draw.text((30,115),'COMMUNITY CALL-IN  /  AFTER HOURS',fill=MUTED,font=F17)
    draw.rectangle((28,159,770,376),fill=(12,32,33),outline=(70,113,99),width=2)
    draw.text((50,188),f'CALLER: {caller.upper()}',fill=GOLD,font=F17)
    # Procedural telephone waveform gently moving with clock, no intense strobe.
    samples=[]
    for x in range(50,748,5):
        wave=(math.sin((x+sec*55)/25)+math.sin((x+sec*30)/9)*.32)*21
        samples.append((x, int(280+wave)))
    draw.line(samples,fill=HILITE,width=3)
    draw.text((52,334),'LOCAL CALLS  /  TELEPHONE AUDIO',fill=MUTED,font=F14)
    draw.text((36,389),'THE VIEWS OF CALLERS ARE THEIR OWN',fill=MUTED,font=F10)

def render_program(program,daily,state):
    name=program['name'];stem=name.lower().replace(' ','_');day=daily['day']
    work=TEMP/stem;work.mkdir(parents=True,exist_ok=True)
    segments=program.get('segments') or [('host',program['narration'])]
    voice=work/'voice.wav';voice_len=synthesize(segments,voice)
    duration=max(13,math.ceil(voice_len+1.5));frame_count=duration*FPS
    for i in range(frame_count):
        sec=i/FPS
        im=Image.new('RGB',(W,H),BG);d=ImageDraw.Draw(im)
        base(d,state['station'],day,name,sec,daily['air_date'])
        if name=='News':draw_news(d,sec,day,program['display'],program['second'])
        elif name=='Weather':draw_weather(d,sec,daily['weather'])
        elif name=='Swap Shop':draw_swap(d,sec,program['display'])
        else:draw_nightline(d,sec,program['second'],program['display'])
        im.save(work/f'f_{i:05d}.jpg',quality=80,subsampling=2)
    output=OUT/f'day_{day:03d}_{stem}.mp4'
    music=next((p for p in [ROOT/'music'/'theme.mp3',ROOT/'music'/'theme.wav',ROOT/'music'/'theme.ogg'] if p.exists()),None)
    args=['ffmpeg','-y','-hide_banner','-loglevel','error','-framerate',str(FPS),
          '-i',str(work/'f_%05d.jpg'),'-i',str(voice)]
    if music:
        args+=['-stream_loop','-1','-i',str(music),'-filter_complex',
               '[1:a]volume=1.0[v];[2:a]volume=0.12[m];[v][m]amix=inputs=2:duration=first:dropout_transition=0[a]',
               '-map','0:v','-map','[a]']
    else:args+=['-map','0:v','-map','1:a']
    args+=['-t',str(duration),'-c:v','libx264','-preset','veryfast','-crf','30',
           '-pix_fmt','yuv420p','-r',str(FPS),'-c:a','aac','-b:a','96k',
           '-movflags','+faststart',str(output)]
    run(*args)
    return {'title':f'{name} — Day {day}','filename':output.name,'duration_seconds':duration,
            'description':f'{state["town"]} {name.lower()} / {daily["air_date"]}'}

def main():
    parser=argparse.ArgumentParser(description='Advance and broadcast a persistent fictional town.')
    parser.add_argument('--no-video',action='store_true',help='Simulate days and save story text only; no FFmpeg/eSpeak required.')
    parser.add_argument('--days',type=int,default=1,help='Advance this many town days (1–30). Video made for last day only.')
    parser.add_argument('--state',type=Path,default=STATE_FILE,help='Custom state file, useful for testing.')
    args=parser.parse_args()
    if not 1 <= args.days <= 30: parser.error('--days must be between 1 and 30')
    if not args.no_video:
        for exe in ('ffmpeg','espeak'):
            if not shutil.which(exe): raise SystemExit(f'{exe} not installed. Read README.md or run on GitHub Actions.')
    state=upgrade_state(json.loads(args.state.read_text('utf-8'))) if args.state.exists() else initial_state()
    OUT.mkdir(exist_ok=True);daily=None
    for _ in range(args.days):
        daily=advance(state)
        print(f'Day {daily["day"]:03d}: {daily["air_date"]}')
        for e in daily['events']: print('  '+('* ' if e['surreal'] else '- ')+e['headline'])
    programs=write_scripts(state,daily)
    report={'station':state['station'],'town':state['town'],'day':daily['day'],
            'air_date':daily['air_date'],'events':daily['events'],
            'weather':daily['weather'],'threads_active':daily['threads_active'],
            'threads_completed':daily['threads_completed'],
            'businesses_closed':daily['businesses_closed'],
            'programs':[],'scripts':{p['name']:p['narration'] for p in programs}}
    (OUT/'town_report.json').write_text(json.dumps(daily,indent=2)+'\n',encoding='utf-8')
    (OUT/'todays_scripts.txt').write_text('\n\n'.join(f'[{p["name"]}]\n{p["narration"]}' for p in programs)+'\n',encoding='utf-8')
    if not args.no_video:
        TEMP.mkdir(exist_ok=True)
        for p in programs:
            clip=render_program(p,daily,state)
            report['programs'].append(clip)
            print('Rendered',clip['filename'],clip['duration_seconds'],'sec')
        shutil.rmtree(TEMP,ignore_errors=True)
    (OUT/'broadcast_manifest.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    state['last_generation']=dt.datetime.now(dt.timezone.utc).isoformat()
    args.state.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
    print(f'Persisted {len(state["history"])} town events in {args.state}.')

if __name__=='__main__':main()
