#!/usr/bin/env python3
"""BRD TV 8 / Channel 02 — a deterministic overhead view of Bramhollow.

Read-only visualization of an existing town/day record. No LLM, paid voices,
new sightings, or edits to town history. The first prototype's itineraries
are rule-based illustrative routines, NOT yet canonical town events.
"""
from __future__ import annotations

import argparse
from datetime import date, timedelta
import hashlib
import json
import math
from pathlib import Path
import subprocess
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
W, H, SCALE = 480, 270, 2
FPS = 8
ROAD_TOP = 97
ROAD_BOTTOM = 173
DARK = (22, 35, 39)
INK = (235, 226, 199)
MUTED = (161, 184, 174)
TREE = (46, 94, 63)
GRASS = (77, 111, 70)
PALETTE = [(255, 209, 115), (131, 208, 218), (239, 135, 126),
           (200, 173, 235), (166, 212, 131), (246, 193, 153),
           (161, 182, 238), (255, 222, 158)]
# Entrance coordinates are outside buildings, on walkways. Each building
# joins the upper or lower road; the vertical connectors use the intersections.
PLACES = {
    "west_homes":   {"name": "OAK ST. HOMES", "box": (20, 39, 90, 80),   "at": (56, 87), "road": ROAD_TOP, "roof": (144, 92, 75)},
    "depot":        {"name": "BUS DEPOT",     "box": (112, 51, 147, 81), "at": (130, 89),"road": ROAD_TOP,"roof": (132, 144, 154)},
    "hardware":     {"name": "VALE HARDWARE", "box": (187, 41, 244, 81), "at": (216, 89),"road": ROAD_TOP,"roof": (191, 133, 84)},
    "library":      {"name": "LIBRARY",       "box": (258, 40, 308, 83), "at": (283, 90),"road": ROAD_TOP,"roof": (142, 104, 142)},
    "laundry":      {"name": "LAUNDRY",       "box": (340, 44, 396, 81), "at": (369, 90),"road": ROAD_TOP,"roof": (93, 142, 154)},
    "reservoir":    {"name": "RESERVOIR",     "box": (414, 38, 467, 87), "at": (440, 91),"road": ROAD_TOP,"roof": (56, 114, 135), "water": True},
    "bakery":       {"name": "BAKERY",        "box": (25, 122, 84, 158), "at": (55, 165),"road": ROAD_BOTTOM,"roof": (206, 123, 94)},
    "park":         {"name": "PUBLIC PARK",   "box": (105, 119, 144, 151),"at": (124, 165),"road": ROAD_BOTTOM,"roof": TREE, "park": True},
    "town_hall":    {"name": "TOWN HALL",     "box": (186, 118, 246, 159),"at": (216, 166),"road": ROAD_BOTTOM,"roof": (174, 165, 130)},
    "post_office":  {"name": "POST OFFICE",   "box": (260, 121, 307, 159),"at": (283, 166),"road": ROAD_BOTTOM,"roof": (192, 140, 106)},
    "cinema":       {"name": "REGENT",        "box": (346, 119, 415, 159),"at": (379, 166),"road": ROAD_BOTTOM,"roof": (139, 100, 132)},
    "east_homes":   {"name": "WILLOW HOMES",  "box": (424, 122, 463, 157),"at": (443, 167),"road": ROAD_BOTTOM,"roof": (151, 115, 85)},
    "recreation":   {"name": "REC CENTER",    "box": (30, 192, 101, 221),"at": (67, 185),"road": ROAD_BOTTOM,"roof": (121, 148, 117)},
    "garden":       {"name": "DUNN GARDEN",   "box": (113, 189, 171, 219),"at": (144, 185),"road": ROAD_BOTTOM,"roof": (104, 149, 83)},
    "square":       {"name": "TOWN SQUARE",   "box": (187, 190, 247, 220),"at": (216, 185),"road": ROAD_BOTTOM,"roof": (103, 131, 114),"park": True},
    "radio_repair": {"name": "RADIO / PHOTO", "box": (262, 190, 311, 222),"at": (285, 185),"road": ROAD_BOTTOM,"roof": (142, 131, 162)},
    "flower_shop":  {"name": "MARKET SHOPS",  "box": (344, 191, 416, 222),"at": (378, 185),"road": ROAD_BOTTOM,"roof": (162, 119, 119)},
}
SHOP_LOCATION = {"hardware": "hardware", "bakery": "bakery", "laundry": "laundry",
                 "cinema": "cinema", "garden": "garden",
                 "radio_repair": "radio_repair", "photo": "radio_repair",
                 "flower_shop": "flower_shop", "clock_repair": "flower_shop"}
EMPLOYMENT = {
    "sam": "depot", "harold": "hardware", "ellen": "library",
    "mara": "town_hall", "june": "post_office", "david": "recreation",
    "ernest": "garden", "violet": "garden",
}
MINS = (6 * 60, 23 * 60)
FONT_PATHS = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf",
)


def font(size=8, bold=False):
    candidates = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ) if bold else FONT_PATHS
    for f in candidates:
        if Path(f).is_file():
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


F7, F8, F9, FB = font(7), font(8), font(9), font(9, True)


def home_for(person_id):
    return "east_homes" if int(hashlib.sha256(person_id.encode()).hexdigest()[:2], 16) % 2 else "west_homes"


def destination_for(person_id, data):
    if person_id in EMPLOYMENT:
        return EMPLOYMENT[person_id]
    job = data.get("job", "").lower()
    if "radio" in job: return "radio_repair"
    if "floris" in job: return "flower_shop"
    if "rail" in job or "bus" in job: return "depot"
    if "school" in job or "music" in job or "book" in job: return "library"
    if "carpent" in job: return "hardware"
    return "square"


def build_schedules(state, daily):
    """Create illustrative, repeatable routines without modifying source state."""
    schedules = {}
    day = int(daily["day"])
    for person_id, resident in sorted(state["residents"].items()):
        if resident.get("status") in ("away", "moved"):
            continue  # never show a person known to be absent
        home = home_for(person_id)
        workplace = destination_for(person_id, resident)
        # Small fixed timing differences avoid synchronizing every resident.
        stagger = (int(hashlib.sha256(f"{day}:{person_id}".encode()).hexdigest()[:4], 16) % 35) - 15
        lunch = ["bakery", "square", "park"][
            int(hashlib.sha256(person_id.encode()).hexdigest()[4:6], 16) % 3
        ]
        if workplace == lunch:
            lunch = "bakery" if workplace != "bakery" else "square"
        schedules[person_id] = [
            (MINS[0], home, "At home"),
            (8 * 60 + stagger, workplace, "At work"),
            (12 * 60 + stagger, lunch, "Lunch / errands"),
            (13 * 60 + stagger, workplace, "Back at work"),
            (17 * 60 + stagger, home, "Home"),
            (19 * 60 + stagger, "square" if person_id in ("sam", "harold", "ellen") else home, "Evening"),
            (21 * 60 + stagger, home, "Home for the night"),
        ]
    return schedules


def walking_path(first, second):
    """Sidewalk-like Manhattan path: no walking across roofs or through water."""
    if first == second:
        return [tuple(PLACES[first]["at"])]
    a, b = PLACES[first], PLACES[second]
    p0, p1 = a["at"], b["at"]
    ya, yb = a["road"], b["road"]
    points = [p0, (p0[0], ya)]
    if ya == yb:
        points.append((p1[0], yb))
    else:
        bridge_x = min((156, 318), key=lambda x: abs(p0[0] - x) + abs(p1[0] - x))
        points.extend([(bridge_x, ya), (bridge_x, yb), (p1[0], yb)])
    points.append(p1)
    return [tuple(x) for i,x in enumerate(points) if i == 0 or x != points[i - 1]]


def position_along(points, progress):
    if len(points) == 1:
        return float(points[0][0]), float(points[0][1])
    lengths = [math.dist(a, b) for a, b in zip(points, points[1:])]
    length = sum(lengths)
    remaining = max(0.0, min(1.0, progress)) * length
    for segment, a, b in zip(lengths, points, points[1:]):
        if remaining <= segment:
            portion = remaining / segment if segment else 0
            return a[0] + (b[0] - a[0]) * portion, a[1] + (b[1] - a[1]) * portion
        remaining -= segment
    return float(points[-1][0]), float(points[-1][1])


def location_at(schedule, minute):
    """Arrive by appointment; spend preceding 32 minutes moving to destination."""
    current = schedule[0]
    for nxt in schedule[1:]:
        if minute < nxt[0]:
            depart = max(current[0], nxt[0] - 32)
            if minute <= depart:
                place = current[1]
                return (*PLACES[place]["at"], place, current[2], False)
            fraction = (minute - depart) / max(1, (nxt[0] - depart))
            x, y = position_along(walking_path(current[1], nxt[1]), fraction)
            return x, y, nxt[1], f"Walking to {PLACES[nxt[1]]['name']}", True
        current = nxt
    return (*PLACES[current[1]]["at"], current[1], current[2], False)


def read_day_report(report, state):
    if report:
        data = json.loads(Path(report).read_text(encoding="utf-8"))
        daily = data.get("day", data)
        for k in ("day", "air_date", "events", "weather"):
            if k not in daily:
                raise ValueError(f"Daily report missing {k}: {report}")
        return daily
    # Standalone preview of the most recent recorded day: NO advance().
    day = max(1, int(state.get("broadcast_day", 1)))
    day_date = date.fromisoformat(state.get("fictional_start_date", "1996-10-01")) + timedelta(days=day - 1)
    current = [ev for ev in state.get("history", []) if ev.get("day") == day]
    weather = state.get("weather", {})
    return {"day": day, "air_date": day_date.isoformat(),
            "events": current, "weather": {
                "label": weather.get("condition", "cloudy"),
                "temp_f": weather.get("temperature_f", 46)}}


def draw_tree(draw, x, y, variant=0):
    draw.rectangle((x - 1, y + 1, x + 1, y + 5), fill=(68, 65, 48))
    draw.ellipse((x - 5, y - 6, x + 5, y + 3),
                 fill=((37, 78, 58) if variant else (52, 99, 65)))
    draw.point((x - 2, y - 2), fill=(99, 139, 82))


def static_map(state):
    im = Image.new("RGB", (W, H), GRASS)
    d = ImageDraw.Draw(im)
    # Lightly varied grass tiles and vacant yards.
    for y in range(30, 229, 7):
        for x in range(6, W - 4, 7):
            v = (x * 17 + y * 29 + 8138) % 11
            if v in (0, 1):
                d.line((x, y, x + 2, y), fill=(95, 126, 78))
            if v == 7:
                d.point((x + 2, y + 3), fill=(113, 126, 79))
    # Sidewalks and the two primary roads. Intersections share walkable rows.
    for y in (ROAD_TOP, ROAD_BOTTOM):
        d.rectangle((4, y - 6, 475, y + 9), fill=(157, 157, 145))
        d.rectangle((4, y - 4, 475, y + 7), fill=(92, 97, 94))
        for x in range(7, 477, 23):
            d.rectangle((x, y + 1, x + 9, y + 2), fill=(183, 176, 137))
    for x in (156, 318):
        d.rectangle((x - 8, 32, x + 9, 224), fill=(164, 165, 148))
        d.rectangle((x - 5, 32, x + 6, 224), fill=(93, 98, 95))
        for y in range(35, 223, 23):
            d.rectangle((x, y, x + 1, y + 9), fill=(180, 174, 135))
    for x in (156, 318):
        for y in (ROAD_TOP, ROAD_BOTTOM):
            for delta in (-5, -2, 1, 4):
                d.line((x - 8, y + delta, x - 4, y + delta), fill=(209, 204, 174))
    # Parcels, autumn trees, and fence segments.
    for x, y in [(14, 48), (99, 57), (248, 47), (334, 78), (417, 60),
                 (17, 138), (96, 148), (168, 129), (330, 136), (460, 145),
                 (18, 205), (180, 204), (330, 205), (458, 204), (466, 215),
                 (111, 219), (443, 55)]:
        if not (420 < x < 470 and 30 < y < 95):
            draw_tree(d, x, y, (x + y) % 2)
    for key, place in PLACES.items():
        x0, y0, x1, y1 = place["box"]
        if place.get("water"):
            d.rectangle((x0-2,y0-2,x1+2,y1+2), fill=(45, 78, 65))
            d.rounded_rectangle((x0,y0,x1,y1),radius=9,fill=(39,91,116),outline=(119,159,154),width=1)
            for j in range(5):
                y = y0 + 10 + j * 7
                d.line((x0+8+(j%2)*3,y,x1-8,y),fill=(67,129,142),width=1)
        elif place.get("park"):
            d.rectangle((x0-2,y0-2,x1+2,y1+2), fill=(91, 130, 79))
            d.rectangle((x0,y0,x1,y1),fill=(100,142,91))
            for j in range(3):
                draw_tree(d,x0+8+j*12,y0+8+(j%2)*7,j%2)
            d.line((x0+1,y1-4,x1-1,y0+4),fill=(178,174,137),width=2)
        else:
            d.rectangle((x0+2,y0+3,x1+4,y1+4),fill=(49,61,51))
            d.rectangle((x0,y0,x1,y1),fill=(197,178,133),outline=(40,51,46),width=1)
            r,g,b=place["roof"]
            d.polygon([(x0+2,y0+3),(x1-2,y0+3),(x1-5,y1-7),(x0+5,y1-7)],
                      fill=(r,g,b),outline=(55,62,61))
            for wx in range(x0+10,x1-4,17):
                d.rectangle((wx,y1-5,wx+5,y1-2),fill=(57,91,104))
            d.rectangle((place["at"][0]-3,y1-4,place["at"][0]+3,y1),fill=(80,62,53))
        # Readable sign on a black stripe even over water and parks.
        tag = place["name"][:18]
        tw = int(d.textbbox((0,0),tag,font=F7)[2])
        tx = max(1,min(W - tw - 4, (x0+x1)//2 - tw//2))
        ty = y0 + 5 if y1-y0 >= 27 else y0 + 2
        d.rectangle((tx-2,ty-1,tx+tw+1,ty+9),fill=(26,40,38))
        d.text((tx,ty),tag,font=F7,fill=INK)
    # Open/closed businesses sourced from actual state.
    for business_id, business in state.get("businesses",{}).items():
        if business.get("status") == "open":
            continue
        place = PLACES.get(SHOP_LOCATION.get(business_id,""))
        if place:
            x0,y0,x1,y1=place["box"]
            d.rectangle((x0,y1-13,x1,y1-1),fill=(80,28,35))
            d.text((x0+2,y1-12),"CLOSED",font=F8,fill=(248,205,187))
    return im


def clip(text, max_chars=85):
    clean = " ".join(str(text).split())
    return clean if len(clean) <= max_chars else clean[:max_chars-3].rstrip() + "..."


def render_frame(base, state, daily, schedules, second, duration):
    im = base.copy()
    d = ImageDraw.Draw(im)
    # The entire 17-hour day passes in ~55 sec; darkness evolves with clock.
    m = MINS[0] + (MINS[1] - MINS[0]) * (second / max(1, duration))
    hour, minute = int(m // 60), int(m % 60)
    dark = max(0, min(104, int((hour-17)*17))) if hour >= 17 else max(0, 52-int((hour-6)*25))
    if dark > 0:
        night = Image.new("RGB", (W,H), (11,21,44))
        im = Image.blend(im, night, dark/220)
        d = ImageDraw.Draw(im)
    characters = []
    for i,(person_id, schedule) in enumerate(sorted(schedules.items())):
        x,y,place,activity,moving = location_at(schedule,m)
        characters.append((int(x),int(y),person_id,activity,moving,i))
    # Tracked sprites: head, coat, shoes, name tags.
    for x,y,pid,activity,moving,i in sorted(characters,key=lambda x:x[1]):
        color=PALETTE[i%len(PALETTE)]
        d.ellipse((x-3,y+4,x+4,y+6),fill=(33,47,43))
        d.rectangle((x-2,y+1,x+2,y+5),fill=color)
        if moving:
            step = int(second*7+i)%2
            d.point((x-2,y+6-step),fill=(40,47,52))
            d.point((x+2,y+5+step),fill=(40,47,52))
        d.ellipse((x-2,y-4,x+2,y+1),fill=(224,184,139),outline=(43,47,45))
        if pid in ("sam", "harold", "ellen"):
            nm=state["residents"][pid]["name"].split(" ")[0].upper()
            tw=d.textbbox((0,0),nm,font=F7)[2]
            lx=max(3,min(W-tw-3,x-tw//2))
            d.rectangle((lx-2,y-16,lx+tw+2,y-6),fill=(22,35,39))
            d.text((lx,y-16),nm,font=F7,fill=INK)
    # CRT-inspired overlay, tuned to keep the map itself visible.
    d.rectangle((0,0,W,29),fill=DARK)
    d.text((9,4),"BRAMHOLLOW   /   TOWN OBSERVATION",font=FB,fill=(238,232,202))
    d.text((9,17),"CH 02  |  OVERHEAD VIEW  |  1996",font=F7,fill=(147,193,171))
    clock=f"{hour%12 or 12:02d}:{minute:02d} {'PM' if hour>=12 else 'AM'}"
    d.text((341,5),daily["air_date"]+"  "+clock,font=F8,fill=(222,215,180))
    d.text((363,18),daily["weather"].get("label","").upper()[:21],font=F7,fill=(154,186,192))
    d.rectangle((0,229,W,H),fill=(17,31,35))
    d.line((0,229,W,229),fill=(92,127,117))
    d.text((8,234),"TOWN RECORD",font=F8,fill=(158,215,186))
    events=[e.get("headline","") for e in daily.get("events",[]) if e.get("headline")]
    current=events[min(int(second // max(1,duration/max(1,len(events)))),len(events)-1)] if events else "NO BULLETIN FILED"
    d.text((93,234),clip(current,67).upper(),font=F8,fill=INK)
    visible=[(pid,activity) for _,_,pid,activity,_,_ in characters]
    detail="  /  ".join(f"{state['residents'][pid]['name'].split(' ')[0]}: {act}" for pid,act in visible[:3])
    d.text((8,250),clip(detail,93),font=F7,fill=(150,181,188))
    d.text((349,263),"ILLUSTRATIVE ROUTINES",font=F7,fill=(108,137,135))
    return im.resize((W*SCALE,H*SCALE),Image.Resampling.NEAREST)


def render_video(state, daily, target, seconds=55, fps=FPS, preview=None):
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    schedules = build_schedules(state,daily)
    background = static_map(state)
    if preview:
        img = render_frame(background,state,daily,schedules,seconds*0.54,seconds)
        Path(preview).parent.mkdir(parents=True,exist_ok=True)
        img.save(preview)
    cmd=["ffmpeg","-y","-loglevel","error","-f","rawvideo","-vcodec","rawvideo",
         "-pix_fmt","rgb24","-s",f"{W*SCALE}x{H*SCALE}","-r",str(fps),
         "-i","pipe:0","-f","lavfi","-i","anullsrc=channel_layout=mono:sample_rate=44100",
         "-t",str(seconds),"-c:v","libx264","-preset","veryfast","-crf","22",
         "-pix_fmt","yuv420p","-c:a","aac","-b:a","64k","-movflags","+faststart",
         "-shortest",str(target)]
    if fps < 1 or fps > 24 or seconds < 3 or seconds > 240:
        raise ValueError("Preview supports 3–240 seconds and 1–24 FPS")
    process=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        for frame_number in range(math.ceil(seconds * fps)):
            frame=render_frame(background,state,daily,schedules,frame_number/fps,seconds)
            process.stdin.write(frame.tobytes())
        process.stdin.close()
        errors=process.stderr.read().decode(errors="replace")
        if process.wait() != 0:
            raise RuntimeError("FFmpeg failed: "+errors[-1200:])
    except BaseException:
        if process.poll() is None:
            process.kill()
            process.wait()
        raise
    return {
        "channel": "BRD TV 8 / TOWN OBSERVATION",
        "number": 2, "day": daily["day"], "air_date": daily["air_date"],
        "duration_seconds": seconds,
        "filename": target.name,
        "residents_shown": [state["residents"][k]["name"] for k in schedules],
        "record_headlines": [e["headline"] for e in daily.get("events",[])],
        "note": "Routine paths are illustrative; core town history is not changed",
    }


def main():
    ap=argparse.ArgumentParser(description="Render Channel 02 pixel town map (read-only)")
    ap.add_argument("--state",type=Path,default=ROOT/"cryptid_trial_state.json")
    ap.add_argument("--report",type=Path,help="Existing day_XXX_cryptid_report.json; grounds clock, weather, bulletin")
    ap.add_argument("--output",type=Path)
    ap.add_argument("--preview",type=Path)
    ap.add_argument("--seconds",type=int,default=55)
    ap.add_argument("--fps",type=int,default=FPS)
    args=ap.parse_args()
    if not args.state.is_file():
        ap.error("Town state missing: "+str(args.state))
    state=json.loads(args.state.read_text(encoding="utf-8"))
    daily=read_day_report(args.report,state)
    output=args.output or OUT/f"town_observation_day_{int(daily['day']):03d}.mp4"
    result=render_video(state,daily,output,args.seconds,args.fps,args.preview)
    manifest=output.with_suffix(".json")
    manifest.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(f"Rendered Bramhollow CH 02 / Day {daily['day']} / {output}")
    print("No API calls and no persistent town-state changes.")


if __name__=="__main__":
    main()
