# -*- coding: utf-8 -*-
from __future__ import absolute_import

import json
import re

from functools import partial

import cherrypy
import rbd

from ..services.ceph_service import CephServiceMixin, CephPoolMixin
from ..tools import ApiController, AuthRequired, BaseController, ViewCache
from .. import logger


@ApiController('rbdmirror')
@AuthRequired()
class RbdMirror(BaseController, CephServiceMixin, CephPoolMixin):

    def __init__(self):
        self.pool_data = {}

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def default(self):
        status, content_data = self._get_content_data()
        return {'status': status, 'content_data': content_data}

    @ViewCache()
    def _get_pool_datum(self, pool_name):
        data = {}
        logger.debug("Constructing IOCtx %s", pool_name)
        try:
            ioctx = self.mgr.rados.open_ioctx(pool_name)
        except TypeError:
            logger.exception("Failed to open pool %s", pool_name)
            return None

        mirror_state = {
            'down': {
                'health': 'issue',
                'state_color': 'warning',
                'state': 'Unknown',
                'description': None
            },
            rbd.MIRROR_IMAGE_STATUS_STATE_UNKNOWN: {
                'health': 'issue',
                'state_color': 'warning',
                'state': 'Unknown'
            },
            rbd.MIRROR_IMAGE_STATUS_STATE_ERROR: {
                'health': 'issue',
                'state_color': 'error',
                'state': 'Error'
            },
            rbd.MIRROR_IMAGE_STATUS_STATE_SYNCING: {
                'health': 'syncing'
            },
            rbd.MIRROR_IMAGE_STATUS_STATE_STARTING_REPLAY: {
                'health': 'ok',
                'state_color': 'success',
                'state': 'Starting'
            },
            rbd.MIRROR_IMAGE_STATUS_STATE_REPLAYING: {
                'health': 'ok',
                'state_color': 'success',
                'state': 'Replaying'
            },
            rbd.MIRROR_IMAGE_STATUS_STATE_STOPPING_REPLAY: {
                'health': 'ok',
                'state_color': 'success',
                'state': 'Stopping'
            },
            rbd.MIRROR_IMAGE_STATUS_STATE_STOPPED: {
                'health': 'ok',
                'state_color': 'info',
                'state': 'Primary'
            }
        }

        rbdctx = rbd.RBD()
        try:
            mirror_image_status = rbdctx.mirror_image_status_list(ioctx)
            data['mirror_images'] = sorted([
                dict({
                    'name': image['name'],
                    'description': image['description']
                }, **mirror_state['down' if not image['up'] else image['state']])
                for image in mirror_image_status
            ], key=lambda k: k['name'])
        except rbd.ImageNotFound:
            pass
        except:  # noqa pylint: disable=W0702
            logger.exception("Failed to list mirror image status %s", pool_name)

        return data

    @ViewCache()
    def _get_content_data(self):  # pylint: disable=R0914

        def get_pool_datum(pool_name):
            pool_datum = self.pool_data.get(pool_name, None)
            if pool_datum is None:
                pool_datum = partial(self._get_pool_datum, pool_name)
                self.pool_data[pool_name] = pool_datum

            _, value = pool_datum()
            return value

        pool_names = [pool['pool_name'] for pool in self.get_pool_list('rbd')]
        _, data = self.get_daemons_and_pools(self.mgr)
        if isinstance(data, Exception):
            logger.exception("Failed to get rbd-mirror daemons list")
            raise type(data)(str(data))
        daemons = data.get('daemons', [])
        pool_stats = data.get('pools', {})

        pools = []
        image_error = []
        image_syncing = []
        image_ready = []
        for pool_name in pool_names:
            pool = get_pool_datum(pool_name) or {}
            stats = pool_stats.get(pool_name, {})
            if stats.get('mirror_mode', None) is None:
                continue

            mirror_images = pool.get('mirror_images', [])
            for mirror_image in mirror_images:
                image = {
                    'pool_name': pool_name,
                    'name': mirror_image['name']
                }

                if mirror_image['health'] == 'ok':
                    image.update({
                        'state_color': mirror_image['state_color'],
                        'state': mirror_image['state'],
                        'description': mirror_image['description']
                    })
                    image_ready.append(image)
                elif mirror_image['health'] == 'syncing':
                    p = re.compile("bootstrapping, IMAGE_COPY/COPY_OBJECT (.*)%")
                    image.update({
                        'progress': (p.findall(mirror_image['description']) or [0])[0]
                    })
                    image_syncing.append(image)
                else:
                    image.update({
                        'state_color': mirror_image['state_color'],
                        'state': mirror_image['state'],
                        'description': mirror_image['description']
                    })
                    image_error.append(image)

            pools.append(dict({
                'name': pool_name
            }, **stats))

        return {
            'daemons': daemons,
            'pools': pools,
            'image_error': image_error,
            'image_syncing': image_syncing,
            'image_ready': image_ready
        }
