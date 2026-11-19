"""Tests for the terminal UI helpers flagged in code review."""

import unittest

import omo_tui


class TuiHelperTests(unittest.TestCase):
    def test_menu_capacity_reserves_metadata_rows(self):
        # 24 rows - 5 chrome rows - 9 title rows - 2 metadata rows.
        self.assertEqual(omo_tui.menu_capacity(24, 9), 8)
        self.assertEqual(omo_tui.menu_capacity(10, 2), 1)
        # Header plus metadata plus options never exceeds draw()'s capacity.
        height, header = 24, 9
        capacity = omo_tui.menu_capacity(height, header)
        self.assertLessEqual(header + 2 + capacity, height - 5)

    def test_nested_agents_target_keeps_agents_segment(self):
        nested = {'agents': {'oracle': {'model': 'p/oracle'}}}
        direct = {'oracle': {'model': 'p/oracle'}}
        self.assertEqual(
            omo_tui.preset_agent_target('p', nested, 'oracle'),
            'presets/p/agents/oracle',
        )
        self.assertEqual(
            omo_tui.preset_agent_target('p', direct, 'oracle'),
            'presets/p/oracle',
        )


if __name__ == '__main__':
    unittest.main()
