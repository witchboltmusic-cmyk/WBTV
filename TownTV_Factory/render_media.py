"""BRD TV 8 / Bramhollow News and Weather media compositor.

All images are drawn with Pillow, sourced from user-provided footage/sprite sheet.
No AI video is generated. If assets are absent, generate.py uses its built-in
procedural fallback. User-provided footage is not reuploaded anywhere by script.
"""
from __future__ import annotations
from pathlib import Path
import glob
import math
import subprocess
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

NAVY=(16,35,72)
INK=(7,19,45)
BROADCAST_BLUE=(38,75,134)
GOLD=(238,195,84)
WHITE=(243,244,240)
PALE=(200,219,238)
MUTED=(160,184,218)

FONT_SEARCH = {
    'bold':['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf','/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf'],
    'regular':['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf'],
    'mono':['/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf','/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf'],
}
_FONT_CACHE={}
def ff(sz=20,style='regular'):
    key=(sz,style)
    if key not in _FONT_CACHE:
        f=next((p for p in FONT_SEARCH[style] if Path(p).exists()),None)
        _FONT_CACHE[key]=ImageFont.truetype(f,sz) if f else ImageFont.load_default()
    return _FONT_CACHE[key]

def text(d,xy,s,sz=19,color=WHITE,style='regular'):
    d.text(xy,str(s),font=ff(sz,style),fill=color,stroke_width=0)

def fit_lines(d,words,x,y,width,maxlines=3,sz=23,color=WHITE,leading=9,style='bold'):
    f=ff(sz,style); out=[];line=''
    for word in str(words).split():
        trial=(line+' '+word).strip()
        if line and d.textlength(trial,font=f)>width:
            out.append(line);line=word
        else: line=trial
    if line:out.append(line)
    for ln in out[:maxlines]:
        if len(out)>maxlines and ln==out[maxlines-1]: ln=ln[:max(4,int(width/(sz*.61)))-3].rstrip()+'...'
        d.text((x,y),ln,font=f,fill=color)
        y+=sz+leading
    return y

def gradient(im, y0, y1, left=(27,63,118), right=(9,25,56)):
    d=ImageDraw.Draw(im)
    for y in range(y0,y1):
        a=(y-y0)/max(1,y1-y0-1)
        c=tuple(int(left[k]*(1-a)+right[k]*a) for k in range(3))
        d.line((0,y,im.width,y),fill=c)

def slim_border(d,box,color=(111,151,204),w=2):d.rectangle(box,outline=color,width=w)

def chrome(d, day, air_date, title, w=960,h=540):
    d.rectangle((0,0,w,63),fill=(14,39,84))
    d.rectangle((0,61,w,64),fill=GOLD)
    d.rectangle((15,10,148,54),fill=(230,230,218))
    text(d,(23,13),'BRD',28,(10,36,82),'bold')
    text(d,(94,22),'TV 8',18,(10,36,82),'bold')
    text(d,(166,13),'BRAMHOLLOW',23,WHITE,'bold')
    text(d,(168,40),'LOCAL TELEVISION',12,MUTED,'mono')
    text(d,(654,18),air_date.replace('-',' / '),18,WHITE,'mono')
    text(d,(658,41),f'CHANNEL 08  •  DAY {day:03d}',12,PALE,'mono')
    d.rectangle((0,505,w,h),fill=(11,33,71))
    d.rectangle((0,505,w,508),fill=GOLD)
    text(d,(23,513),title.upper(),18,WHITE,'bold')
    text(d,(651,517),'BRD TV 8  /  BRAMHOLLOW',14,PALE,'mono')

def _news_monitor(im,day,program,second=False):
    d=ImageDraw.Draw(im)
    # The supplied clip has a GREEN PRESENTATION MONITOR, not a green background
    # behind the presenter. Cover the exact inner area, leaving the actor and
    # original studio physically intact. This also removes white tracking Xs.
    x0,y0,x1,y1=(40,36,580,358)
    d.rectangle((x0,y0,x1,y1),fill=(21,56,108))
    for y in range(y0+4,y1,8):
        d.line((x0+5,y,x1-5,y),fill=(25,63,119),width=1)
    d.rectangle((x0+10,y0+9,x1-10,y0+51),fill=(12,43,98))
    text(d,(x0+23,y0+13),'BRAMHOLLOW / 8',22,WHITE,'bold')
    text(d,(x0+19,y0+68),'LOCAL REPORT',16,GOLD,'mono')
    headline=program['second'] if second else program['display']
    fit_lines(d,headline.upper(),x0+21,y0+105,x1-x0-46,3,27,WHITE,8,'bold')
    d.rectangle((x0+18,y1-39,x1-18,y1-36),fill=GOLD)
    text(d,(x0+19,y1-31),'COUNTY DESK  /  BRD TELEVISION',12,PALE,'mono')

def _news_card(day,daily,program,secondary=False):
    im=Image.new('RGB',(960,540)); gradient(im,0,540,(28,72,129),(7,18,43));d=ImageDraw.Draw(im)
    for x in range(-40,1060,61):d.line((x,60,x-146,510),fill=(33,80,136),width=1)
    for y in range(102,530,35):d.line((0,y,960,y),fill=(28,68,117),width=1)
    d.polygon([(520,80),(930,80),(893,465),(620,465)],fill=(35,81,133))
    d.ellipse((665,140,887,365),outline=(64,126,169),width=3)
    d.ellipse((701,178,851,330),outline=(57,115,160),width=3)
    d.line((765,145,765,365),fill=(53,104,149),width=2)
    d.line((661,250,891,250),fill=(53,104,149),width=2)
    chrome(d,day,daily['air_date'],'THE EVENING REPORT')
    d.rectangle((38,101,596,441),fill=(12,39,83),outline=(101,144,205),width=2)
    d.rectangle((40,103,594,158),fill=(41,91,163))
    text(d,(57,113),'STORY 02' if secondary else 'TOP STORY',27,WHITE,'bold')
    text(d,(60,187),'BRAMHOLLOW COUNTY NEWS',17,GOLD,'mono')
    headline=(program['second'] if secondary else program['display']).upper()
    fit_lines(d,headline,59,241,502,4,31,WHITE,11,'bold')
    text(d,(627,412),'LOCAL  /  BRD TV 8',16,PALE,'mono')
    return im

class AssetRenderer:
    def __init__(self,asset_dir,temp,w=960,h=540,fps=8):
        self.assets=Path(asset_dir);self.temp=Path(temp)
        self.w,self.h,self.fps=w,h,fps
        self.frames={'News':[],'Weather':[]}; self.icons=None
        icons=self.assets/'weather_icons.png'
        if icons.exists():
            self.icons=Image.open(icons).convert('RGBA')

    def prepare(self,name):
        src=self.assets/('news_anchor.mp4' if name=='News' else 'weather_radar.mp4')
        if not src.exists():return
        out=self.temp/name.lower();out.mkdir(parents=True,exist_ok=True)
        if name=='News':
            # Source is 760x538. Crop to widescreen and keep the monitor region.
            vf=f'fps={self.fps},crop=760:428:0:52,scale=960:540'
        else:
            # Wide radar loop occupies central weather screen only.
            vf=f'fps={self.fps},crop=1122:530:0:127,scale=615:280'
        p=subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error',
            '-i',str(src),'-vf',vf,'-q:v','5',str(out/'frame_%04d.jpg')],capture_output=True,text=True)
        if p.returncode:raise RuntimeError('Could not prepare supplied '+name+' footage: '+p.stderr[-700:])
        self.frames[name]=sorted(out.glob('frame_*.jpg'))

    def has_media(self,name):return bool(self.frames.get(name))
    def frame(self,name,sec):
        frames=self.frames[name]
        index=int(sec*self.fps)%len(frames)
        return Image.open(frames[index]).convert('RGB')

    def icon(self,condition):
        # Original sprite sheet has 15 columns of 40px and 64 rows of 32px.
        # Use real source icons (white backing is kept to preserve details).
        source={'clear':(425,108,460,148), 'cloudy':(382,83,419,108), 'showers':(382,194,414,222), 'fog':(43,169,80,198), 'wind':(43,5,80,32)}
        if self.icons is None:return None
        box=source.get(condition,source['cloudy'])
        cropped=self.icons.crop(box).convert('RGB')
        return cropped.resize((120,96),Image.Resampling.BICUBIC)

def _headlines_crawl(d,daily,sec):
    info='    /    '.join(e['headline'].upper() for e in daily['events'][:3])
    if not info: return
    x=960-int(sec*36)%max(1,960+int(d.textlength(info,font=ff(14,'mono'))))
    d.rectangle((0,475,960,504),fill=(13,31,67))
    d.text((x,483),info,fill=(213,230,232),font=ff(14,'mono'))


def render_news_frame(renderer,sec,day,daily,program,duration=30):
    portion=sec/max(1,duration)
    scene=0 if portion < .25 or portion >= .9 else (1 if portion < .58 else 2)
    if scene in (1,2):
        im=_news_card(day,daily,program,secondary=(scene==2))
        d=ImageDraw.Draw(im)
        _headlines_crawl(d,daily,sec)
        return im
    im=renderer.frame('News',sec+1)
    im=ImageEnhance.Color(im).enhance(.83)
    _news_monitor(im,day,program,second=(int(sec//33)%2==1))
    d=ImageDraw.Draw(im)
    # Restrained broadcast graphics over the actual supplied actor/studio footage.
    d.rectangle((0,427,960,505),fill=(12,32,73))
    d.rectangle((0,426,960,430),fill=GOLD)
    text(d,(26,439),'EVENING REPORT',23,WHITE,'bold')
    text(d,(29,472),'BRAMHOLLOW  /  COUNTY DESK',14,PALE,'mono')
    text(d,(653,449),daily['air_date'].replace('-',' / '),20,WHITE,'mono')
    chrome_top=Image.new('RGB',(960,64));td=ImageDraw.Draw(chrome_top);chrome(td,day,daily['air_date'],'NEWS')
    # chrome() draws footer too, but this 64px canvas only retains the header.
    im.paste(chrome_top,(0,0))
    _headlines_crawl(d,daily,sec)
    d.rectangle((0,505,960,540),fill=(11,33,71))
    d.rectangle((0,505,960,508),fill=GOLD)
    text(d,(23,513),'THE EVENING REPORT',18,WHITE,'bold')
    text(d,(651,517),'BRD TV 8  /  BRAMHOLLOW',14,PALE,'mono')
    return im

def render_weather_frame(renderer,sec,day,daily,program,duration=30):
    wx=daily['weather']
    im=Image.new('RGB',(960,540));gradient(im,0,540,(38,79,145),(11,31,72))
    d=ImageDraw.Draw(im)
    for x in range(0,960,48):d.line((x,78,x-165,502),fill=(36,82,143),width=1)
    chrome(d,day,daily['air_date'],'COUNTY WEATHER')
    forecast=(sec/max(1,duration) >= .60)
    if not forecast:
        d.rectangle((28,83,646,439),fill=INK,outline=(99,154,205),width=2)
        text(d,(44,94),'BRAMHOLLOW REGIONAL RADAR',22,WHITE,'bold')
        text(d,(45,125),'COUNTY OBSERVATION / WDR 08',14,PALE,'mono')
        radar=renderer.frame('Weather',sec)
        im.paste(radar,(30,150))
        d=ImageDraw.Draw(im)
        d.rectangle((30,150,645,430),outline=(139,181,224),width=2)
        for x,y,n in [(161,253,'BRAMHOLLOW'),(404,354,'LAKE MERCER'),(466,216,'NORTH RIDGE')]:
            d.ellipse((x-3,y-3,x+3,y+3),fill=WHITE,outline=INK)
            d.rectangle((x+7,y-18,x+8+len(n)*8,y+1),fill=(13,37,65))
            text(d,(x+9,y-18),n,12,WHITE,'mono')
        text(d,(44,447),'RADAR LOOP  /  NOT FOR NAVIGATION',12,PALE,'mono')
        d.rectangle((663,83,931,440),fill=(18,43,93),outline=(114,159,199),width=2)
        text(d,(682,99),'CURRENT CONDITIONS',18,WHITE,'bold')
        d.rectangle((684,143,908,266),fill=(238,239,231))
        ic=renderer.icon(wx['condition'])
        if ic: im.paste(ic,(733,154))
        d=ImageDraw.Draw(im)
        text(d,(685,271),str(wx['temp_f'])+'°F',60,WHITE,'bold')
        fit_lines(d,wx['label'].upper(),688,357,208,2,18,GOLD,4,'bold')
    else:
        d.rectangle((28,84,931,440),fill=(17,43,91),outline=(115,154,200),width=2)
        text(d,(50,104),'FIVE DAY FORECAST',32,WHITE,'bold')
        from datetime import date,timedelta
        start=date.fromisoformat(daily['air_date'])
        for i in range(5):
            x=48+i*174
            d.rectangle((x,161,x+163,410),fill=(32,68,126),outline=(124,166,211),width=2)
            dd=start+timedelta(days=i)
            text(d,(x+14,173),dd.strftime('%a').upper(),24,WHITE,'bold')
            text(d,(x+14,203),dd.strftime('%m/%d'),15,PALE,'mono')
            conditions=['clear','cloudy','showers','fog','wind']
            condition=wx['condition'] if i==0 else conditions[(day*3+i*7)%5]
            icon=renderer.icon(condition)
            if icon:im.paste(icon,(x+22,246))
            d=ImageDraw.Draw(im)
            temp=wx['temp_f']+(-2+i*2 if i else 0)
            text(d,(x+26,351),f'{temp}°',33,WHITE,'bold')
            text(d,(x+12,392),condition.upper(),14,PALE,'mono')
    _headlines_crawl(d,daily,sec)
    if wx.get('footnote'):
        d.rectangle((30,443,930,471),fill=(13,34,69))
        fit_lines(d,'COUNTY NOTE: '+wx['footnote'].upper(),40,451,875,1,13,GOLD,0,'mono')
    return im
