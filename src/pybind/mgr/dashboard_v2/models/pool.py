import sys

from ..models.send_command_api import SendCommandApiMixin
from .nodb import NodbModel, NodbManager, IntegerField, CharField, BooleanField, FloatField,\
    JsonField, bulk_attribute_setter


class CephPool(NodbModel, SendCommandApiMixin):
    """Represents a Ceph pool."""

    id = IntegerField(primary_key=True, editable=False)
    name = CharField()
    type = CharField(choices=[('replicated', 'replicated'), ('erasure', 'erasure')], blank=True)
    # TODO: Replace with CephErasureCodeProfile reference
    erasure_code_profile = IntegerField(null=True, default=None, blank=True)
    last_change = IntegerField(editable=False, blank=True)
    quota_max_objects = IntegerField(blank=True)
    quota_max_bytes = IntegerField(blank=True)
    pg_num = IntegerField(blank=True)
    pgp_num = IntegerField(editable=False, blank=True)
    size = IntegerField(help_text='Replica size', blank=True, null=True, editable=True)
    min_size = IntegerField(help_text='Replica size', blank=True, null=True, editable=True)
    crush_rule = IntegerField(blank=True)
    crash_replay_interval = IntegerField(blank=True)
    max_avail = IntegerField(editable=False, blank=True)
    kb_used = IntegerField(editable=False, blank=True)
    percent_used = FloatField(editable=False, blank=True, default=None)
    stripe_width = IntegerField(editable=False, blank=True)
    cache_mode = CharField(choices=[(c, c) for c in 'none|writeback|forward|readonly|readforward|'
                                                    'readproxy'.split('|')], blank=True)
    # TODO: Replace with CephPool reference
    tier_of = IntegerField(null=True, default=None, blank=True)
    # TODO: Replace with CephPool reference
    write_tier = IntegerField(null=True, default=None, blank=True)
    # TODO: Replace with CephPool reference
    read_tier = IntegerField(null=True, default=None, blank=True)
    target_max_bytes = IntegerField(blank=True)
    hit_set_period = IntegerField(blank=True)
    hit_set_count = IntegerField(blank=True)
    hit_set_params = JsonField(base_type=dict, editable=False, blank=True)
    tiers = JsonField(base_type=list, editable=False, blank=True)
    flags = JsonField(base_type=list, blank=True, default=[])

    _compr_mode_choices = 'force aggressive passive none'.split(' ')
    _compr_algorithm_choices = 'none snappy zlib zstd lz4'.split(' ')
    compression_mode = CharField(default='none', choices=[(x, x) for x in _compr_mode_choices])

    compression_algorithm = CharField(default='none',
                                      choices=[(x, x) for x in _compr_algorithm_choices])
    # TODO: Add validation for value to be between 0 and 1
    compression_required_ratio = FloatField(default=0.0)
    compression_max_blob_size = IntegerField(default=0)
    compression_min_blob_size = IntegerField(default=0)

    pool_snaps = JsonField(base_type=list, editable=False, blank=True)

    application_metadata = JsonField(base_type=dict, default={}, blank=True)

    @staticmethod
    def get_all_objects(api_controller, query):
        """":type api_controller: RESTController"""
        result = []

        osd_map = api_controller.mgr.get('osd_map')

        pool_data = None

        for pool_data in osd_map['pools']:

            if sys.version_info < (3, 0):
                for key, value in pool_data.items():
                    if isinstance(value, long):
                        pool_data[key] = int(value)

            def options(key, default=None):
                opts = pool_data.get('options', {})
                return opts.get(key, default)

            object_data = {
                'id': pool_data['pool'],
                'name': pool_data['pool_name'],
                'type': {1: 'replicated', 3: 'erasure'}[pool_data['type']],  # type is an
                                                                             # undocumented dump of
                # https://github.com/ceph/ceph/blob/289c10c9c79c46f7a29b5d2135e3e4302ac378b0/src/osd/osd_types.h#L1035
                'erasure_code_profile_id':
                    (pool_data['erasure_code_profile'] if 'erasure_code_profile' in pool_data
                     else None),
                'last_change': pool_data['last_change'],
                'min_size': pool_data['min_size'],
                # TODO: 'crash_replay_interval': pool_data['crash_replay_interval'],
                'pg_num': pool_data['pg_num'],
                'size': pool_data['size'],
                'crush_rule': pool_data['crush_rule'],
                # Considered advanced options
                'pgp_num': pool_data['pg_placement_num'],
                'stripe_width': pool_data['stripe_width'],
                'quota_max_bytes': pool_data['quota_max_bytes'],
                'quota_max_objects': pool_data['quota_max_objects'],
                # Cache tiering related
                'cache_mode': pool_data['cache_mode'],
                'tier_of': pool_data['tier_of'] if pool_data['tier_of'] > 0 else None,
                'write_tier': pool_data['write_tier'] if pool_data['write_tier'] > 0 else None,
                'read_tier': pool_data['read_tier'] if pool_data['read_tier'] > 0 else None,
                # Attributes for cache tiering
                'target_max_bytes': pool_data['target_max_bytes'],
                'hit_set_period': pool_data['hit_set_period'],
                'hit_set_count': pool_data['hit_set_count'],
                'hit_set_params': pool_data['hit_set_params'],
                'tiers': pool_data['tiers'],
                'flags': pool_data['flags_names'].split(','),
                'pool_snaps': pool_data['pool_snaps'],
                'compression_mode': options('compression_mode', 'none'),
                'compression_algorithm': options('compression_algorithm', 'none'),
                'compression_required_ratio': options('compression_required_ratio'),
                'compression_max_blob_size': options('compression_max_blob_size'),
                'compression_min_blob_size': options('compression_min_blob_size'),
                'application_metadata': pool_data.get('application_metadata'),
            }

            ceph_pool = CephPool(**CephPool.make_model_args(object_data))

            result.append(ceph_pool)

        return result

    @bulk_attribute_setter(['max_avail', 'kb_used', 'percent_used'])
    def ceph_df(self, pools, field_names):  # pylint: disable=W0613
        context = NodbManager.nodb_context
        df_data = context.mgr.get('df')

        df_per_pool = {}
        for elem in df_data['pools']:
            if 'stats' in elem and 'id' in elem:
                df_per_pool[elem['id']] = elem['stats']

        for pool in pools:
            if pool.id in df_per_pool:
                pool.max_avail = df_per_pool[pool.id]['max_avail']
                pool.kb_used = df_per_pool[pool.id]['kb_used']
                pool.percent_used = df_per_pool[pool.id]['percent_used']
            else:
                pool.max_avail = None
                pool.kb_used = None
                pool.percent_used = None

    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.name
