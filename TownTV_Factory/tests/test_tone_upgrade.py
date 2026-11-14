from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from town_engine import initial_state, upgrade_state, advance

class ToneUpgradeTest(unittest.TestCase):
    def test_previous_town_history_preserved(self):
        state=initial_state();state['surreal_chance']=.16
        for _ in range(10):advance(state)
        history=list(state['history']);day=state['broadcast_day']
        updated=upgrade_state(state)
        self.assertEqual(updated['broadcast_day'],day)
        self.assertEqual(updated['history'],history)
        self.assertAlmostEqual(updated['surreal_chance'],.17)
        self.assertEqual(upgrade_state(updated)['surreal_chance'],.17)
    def test_user_custom_odds_not_reset(self):
        state=initial_state();state['surreal_chance']=.08
        self.assertEqual(upgrade_state(state)['surreal_chance'],.08)

if __name__=='__main__':unittest.main()
