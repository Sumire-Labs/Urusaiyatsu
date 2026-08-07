"""Tests for core.utils: inventory mutation, stats, advancement, shop rotation.

Each test runs the real application code in an isolated subprocess (see
``_harness``) so it never touches the real ``data/`` directory, needs no
Discord credentials, and is fully deterministic.
"""

import unittest

from _harness import run_ok


class TestCountValidation(unittest.TestCase):
    def test_non_positive_counts_do_not_mutate(self):
        run_ok('''
_new_user(1)
inv = USERS['1']['inventory']
assert u.add_item(1, 'wood', 0) == -1
assert u.add_item(1, 'wood', -5) == -1
assert u.remove_item(1, 'wood', 0) == {}
assert u.remove_item(1, 'wood', -1) == {}
assert u.remove_item_stacked(1, 'wood', 0) == []
assert u.remove_item_stacked(1, 'wood', -3) == []
assert u.remove_item_from_index(1, 0, 0) == {}
assert u.remove_item_match_meta(1, 'wood', 0) == {}
assert inv == []
''')


class TestAddAndRemoveByIndex(unittest.TestCase):
    def test_add_and_remove_by_index(self):
        run_ok('''
_new_user(1)
u.add_item(1, 'wood', 3)
u.add_item(1, 'stone', 2)
assert [i['id'] for i in USERS['1']['inventory']] == ['wood', 'stone']

# remove 1 from index 0
r = u.remove_item_from_index(1, 0, 1)
assert r['id'] == 'wood' and r['count'] == 1
assert USERS['1']['inventory'][0]['count'] == 2

# remove the rest from index 0 -> element is popped
r = u.remove_item_from_index(1, 0, 2)
assert r['count'] == 2
assert [i['id'] for i in USERS['1']['inventory']] == ['stone']
''')


class TestStackedRemoval(unittest.TestCase):
    def test_required_transactional_no_partial_mutation(self):
        # required=True must not mutate when total stock is insufficient.
        run_ok('''
_new_user(1)
u.add_item(1, 'wood', 3)
u.add_item(1, 'stone', 2)
before = [dict(i) for i in USERS['1']['inventory']]
result = u.remove_item_stacked(1, 'wood', 10, required=True)
assert result == []
assert USERS['1']['inventory'] == before
''')

    def test_required_transactional_success(self):
        run_ok('''
_new_user(1)
u.add_item(1, 'wood', 3)
u.add_item(1, 'stone', 2)
result = u.remove_item_stacked(1, 'wood', 2, required=True)
assert len(result) == 1 and result[0]['count'] == 2
assert USERS['1']['inventory'][0]['count'] == 1
''')

    def test_non_required_adjacent_stacks_not_skipped(self):
        # Two adjacent stacks of the same item (distinct meta) must both be
        # consumed without skipping the second one.
        run_ok('''
_new_user(1)
u.add_item(1, 'wood', 2, meta={'a': 1})
u.add_item(1, 'wood', 2, meta={'b': 1})
assert len(USERS['1']['inventory']) == 2
result = u.remove_item_stacked(1, 'wood', 3)
assert len(result) == 2
assert result[0]['count'] == 2 and result[1]['count'] == 1
# one stack fully consumed, one remains with 1
assert [i['count'] for i in USERS['1']['inventory']] == [1]
''')


class TestAccessoryStats(unittest.TestCase):
    def test_accessory_and_equipment_stats(self):
        run_ok('''
_new_user(1)
ud = USERS['1']
ud['equipment']['accessory'][0] = {'id': 'rest_charm'}   # stamina_regeneration_rate +1
ud['equipment']['accessory'][1] = {'id': 'money_charm'}   # money_bonus +1
ud['equipment']['gathering_tool'] = {'id': 'pickaxe'}     # gathering_power +1
stats = u.get_stats(1)
assert stats['stamina_regeneration_rate'] == 21.0
assert stats['money_bonus'] == 1
assert stats['gathering_power'] == 1
''')


class TestAdvancement(unittest.TestCase):
    def test_initial_only_null_previous_not_reunlocked(self):
        # gather_forest has previous_advancement=[None] -> initial-only.
        run_ok('''
_new_user(1)
ud = USERS['1']
ud['advancement_completed'] = ['gather_forest']
ud['advancement_now'] = ['craft_saw']
msg = u.complete_advancement(1, 'craft_saw')
assert '目標を達成' in msg
assert 'craft_saw' in ud['advancement_completed']
assert 'craft_planks' in ud['advancement_now']
# gather_forest must NOT be re-unlocked (null previous is initial-only)
assert 'gather_forest' not in ud['advancement_now']
''')

    def test_broken_advancement_ref_does_not_crash(self):
        run_ok('''
from core.state import ADVANCEMENTS
_new_user(1)
ud = USERS['1']
ud['advancement_completed'] = ['gather_forest']
ud['advancement_now'] = ['craft_saw']
# Inject an advancement whose previous ref does not exist anywhere.
ADVANCEMENTS['broken_adv'] = {
    'previous_advancement': ['does_not_exist'],
    'title': 'x', 'description': 'y', 'complete_message': 'z',
    'clear_condition': {},
}
msg = u.complete_advancement(1, 'craft_saw')
assert '目標を達成' in msg
# broken ref must not be unlocked and must not raise.
assert 'broken_adv' not in ud['advancement_now']
''')


class TestShopRotation(unittest.TestCase):
    def test_hourly_idempotent_non_overlap(self):
        run_ok('''
from core.state import shop_list
shop_list[:] = [f'item_{i}' for i in range(20)]
_new_user(1)
ud = USERS['1']
ud['level_global'] = 7

# first rotation at wall-clock hour 1000
u.rotate_shop(ud, now=3600 * 1000)
content1 = list(ud['shop_content'])
assert len(content1) == 10
assert ud['last_rotation_hour'] == 1000

# same hour -> idempotent, no re-roll
u.rotate_shop(ud, now=3600 * 1000 + 1800)
assert ud['shop_content'] == content1

# next hour -> re-roll with no overlap against previous content
u.rotate_shop(ud, now=3600 * 1001)
content2 = ud['shop_content']
assert content2 != content1
assert set(content2).isdisjoint(set(content1))
''')

    def test_below_level_7_does_nothing(self):
        run_ok('''
from core.state import shop_list
shop_list[:] = [f'item_{i}' for i in range(20)]
_new_user(1)
ud = USERS['1']
ud['level_global'] = 5
u.rotate_shop(ud, now=3600 * 2000)
assert ud['shop_content'] == []
assert 'last_rotation_hour' not in ud
''')


if __name__ == '__main__':
    unittest.main()
