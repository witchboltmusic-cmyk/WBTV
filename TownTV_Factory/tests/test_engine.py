from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from town_engine import initial_state, advance, write_scripts, THREADS

class TownSimulationTest(unittest.TestCase):
    def test_long_term_continuity(self):
        state=initial_state()
        stages_seen={k:[] for k in THREADS}
        days=[]
        for i in range(120):
            today=advance(state)
            self.assertEqual(today['day'],i+1)
            self.assertEqual(len(write_scripts(state,today)),4)
            self.assertTrue(28<=today['weather']['temp_f']<=84)
            for event in today['events']:
                if event['thread']:
                    stages_seen[event['thread']].append(event['headline'])
            days.append(today)
        self.assertEqual(state['broadcast_day'],120)
        self.assertGreaterEqual(len(state['residents']),9,'new characters should move in')
        self.assertGreaterEqual(len(state['businesses']),6,'new shops should open')
        self.assertGreater(len(state['history']),150)
        for key, stages in stages_seen.items():
            self.assertEqual(len(stages),len(set(stages)),f'{key} repeated a plot beat')
            self.assertLessEqual(len(stages),len(THREADS[key]['stages']))
        self.assertLess(sum(1 for d in days for e in d['events'] if e['surreal']),140)

    def test_deterministic_days(self):
        a,b=initial_state(),initial_state()
        self.assertEqual([advance(a) for _ in range(12)], [advance(b) for _ in range(12)])

    def test_news_avoids_away_callers(self):
        state=initial_state()
        for _ in range(40):
            d=advance(state)
            self.assertTrue(any(r['name']==d['call']['caller'] and r['status']=='home'
                            for r in state['residents'].values()))

if __name__=='__main__':unittest.main()
