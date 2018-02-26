# -*- coding: utf-8 -*-
from __future__ import absolute_import

import json
import rbd

from ..tools import ViewCache
from .. import logger


def _get_service_map(mgr, service_name):
    service_map = {}
    for server in mgr.list_servers():
        for service in server['services']:
            if service['type'] == service_name:
                if server['hostname'] not in service_map:
                    service_map[server['hostname']] = {
                        'server': server,
                        'services': []
                    }
                inst_id = service['id']
                metadata = mgr.get_metadata(service_name, inst_id)
                status = mgr.get_daemon_status(service_name, inst_id)
                service_map[server['hostname']]['services'].append({
                    'id': inst_id,
                    'type': service_name,
                    'hostname': server['hostname'],
                    'metadata': metadata,
                    'status': status
                })
    return service_map


def _get_pool_list(mgr, application=None):
    osd_map = mgr.get('osd_map')
    if not application:
        return osd_map['pools']
    return [pool for pool in osd_map['pools']
            if application in pool.get('application_metadata', {})]


def _get_daemons(mgr):
    daemons = []
    for hostname, server in _get_service_map(mgr, 'rbd-mirror').items():
        for service in server['services']:
            id = service['id']  # pylint: disable=W0622
            metadata = service['metadata']
            status = service['status']

            try:
                status = json.loads(status['json'])
            except (ValueError, KeyError) as _:
                status = {}

            instance_id = metadata['instance_id']
            if id == instance_id:
                # new version that supports per-cluster leader elections
                id = metadata['id']

            # extract per-daemon service data and health
            daemon = {
                'id': id,
                'instance_id': instance_id,
                'version': metadata['ceph_version'],
                'server_hostname': hostname,
                'service': service,
                'server': server,
                'metadata': metadata,
                'status': status
            }
            daemon = dict(daemon, **_get_daemon_health(daemon))
            daemons.append(daemon)

    return sorted(daemons, key=lambda k: k['instance_id'])


def _get_daemon_health(daemon):
    health = {
        'health_color': 'info',
        'health': 'Unknown'
    }
    for _, pool_data in daemon['status'].items():  # TODO: simplify
        if (health['health'] != 'error' and
            [k for k, v in pool_data.get('callouts', {}).items()
             if v['level'] == 'error']):
            health = {
                'health_color': 'error',
                'health': 'Error'
            }
        elif (health['health'] != 'error' and
              [k for k, v in pool_data.get('callouts', {}).items()
               if v['level'] == 'warning']):
            health = {
                'health_color': 'warning',
                'health': 'Warning'
            }
        elif health['health_color'] == 'info':
            health = {
                'health_color': 'success',
                'health': 'OK'
            }
    return health


class CephServiceMixin(object):

    @classmethod
    def get_service_map(cls, service_name):
        return _get_service_map(cls.mgr, service_name)

    @classmethod
    def get_service_list(cls, service_name):
        service_map = cls.get_service_map(service_name)
        return [svc for _, svcs in service_map.items() for svc in svcs['services']]

    @classmethod
    def get_service(cls, service_name, service_id):
        for server in cls.mgr.list_servers():
            for service in server['services']:
                if service['type'] == service_name:
                    inst_id = service['id']
                    if inst_id == service_id:
                        metadata = cls.mgr.get_metadata(service_name, inst_id)
                        status = cls.mgr.get_daemon_status(service_name, inst_id)
                        return {
                            'id': inst_id,
                            'type': service_name,
                            'hostname': server['hostname'],
                            'metadata': metadata,
                            'status': status
                        }
        return None

    @classmethod
    def get_pool_list(cls, application=None):
        return _get_pool_list(cls.mgr, application)


class CephDaemonMixin(object):
    @classmethod
    def get_daemons(cls):
        return _get_daemons(cls.mgr)

    @classmethod
    def get_daemon_health(cls, daemon):
        return _get_daemon_health(daemon)


class CephPoolMixin(object):
    @classmethod
    def get_pools(cls, daemons):  # pylint: disable=R0912, R0915
        pool_names = [pool['pool_name'] for pool in _get_pool_list(cls.mgr, 'rbd')]
        pool_stats = {}
        rbdctx = rbd.RBD()
        for pool_name in pool_names:
            logger.debug("Constructing IOCtx %s", pool_name)
            try:
                ioctx = cls.mgr.rados.open_ioctx(pool_name)
            except TypeError:
                logger.exception("Failed to open pool %s", pool_name)
                continue

            mirror_mode = rbd.RBD_MIRROR_MODE_DISABLED
            try:
                mirror_mode = rbdctx.mirror_mode_get(ioctx)
            except:  # noqa pylint: disable=W0702
                logger.exception("Failed to query mirror mode %s", pool_name)

            stats = {}
            if mirror_mode == rbd.RBD_MIRROR_MODE_DISABLED:
                continue
            elif mirror_mode == rbd.RBD_MIRROR_MODE_IMAGE:
                mirror_mode = "image"
            elif mirror_mode == rbd.RBD_MIRROR_MODE_POOL:
                mirror_mode = "pool"
            else:
                mirror_mode = "unknown"
                stats['health_color'] = "warning"
                stats['health'] = "Warning"

            pool_stats[pool_name] = dict(stats, **{
                'mirror_mode': mirror_mode
            })

        for daemon in daemons:
            for _, pool_data in daemon['status'].items():
                stats = pool_stats.get(pool_data['name'], None)
                if stats is None:
                    continue

                if pool_data.get('leader', False):
                    # leader instance stores image counts
                    stats['leader_id'] = daemon['metadata']['instance_id']
                    stats['image_local_count'] = pool_data.get('image_local_count', 0)
                    stats['image_remote_count'] = pool_data.get('image_remote_count', 0)

                if (stats.get('health_color', '') != 'error' and
                        pool_data.get('image_error_count', 0) > 0):
                    stats['health_color'] = 'error'
                    stats['health'] = 'Error'
                elif (stats.get('health_color', '') != 'error' and
                      pool_data.get('image_warning_count', 0) > 0):
                    stats['health_color'] = 'warning'
                    stats['health'] = 'Warning'
                elif stats.get('health', None) is None:
                    stats['health_color'] = 'success'
                    stats['health'] = 'OK'

        for _, stats in pool_stats.items():
            if stats.get('health', None) is None:
                # daemon doesn't know about pool
                stats['health_color'] = 'error'
                stats['health'] = 'Error'
            elif stats.get('leader_id', None) is None:
                # no daemons are managing the pool as leader instance
                stats['health_color'] = 'warning'
                stats['health'] = 'Warning'
        return pool_stats

    @classmethod
    @ViewCache()
    def get_daemons_and_pools(cls):
        daemons = _get_daemons(cls.mgr)
        return {
            'daemons': daemons,
            'pools': cls.get_pools(daemons),
        }
