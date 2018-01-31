from unittest import TestCase

import mock

from ..models.pool import CephPool
from ..models.nodb import nodb_context


class CephPoolTestCase(TestCase):

    pool_data = {
        'pools': [{
            'stripe_width': 0,
            'flags_names': 'hashpspool',
            'tier_of': -1,
            'pg_placement_num': 8,
            'quota_max_bytes': 0,
            'size': 3,
            'hit_set_period': 0,
            'pg_num': 8,
            'type': 1,
            'pool_name': 'cephfs_data_a',
            'cache_mode': 'none',
            'min_size': 1,
            'application_metadata': {
                'cephfs': {
                    'data': 'cephfs_a'
                }
            },
            'write_tier': -1,
            'pool': 1,
            'crush_rule': 0,
            'tiers': [],
            'hit_set_params': {
                'type': 'none'
            },
            'pool_snaps': [],
            'quota_max_objects': 0,
            'options': {},
            'hit_set_count': 0,
            'target_max_bytes': 0,
            'last_change': '12',
            'read_tier': -1
        }, {
            'stripe_width': 0,
            'flags_names': 'hashpspool',
            'tier_of': -1,
            'pg_placement_num': 8,
            'quota_max_bytes': 0,
            'size': 3,
            'hit_set_period': 0,
            'pg_num': 8,
            'type': 1,
            'pool_name': 'cephfs_metadata_a',
            'cache_mode': 'none',
            'min_size': 1,
            'application_metadata': {
                'cephfs': {
                    'metadata': 'cephfs_a'
                }
            },
            'write_tier': -1,
            'pool': 2,
            'crush_rule': 0,
            'tiers': [],
            'hit_set_params': {
                'type': 'none'
            },
            'pool_snaps': [],
            'quota_max_objects': 0,
            'options': {},
            'hit_set_count': 0,
            'target_max_bytes': 0,
            'last_change': '12',
            'read_tier': -1
        }]
    }

    def test_all(self):
        api_controller = mock.MagicMock()
        api_controller.mgr.get.return_value = self.pool_data
        with nodb_context(api_controller):
            pools = CephPool.objects.all()
            self.assertEqual(len(pools), 2)
            self.assertEqual(pools[0].name, 'cephfs_data_a')
            self.assertEqual(pools[0].id, 1)
            self.assertEqual(pools[1].name, 'cephfs_metadata_a')
            self.assertEqual(pools[1].id, 2)
