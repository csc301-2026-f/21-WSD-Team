"""D2 contract checks. These do not prove OS/DB/CORE/UI integration."""
import copy
import importlib
import io
import json
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from backend.algorithms.algo01 import evaluate_raid0_policy, PolicyInputError
from backend.algorithms.algo01.demo import main
from backend.algorithms.common.recommendations import FIELDS
FIXTURES = Path(__file__).parent / 'fixtures'

def payload():
    return json.loads((FIXTURES / 'd2-temp-valid.json').read_text(encoding='utf-8'))

class D2ContractTests(unittest.TestCase):

    def none(self, data, code):
        rows = evaluate_raid0_policy(**data)
        self.assertEqual(len(rows), 1)
        item = rows[0]
        self.assertEqual(set(item), FIELDS)
        self.assertEqual(item['action'], 'none')
        self.assertIsNone(item['file_id'])
        self.assertIsNone(item['source_device_id'])
        self.assertIsNone(item['target_device_id'])
        self.assertFalse(item['requires_approval'])
        self.assertIn(code, item['constraints'])

    def test_positive_uses_only_current_shared_fields(self):
        data = payload()
        self.assertNotIn('is_writable', data['devices'][1])
        self.assertNotIn('input_schema_version', data['realtime'])
        self.assertNotIn('files', data['realtime'])
        self.assertNotIn('verified', data['history']['file_activity'][0])
        rows = evaluate_raid0_policy(**data)
        self.assertEqual(len(rows), 1)
        item = rows[0]
        self.assertEqual(set(item), FIELDS)
        self.assertEqual((item['action'], item['file_id'], item['source_device_id'], item['target_device_id']), ('move', 'sample-video', 'hdd-1', 'ssd-1'))
        self.assertTrue(item['requires_approval'])
        self.assertIsNone(item['estimated_benefit'])
        self.assertIn('unmeasured', item['reason'])

    def test_no_input_mutation_and_repeatability(self):
        data = payload()
        before = copy.deepcopy(data)
        self.assertEqual(evaluate_raid0_policy(**data), evaluate_raid0_policy(**data))
        self.assertEqual(data, before)

    def test_unrelated_bad_row_does_not_change_valid_record_or_id(self):
        data = payload()
        baseline = evaluate_raid0_policy(**data)
        data['history']['file_activity'].extend([{}, None])
        self.assertEqual(evaluate_raid0_policy(**data), baseline)

    def test_time_error_never_returns_a_fake_date(self):
        for value in (None, 'bad', '2026-10-17T12:00:00', '2026-10-17T12:00:00+01:00'):
            with self.subTest(value=value):
                data = payload()
                data['realtime']['evaluation_time_utc'] = value
                with self.assertRaises(PolicyInputError) as caught:
                    evaluate_raid0_policy(**data)
                self.assertEqual(caught.exception.code, 'invalid_evaluation_time')

    def test_none_empty_history(self):
        data = payload()
        data['history'] = {}
        self.none(data, 'missing_file_activity')

    def test_unknown_metrics_are_not_zero(self):
        for key in ('read_ops', 'write_ops'):
            data = payload()
            data['history']['file_activity'][0][key] = None
            self.none(data, 'missing_read_or_write_ops')

    def test_stale_future_and_zero_length_windows(self):
        windows = (('2026-10-17T11:40:00Z', '2026-10-17T11:41:00Z'), ('2026-10-17T12:00:00Z', '2026-10-17T12:01:00Z'), ('2026-10-17T12:00:00Z', '2026-10-17T12:00:00Z'))
        for start, end in windows:
            data = payload()
            data['history']['file_activity'][0].update(window_start_utc=start, window_end_utc=end)
            self.none(data, 'invalid_or_stale_activity_window')

    def test_duplicate_device_identity_is_rejected(self):
        data = payload()
        data['devices'].append(copy.deepcopy(data['devices'][0]))
        self.none(data, 'duplicate_device_id')

    def test_unknown_source_and_cross_host_records(self):
        data = payload()
        data['devices'][0]['host_id'] = 'other-host'
        self.none(data, 'source_unavailable_or_unknown')
        data = payload()
        data['devices'][1]['host_id'] = 'other-host'
        self.none(data, 'no_eligible_ssd')

    def test_existing_ssd_files_are_left_alone(self):
        data = payload()
        data['history']['file_activity'][0]['device_id'] = 'ssd-1'
        self.none(data, 'source_outside_d2_hdd_scope')

    def test_write_heavy_and_inactive_files_are_deferred(self):
        data = payload()
        data['history']['file_activity'][0]['write_ops'] = 200
        self.none(data, 'write_heavy_workload_deferred')
        data['history']['file_activity'][0].update(read_ops=0, write_ops=0)
        self.none(data, 'insufficient_read_activity')

    def test_free_space_and_reserve_are_both_required(self):
        for key, value in (('free_bytes', None), ('free_bytes', 0), ('capacity_bytes', None), ('free_bytes', 30 * 1024 ** 3), ('is_available', False)):
            data = payload()
            data['devices'][1][key] = value
            self.none(data, 'no_eligible_recommendation')

    def test_capacity_is_charged_for_the_whole_batch(self):
        data = payload()
        data['mode_config'] = {'reserve_bytes': 0, 'reserve_fraction': 0}
        data['devices'][1]['free_bytes'] = 6 * 1024 ** 2
        second = copy.deepcopy(data['history']['file_activity'][0])
        second.update(file_id='second-file', path='/mock/hdd-1/second.mp4', read_ops=60)
        data['history']['file_activity'].append(second)
        rows = evaluate_raid0_policy(**data)
        self.assertEqual([row['file_id'] for row in rows], ['sample-video'])

    def test_target_ties_use_device_id_and_input_order_does_not_matter(self):
        data = payload()
        other = copy.deepcopy(data['devices'][1])
        other['device_id'] = 'ssd-0'
        data['devices'].append(other)
        rows = evaluate_raid0_policy(**data)
        self.assertEqual(rows[0]['target_device_id'], 'ssd-0')
        data['devices'].reverse()
        self.assertEqual(rows, evaluate_raid0_policy(**data))

    def test_invalid_config_does_not_silently_activate_v2(self):
        for config, code in (({'min_cost_confidence': 0.8}, 'invalid_config'), ({'goal': 'lifespan'}, 'goal_not_implemented_in_d2'), ({'reserve_fraction': float('nan')}, 'invalid_config'), ({'reserve_bytes': True}, 'invalid_config'), ({'max_recommendations': 0}, 'invalid_config')):
            data = payload()
            data['mode_config'] = config
            self.none(data, code)

    def test_old_entry_import_calls_d2(self):
        from backend.algorithms.algo01.raid0_policy import evaluate_raid0_policy as old_entry
        self.assertEqual(old_entry(**payload()), evaluate_raid0_policy(**payload()))

    def test_only_file_observation_capability_is_required(self):
        for value in (False, None, 1, 'UNSUPPORTED'):
            data = payload()
            data['capabilities']['file_access_metrics'] = value
            self.none(data, 'unsupported_capability')

    def test_advice_does_not_require_file_move_or_pooling(self):
        for value in (False, None):
            data = payload()
            data['capabilities'].update(file_move=value, file_level_pooling=value)
            item = evaluate_raid0_policy(**data)[0]
            self.assertEqual(item['action'], 'move')
            self.assertTrue(item['requires_approval'])
            self.assertIn('file_move_execution_not_confirmed', item['constraints'])
        data = payload()
        data['capabilities'] = {'file_access_metrics': True}
        self.assertEqual(evaluate_raid0_policy(**data)[0]['action'], 'move')

    def test_pooling_false_alone_does_not_change_advice(self):
        data = payload()
        expected = evaluate_raid0_policy(**data)
        data['capabilities']['file_level_pooling'] = False
        self.assertEqual(evaluate_raid0_policy(**data), expected)

    def test_path_can_be_null_or_omitted_when_file_id_is_known(self):
        data = payload()
        expected = evaluate_raid0_policy(**data)
        data['history']['file_activity'][0]['path'] = None
        self.assertEqual(evaluate_raid0_policy(**data), expected)
        del data['history']['file_activity'][0]['path']
        self.assertEqual(evaluate_raid0_policy(**data), expected)

    def test_unknown_file_identity_size_or_source_still_prevents_advice(self):
        for key in ('file_id', 'device_id', 'file_size_bytes', 'source', 'host_id'):
            data = payload()
            data['history']['file_activity'][0][key] = None
            self.none(data, 'incomplete_file_activity')

    def test_core_can_fill_existing_size_field_without_os_extension(self):
        data = payload()
        row = data['history']['file_activity'][0]
        row['file_size_bytes'] = None
        self.none(data, 'incomplete_file_activity')
        row['file_size_bytes'] = 4 * 1024 ** 2
        self.assertEqual(evaluate_raid0_policy(**data)[0]['action'], 'move')
        self.assertNotIn('metadata_verified', row)

    def test_multiple_windows_choose_latest_instead_of_rejecting_the_file(self):
        data = payload()
        expected = evaluate_raid0_policy(**data)
        older = copy.deepcopy(data['history']['file_activity'][0])
        older.update(window_start_utc='2026-10-17T11:58:00Z', window_end_utc='2026-10-17T11:59:00Z', read_ops=6000)
        data['history']['file_activity'].append(older)
        self.assertEqual(evaluate_raid0_policy(**data), expected)
        data['history']['file_activity'].reverse()
        self.assertEqual(evaluate_raid0_policy(**data), expected)

    def test_identical_duplicate_window_does_not_double_count_reads(self):
        data = payload()
        expected = evaluate_raid0_policy(**data)
        data['history']['file_activity'] *= 2
        self.assertEqual(evaluate_raid0_policy(**data), expected)

    def test_overlapping_windows_are_not_added_together(self):
        data = payload()
        expected = evaluate_raid0_policy(**data)
        older = copy.deepcopy(data['history']['file_activity'][0])
        older.update(window_start_utc='2026-10-17T11:58:30Z', window_end_utc='2026-10-17T11:59:30Z', read_ops=9000)
        data['history']['file_activity'].append(older)
        self.assertEqual(evaluate_raid0_policy(**data), expected)

    def test_conflicting_latest_counts_or_window_bounds_are_ambiguous(self):
        for change in ({'read_ops': 240}, {'window_start_utc': '2026-10-17T11:58:00Z'}, {'device_id': 'ssd-1'}, {'file_size_bytes': 8 * 1024 ** 2}):
            data = payload()
            other = copy.deepcopy(data['history']['file_activity'][0])
            other.update(change)
            data['history']['file_activity'].append(other)
            self.none(data, 'conflicting_latest_file_activity')

    def test_latest_write_heavy_window_does_not_fall_back_to_old_hot_reads(self):
        data = payload()
        older = copy.deepcopy(data['history']['file_activity'][0])
        older.update(window_start_utc='2026-10-17T11:58:00Z', window_end_utc='2026-10-17T11:59:00Z')
        data['history']['file_activity'].append(older)
        data['history']['file_activity'][0]['write_ops'] = 1000
        self.none(data, 'write_heavy_workload_deferred')

    def test_latest_ssd_location_does_not_fall_back_to_old_hdd_location(self):
        data = payload()
        older = copy.deepcopy(data['history']['file_activity'][0])
        older.update(window_start_utc='2026-10-17T11:58:00Z', window_end_utc='2026-10-17T11:59:00Z')
        data['history']['file_activity'].append(older)
        data['history']['file_activity'][0]['device_id'] = 'ssd-1'
        self.none(data, 'source_outside_d2_hdd_scope')

    def test_direct_call_marks_mock_without_cli_wrapper(self):
        for label in ('mock', 'mock:history-fixture', 'MOCK:fixture'):
            data = payload()
            data['history']['file_activity'][0]['source'] = label
            item = evaluate_raid0_policy(**data)[0]
            self.assertTrue(item['reason'].startswith('MOCK: '))
            self.assertIn('mock_data_not_real_file_activity', item['constraints'])
            self.assertEqual(set(item), FIELDS)

    def test_mock_no_advice_is_marked_too(self):
        data = payload()
        data['history']['file_activity'][0]['write_ops'] = 1000
        item = evaluate_raid0_policy(**data)[0]
        self.assertEqual(item['action'], 'none')
        self.assertTrue(item['reason'].startswith('MOCK: '))
        self.assertIn('mock_data_not_real_file_activity', item['constraints'])

    def test_real_candidate_is_not_relabelled_by_unrelated_mock_row(self):
        data = payload()
        data['history']['file_activity'][0]['source'] = 'os:file-observation'
        expected = evaluate_raid0_policy(**data)
        self.assertFalse(expected[0]['reason'].startswith('MOCK:'))
        data['history']['file_activity'].append({'source': 'mock:invalid-unrelated-row'})
        self.assertEqual(evaluate_raid0_policy(**data), expected)

    def test_two_targets_sharing_5mib_cannot_receive_two_4mib_files(self):
        data = payload()
        data['mode_config'] = {'reserve_bytes': 0, 'reserve_fraction': 0}
        data['devices'][1]['free_bytes'] = 5 * 1024 ** 2
        alias = copy.deepcopy(data['devices'][1])
        alias['device_id'] = 'ssd-alias'
        data['devices'].append(alias)
        second = copy.deepcopy(data['history']['file_activity'][0])
        second.update(file_id='second-file', read_ops=60)
        data['history']['file_activity'].append(second)
        items = evaluate_raid0_policy(**data)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['file_id'], 'sample-video')
        self.assertIn('d2_single_ssd_target_per_evaluation', items[0]['constraints'])

    def test_entire_batch_uses_one_target_even_if_multiple_ssds_are_independent(self):
        data = payload()
        data['mode_config'] = {'reserve_bytes': 0, 'reserve_fraction': 0}
        data['devices'][1]['free_bytes'] = 8 * 1024 ** 2
        other = copy.deepcopy(data['devices'][1])
        other.update(device_id='ssd-second', free_bytes=7 * 1024 ** 2)
        data['devices'].append(other)
        second = copy.deepcopy(data['history']['file_activity'][0])
        second.update(file_id='second-file', read_ops=60)
        data['history']['file_activity'].append(second)
        items = evaluate_raid0_policy(**data)
        self.assertEqual(len(items), 2)
        self.assertEqual({item['target_device_id'] for item in items}, {'ssd-1'})

    def test_normal_import_paths_are_working_implementations(self):
        from backend.algorithms.algo01.inputs import validate_inputs
        from backend.algorithms.algo01.candidates import collect_candidates
        from backend.algorithms.algo01.selection import select_recommendations
        from backend.algorithms.common import index_devices, build_ssd_budgets, is_integer
        data = payload()
        context = validate_inputs(**data)
        devices = index_devices(data['devices'], context.host, set())
        candidates = collect_candidates(context, devices, set())
        budgets = build_ssd_budgets(devices, 0, 0)
        self.assertTrue(is_integer(4096))
        rows = select_recommendations(candidates, budgets, context, set(), execution_supported=False)
        self.assertEqual(rows[0]['action'], 'move')

    def test_advanced_placeholders_are_not_exported_by_d2(self):
        import backend.algorithms.algo01 as algo01
        import backend.algorithms.common as common
        self.assertFalse(hasattr(algo01, 'evaluate_new_file_placement'))
        self.assertFalse(hasattr(algo01, 'evaluate_raid0_policy_detailed'))
        self.assertFalse(hasattr(common, 'build_device_cost_model'))

class D2DemoTests(unittest.TestCase):

    def test_mock_move_and_none(self):
        for name, action in (('d2-temp-valid.json', 'move'), ('d2-temp-none.json', 'none')):
            stream = io.StringIO()
            with redirect_stdout(stream):
                code = main(['--mock-input', str(FIXTURES / name)])
            self.assertEqual(code, 0)
            value = json.loads(stream.getvalue())
            self.assertFalse(value['storage_actions_executed'])
            self.assertEqual(value['recommendations'][0]['action'], action)

    def test_demo_input_error(self):
        with redirect_stderr(io.StringIO()):
            self.assertEqual(main(['--mock-input', 'does-not-exist.json']), 2)
if __name__ == '__main__':
    unittest.main()
