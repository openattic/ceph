import json
from collections import deque
from contextlib import contextmanager
from errno import EPERM
from functools import reduce

from ..tools import ExternalCommandError, cached_property
from .nodb import NodbManager
from mgr_module import MgrModule, CommandResult


class SendCommandApiMixin(object):

    @cached_property
    def send_command_api(self):
        mgr = NodbManager.nodb_context.mgr  # type: MgrModule

        return SendCommandApi(mgr)


def undoable(func):
    """decorator for undoable actions. See `undo_transaction` for starting a transaction.

    Inspired by http://undo.readthedocs.io/. The decorated method should use the side
    effect of the first value as the "do" step and the side effect after the first element
    as the "undo" step.
    """
    def undo(runner):
        try:
            next(runner)
        except StopIteration:
            pass

    def wrapper(*args, **kwargs):
        self = args[0]
        runner = func(*args, **kwargs)
        ret = next(runner)
        stack = getattr(self, '_undo_stack', None)
        if stack is not None:
            stack.append(lambda: undo(runner))
        return ret
    return wrapper


def logged(func):
    def wrapper(*args, **kwargs):
        retval = None
        try:
            retval = func(*args, **kwargs)
        finally:
            pass
            # logger.debug('{}, {}, {} -> {}'.format(func.__name__, args, kwargs, retval))
        return retval
    return wrapper


@contextmanager
def undo_transaction(undo_context, exception_type=ExternalCommandError, re_raise_exception=False):
    """Context manager for starting a transaction. Use `undoable` decorator for undoable actions.
    :type undo_context: T <= object
    :rtype: T
    """
    if getattr(undo_context, '_undo_stack', None) is not None:
        raise ValueError('Nested transactions are not supported.')
    try:
        undo_context._undo_stack = deque()
        yield undo_context
        try:
            delattr(undo_context, '_undo_stack')
        except AttributeError:
            pass
            # logger.exception('Ignoring Attribute error here.')
    except exception_type as e:
        # logger.exception('Will now undo steps performed.')
        stack = getattr(undo_context, '_undo_stack')
        delattr(undo_context, '_undo_stack')
        for undo_closure in reversed(stack):
            undo_closure()
        if re_raise_exception:
            raise


class SendCommandApi(object):
    """
    API source: https://github.com/ceph/ceph/blob/master/src/mon/MonCommands.h
    """

    def __init__(self, mgr):
        """
        :type mgr: MgrModule
        """
        self.mgr = mgr

    @staticmethod
    def _args_to_argdict(**kwargs):
        return {k: v for (k, v) in kwargs.items() if v is not None}

    def mds_metadata(self, who=None):
        """
        COMMAND("mds metadata name=who,type=CephString,req=false",
        "fetch metadata for mds <who>",
        "mds", "r", "cli,rest")
        """
        return self._call_mon_command('mds metadata',
                                      self._args_to_argdict(who=who))

    def mgr_metadata(self, who=None):
        """
        COMMAND("mgr metadata name=id,type=CephString,req=false",
        "dump metadata for all daemons or a specific daemon",
        "mgr", "r", "cli,rest")
        """
        return self._call_mon_command('mgr metadata',
                                      self._args_to_argdict(who=who))

    def mon_metadata(self, id=None):
        """
        COMMAND("mon metadata name=id,type=CephString,req=false",
        "fetch metadata for mon <id>",
        "mon", "r", "cli,rest")
        """
        return self._call_mon_command('mon metadata',
                                      self._args_to_argdict(id=id))

    def osd_crush_dump(self):
        return self._call_mon_command('osd crush dump')

    @undoable
    def osd_erasure_code_profile_set(self, name, profile=None):
        """
        COMMAND("osd erasure-code-profile set " \
                "name=name,type=CephString,goodchars=[A-Za-z0-9-_.] " \
                "name=profile,type=CephString,n=N,req=false", \
                "create erasure code profile <name> with [<key[=value]> ...] pairs. Add a --force
                at the end to override an existing profile (VERY DANGEROUS)", \
                "osd", "rw", "cli,rest")

        .. example::
            >>> api = SendCommandApi()
            >>> api.osd_erasure_code_profile_set('five-three', ['k=5', 'm=3'])
            >>> api.osd_erasure_code_profile_set('my-rack', ['k=3', 'm=2',
            >>>                                  'ruleset-failure-domain=rack'])

        :param profile: Reverse engineering revealed: this is in fact a list of strings.
        :type profile: list[str]
        """
        yield self._call_mon_command('osd erasure-code-profile set',
                                     self._args_to_argdict(name=name, profile=profile),
                                     output_format='string')
        self.osd_erasure_code_profile_rm(name)

    def osd_erasure_code_profile_get(self, name):
        """
        COMMAND("osd erasure-code-profile get " \
                "name=name,type=CephString,goodchars=[A-Za-z0-9-_.]", \
                "get erasure code profile <name>", \
                "osd", "r", "cli,rest")
        """
        return self._call_mon_command('osd erasure-code-profile get',
                                      self._args_to_argdict(name=name))

    def osd_erasure_code_profile_rm(self, name):
        """
        COMMAND("osd erasure-code-profile rm " \
                "name=name,type=CephString,goodchars=[A-Za-z0-9-_.]", \
                "remove erasure code profile <name>", \
                "osd", "rw", "cli,rest")
        """
        return self._call_mon_command('osd erasure-code-profile rm',
                                      self._args_to_argdict(name=name), output_format='string')

    def osd_erasure_code_profile_ls(self):
        """
        COMMAND("osd erasure-code-profile ls", \
                "list all erasure code profiles", \
                "osd", "r", "cli,rest")
        """
        return self._call_mon_command('osd erasure-code-profile ls')

    @undoable
    def osd_pool_create(self, pool, pg_num, pgp_num, pool_type, erasure_code_profile=None,
                        ruleset=None, expected_num_objects=None):
        """
        COMMAND("osd pool create " \
            "name=pool,type=CephPoolname " \
            "name=pg_num,type=CephInt,range=0 " \
            "name=pgp_num,type=CephInt,range=0,req=false " \
            "name=pool_type,type=CephChoices,strings=replicated|erasure,req=false " \
            "name=erasure_code_profile,type=CephString,req=false,goodchars=[A-Za-z0-9-_.] " \
            "name=ruleset,type=CephString,req=false " \
            "name=expected_num_objects,type=CephInt,req=false", \
            "create pool", "osd", "rw", "cli,rest")

        :param pool: The pool name.
        :type pool: str
        :param pg_num: Number of pgs. pgs per osd should be about 100, independent of the number of
                       pools, as each osd can store pgs of multiple pools.
        :type pg_num: int
        :param pgp_num: *MUST* equal pg_num
        :type pgp_num: int
        :param pool_type: replicated | erasure
        :type pool_type: str
        :param erasure_code_profile: name of the erasure code profile.
            Created by :method:`osd_erasure_code_profile_set`.
        :type erasure_code_profile: str
        :returns: empty string
        :rtype: str
        """
        if pool_type == 'erasure' and not erasure_code_profile:
            raise ExternalCommandError('erasure_code_profile missing')
        yield self._call_mon_command(
            'osd pool create', self._args_to_argdict(pool=pool,
                                                     pg_num=pg_num,
                                                     pgp_num=pgp_num,
                                                     pool_type=pool_type,
                                                     erasure_code_profile=erasure_code_profile,
                                                     ruleset=ruleset,
                                                     expected_num_objects=expected_num_objects),
            output_format='string')
        self.osd_pool_delete(pool, pool, "--yes-i-really-really-mean-it")

    @undoable
    def osd_pool_set(self, pool, var, val, force=None, undo_previous_value=None):
        # TODO: crush_ruleset was renamed to crush_rule in Luminous. Thus add:
        #       >>> if var == 'crush_ruleset' and ceph_version >= luminous:
        #       >>>     var = 'crush_rule'
        """
        COMMAND("osd pool set " \
        "name=pool,type=CephPoolname " \
        "name=var,type=CephChoices,strings=size|min_size|crash_replay_interval|pg_num|pgp_num|
            crush_ruleset|hashpspool|nodelete|nopgchange|nosizechange|write_fadvise_dontneed|
            noscrub|nodeep-scrub|hit_set_type|hit_set_period|hit_set_count|hit_set_fpp|
            use_gmt_hitset|debug_fake_ec_pool|target_max_bytes|target_max_objects|
            cache_target_dirty_ratio|cache_target_dirty_high_ratio|cache_target_full_ratio|
            cache_min_flush_age|cache_min_evict_age|auid|min_read_recency_for_promote|
            min_write_recency_for_promote|fast_read|hit_set_grade_decay_rate|hit_set_search_last_n|
            scrub_min_interval|scrub_max_interval|deep_scrub_interval|recovery_priority|
            recovery_op_priority|scrub_priority " \
        "name=val,type=CephString " \
        "name=force,type=CephChoices,strings=--yes-i-really-mean-it,req=false", \
        "set pool parameter <var> to <val>", "osd", "rw", "cli,rest")

        :param pool: Pool name.
        :type pool: str
        :param var: The key
        :type var: Any
        :return: empty string.
        """
        yield self._call_mon_command(
            'osd pool set', self._args_to_argdict(pool=pool, var=var, val=val, force=force),
            output_format='string')
        self.osd_pool_set(pool, var, undo_previous_value)

    def osd_pool_delete(self, pool, pool2=None, sure=None):
        """
        COMMAND("osd pool delete " \
        "name=pool,type=CephPoolname " \
        "name=pool2,type=CephPoolname,req=false " \
        "name=sure,type=CephChoices,strings=--yes-i-really-really-mean-it,req=false", \
        "delete pool", \
        "osd", "rw", "cli,rest")

        Also handles `mon-allow-pool-delete=false`

        :param pool: Pool name
        :type pool: str | unicode
        :param pool2: Second pool name
        :type pool2: str | unicode
        :param sure: should be "--yes-i-really-really-mean-it"
        :type sure: str
        :return: empty string
        """

        cmd = 'osd pool delete'

        pool_delete_args = self._args_to_argdict(pool=pool, pool2=pool2, sure=sure)

        try:
            return self._call_mon_command(cmd, pool_delete_args, output_format='string')
        except ExternalCommandError as e:
            if e.code != EPERM:
                raise

            if 'mon_allow_pool_delete' not in str(e):
                # logger.info('Expected to find "mon_allow_pool_delete" in ""'.format(str(e)))
                raise

            # logger.info('Executing fallback for mon_allow_pool_delete=false\n{}'.format(str(e)))

            mon_names = [mon['name'] for mon in
                         self._call_mon_command('mon dump')['mons']]  # ['a', 'b', 'c']
            try:
                for mon_name in mon_names:
                    self._call_mon_command('injectargs',
                                           self._args_to_argdict(
                                                    injected_args=['--mon-allow-pool-delete=true']),
                                           output_format='string',
                                           target=mon_name)
                res = self._call_mon_command(cmd, pool_delete_args, output_format='string')
            finally:
                for mon_name in mon_names:
                    self._call_mon_command('injectargs',
                                           self._args_to_argdict(
                                                   injected_args=['--mon-allow-pool-delete=false']),
                                           output_format='string',
                                           target=mon_name)
            return res

    @undoable
    def osd_pool_mksnap(self, pool, snap):
        """
        COMMAND("osd pool mksnap " \
        "name=pool,type=CephPoolname " \
        "name=snap,type=CephString", \
        "make snapshot <snap> in <pool>", "osd", "rw", "cli,rest")
        """
        yield self._call_mon_command('osd pool mksnap', self._args_to_argdict(pool=pool, snap=snap),
                                     output_format='string')
        self.osd_pool_rmsnap(pool, snap)

    def osd_pool_rmsnap(self, pool, snap):
        """
        COMMAND("osd pool rmsnap " \
        "name=pool,type=CephPoolname " \
        "name=snap,type=CephString", \
        "remove snapshot <snap> from <pool>", "osd", "rw", "cli,rest")
        """
        return self._call_mon_command('osd pool rmsnap',
                                      self._args_to_argdict(pool=pool, snap=snap),
                                      output_format='string')

    @undoable
    def osd_pool_application_enable(self, pool, app):
        """COMMAND("osd pool application enable " \
        "name=pool,type=CephPoolname " \
        "name=app,type=CephString,goodchars=[A-Za-z0-9-_.] " \
        "name=force,type=CephChoices,strings=--yes-i-really-mean-it,req=false", \
        "enable use of an application <app> [cephfs,rbd,rgw] on pool <poolname>",
        "osd", "rw", "cli,rest")"""
        yield self._call_mon_command('osd pool application enable', self._args_to_argdict(
            pool=pool, app=app, force='--yes-i-really-mean-it'), output_format='string')
        self.osd_pool_application_disable(pool, app)

    @undoable
    def osd_pool_application_disable(self, pool, app):
        """COMMAND("osd pool application disable " \
        "name=pool,type=CephPoolname " \
        "name=app,type=CephString " \
        "name=force,type=CephChoices,strings=--yes-i-really-mean-it,req=false", \
        "disables use of an application <app> on pool <poolname>",
        "osd", "rw", "cli,rest")"""
        yield self._call_mon_command('osd pool application disable', self._args_to_argdict(
            pool=pool, app=app, force='--yes-i-really-mean-it'), output_format='string')
        self.osd_pool_application_enable(pool, app)

    @undoable
    def osd_tier_add(self, pool, tierpool):
        """
        COMMAND("osd tier add " \
        "name=pool,type=CephPoolname " \
        "name=tierpool,type=CephPoolname " \
        "name=force_nonempty,type=CephChoices,strings=--force-nonempty,req=false",
        "add the tier <tierpool> (the second one) to base pool <pool> (the first one)", \
        "osd", "rw", "cli,rest")

        Modifies the 'tier_of' field of the cachepool

        .. example::
            >>> api = MonApi()
            >>> api.osd_tier_add('storagepool', 'cachepool')
            >>> api.osd_tier_cache_mode('cachepool', 'writeback')
            >>> api.osd_tier_set_overlay('storagepool', 'cachepool')

        .. note:: storagepool is typically of type replicated and cachepool is of type erasure
        """
        yield self._call_mon_command('osd tier add',
                                     self._args_to_argdict(pool=pool, tierpool=tierpool),
                                     output_format='string')
        self.osd_tier_remove(pool, tierpool)

    @undoable
    def osd_tier_remove(self, pool, tierpool):
        """
        COMMAND("osd tier remove " \
        "name=pool,type=CephPoolname " \
        "name=tierpool,type=CephPoolname",
        "remove the tier <tierpool> (the second one) from base pool <pool> (the first one)", \
        "osd", "rw", "cli,rest")

        .. example::
            >>> api = MonApi()
            >>> api.osd_tier_add('storagepool', 'cachepool')
            >>> api.osd_tier_remove('storagepool', 'cachepool')
        """
        yield self._call_mon_command('osd tier remove',
                                     self._args_to_argdict(pool=pool, tierpool=tierpool),
                                     output_format='string')
        self.osd_tier_add(pool, tierpool)

    @undoable
    def osd_tier_cache_mode(self, pool, mode, undo_previous_mode=None):
        """
        COMMAND("osd tier cache-mode " \
        "name=pool,type=CephPoolname " \
        "name=mode,type=CephChoices,strings=none|writeback|forward|readonly|readforward|proxy|
            readproxy " \
        "name=sure,type=CephChoices,strings=--yes-i-really-mean-it,req=false", \
        "specify the caching mode for cache tier <pool>", "osd", "rw", "cli,rest")

        Modifies the  'cache_mode' field  of `osd dump`.

        .. seealso:: method:`osd_tier_add`
        """
        yield self._call_mon_command('osd tier cache-mode',
                                     self._args_to_argdict(pool=pool, mode=mode),
                                     output_format='string')
        self.osd_tier_cache_mode(pool, undo_previous_mode)

    @undoable
    def osd_tier_set_overlay(self, pool, overlaypool):
        """
        COMMAND("osd tier set-overlay " \
        "name=pool,type=CephPoolname " \
        "name=overlaypool,type=CephPoolname", \
        "set the overlay pool for base pool <pool> to be <overlaypool>", "osd", "rw", "cli,rest")

        .. seealso:: method:`osd_tier_add`

        Modifies the `read_tier` field of the storagepool
        """
        yield self._call_mon_command('osd tier set-overlay',
                                     self._args_to_argdict(pool=pool, overlaypool=overlaypool),
                                     output_format='string')
        self.osd_tier_remove_overlay(pool)

    @undoable
    def osd_tier_remove_overlay(self, pool, undo_previous_overlay):
        """
        COMMAND("osd tier remove-overlay " \
        "name=pool,type=CephPoolname ", \
        "remove the overlay pool for base pool <pool>", "osd", "rw", "cli,rest")

        .. seealso:: method:`osd_tier_set_overlay`

        Modifies the `read_tier` field of the storagepool
        """
        yield self._call_mon_command('osd tier remove-overlay', self._args_to_argdict(pool=pool),
                                     output_format='string')
        self.osd_tier_set_overlay(pool, undo_previous_overlay)

    @undoable
    def osd_out(self, name):
        """
        COMMAND("osd out " \
        "name=ids,type=CephString,n=N", \
        "set osd(s) <id> [<id>...] out", "osd", "rw", "cli,rest")
        """
        yield self._call_mon_command('osd out', self._args_to_argdict(name=name),
                                     output_format='string')
        self.osd_in(name)

    @undoable
    def osd_in(self, name):
        """
        COMMAND("osd in " \
        "name=ids,type=CephString,n=N", \
        "set osd(s) <id> [<id>...] in", "osd", "rw", "cli,rest")
        """
        yield self._call_mon_command('osd in', self._args_to_argdict(name=name),
                                     output_format='string')
        self.osd_out(name)

    @undoable
    def osd_set(self, key):
        """
        COMMAND("osd set " \
        "name=key,type=CephChoices,strings=full|pause|noup|nodown|noout|noin|nobackfill|norebalance|
                                           norecover|noscrub|nodeep-scrub|notieragent|sortbitwise|
                                           recovery_deletes|require_jewel_osds|
                                           require_kraken_osds", \
        "set <key>", "osd", "rw", "cli,rest")
        """
        yield self._call_mon_command('osd set', self._args_to_argdict(key=key),
                                     output_format='string')
        self.osd_unset(key)

    @undoable
    def osd_unset(self, key):
        """
        COMMAND("osd unset " \
        "name=key,type=CephChoices,strings=full|pause|noup|nodown|noout|noin|nobackfill|norebalance|
                                           norecover|noscrub|nodeep-scrub|notieragent", \
        "unset <key>", "osd", "rw", "cli,rest")
        """
        yield self._call_mon_command('osd unset', self._args_to_argdict(key=key),
                                     output_format='string')
        self.osd_set(key)

    @undoable
    def osd_crush_reweight(self, name, weight, undo_previous_weight=None):
        """
        COMMAND("osd crush reweight " \
        "name=name,type=CephString,goodchars=[A-Za-z0-9-_.] " \
        "name=weight,type=CephFloat,range=0.0", \
        "change <name>'s weight to <weight> in crush map", \
        "osd", "rw", "cli,rest")
        """
        yield self._call_mon_command('osd crush reweight',
                                     self._args_to_argdict(name=name, weight=weight),
                                     output_format='string')
        self.osd_crush_reweight(name, undo_previous_weight)

    def osd_dump(self):
        """
        COMMAND("osd dump " \
        "name=epoch,type=CephInt,range=0,req=false",
        "print summary of OSD map", "osd", "r", "cli,rest")
        """
        return self._call_mon_command('osd dump')

    def osd_list(self):
        """
        Info about each osd, eg "up" or "down".

        :rtype: list[dict[str, Any]]
        """
        def unique_list_of_dicts(l):
            return reduce(lambda x, y: x if y in x else x + [y], l, [])

        tree = self.osd_tree()
        nodes = tree['nodes']
        if 'stray' in tree:
            nodes += tree['stray']
        for node in nodes:
            if u'depth' in node:
                del node[u'depth']
        nodes = unique_list_of_dicts(nodes)
        return list(unique_list_of_dicts([node for node in nodes if node['type'] == 'osd']))

    def osd_tree(self):
        """Does not return a tree, but a directed graph with multiple roots.

        Possible node types are: pool. zone, root, host, osd

        Note, OSDs may be duplicated in the list, although the u'depth' attribute may differ between
        them.

        ..warning:: does not return the physical structure, but the crushmap, which will differ on
            some clusters. An osd may be physically located on a different host, than it is returned
            by osd tree.
        """
        return self._call_mon_command('osd tree')

    def osd_metadata(self, id=None):
        """
        COMMAND("osd metadata " \
        "name=id,type=CephInt,range=0,req=false", \
        "fetch metadata for osd {id} (default all)", \
        "osd", "r", "cli,rest")

        :type name: int
        :rtype: list[dict] | dict
        """
        return self._call_mon_command('osd metadata', self._args_to_argdict(id=id))

    def osd_scrub(self, who):
        """
        COMMAND("osd scrub " \
        "name=who,type=CephString", \
        "initiate scrub on osd <who>, or use <all|any|*> to scrub all", \
        "osd", "rw", "cli,rest")
        """
        return self._call_mon_command('osd scrub', self._args_to_argdict(who=who),
                                      output_format='string')

    def osd_deep_scrub(self, who):
        """
        COMMAND("osd deep-scrub " \
        "name=who,type=CephString", \
        "initiate deep-scrub on osd <who>, or use <all|any|*> to scrub all", \
        "osd", "rw", "cli,rest")
        """
        return self._call_mon_command('osd deep-scrub', self._args_to_argdict(who=who),
                                      output_format='string')

    def fs_ls(self):
        return self._call_mon_command('fs ls')

    @undoable
    def fs_new(self, fs_name, metadata, data):
        """
        COMMAND("fs new " \
        "name=fs_name,type=CephString " \
        "name=metadata,type=CephString " \
        "name=data,type=CephString ", \
        "make new filesystem using named pools <metadata> and <data>", \
        "fs", "rw", "cli,rest")
        """
        yield self._call_mon_command('fs new', SendCommandApi._args_to_argdict(
            fs_name=fs_name, metadata=metadata, data=data), output_format='string')
        self.fs_rm(fs_name, '--yes-i-really-mean-it')

    def fs_rm(self, fs_name, sure):
        """
        COMMAND("fs rm " \
        "name=fs_name,type=CephString " \
        "name=sure,type=CephChoices,strings=--yes-i-really-mean-it,req=false", \
        "disable the named filesystem", \
        "fs", "rw", "cli,rest")
        """
        return self._call_mon_command('fs rm', self._args_to_argdict(fs_name=fs_name, sure=sure),
                                      output_format='string')

    def pg_dump(self):
        """Also contains OSD statistics"""
        return self._call_mon_command('pg dump')

    def status(self):
        return self._call_mon_command('status')

    def health(self, detail=None):
        """:param detail: 'detail' or None"""
        return self._call_mon_command('health', self._args_to_argdict(detail=detail))

    def time_sync_status(self):
        return self._call_mon_command('time-sync-status')

    def df(self):
        return self._call_mon_command('df', self._args_to_argdict(detail='detail'))

    def _call_mon_command(self, cmd, argdict=None, output_format='json', target=None, timeout=30):
        """Calls a command and returns the result as dict.


        :param cmd: the command
        :type cmd: str
        :param argdict: Additional Command-Parameters
        :type argdict: dict[str, Any]
        :param output_format: Format of the return value
        :type output_format: str
        :return: Return type is json (aka dict) if output_format == 'json' else str.
        :rtype: str | dict[str, Any]

        :raises ExternalCommandError: The command failed with an error code instead of an exception.
        :raises PermissionError: See rados.make_ex
        :raises ObjectNotFound: See rados.make_ex
        :raises IOError: See rados.make_ex
        :raises NoSpace: See rados.make_ex
        :raises ObjectExists: See rados.make_ex
        :raises ObjectBusy: See rados.make_ex
        :raises NoData: See rados.make_ex
        :raises InterruptedOrTimeoutError: See rados.make_ex
        :raises TimedOut: See rados.make_ex
        """

        if type(cmd) is str:
            cmd = {'prefix': cmd}

        assert isinstance(cmd, dict)
        result = CommandResult('dashboard_v2')

        # logger.debug('mod command {}, {}, {}'.format(cmd, argdict, err))
        self.mgr.send_command(result, 'mon', '', json.dumps(dict(cmd,
                              format=output_format,
                              **argdict if argdict is not None else {})), tag='dashboard_v2',
                              taget=target)

        ret, out, err = result.wait()

        if ret == 0:
            if output_format == 'json':
                if out:
                    return json.loads(out)
            return out
        else:
            raise ExternalCommandError(err, cmd, argdict, code=ret)
