#!/usr/bin/env python3
"""A deterministic, persistent rules-based fictional-town simulator.

No LLM or generated video required. This engine owns a shared town state and
creates events that news/weather/local shows can all reference.
"""
from __future__ import annotations
from datetime import date, timedelta
from copy import deepcopy
import random

START_DATE = '1996-10-01'
# The town has ordinary problems, plus a SMALL thread of impossible occurrences.
# Each thread is linear and has one-time stages. State records which stages aired.
THREADS = {
 'reservoir': {
  'title': 'The Reservoir Road File',
  'stages': [
   ('Reservoir noise prompts equipment check', 'The public works office will inspect a humming noise reported near the reservoir gate. Residents are asked to avoid parking on the service road.'),
   ('Reservoir equipment records reviewed', 'The water authority says most electrical equipment beside the reservoir was disconnected in 1981. Inspectors are reviewing the remaining records.'),
   ('Gate found open after routine inspection', 'A county inspector reported finding the reservoir gate unlatched. No signs of damage were found, and the gate has been secured.'),
   ('Road sign temporarily removed', 'Road crews have removed the Reservoir Road sign for replacement. A historical map displayed at the library has already been updated.'),
   ('County closes reservoir service inquiry', 'Public Works has completed its inspection and found no source of the humming. A second inspection is not currently scheduled.'),
  ],
  'swap': ['Wanted: working AM radios. Buyer is interested in units that receive clear signals after midnight.',
           'For sale: two folding chairs and a portable radio. Please collect them before the reservoir gate closes.'],
  'call': 'I was walking near the reservoir and heard something that sounded like a generator, but the power was off.',
 },
 'library': {
  'title': 'The Library Return Ledger',
  'stages': [
   ('Library launches overdue-book amnesty', 'Briar Glen Library has begun an amnesty for overdue books and asked patrons to return unidentified volumes to the front desk.'),
   ('Unlisted book returned to circulation desk', 'Library staff received a volume with no accession number. The book has been set aside while staff locate its original record.'),
   ('Library asks patrons about missing catalog pages', 'A small number of catalog cards are missing from the local history cabinet. Staff say no books appear to be missing.'),
   ('Historical society receives disputed library inventory', 'An inventory delivered to the historical society lists a reading room that was removed during a renovation in 1972.'),
   ('Library completes inventory review', 'The library has closed its inventory review. Its public catalog has not been amended.'),
  ],
  'swap':['Wanted: old library cards or card-catalog drawers. The buyer is collecting local memorabilia.',
          'Free: one oak bookcase, four shelves. The seller would prefer not to discuss the books that came with it.'],
  'call':'I returned a book last week, and today I got a receipt dated before I was born.',
 },
 'bus': {
  'title': 'The Northbound Bus',
  'stages': [
   ('Transit authority adjusts northbound route', 'The county bus service is changing two afternoon stops on the northbound route to improve reliability.'),
   ('Northbound vehicle reported at closed stop', 'A resident reported seeing a county bus at a stop closed several years ago. Transit officials are reviewing vehicle logs.'),
   ('Bus timetable printed with duplicate departure', 'The new northbound schedule contains two identical departure times. The transit office says a corrected printing is underway.'),
   ('Transit office clarifies missing route number', 'The transit office says route 6 was discontinued in 1988 and has no active drivers or vehicles.'),
   ('Bus review closed without service changes', 'The northbound schedule review is complete. Regular service will continue on all currently recognized routes.'),
  ],
  'swap':['Wanted: an older county bus timetable with the green cover, preferably before 1989.',
          'For sale: unused bus tokens and a folding umbrella. Please do not phone after the last departure.'],
  'call':'A bus stopped outside our house, but the route number was printed on the inside of the windshield.',
 },
 'clock': {
  'title': 'The Courthouse Clock',
  'stages': [
   ('Courthouse clock scheduled for maintenance', 'County maintenance will inspect the courthouse clock following complaints that it is running two minutes behind.'),
   ('Clock mechanism inspected', 'The courthouse clock mechanism was examined this morning. Technicians found no broken parts.'),
   ('New timekeeping policy approved', 'County staff will continue using the telephone time service until repairs to the courthouse clock are complete.'),
   ('Clock chimes reported after power interruption', 'Several downtown businesses reported hearing the courthouse chime during last night’s scheduled electrical outage.'),
   ('Clock maintenance ticket closed', 'The county says the courthouse clock is operating within acceptable tolerances. No additional work is planned.'),
  ],
  'swap':['Wanted: brass clock parts, especially small bells. Cash paid for working components.',
          'For trade: two wall clocks. Both work, but must be kept in separate rooms.'],
  'call':'The courthouse clock rang thirteen times. Maybe I just counted wrong.',
 },
 'orchard': {
  'title': 'The Orchard Survey',
  'stages': [
   ('Agricultural office begins orchard survey', 'Agricultural inspectors will visit farms west of Briar Glen to update tree inventories.'),
   ('Unmarked rows noted on orchard map', 'Inspectors found several rows of trees missing from an older survey. Property boundaries are unchanged.'),
   ('Orchard growers invited to public meeting', 'Residents with questions about land records are invited to a short meeting at the recreation hall.'),
   ('Old bell located near orchard property', 'Survey workers located a rusted farm bell on the northern boundary. The owner says it has not been used for decades.'),
   ('Orchard survey completed', 'The agricultural office has finalized its updated tree inventory. The bell will remain where it was found.'),
  ],
  'swap':['For sale: orchard ladder and wooden crates. Buyer must collect them from the western gate.',
          'Wanted: farm bell, any size. The buyer will consider exchanges for tools.'],
  'call':'The bell on the old orchard has been ringing at night, but nobody knows whose land it is on.',
 },
}

INITIAL_RESIDENTS = {
 'mara': {'name':'Mara Voss','job':'County clerk','status':'home','away_until':0,'mentions':0},
 'ellen': {'name':'Ellen Price','job':'Librarian','status':'home','away_until':0,'mentions':0},
 'harold': {'name':'Harold Vale','job':'Hardware store owner','status':'home','away_until':0,'mentions':0},
 'sam': {'name':'Sam Evers','job':'Bus driver','status':'home','away_until':0,'mentions':0},
 'violet': {'name':'Violet Dunn','job':'Retired schoolteacher','status':'home','away_until':0,'mentions':0},
 'ernest': {'name':'Ernest Pike','job':'Garden club president','status':'home','away_until':0,'mentions':0},
 'june': {'name':'June Mercer','job':'Postal worker','status':'home','away_until':0,'mentions':0},
 'david': {'name':'David Bell','job':'Recreation director','status':'home','away_until':0,'mentions':0},
}
INITIAL_BUSINESSES = {
 'hardware': {'name':'Vale Hardware','owner':'harold','status':'open','reopen_day':0},
 'bakery': {'name':'Bell Street Bakery','owner':None,'status':'open','reopen_day':0},
 'laundry': {'name':'West End Laundromat','owner':None,'status':'open','reopen_day':0},
 'cinema': {'name':'Regent Picture House','owner':None,'status':'open','reopen_day':0},
 'garden': {'name':'Dunn Garden Supply','owner':None,'status':'open','reopen_day':0},
}
MUNDANE_EVENTS = [
 ('Library extends weekend hours', 'The Briar Glen Library will remain open an additional hour on Saturdays following a successful trial period.'),
 ('Community choir welcomes new singers', 'The recreation hall choir is accepting new members. Rehearsals are held on Tuesday evenings.'),
 ('Painting planned for Maple Avenue', 'Crews will refresh the lane markings along Maple Avenue. Drivers should allow extra time near the square.'),
 ('County fair announces pie contest', 'Organizers have opened entries for the annual county fair pie competition. Forms are available at the library.'),
 ('Garden club schedules seed exchange', 'The Garden Club will hold a seed exchange at the recreation center. All residents are welcome.'),
 ('Local cinema adds Sunday matinee', 'The Regent Picture House has added an afternoon screening to its Sunday program.'),
 ('Post office adjusts collection time', 'The Main Street post office has moved its final weekday collection back by fifteen minutes.'),
 ('Youth bowling league registration opens', 'The recreation department is registering teams for the autumn bowling league.'),
 ('Pothole repair scheduled on Willow Street', 'County crews will repair several potholes on Willow Street before the weekend.'),
 ('Historical society seeks volunteers', 'The Morrow County Historical Society is asking for help indexing photographs and maps.'),
 ('Neighborhood cleanup scheduled', 'Volunteers will meet behind the old fire hall to collect roadside litter on Saturday.'),
 ('Lions Club schedules monthly breakfast', 'The Lions Club has announced a pancake breakfast in the church basement. Proceeds will support school supplies.'),
 ('High school band fund-raiser begins', 'Students are selling raffle tickets to help pay for new marching band uniforms.'),
 ('Farmers market announces apple tasting', 'Growers from the western farms will offer samples at the Saturday morning market.'),
 ('Roadside flower beds replanted', 'Parks workers have completed the seasonal planting near the county welcome sign.'),
 ('Town Hall replaces front door', 'The replacement front door at Town Hall will be installed during normal office hours.'),
 ('Senior center announces card tournament', 'The senior center will host a cards and dominoes tournament next Thursday afternoon.'),
 ('Animal shelter seeks blankets', 'The shelter is accepting clean towels and blankets throughout the coming week.'),
 ('Community theater schedules auditions', 'The county theater group will hold auditions for its annual autumn production.'),
 ('Recycling center updates weekend hours', 'The county recycling center will begin opening earlier on the first Saturday of each month.'),
 ('School bus safety meeting scheduled', 'Parents are invited to a short meeting with transportation staff at the school cafeteria.'),
 ('Fire hall announces open house', 'The volunteer fire department will hold an open house with equipment demonstrations.'),
 ('County fair announces flower competition', 'Registration for the county fair flower arrangement contest is available at the recreation hall.'),
 ('Birdwatching society schedules outing', 'The local birdwatching society will meet at dawn at the public park entrance.'),
 ('Volunteer reading program expands', 'The reading program is seeking volunteers to help younger students on Thursday afternoons.'),
 ('Downtown sidewalk repairs begin', 'Sidewalk repair work will begin outside the hardware store this week.'),
 ('New benches installed by courthouse', 'Public Works has installed two benches near the courthouse entrance after receiving requests from residents.'),
 ('Briar Glen school announces book drive', 'The school is collecting used books for its winter reading program. Donations may be dropped off at the office.'),
 ('Street market changes opening time', 'Market vendors will begin setting up an hour earlier on the first Saturday of next month.'),
]
# New characters and businesses appear slowly, with names persisted in the town record.
NEW_ARRIVALS = [
 ('irene', 'Irene Weller', 'Seamstress'),
 ('calvin', 'Calvin Rowe', 'Radio repair technician'),
 ('beatrice', 'Beatrice Sloane', 'Florist'),
 ('walter', 'Walter Haines', 'Carpenter'),
 ('lena', 'Lena Rhodes', 'Music teacher'),
 ('arthur', 'Arthur Finch', 'Retired railway worker'),
 ('nina', 'Nina Booth', 'Bookkeeper'),
 ('oscar', 'Oscar Reed', 'Sign painter'),
]
NEW_SHOPS = [
 ('radio_repair', 'North Ridge Radio Repair'),
 ('flower_shop', 'Market Street Florist'),
 ('clock_repair', 'County Clock & Watch'),
 ('photo', 'Briar Glen Photo Service'),
]

SWAP_OBJECTS = ['a small oak dresser','a portable radio','two porch chairs','a working table lamp','three enamel mixing bowls',
                'a box of garden tools','an upright vacuum cleaner','a collection of road maps','a wooden rocking chair',
                'a set of kitchen canisters','an unused bicycle basket','an old fishing rod','a cast-iron skillet',
                'two rolls of wallpaper','a sewing machine','a weatherproof mailbox']
SWAP_ACTIONS = ['For sale','Wanted','Free to a good home','For trade']
WEATHER = {
 'clear': ('clear skies','Dry conditions will continue overnight with light winds.'),
 'cloudy': ('mostly cloudy skies','Cloud cover will persist across the county through the morning.'),
 'showers': ('isolated showers','Light rain is possible near the county line before daybreak.'),
 'fog': ('patchy ground fog','Visibility may be reduced on lower roads and near the reservoir.'),
 'wind': ('gusty conditions','Occasional wind gusts are expected along exposed roads.'),
}
WEATHER_TRANSITIONS = {
 'clear': ['clear','clear','cloudy','cloudy','wind'],
 'cloudy':['cloudy','clear','showers','fog','wind'],
 'showers':['showers','cloudy','fog','clear'],
 'fog':['fog','cloudy','clear','showers'],
 'wind':['wind','clear','cloudy','showers'],
}
LOW_STAKE_ODDITIES = [
 ('Unclaimed umbrella located at courthouse', 'The county clerk has placed a gray umbrella in lost property. No one remembers seeing it arrive.'),
 ('An unusual municipal calendar error', 'The printed community calendar includes a second Thursday. The printer has been notified.'),
 ('Postal box temporarily unavailable', 'The post office has covered a mailbox after letters addressed to an unlisted street were found inside.'),
 ('Town sign receives unexpected correction', 'The welcome sign outside Briar Glen briefly listed a population one person higher than the latest census.'),
 ('Community notice issued about fountain', 'The parks department reminds residents that the fountain behind Town Hall is decorative and has no public water connection.'),
 ('Empty room added to building inspection', 'A room with no listed use was included in the annual recreation hall inspection. The report will be corrected.'),
 ('Recorded time signal being reviewed', 'The telephone time service briefly repeated yesterday’s announcement. Engineers describe the problem as routine.'),
 ('Two identical notices posted at library', 'Library staff removed a duplicate notice from the display board. The second copy was dated one week from today.'),
 ('School reports misplaced attendance sheet', 'An attendance sheet was filed with an extra name. Teachers say all students have been accounted for.'),
 ('County phone directory corrections announced', 'The new telephone directory includes a listing for the old water office. The number was disconnected several years ago.'),
 ('Clock at station platform being checked', 'Maintenance has been asked to inspect a clock that has been running four minutes ahead only on Tuesdays.'),
 ('Public Works retrieves duplicate street marker', 'A second Maple Street sign was found in storage. Officials have not determined when it was installed.'),
 ('Broadcast music briefly changed overnight', 'The station received calls about an unfamiliar instrumental during the midnight sign-off. A recording was not retained.'),
]

def initial_state():
    return {
      'schema_version': 2, 'town': 'Briar Glen', 'county': 'Morrow County',
      'station': 'WMRW CHANNEL 8', 'broadcast_day': 0, 'fictional_start_date': START_DATE,
      'seed': 81381996, 'surreal_chance': .17, 'weather': {'condition':'cloudy', 'temperature_f':46},
      'residents': deepcopy(INITIAL_RESIDENTS), 'businesses':deepcopy(INITIAL_BUSINESSES),
      'town_flags': {'bridge_closed': False}, 'mundane_last_used':{},'business_last_mentioned':{},
      'threads':{}, 'threads_completed':[], 'last_thread_day':-5,
      'history':[], 'metadata':{'origin':'Briar Glen prototype; entirely fictional'},
    }

def upgrade_state(raw):
    """Upgrade previous five-day prototype without losing station identity/day."""
    state = initial_state()
    for k in ('town','county','station','broadcast_day','seed','surreal_chance','fictional_start_date'):
        if k in raw: state[k]=raw[k]
    if raw.get('schema_version') == 2:
        for k in ('weather','residents','businesses','threads','threads_completed',
                  'last_thread_day','history','metadata','town_flags','mundane_last_used','business_last_mentioned'):
            if k in raw: state[k]=raw[k]
    # One-time subtle tonal upgrade for pre-existing v2 saves, without changing custom settings.
    if not state.get('metadata', {}).get('tone_upgrade_v2'):
        if float(state.get('surreal_chance', 0)) == .16:
            state['surreal_chance'] = .17
        state.setdefault('metadata', {})['tone_upgrade_v2'] = True
    return state

def evt(day, headline, text, category='community', weird=False, thread=None):
    return {'day':day,'headline':headline,'text':text,'category':category,'surreal':weird,'thread':thread}

def maybe_thread(state, day, rng):
    active = [(name, x) for name,x in state['threads'].items() if not x['done']]
    if not active and day - state.get('last_thread_day',-5) >= 3:
        available = [x for x in THREADS if x not in state['threads']]
        # Only one mystery at a time; start a new one after some ordinary days.
        if available and rng.random() < .45:
            name = rng.choice(available)
            state['threads'][name] = {'stage':0,'due_day':day,'done':False,'last_day':0}
            active = [(name,state['threads'][name])]
    if not active: return None
    name, thread = active[0]
    if day < thread['due_day']: return None
    stages = THREADS[name]['stages']
    stage = thread['stage']
    if stage >= len(stages):
        thread['done']=True
        return None
    title, description = stages[stage]
    thread['stage'] += 1
    thread['last_day'] = day
    thread['due_day'] = day + rng.randint(2,5)
    state['last_thread_day'] = day
    if thread['stage'] >= len(stages):
        thread['done'] = True
        state['threads_completed'].append(name)
    return evt(day,title,description,'county',weird=(stage>=1),thread=name)

def business_activity(state, day, rng):
    # Persist business closures and reopening dates; reports reflect actual status.
    possible=[x for x in NEW_SHOPS if x[0] not in state['businesses']]
    if day>15 and day % 23 == 0 and possible:
        key,name=rng.choice(possible)
        state['businesses'][key]={'name':name,'owner':None,'status':'open','reopen_day':0}
        return evt(day,f'{name} opens downtown',
                   f'A new business called {name} has opened in a vacant storefront near Main Street. Opening hours are posted in the front window.','business')
    closed = [(k,v) for k,v in state['businesses'].items() if v['status']=='temporary_closed']
    for key, b in closed:
        if day >= b['reopen_day']:
            b['status']='open'
            return evt(day,f'{b["name"]} reopens',f'{b["name"]} has reopened after a short period of repairs and is operating on regular hours.','business')
    open_items=[(key,b) for key,b in state['businesses'].items() if b['status']=='open']
    if open_items and day > 3 and rng.random() < .09:
        key,b = rng.choice(open_items)
        b['status']='temporary_closed'; b['reopen_day']=day + rng.randint(2,5)
        return evt(day,f'{b["name"]} closes briefly for repairs',
                   f'{b["name"]} will be closed for several days while its front entrance is repaired. Employees expect to reopen shortly.', 'business')
    if open_items:
        candidates=[(k,b) for k,b in open_items if day-state['business_last_mentioned'].get(k,-99)>=3]
        key,b=rng.choice(candidates or open_items)
        state['business_last_mentioned'][key]=day
        headlines = [
           (f'{b["name"]} extends Saturday opening',f'{b["name"]} will offer extended Saturday hours throughout the month.'),
           (f'{b["name"]} seeks weekend staff',f'{b["name"]} is accepting applications for part-time weekend help.'),
           (f'{b["name"]} joins county fair',f'{b["name"]} will sponsor a table at the next county fair.'),
           (f'{b["name"]} replaces store sign',f'{b["name"]} has installed a new sign near its entrance.'),
        ]
        h,body=rng.choice(headlines)
        return evt(day,h,body,'business')
    return evt(day,'Community commerce update','The Chamber of Commerce will hold a meeting next Wednesday evening.','business')

def resident_activity(state, day, rng):
    residents = state['residents']
    # Very occasional permanent arrivals/departures create long-lived change.
    possible=[x for x in NEW_ARRIVALS if x[0] not in residents]
    if day > 6 and day % 11 == 0 and possible:
        key,name,job=rng.choice(possible)
        residents[key]={'name':name,'job':job,'status':'home','away_until':0,'mentions':0}
        return evt(day,f'{name} settles in Briar Glen',
                   f'{name}, a {job.lower()}, has moved into a home on the west side of town. Neighbors are planning a small welcome gathering.','people')
    eligible_longtime=[r for r in residents.values() if r['status']=='home' and r['mentions']>=2]
    if day > 35 and len([r for r in residents.values() if r['status']=='home'])>7 and rng.random()<.025 and eligible_longtime:
        r=rng.choice(eligible_longtime);r['status']='moved'
        return evt(day,f'{r["name"]} leaves Briar Glen',
                   f'{r["name"]} has moved out of town to be nearer to family. A farewell gathering was held at the recreation center.','people')
    for r in residents.values():
        if r['status']=='away' and day >= r['away_until']:
            r['status']='home'
            return evt(day, f'{r["name"]} returns from family visit', f'{r["name"]} has returned to Briar Glen following a brief visit with relatives.', 'people')
    eligible = [r for r in residents.values() if r['status']=='home']
    if day > 5 and eligible and rng.random() < .09:
        r = rng.choice(eligible)
        r['status']='away'; r['away_until'] = day + rng.randint(3,6)
        return evt(day, f'{r["name"]} visiting relatives', f'{r["name"]} will be away from town for several days to visit family.', 'people')
    r = rng.choice(eligible or list(residents.values()))
    r['mentions'] += 1
    action = rng.choice([
       'will help organize the annual neighborhood cleanup',
       'has volunteered to sort records at the historical society',
       'is assisting with preparations for the county fair',
       'will speak briefly at the next recreation hall meeting',
       'has offered to lend supplies to the community garden',
    ])
    return evt(day,f'Community volunteer: {r["name"]}',f'{r["name"]}, a local {r["job"].lower()}, {action}.','people')

def weather_update(state, day, rng, focus):
    prev = state['weather']['condition']
    current = rng.choice(WEATHER_TRANSITIONS.get(prev, WEATHER_TRANSITIONS['cloudy']))
    last = int(state['weather']['temperature_f'])
    temp = max(28,min(84,last + rng.randint(-4,4)))
    state['weather'] = {'condition':current,'temperature_f':temp}
    label, forecast = WEATHER[current]
    # The majority of weather forecasts stay ordinary. Rare cross-program context.
    footnote = ''
    if focus and focus['thread']=='reservoir' and current in ('fog','cloudy'):
        footnote = 'A low-lying cloud has been reported above the reservoir. This has not affected the main forecast.'
    elif focus and focus['thread']=='orchard' and rng.random()<.35:
        footnote = 'Conditions around the western orchards are expected to remain similar.'
    elif rng.random() < .05:
        footnote = rng.choice([
            'The eastern gauge submitted two identical readings. This does not affect the forecast.',
            'A late observation from the old water office has been excluded from tonight’s report.',
            'The county has not requested a correction to the published sunrise time.',
        ])
    return {'condition':current,'label':label,'temp_f':temp,'forecast':forecast,'footnote':footnote}

def make_swap(state, day, rng, focus):
    residents=[r for r in state['residents'].values() if r['status']=='home']
    seller = rng.choice(residents or list(state['residents'].values()))['name']
    action=rng.choice(SWAP_ACTIONS)
    item=rng.choice(SWAP_OBJECTS)
    notes = rng.choice(['Please call after six.','Pickup is available on Saturdays.',
                        'Contact the station for details.','Delivery is not available.',
                        'The seller prefers written inquiries.'])
    listing=f'{action}: {item}. Listing placed by {seller}. {notes}'
    if focus and focus['thread'] and rng.random()<.60:
        listing=rng.choice(THREADS[focus['thread']]['swap'])
    return listing

def make_call(state, day, rng, focus, routine):
    residents=[r for r in state['residents'].values() if r['status']=='home']
    caller=rng.choice(residents or list(state['residents'].values()))['name']
    if focus and focus['thread'] and rng.random()<.75:
        message=THREADS[focus['thread']]['call']
    else:
        message=rng.choice([
         'Are they still accepting pies for the county fair? I could not find the form.',
         'Somebody left a bicycle by the garden club shed. Should I take it to the police station?',
         'The sign near the post office has the old Saturday hours on it.',
         'I would like to know whether the bus service is running on the holiday.',
         'There was a strange humming from the telephone after the weather report. It might have been my radio.',
        ])
    response=rng.choice([
       'Thank you for calling. We will pass that along to the appropriate office.',
       'Our understanding is that the county is already looking into it.',
       'That information should be available at the library tomorrow.',
       'We cannot confirm that report, but we appreciate the call.',
    ])
    return {'caller':caller,'caller_text':message, 'host_text':response}

def advance(state):
    """Advance exactly one day. Caller persists returned state to disk."""
    day = int(state['broadcast_day'])+1
    rng = random.Random(int(state['seed']) + day*7919)
    state['broadcast_day']=day
    air_date=(date.fromisoformat(state['fictional_start_date'])+timedelta(days=day-1)).isoformat()
    story=maybe_thread(state,day,rng)
    business=business_activity(state,day,rng)
    citizen=resident_activity(state,day,rng)
    options=[(title,body) for title,body in MUNDANE_EVENTS
             if day - state['mundane_last_used'].get(title,-99) >= 21]
    ordinary_headline,ordinary_text=rng.choice(options or MUNDANE_EVENTS)
    state['mundane_last_used'][ordinary_headline]=day
    community=evt(day,ordinary_headline,ordinary_text,'community')
    events=[business,citizen,community]
    if story: events.insert(0,story)
    elif rng.random() < float(state['surreal_chance']):
        title,body=rng.choice(LOW_STAKE_ODDITIES)
        events.append(evt(day,title,body,'county',weird=True))
    rng.shuffle(events)  # mixed tone; news chooses priority separately
    focus=story or next((e for e in events if e['surreal']),None)
    weather=weather_update(state,day,rng,focus)
    swap=make_swap(state,day,rng,focus)
    call=make_call(state,day,rng,focus,business)
    # Always retain named references so future shows can look up their history.
    state['history'].extend(events)
    state['history']=state['history'][-800:]
    return {'day':day,'air_date':air_date,'events':events,'focus':focus,'weather':weather,
            'swap':swap,'call':call,'threads_active':[name for name,t in state['threads'].items() if not t['done']],
            'threads_completed':list(state['threads_completed']),
            'businesses_closed':[b['name'] for b in state['businesses'].values() if b['status']!='open']}

def write_scripts(state, daily):
    town=state['town']; day=daily['day']; rng=random.Random(int(state['seed'])+day*1151)
    events=daily['events']
    ordered=sorted(events,key=lambda e:(e['thread'] is None, e['surreal'],e['category']!='business'))
    first=ordered[0]; second=ordered[1]
    # A low-stakes oddity should occasionally reach the airwaves, usually as
    # the SECOND story, while ordinary local news still leads the broadcast.
    odd=next((e for e in events if e['surreal'] and not e['thread']),None)
    if odd and first['thread'] is None:
        second=odd
    news=(f'Good evening, this is the {state["county"]} Evening News. '
          f'{first["text"]} {second["text"]} '
          'For other community notices, consult the noticeboard at the public library. Good night.')
    wx=daily['weather']
    weather=f'Good evening. This is the {state["county"]} Weather Service. The temperature is {wx["temp_f"]} degrees. Tonight, {wx["label"]}. {wx["forecast"]} '
    if wx['footnote']: weather += wx['footnote']+' '
    weather+='This concludes the forecast.'
    swap=f'Welcome to County Swap Shop. {daily["swap"]} Contact the station if you wish to place a listing. Good evening.'
    call=daily['call']
    nline=[('host','Good evening. You are listening to the Night Line. We have a caller on the line.'),
           ('caller',f'Hello. My name is {call["caller"]}. {call["caller_text"]}'),
           ('host',call['host_text']+' That is all the time we have tonight. Good evening.')]
    return [
      {'name':'News','narration':news,'display':first['headline'],'second':second['headline'],'events':[first['headline'],second['headline']]},
      {'name':'Weather','narration':weather,'display':wx['label'],'second':wx['forecast'],'events':[wx['label']]},
      {'name':'Swap Shop','narration':swap,'display':daily['swap'],'second':'County classifieds','events':[daily['swap']]},
      {'name':'Night Line','segments':nline,'narration':' '.join(t for _,t in nline),'display':call['caller_text'], 'second':call['caller'],'events':[call['caller_text']]},
    ]
